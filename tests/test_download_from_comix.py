import os
import shutil

import pytest
from types import SimpleNamespace

import download_from_comix as module
from download_from_comix import (
    download_from_comix,
    find_browser,
    parse_comix_url,
    pick_best_upload,
    pick_best_upload_of_each_chapter,
    select_chapters_in_range,
)
from src.api.comix import ComixAPI
from src.core import downloader
from src.core.models import Chapter, MangaInfo


def make_chapter(chapter_id, number, group="Group", votes=0, official=False):
    return Chapter(chapter_id=chapter_id, number=str(number), group_name=group, votes=votes, official=official)


def test_the_copied_comix_downloader_code_loads():
    from src.utils import nodriver_browser

    assert ComixAPI.extract_manga_code("https://comix.to/title/w25zn-slam-dunk") == "w25zn"
    assert hasattr(nodriver_browser, "BROWSER_EXECUTABLE_PATH")
    assert Chapter(chapter_id=1, number="1").official is False


def test_series_and_chapter_links_are_understood():
    assert parse_comix_url("https://comix.to/title/w25zn-slam-dunk") == ("w25zn", None)
    assert parse_comix_url("https://comix.to/title/w25zn-slam-dunk/") == ("w25zn", None)
    assert parse_comix_url(" https://comix.to/title/699r0-dragon-ball/1994414-chapter-51 ") == ("699r0", 1994414)


@pytest.mark.parametrize(
    "url",
    [
        "https://mangadex.org/title/w25zn-slam-dunk",
        "https://comix.to.evil.com/title/w25zn-slam-dunk",
        "https://comix.to/browse?keyword=slam",
    ],
)
def test_other_links_give_a_clear_error(url):
    with pytest.raises(ValueError, match="comix.to"):
        parse_comix_url(url)


def test_a_chapter_range_keeps_the_chapters_in_it():
    chapters = [make_chapter(i, number) for i, number in enumerate(["1", "2", "2.5", "3", "4", "Oneshot"])]

    assert [c.number for c in select_chapters_in_range(chapters, "2", "3")] == ["2", "2.5", "3"]
    assert [c.number for c in select_chapters_in_range(chapters, "", "2")] == ["1", "2"]
    assert [c.number for c in select_chapters_in_range(chapters, "4", "")] == ["4"]
    # No range: every chapter, even ones without a number.
    assert len(select_chapters_in_range(chapters)) == 6


def test_the_official_upload_is_picked_first_then_the_most_liked_then_the_first():
    first = make_chapter(1, 274, votes=6)
    liked = make_chapter(2, 274, votes=9)
    official = make_chapter(3, 274, "VIZ Media", votes=0, official=True)

    assert pick_best_upload([first, liked, official]) is official
    assert pick_best_upload([first, liked]) is liked
    assert pick_best_upload([make_chapter(4, 1), make_chapter(5, 1)]).chapter_id == 4


def test_each_chapter_is_downloaded_only_once():
    chapters = [
        make_chapter(1, 274, "Tensai Manga Project", votes=6),
        make_chapter(2, 274, None),
        make_chapter(3, 274, "VIZ Media", official=True),
        make_chapter(4, 275, "Tensai Manga Project"),
    ]

    assert [c.chapter_id for c in pick_best_upload_of_each_chapter(chapters)] == [3, 4]


def make_app(tmp_path, name):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("")
    path.chmod(0o755)
    return str(path)


def test_the_first_browser_found_is_used(tmp_path):
    chrome = str(tmp_path / "Google Chrome")
    edge = make_app(tmp_path, "Microsoft Edge")
    chromium = make_app(tmp_path, "Chromium")

    assert find_browser([chrome, edge, chromium]) == edge
    with pytest.raises(RuntimeError, match="needs Google Chrome, Chromium or Microsoft Edge"):
        find_browser([chrome])


def fake_comix(monkeypatch, chapters, chapter_succeeds=True):
    """
    Fakes comix.to and the browser. Returns the chapters that were downloaded.
    """
    downloaded = []

    monkeypatch.setattr(module, "find_browser", lambda: "/Applications/Microsoft Edge.app")
    monkeypatch.setattr(ComixAPI, "get_manga_info", classmethod(lambda cls, code, headless=None: MangaInfo(manga_id=1, hash_id=code, title="Slam Dunk")))
    monkeypatch.setattr(ComixAPI, "get_all_chapters", classmethod(lambda cls, code, headless=None: list(chapters)))

    def fake_download_chapters(self, manga, chapters_to_download, progress, on_chapter_complete=None):
        downloaded.extend(chapters_to_download)
        for chapter in chapters_to_download:
            on_chapter_complete(chapter, chapter_succeeds, "")
        count = len(chapters_to_download)
        return (count, 0) if chapter_succeeds else (0, count)

    monkeypatch.setattr(downloader.MangaDownloader, "download_chapters", fake_download_chapters)
    return downloaded


SLAM_DUNK_CHAPTERS = [
    make_chapter(10, 1, "Tensai Manga Project", votes=3),
    make_chapter(11, 1, "VIZ Media", official=True),
    make_chapter(20, 2, "Tensai Manga Project"),
    make_chapter(30, 3, "Tensai Manga Project"),
]


def test_a_series_link_downloads_the_best_upload_of_each_chapter_in_the_range(monkeypatch, tmp_path):
    downloaded = fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    storage = {"use_start_and_end_chapters": True, "start_chapter": "1", "end_chapter": "2"}

    download_from_comix("https://comix.to/title/w25zn-slam-dunk", str(tmp_path), None, storage)

    assert [c.chapter_id for c in downloaded] == [11, 20]


def test_without_a_range_every_chapter_is_downloaded(monkeypatch, tmp_path):
    downloaded = fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)

    download_from_comix("https://comix.to/title/w25zn-slam-dunk", str(tmp_path), None, {})

    assert [c.chapter_id for c in downloaded] == [11, 20, 30]


def test_a_chapter_link_downloads_only_that_upload(monkeypatch, tmp_path):
    downloaded = fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)

    download_from_comix("https://comix.to/title/w25zn-slam-dunk/10-chapter-1", str(tmp_path), None, {})

    assert [c.chapter_id for c in downloaded] == [10]


def test_a_clear_error_when_every_chapter_failed(monkeypatch, tmp_path):
    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS, chapter_succeeds=False)

    with pytest.raises(RuntimeError, match="No chapters could be downloaded"):
        download_from_comix("https://comix.to/title/w25zn-slam-dunk", str(tmp_path), None, {})


def test_a_clear_error_when_the_range_has_no_chapters(monkeypatch, tmp_path):
    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    storage = {"use_start_and_end_chapters": True, "start_chapter": "50", "end_chapter": "60"}

    with pytest.raises(RuntimeError, match="No chapters of Slam Dunk"):
        download_from_comix("https://comix.to/title/w25zn-slam-dunk", str(tmp_path), None, storage)


@pytest.mark.parametrize(
    "url, expected_site",
    [
        ("https://mangadex.org/title/a1c7c817-4e59-43b7-9365-09675a149a6f", "MangaDex"),
        ("https://comix.to/title/w25zn-slam-dunk", "comix.to"),
        ("https://archive.org/details/hillman-pirates-comics-001", "the Internet Archive"),
        ("https://comicbookclublive.com/2024/10/04/dc-comics-preview-absolute-batman-1", "the web page"),
        # Not really MangaDex, so it's treated as any other web page.
        ("https://mangadex.org.evil.com/title/x", "the web page"),
    ],
)
def test_the_downloader_follows_the_site_of_the_link(url, expected_site):
    from gui_classes.MangaDexDownloaderView import get_downloader

    assert get_downloader(url)[0] == expected_site


@pytest.mark.parametrize("url", ["not a link", "mangadex.org/title/x", "file:///Users/me/page.html"])
def test_text_that_is_not_a_web_link_is_refused_before_anything_starts(url):
    from gui_classes.MangaDexDownloaderView import get_downloader

    with pytest.raises(ValueError, match="Not a web link"):
        get_downloader(url)


def test_the_downloader_tab_downloads_comix_links_with_a_cancel_button(make_gui, tmp_path, monkeypatch):
    from gui_classes import MangaDexDownloaderView
    from tests.fake_gui import fake_event

    downloads = []
    monkeypatch.setattr(
        MangaDexDownloaderView, "download_from_comix", lambda *arguments: downloads.append(arguments)
    )
    gui = make_gui()
    gui.page.client_storage.set("output_directory_mangadex", str(tmp_path))
    tab = gui.MangaDexDownloaderView
    tab.mangadex_url_text_field.value = "https://comix.to/title/w25zn-slam-dunk"
    cancel_shown = []
    monkeypatch.setattr(tab.cancel_button, "update", lambda: cancel_shown.append(tab.cancel_button.visible))

    tab.handle_download(fake_event())

    # The URL, output folder, terminal, settings and the Cancel button, which is shown while it downloads.
    assert len(downloads) == 1 and downloads[0][0] == "https://comix.to/title/w25zn-slam-dunk"
    assert len(downloads[0]) == 5 and downloads[0][4] is tab.cancel_button
    assert cancel_shown[0] is True and tab.cancel_button.visible is False
    assert gui.is_job_running is False


def test_the_download_tab_refuses_text_that_is_not_a_link(make_gui, monkeypatch):
    from tests.fake_gui import fake_event

    gui = make_gui()
    errors = []
    monkeypatch.setattr(gui.terminal_output, "update_terminal_with_error_message", errors.append)
    gui.MangaDexDownloaderView.mangadex_url_text_field.value = "slam dunk"

    gui.MangaDexDownloaderView.handle_download(fake_event())

    assert errors == ["ERROR: Not a web link (it should start with https://): slam dunk"]
    assert gui.is_job_running is False


def test_the_download_tab_saves_a_web_pages_images_in_the_downloads_folder(make_gui, tmp_path, monkeypatch):
    from gui_classes import MangaDexDownloaderView
    from tests.fake_gui import fake_event

    def fake_download_pages_from_url(url, cancel_event=None, min_side=0):
        folder = tmp_path / "temporary" / "Absolute Batman Preview"
        folder.mkdir(parents=True)
        (folder / "001.jpg").write_bytes(b"1")
        return str(folder)

    monkeypatch.setattr(MangaDexDownloaderView, "download_pages_from_url", fake_download_pages_from_url)
    gui = make_gui()
    downloads = tmp_path / "Downloads"
    gui.page.client_storage.set("output_directory_mangadex", str(downloads))
    (downloads / "Absolute Batman Preview").mkdir(parents=True)
    tab = gui.MangaDexDownloaderView
    tab.mangadex_url_text_field.value = "https://comicbookclublive.com/preview"

    tab.handle_download(fake_event())

    # A folder with the same name is kept, and the temporary folder is gone.
    assert (downloads / "Absolute Batman Preview (2)" / "001.jpg").exists()
    assert not (tmp_path / "temporary").exists()
    # Panel-By-Panel starts with what was just downloaded.
    assert gui.MagiPanelByPanelView.pick_input_output_directories_container.input_directory == str(downloads / "Absolute Batman Preview (2)")


@pytest.mark.parametrize(
    "language, manga_type, expected",
    [
        ("ja", "manga", "rtl"),
        ("ko", "manhwa", "webtoon"),
        ("zh", "manhua", "webtoon"),
        ("en", "other", "ltr"),
        ("fr", None, "ltr"),
    ],
)
def test_the_reading_direction_comes_from_the_series(language, manga_type, expected):
    from download_from_comix import get_reading_direction_from_comix

    manga = MangaInfo(title="Series", original_language=language, manga_type=manga_type)
    assert get_reading_direction_from_comix(manga) == expected


def test_each_downloaded_chapter_gets_the_reading_direction(monkeypatch, tmp_path):
    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    monkeypatch.setattr(
        ComixAPI, "get_manga_info",
        classmethod(lambda cls, code, headless=None: MangaInfo(title="Solo Leveling", original_language="ko", manga_type="manhwa")),
    )
    old_chapter = tmp_path / "Other Series" / "Chapter_1"
    old_chapter.mkdir(parents=True)
    fake_download = downloader.MangaDownloader.download_chapters

    def download_and_save_folders(self, manga, chapters, progress, on_chapter_complete=None):
        for chapter in chapters:
            (tmp_path / "Solo Leveling" / f"Chapter_{chapter.number}").mkdir(parents=True)
        return fake_download(self, manga, chapters, progress, on_chapter_complete)

    monkeypatch.setattr(downloader.MangaDownloader, "download_chapters", download_and_save_folders)

    download_from_comix("https://comix.to/title/emqg8-solo-leveling", str(tmp_path), None, {})

    assert (tmp_path / "Solo Leveling" / "Chapter_1" / "reading-direction.txt").read_text() == "webtoon"
    assert (tmp_path / "Solo Leveling" / "Chapter_3" / "reading-direction.txt").read_text() == "webtoon"
    # A series downloaded earlier is left alone.
    assert not (old_chapter / "reading-direction.txt").exists()


def test_the_download_settings_follow_the_site_of_the_link(make_gui):
    from tests.fake_gui import fake_event

    gui = make_gui()
    tab = gui.MangaDexDownloaderView
    settings = tab.settings

    def shown(url):
        tab.mangadex_url_text_field.value = url
        tab.handle_url_change(fake_event())
        return settings.title_text.value, [control for control in settings.inner_content[1:] if control.visible]

    # Before a link is pasted: what can be pasted.
    assert shown("") == ("PASTE A LINK FROM", [settings.sources_list])
    assert shown("slam dunk") == ("PASTE A LINK FROM", [settings.sources_list])
    assert shown("https://mangadex.org/title/319df2e2") == (
        "MANGADEX",
        [settings.language_dropdown, settings.chapter_range, settings.which_upload, settings.replace_checkbox, settings.more_options],
    )
    # One "Download again" checkbox for every site, so it always shows the setting as it is.
    from tests.fake_gui import get_all_controls

    labels = [getattr(control, "value", None) for control in get_all_controls(settings)]
    assert labels.count("Download again even if already downloaded") == 1
    assert shown("https://comix.to/title/w25zn-slam-dunk") == (
        "COMIX.TO", [settings.chapter_range, settings.comix_help, settings.replace_checkbox]
    )
    assert shown("https://archive.org/details/x") == ("INTERNET ARCHIVE", [settings.internet_archive_help, settings.replace_checkbox])
    assert shown("https://example.com/preview") == ("WEB PAGE", [settings.web_page_help, settings.web_page_options, settings.replace_checkbox])


def test_the_group_link_box_only_shows_for_that_choice(make_gui):
    from tests.fake_gui import fake_event

    gui = make_gui()
    settings = gui.MangaDexDownloaderView.settings
    radio_group = next(control for control in settings.which_upload.controls if hasattr(control, "content") and control.__class__.__name__ == "RadioGroup")

    radio_group.value = "group"
    settings.handle_upload_choice_change(fake_event(control=radio_group))
    assert settings.preferred_group_textfield.visible is True
    assert gui.page.client_storage.get("upload_choice") == "group"

    radio_group.value = "newest"
    settings.handle_upload_choice_change(fake_event(control=radio_group))
    assert settings.preferred_group_textfield.visible is False


def get_status(gui):
    panel = gui.terminal_output.progress_panel
    return panel.state, panel.title_text.value


def test_the_download_tab_locks_the_link_while_downloading_and_shows_the_result(make_gui, tmp_path, monkeypatch):
    from gui_classes import MangaDexDownloaderView
    from tests.fake_gui import fake_event

    gui = make_gui()
    gui.page.client_storage.set("output_directory_mangadex", str(tmp_path))
    tab = gui.MangaDexDownloaderView
    seen_during_download = {}

    def fake_download(url, output_directory, terminal_output_list_view, storage, cancel_button):
        seen_during_download.update(
            link_disabled=tab.mangadex_url_text_field.disabled,
            download_shown=tab.download_button.visible,
            cancel_shown=tab.cancel_button.visible,
            job_running=gui.is_job_running,
            state=get_status(gui)[0],
        )
        return "Downloaded Absolute Batman chapter 25 · 25 pages"

    monkeypatch.setattr(MangaDexDownloaderView, "download_from_comix", fake_download)
    tab.mangadex_url_text_field.value = "https://comix.to/title/x"

    tab.handle_download(fake_event())

    assert seen_during_download == dict(
        link_disabled=True, download_shown=False, cancel_shown=True, job_running=True, state="running"
    )
    # Afterwards it's all back, and the Status view says what was downloaded.
    assert not tab.mangadex_url_text_field.disabled and tab.download_button.visible and not tab.cancel_button.visible
    assert get_status(gui) == ("finished", "Downloaded Absolute Batman chapter 25 · 25 pages")


def test_a_cancelled_download_is_shown_as_cancelled_not_as_an_error(make_gui, tmp_path, monkeypatch):
    from gui_classes import MangaDexDownloaderView
    from tests.fake_gui import fake_event
    from utils import DownloadCancelled

    def cancelled_download(*arguments):
        raise DownloadCancelled("Download cancelled. 2 chapters already downloaded were kept.")

    monkeypatch.setattr(MangaDexDownloaderView, "download_from_comix", cancelled_download)
    gui = make_gui()
    gui.page.client_storage.set("output_directory_mangadex", str(tmp_path))
    tab = gui.MangaDexDownloaderView
    tab.mangadex_url_text_field.value = "https://comix.to/title/x"

    tab.handle_download(fake_event())

    assert get_status(gui) == ("cancelled", "Download cancelled. 2 chapters already downloaded were kept.")
    assert not tab.mangadex_url_text_field.disabled and gui.is_job_running is False
    # It isn't an error: nothing red in the Raw Output.
    raw_lines = [control.value for control in gui.terminal_output.terminal_output_list_view.controls]
    assert not any("ERROR" in line for line in raw_lines)


def test_a_failed_download_shows_why_in_the_status_view(make_gui, tmp_path, monkeypatch):
    from gui_classes import MangaDexDownloaderView
    from tests.fake_gui import fake_event

    def failing_download(*arguments):
        raise RuntimeError("Downloading from comix.to needs Google Chrome or Microsoft Edge installed.")

    monkeypatch.setattr(MangaDexDownloaderView, "download_from_comix", failing_download)
    gui = make_gui()
    gui.page.client_storage.set("output_directory_mangadex", str(tmp_path))
    tab = gui.MangaDexDownloaderView
    tab.mangadex_url_text_field.value = "https://comix.to/title/x"

    tab.handle_download(fake_event())

    panel = gui.terminal_output.progress_panel
    assert panel.state == "failed"
    assert panel.title_text.value == "Download from comix.to failed."
    assert panel.status_text.value == "Downloading from comix.to needs Google Chrome or Microsoft Edge installed."
    assert not tab.mangadex_url_text_field.disabled


def test_the_comix_progress_shows_the_pages_of_one_chapter(monkeypatch):
    from download_from_comix import ChapterProgressReporter

    reports = []
    monkeypatch.setattr(module, "report_progress", lambda **fields: reports.append(fields))
    progress = ChapterProgressReporter(chapter_count=1)

    all_chapters = progress.add_task("[bold green]Downloading Dragon Ball", total=1)
    chapter = progress.add_task("[cyan]  └─ Chapter 93", total=25)
    for _ in range(3):
        progress.advance(chapter)
    progress.update(chapter, completed=25)
    progress.advance(all_chapters)

    assert reports[0] == dict(chapter=1, chapters=1, unit="pages", detail=None, pages_done=0, pages_total=25)
    assert reports[3] == dict(chapter=1, chapters=1, unit="pages", detail=None, pages_done=3, pages_total=25)


def test_the_comix_progress_counts_chapters_and_the_pages_downloaded_so_far(monkeypatch):
    from download_from_comix import ChapterProgressReporter

    reports = []
    monkeypatch.setattr(module, "report_progress", lambda **fields: reports.append(fields))
    progress = ChapterProgressReporter(chapter_count=3)

    all_chapters = progress.add_task("[bold green]Downloading Slam Dunk", total=3)
    first = progress.add_task("[cyan]  └─ Chapter 1", total=35)
    progress.advance(first)
    progress.advance(first)
    progress.advance(all_chapters)
    progress.advance(progress.add_task("[cyan]  └─ Chapter 2", total=22))

    assert reports[2] == dict(chapter=1, chapters=3, pages_done=None, pages_total=None, detail="2 pages downloaded")
    # The first chapter is done, so the second one is being downloaded.
    assert reports[-1] == dict(chapter=2, chapters=3, pages_done=None, pages_total=None, detail="3 pages downloaded")


def test_cancelling_a_comix_download_keeps_the_chapters_that_were_done(monkeypatch, tmp_path):
    from src.core import downloader
    from utils import DownloadCancelled

    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    stopped = []
    monkeypatch.setattr(downloader, "cancel_downloads", lambda: stopped.append(True))
    cancel_button = SimpleNamespace(on_click=None)

    def download_chapters_and_get_cancelled(self, manga, chapters, progress, on_chapter_complete=None):
        # The user clicks Cancel while the chapters download. Two of them were finished.
        cancel_button.on_click(None)
        return 2, 0

    monkeypatch.setattr(downloader.MangaDownloader, "download_chapters", download_chapters_and_get_cancelled)

    with pytest.raises(DownloadCancelled, match="2 chapters already downloaded were kept"):
        download_from_comix("https://comix.to/title/w25zn-slam-dunk", str(tmp_path), None, {}, cancel_button)

    # Clicking Cancel also stops the downloader's own threads.
    assert stopped == [True]


def fake_chapters_being_downloaded(monkeypatch, output_directory, page_counts):
    """
    Replaces the downloader with one that saves "page_counts" pages for each chapter the way the real one does: it tells the progress object about each page and says when a chapter is done. A chapter folder that's already there is written over.
    """
    from src.core import downloader

    def download_chapters(self, manga, chapters, progress, on_chapter_complete=None):
        progress.add_task("[bold green]Downloading", total=len(chapters))
        for chapter, page_count in zip(chapters, page_counts):
            folder = output_directory / manga.title / chapter.get_safe_folder_name()
            folder.mkdir(parents=True, exist_ok=True)
            task = progress.add_task("[cyan]  └─ chapter", total=page_count)
            for number in range(page_count):
                (folder / f"{number:03d}.webp").write_bytes(b"page")
                progress.advance(task)
            on_chapter_complete(chapter, True, f"Downloaded {chapter.get_display_name()} ({page_count} pages)")
        return len(chapters), 0

    monkeypatch.setattr(downloader.MangaDownloader, "download_chapters", download_chapters)


def test_a_comix_download_is_summed_up_with_the_series_and_chapter(monkeypatch, tmp_path):
    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    fake_chapters_being_downloaded(monkeypatch, tmp_path, [3])

    summary = download_from_comix("https://comix.to/title/w25zn-slam-dunk/10-chapter-1", str(tmp_path), None, {})

    assert summary == "Downloaded Slam Dunk chapter 1 · 3 pages"


def test_several_chapters_are_summed_up_together(monkeypatch, tmp_path):
    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    fake_chapters_being_downloaded(monkeypatch, tmp_path, [35, 22, 20])

    summary = download_from_comix("https://comix.to/title/w25zn-slam-dunk", str(tmp_path), None, {})

    assert summary == "Downloaded Slam Dunk: 3 chapters · 77 pages"


def watch_comix(monkeypatch, tmp_path, page_counts, chapters=SLAM_DUNK_CHAPTERS):
    """
    A fake comix.to that saves "page_counts" pages for each chapter it's asked for. Returns what it was asked for: the chapter lists it was given out and the chapters it downloaded.
    """
    asked = {"chapter lists": 0, "downloaded": []}
    fake_comix(monkeypatch, chapters)
    original = ComixAPI.get_all_chapters.__func__

    def get_all_chapters(cls, code, headless=None):
        asked["chapter lists"] += 1
        return original(cls, code, headless)

    monkeypatch.setattr(ComixAPI, "get_all_chapters", classmethod(get_all_chapters))
    fake_chapters_being_downloaded(monkeypatch, tmp_path, page_counts)
    from src.core import downloader

    real_download_chapters = downloader.MangaDownloader.download_chapters

    def download_chapters(self, manga, chapters_to_download, progress, on_chapter_complete=None):
        asked["downloaded"].extend(chapter.chapter_id for chapter in chapters_to_download)
        return real_download_chapters(self, manga, chapters_to_download, progress, on_chapter_complete)

    monkeypatch.setattr(downloader.MangaDownloader, "download_chapters", download_chapters)
    return asked


CHAPTER_LINK = "https://comix.to/title/w25zn-slam-dunk/10-chapter-1"
SERIES_LINK = "https://comix.to/title/w25zn-slam-dunk"


def test_a_chapter_that_was_already_downloaded_is_not_downloaded_again(monkeypatch, tmp_path):
    asked = watch_comix(monkeypatch, tmp_path, [3])
    download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})
    folder = tmp_path / "Slam Dunk" / "Chapter_1"
    assert (folder / "download-info.json").exists()

    summary = download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})

    assert summary == "Already downloaded: Slam Dunk chapter 1 · 3 pages"
    assert summary.folder == str(folder)
    # No second download, and a link to one chapter didn't even need the chapter list (which can take minutes).
    assert asked["downloaded"] == [10] and asked["chapter lists"] == 1


def test_a_chapter_is_downloaded_again_when_its_folder_was_deleted(monkeypatch, tmp_path):
    asked = watch_comix(monkeypatch, tmp_path, [3])
    download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})
    shutil.rmtree(tmp_path / "Slam Dunk" / "Chapter_1")

    summary = download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})

    assert summary == "Downloaded Slam Dunk chapter 1 · 3 pages"
    assert asked["downloaded"] == [10, 10]


def test_a_chapter_is_downloaded_again_when_pages_were_deleted_from_it(monkeypatch, tmp_path):
    asked = watch_comix(monkeypatch, tmp_path, [3])
    download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})
    (tmp_path / "Slam Dunk" / "Chapter_1" / "001.webp").unlink()

    summary = download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})

    assert summary == "Downloaded Slam Dunk chapter 1 · 3 pages"
    assert asked["downloaded"] == [10, 10]
    # And the reading direction is saved again.
    assert (tmp_path / "Slam Dunk" / "Chapter_1" / "reading-direction.txt").read_text() == "ltr"


def test_a_chapter_is_downloaded_again_when_replacing_is_asked_for(monkeypatch, tmp_path):
    asked = watch_comix(monkeypatch, tmp_path, [3])
    download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})

    summary = download_from_comix(CHAPTER_LINK, str(tmp_path), None, {"replace_existing_manga": True})

    assert summary == "Downloaded Slam Dunk chapter 1 · 3 pages"
    assert asked["downloaded"] == [10, 10]


def test_another_upload_of_the_same_chapter_is_not_mistaken_for_the_one_that_is_there(monkeypatch, tmp_path):
    asked = watch_comix(monkeypatch, tmp_path, [3])
    download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})

    # Chapter 1 by another group: the same folder name, but not the same upload.
    download_from_comix("https://comix.to/title/w25zn-slam-dunk/11-chapter-1", str(tmp_path), None, {})

    assert asked["downloaded"] == [10, 11]


def test_only_the_chapters_of_a_series_that_are_missing_are_downloaded(monkeypatch, tmp_path):
    asked = watch_comix(monkeypatch, tmp_path, [3, 3, 3])
    download_from_comix(SERIES_LINK, str(tmp_path), None, {})
    assert asked["downloaded"] == [11, 20, 30]
    shutil.rmtree(tmp_path / "Slam Dunk" / "Chapter_2")

    summary = download_from_comix(SERIES_LINK, str(tmp_path), None, {})

    # Chapter 2 only (the folders of 1 and 3 are fine).
    assert asked["downloaded"] == [11, 20, 30, 20]
    assert summary == "Downloaded Slam Dunk chapter 2 · 3 pages · 2 more chapters already downloaded"


def test_a_series_that_is_all_downloaded_says_so_without_downloading(monkeypatch, tmp_path):
    asked = watch_comix(monkeypatch, tmp_path, [3, 3, 3])
    download_from_comix(SERIES_LINK, str(tmp_path), None, {})

    summary = download_from_comix(SERIES_LINK, str(tmp_path), None, {})

    assert summary == "Already downloaded: Slam Dunk: 3 chapters · 9 pages"
    assert summary.folder == str(tmp_path / "Slam Dunk")
    assert asked["downloaded"] == [11, 20, 30]


def test_cookies_saved_by_an_earlier_download_are_forgotten_when_a_download_starts(monkeypatch, tmp_path):
    from src.api import comix

    saved_cookies = tmp_path / "cf_cookies.dat"
    saved_cookies.write_text("stale cookies")
    monkeypatch.setattr(comix, "_CANONICAL_COOKIE_FILE", saved_cookies)
    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    seen_when_the_site_is_opened = []
    monkeypatch.setattr(
        ComixAPI, "get_manga_info",
        classmethod(lambda cls, code, headless=None: seen_when_the_site_is_opened.append(saved_cookies.exists()) or MangaInfo(title="Slam Dunk")),
    )

    download_from_comix("https://comix.to/title/w25zn-slam-dunk", str(tmp_path / "out"), None, {})

    assert seen_when_the_site_is_opened == [False]


def test_only_panelyzes_own_cookie_file_is_loaded(monkeypatch, tmp_path):
    from src.api import comix

    monkeypatch.chdir(tmp_path)
    (tmp_path / "cf_cookies.dat").write_text("someone else's file")

    assert comix._cookie_file_candidates() == [comix._CANONICAL_COOKIE_FILE]


def test_the_chapter_list_shows_how_far_it_is(monkeypatch, tmp_path):
    from src.api import comix

    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    reports = []
    monkeypatch.setattr(module, "report_progress", lambda **fields: reports.append(fields.get("detail")))

    def get_all_chapters_one_page_at_a_time(cls, code, headless=None):
        # What the copied code does after each page of the list.
        comix.CHAPTER_LIST_PROGRESS_CALLBACK(1, 20)
        comix.CHAPTER_LIST_PROGRESS_CALLBACK(2, 40)
        return list(SLAM_DUNK_CHAPTERS)

    monkeypatch.setattr(ComixAPI, "get_all_chapters", classmethod(get_all_chapters_one_page_at_a_time))

    download_from_comix("https://comix.to/title/w25zn-slam-dunk", str(tmp_path), None, {})

    assert "Reading the chapter list: page 2 (40 uploads so far)..." in reports
    # It's only wanted for that one call.
    assert comix.CHAPTER_LIST_PROGRESS_CALLBACK is None


def test_the_web_page_options_start_off_and_show_their_size_box_when_turned_on(make_gui):
    from tests.fake_gui import fake_event

    gui = make_gui()
    settings = gui.MangaDexDownloaderView.settings

    # Every image is saved by default.
    assert gui.page.client_storage.get("use_web_page_min_size") is False
    assert not settings.web_page_min_size_textfield.visible

    checkbox = settings.web_page_options.controls[0]
    checkbox.on_checkbox_change(fake_event(data="true"))
    assert gui.page.client_storage.get("use_web_page_min_size") is True
    assert settings.web_page_min_size_textfield.visible
    assert gui.page.client_storage.get("web_page_min_size") == "600"


def test_a_pipeline_download_copies_a_chapter_from_the_download_tabs_folder(monkeypatch, tmp_path):
    library = tmp_path / "library"
    pipeline = tmp_path / "pipeline"
    asked = watch_comix(monkeypatch, library, [3, 3, 3])
    download_from_comix(SERIES_LINK, str(library), None, {})
    assert asked["downloaded"] == [11, 20, 30]
    # The Download tab's folder is the library; the pipeline saves somewhere else.
    monkeypatch.setattr("default_settings.get_output_directory", lambda storage, key: str(library))

    summary = download_from_comix(SERIES_LINK, str(pipeline), None, {"x": 1})

    assert asked["downloaded"] == [11, 20, 30]
    assert summary == "Already downloaded: Slam Dunk: 3 chapters · 9 pages"
    assert len(list((pipeline / "Slam Dunk" / "Chapter_1").glob("*.webp"))) == 3
    assert (library / "Slam Dunk" / "Chapter_1").exists()


def test_a_pipeline_download_copies_one_chapter_from_the_download_tabs_folder(monkeypatch, tmp_path):
    library = tmp_path / "library"
    pipeline = tmp_path / "pipeline"
    asked = watch_comix(monkeypatch, library, [3])
    download_from_comix(CHAPTER_LINK, str(library), None, {})
    monkeypatch.setattr("default_settings.get_output_directory", lambda storage, key: str(library))

    summary = download_from_comix(CHAPTER_LINK, str(pipeline), None, {"x": 1})

    assert asked["downloaded"] == [10]
    assert summary.folder == str(pipeline / "Slam Dunk" / "Chapter_1")
    assert len(list((pipeline / "Slam Dunk" / "Chapter_1").glob("*.webp"))) == 3


def test_a_chapter_downloaded_again_keeps_only_its_new_pages(monkeypatch, tmp_path):
    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    fake_chapters_being_downloaded(monkeypatch, tmp_path, [5])
    download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})
    folder = tmp_path / "Slam Dunk" / "Chapter_1"
    (folder / "notes.txt").write_text("mine")
    # An image the user added: not one of the downloader's pages ("001.webp", ...), so it's never taken for an old page.
    (folder / "my-fan-art.png").write_bytes(b"mine")

    # Downloaded again (here with fewer pages): the old pages that weren't written over go.
    fake_chapters_being_downloaded(monkeypatch, tmp_path, [3])
    download_from_comix(CHAPTER_LINK, str(tmp_path), None, {"replace_existing_manga": True})

    assert sorted(name for name in os.listdir(folder) if name.endswith(".webp")) == ["000.webp", "001.webp", "002.webp"]
    assert (folder / "notes.txt").exists() and (folder / "my-fan-art.png").exists()


def test_a_page_comix_to_serves_as_a_gif_is_saved_as_a_png(monkeypatch, tmp_path):
    from PIL import Image
    from src.core import downloader as copied_downloader

    fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)

    def download_chapters(self, manga, chapters, progress, on_chapter_complete=None):
        progress.add_task("[bold green]Downloading", total=1)
        folder = tmp_path / manga.title / chapters[0].get_safe_folder_name()
        folder.mkdir(parents=True)
        Image.new("RGB", (10, 10), "white").save(folder / "000.jpg")
        Image.new("P", (10, 10)).save(folder / "001.gif")
        on_chapter_complete(chapters[0], True, "Downloaded")
        return 1, 0

    monkeypatch.setattr(copied_downloader.MangaDownloader, "download_chapters", download_chapters)
    download_from_comix(CHAPTER_LINK, str(tmp_path), None, {})

    folder = tmp_path / "Slam Dunk" / "Chapter_1"
    # Every tool reads it, and it's counted, so the chapter isn't downloaded again every time.
    assert sorted(name for name in os.listdir(folder) if name != "download-info.json" and not name.endswith(".txt")) == ["000.jpg", "001.png"]
    assert module.read_download_info(str(folder))["pages"] == 2


def test_a_cancel_clicked_while_the_download_was_starting_still_stops_it(monkeypatch, tmp_path):
    from utils import CANCELLING_TEXT, DownloadCancelled

    downloaded = fake_comix(monkeypatch, SLAM_DUNK_CHAPTERS)
    # The Download tab's own Cancel was clicked before the downloader said what it stops.
    cancel_button = SimpleNamespace(on_click=None, disabled=True, text=CANCELLING_TEXT)

    with pytest.raises(DownloadCancelled):
        download_from_comix(SERIES_LINK, str(tmp_path), None, {}, cancel_button)

    assert downloaded == [] and downloader.is_cancelled()
    downloader.reset_downloads()


def test_the_copied_downloader_keeps_a_cancel_from_just_before_it_starts(monkeypatch):
    from src.api import comix

    fetched = []
    # The browser that would load each chapter's pages.
    monkeypatch.setattr(comix, "ChapterReaderService", lambda headless: SimpleNamespace(close=lambda: None, fetch=lambda *args: fetched.append(args)))
    monkeypatch.setattr(comix.ComixAPI, "get_chapter_image_report", classmethod(lambda cls, *args, **kwargs: fetched.append(args)))
    downloader.cancel_downloads()
    try:
        result = downloader.MangaDownloader(downloader.DownloadConfig()).download_chapters(
            MangaInfo(title="Slam Dunk"), [make_chapter(10, 1)], module.ChapterProgressReporter(1)
        )
    finally:
        downloader.reset_downloads()

    assert result == (0, 0)
    # No chapter's pages were loaded.
    assert fetched == []


def test_a_chapter_number_from_a_link_cannot_name_another_folder():
    assert "/" not in Chapter(chapter_id=1, number="1/../../Documents").get_safe_folder_name()
    assert Chapter(chapter_id=1, number="12.5", title="Sakuragi").get_safe_folder_name() == "Chapter_12.5_Sakuragi"


def test_a_start_or_end_chapter_that_is_not_a_number_gives_a_clear_error():
    with pytest.raises(ValueError, match="must be numbers"):
        select_chapters_in_range(SLAM_DUNK_CHAPTERS, "one", "3")


def test_the_download_tab_downloads_a_link_pasted_with_spaces_around_it(make_gui, tmp_path, monkeypatch):
    from gui_classes import MangaDexDownloaderView
    from tests.fake_gui import fake_event

    gui = make_gui()
    gui.page.client_storage.set("output_directory_mangadex", str(tmp_path))
    links = []
    monkeypatch.setattr(MangaDexDownloaderView, "download_from_comix", lambda url, *args: links.append(url) or "Done")
    gui.MangaDexDownloaderView.mangadex_url_text_field.value = "  https://comix.to/title/w25zn-slam-dunk \n"

    gui.MangaDexDownloaderView.handle_download(fake_event())

    assert links == ["https://comix.to/title/w25zn-slam-dunk"]


def test_shortened_like_counts_are_read_as_the_full_number():
    from src.api.comix import parse_count

    assert [parse_count(text) for text in ("37", "1,234", "1.2k", "10K", "1M", "", None)] == [37, 1234, 1200, 10000, 1_000_000, 0, 0]
