import os
import sys
import time
from types import SimpleNamespace

import pytest
import requests

import download_from_mangadex
from default_settings import DEFAULT_SETTINGS
from download_from_mangadex import (
    CHAPTER_FOLDER_NAME_WITH_TITLE,
    get_additional_terminal_options,
    get_chapter_folders,
    get_download_folder,
    get_reading_direction_from_manga,
    get_reading_direction_from_mangadex,
    get_tidy_chapter_folder_name,
    save_reading_direction,
)
from utils import READING_DIRECTION_FILE_NAME, DownloadSummary
from tests.fake_gui import FakeClientStorage


def get_storage(**settings):
    storage = FakeClientStorage()
    storage.values.update(DEFAULT_SETTINGS)
    storage.values.update(settings)
    return storage


def test_chapter_titles_are_in_the_chapter_folder_names_by_default():
    options = get_additional_terminal_options(get_storage())

    assert (
        options[options.index("--filename-chapter") + 1]
        == "{chapter.simple_name} - {chapter.title}"
    )
    assert CHAPTER_FOLDER_NAME_WITH_TITLE == "{chapter.simple_name} - {chapter.title}"


def test_chapter_titles_can_be_left_out_of_the_folder_names():
    options = get_additional_terminal_options(get_storage(use_chapter_title=False))

    assert "--filename-chapter" not in options


def test_by_default_the_newest_upload_of_each_chapter_is_downloaded():
    options = get_additional_terminal_options(get_storage())

    assert "--group" not in options
    assert "--order" not in options


def test_a_preferred_group_is_used_when_it_uploaded_the_chapter():
    group = "https://mangadex.org/group/4f1de6a2-f0c5-4ac5-bce5-02c7dbb67deb/mangaplus"
    options = get_additional_terminal_options(
        get_storage(upload_choice="group", preferred_group=f"  {group} ")
    )

    # Another group's upload is used for the chapters that group skipped.
    assert options[options.index("--group") : options.index("--group") + 4] == [
        "--group",
        group,
        "--group-nomatch-behaviour",
        "fallback",
    ]


def test_the_first_upload_can_be_used_instead_of_the_newest():
    options = get_additional_terminal_options(get_storage(upload_choice="first"))

    assert options[options.index("--order") + 1] == "oldest"


def test_a_group_link_is_only_used_when_that_choice_is_picked():
    options = get_additional_terminal_options(
        get_storage(
            upload_choice="newest", preferred_group="https://mangadex.org/group/x"
        )
    )

    assert "--group" not in options


@pytest.mark.parametrize(
    "setting, option",
    [
        ("no_group_name", "--no-group-name"),
        ("no_oneshot_chapters", "--no-oneshot-chapter"),
        ("use_chapter_cover", "--use-chapter-cover"),
        ("use_volume_cover", "--use-volume-cover"),
        ("replace_existing_manga", "--replace"),
    ],
)
def test_each_download_checkbox_gives_its_downloader_option(setting, option):
    assert option in get_additional_terminal_options(get_storage(**{setting: True}))
    assert option not in get_additional_terminal_options(
        get_storage(**{setting: False})
    )


@pytest.mark.parametrize("use_range", [True, False])
def test_the_chapter_and_page_ranges_are_only_used_when_turned_on(use_range):
    options = get_additional_terminal_options(
        get_storage(
            use_start_and_end_chapters=use_range,
            start_chapter="3",
            end_chapter="5",
            use_start_and_end_pages=use_range,
            start_page="2",
            end_page="10",
        )
    )

    for option, value in (
        ("--start-chapter", "3"),
        ("--end-chapter", "5"),
        ("--start-page", "2"),
        ("--end-page", "10"),
    ):
        if use_range:
            assert options[options.index(option) + 1] == value
        else:
            assert option not in options


def test_the_picked_language_is_downloaded():
    options = get_additional_terminal_options(
        get_storage(language={"name": "Spanish", "code": "es"})
    )

    assert options[options.index("--language") + 1] == "es"


def find_checkbox(root, label):
    from gui_classes.WrappingCheckbox import WrappingCheckbox
    from tests.fake_gui import get_all_controls

    return next(
        control
        for control in get_all_controls(root)
        if isinstance(control, WrappingCheckbox)
        and any(
            getattr(part, "value", None) == label for part in get_all_controls(control)
        )
    )


@pytest.mark.parametrize(
    "label, option",
    [
        ("No Group Name", "--no-group-name"),
        ("No Oneshot Chapters", "--no-oneshot-chapter"),
        ("Use Chapter Cover", "--use-chapter-cover"),
        ("Use Volume Cover", "--use-volume-cover"),
        ("Download again even if already downloaded", "--replace"),
    ],
)
def test_ticking_a_download_checkbox_in_the_tab_adds_its_option(
    make_gui, label, option
):
    from tests.fake_gui import fake_event

    gui = make_gui()
    checkbox = find_checkbox(gui.MangaDexDownloaderView.settings, label)

    assert checkbox.checkbox.on_change is not None
    checkbox.checkbox.on_change(fake_event(data="true"))
    assert option in get_additional_terminal_options(gui.page.client_storage)

    checkbox.checkbox.on_change(fake_event(data="false"))
    assert option not in get_additional_terminal_options(gui.page.client_storage)


def test_picking_a_language_in_the_tab_saves_its_code(make_gui):
    from tests.fake_gui import fake_event

    from utils import get_all_mangadex_languages

    gui = make_gui()
    # The name the downloader gives Spanish ("es"), as listed in the dropdown.
    spanish = next(
        language["name"]
        for language in get_all_mangadex_languages()["mangadex_languages"]
        if language["code"] == "es"
    )

    gui.MangaDexDownloaderView.settings.language_dropdown.on_change(
        fake_event(data=spanish)
    )

    assert gui.page.client_storage.get("language")["code"] == "es"
    options = get_additional_terminal_options(gui.page.client_storage)
    assert options[options.index("--language") + 1] == "es"


def test_each_manga_gets_its_own_folder_in_the_output_folder():
    assert get_download_folder("/Users/me/Panelyze/Downloads") == os.path.join(
        "/Users/me/Panelyze/Downloads", "{manga.title}"
    )


def test_braces_in_the_output_folder_are_not_mistaken_for_placeholders():
    assert get_download_folder("/Users/me/{odd}") == os.path.join(
        "/Users/me/{{odd}}", "{manga.title}"
    )


def test_a_dash_with_no_title_after_it_is_dropped():
    assert get_tidy_chapter_folder_name("Vol. 1 Ch. 3 - ") == "Vol. 1 Ch. 3"
    assert get_tidy_chapter_folder_name("Vol. 1 Ch. 3 -") == "Vol. 1 Ch. 3"
    assert (
        get_tidy_chapter_folder_name("Vol. 1 Ch. 3 - Boss and The Panda")
        == "Vol. 1 Ch. 3 - Boss and The Panda"
    )
    assert get_tidy_chapter_folder_name("Vol. 1 Ch. 3") == "Vol. 1 Ch. 3"


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows can't make a folder whose name ends with a space",
)
def test_a_chapter_folder_without_a_title_keeps_the_downloader_s_name_but_the_result_line_drops_the_dash(
    tmp_path,
):
    from download_from_mangadex import get_download_summary

    # Renaming it made the next download of the same link miss its pages and download it again (Eleceed ch. 2).
    chapter = tmp_path / "Eleceed" / "Ch. 2 - "
    chapter.mkdir(parents=True)
    (chapter / "00.jpg").write_bytes(b"page")

    summary = get_download_summary(str(tmp_path), {})

    assert summary == "Downloaded Eleceed Ch. 2 · 1 page"
    assert os.listdir(tmp_path / "Eleceed") == ["Ch. 2 - "]


MANGA_ID = "a1c7c817-4e59-43b7-9365-09675a149a6f"
CHAPTER_ID = "0b2b5c3a-1111-4222-8333-944455556666"


def get_manga_attributes(original_language, *format_tags):
    return {
        "originalLanguage": original_language,
        "tags": [
            {"attributes": {"name": {"en": tag}, "group": "format"}}
            for tag in format_tags
        ],
    }


@pytest.mark.parametrize(
    "original_language, format_tags, reading_direction",
    [
        ("ja", [], "rtl"),
        ("ar", [], "rtl"),
        ("zh", [], "ltr"),
        ("en", ["Full Color"], "ltr"),
        ("ja", ["Long Strip"], "webtoon"),
        ("ko", ["Long Strip", "4-Koma"], "webtoon"),
        ("ja", ["4-Koma"], "4koma"),
        ("en", ["4-Koma"], "ltr"),
    ],
)
def test_reading_direction_from_the_series_language_and_format(
    original_language, format_tags, reading_direction
):
    assert (
        get_reading_direction_from_manga(
            get_manga_attributes(original_language, *format_tags)
        )
        == reading_direction
    )


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


def fake_mangadex_api(monkeypatch, manga_attributes):
    asked_urls = []

    def get(url, timeout):
        asked_urls.append(url)
        if "/chapter/" in url:
            return FakeResponse(
                {
                    "data": {
                        "relationships": [
                            {"type": "scanlation_group", "id": "x"},
                            {"type": "manga", "id": MANGA_ID},
                        ]
                    }
                }
            )
        return FakeResponse({"data": {"attributes": manga_attributes}})

    monkeypatch.setattr(download_from_mangadex.requests, "get", get)
    return asked_urls


def test_a_series_url_looks_up_the_series(monkeypatch):
    asked_urls = fake_mangadex_api(monkeypatch, get_manga_attributes("zh"))

    assert (
        get_reading_direction_from_mangadex(
            f"https://mangadex.org/title/{MANGA_ID}/some-title"
        )
        == "ltr"
    )
    assert asked_urls == [f"https://api.mangadex.org/manga/{MANGA_ID}"]


def test_a_chapter_url_looks_up_its_series(monkeypatch):
    asked_urls = fake_mangadex_api(monkeypatch, get_manga_attributes("ja"))

    assert (
        get_reading_direction_from_mangadex(
            f"https://mangadex.org/chapter/{CHAPTER_ID}"
        )
        == "rtl"
    )
    assert asked_urls == [
        f"https://api.mangadex.org/chapter/{CHAPTER_ID}",
        f"https://api.mangadex.org/manga/{MANGA_ID}",
    ]


def test_other_urls_are_not_looked_up(monkeypatch):
    asked_urls = fake_mangadex_api(monkeypatch, get_manga_attributes("ja"))

    assert (
        get_reading_direction_from_mangadex("https://mangadex.org/list/whatever")
        is None
    )
    assert asked_urls == []


def test_no_internet_means_no_reading_direction(monkeypatch):
    def get(url, timeout):
        raise requests.ConnectionError("no internet")

    monkeypatch.setattr(download_from_mangadex.requests, "get", get)

    assert (
        get_reading_direction_from_mangadex(f"https://mangadex.org/title/{MANGA_ID}")
        is None
    )


def test_the_reading_direction_is_saved_only_in_chapters_from_this_download(tmp_path):
    old_chapter = tmp_path / "Old Manga" / "Ch. 1"
    changed_chapter = tmp_path / "Old Manga" / "Ch. 2"
    new_chapter = tmp_path / "New Manga" / "Ch. 1"
    old_chapter.mkdir(parents=True)
    changed_chapter.mkdir()
    an_hour_ago = time.time() - 3600
    os.utime(changed_chapter, (an_hour_ago, an_hour_ago))
    before = get_chapter_folders(str(tmp_path))

    # The download adds a page to "Ch. 2" and makes a new chapter.
    (changed_chapter / "page_1.png").write_bytes(b"")
    new_chapter.mkdir(parents=True)
    save_reading_direction(str(tmp_path), "ltr", before)

    assert (new_chapter / READING_DIRECTION_FILE_NAME).read_text() == "ltr"
    assert (changed_chapter / READING_DIRECTION_FILE_NAME).read_text() == "ltr"
    assert not (old_chapter / READING_DIRECTION_FILE_NAME).exists()


def test_no_chapter_folders_in_a_missing_output_folder(tmp_path):
    assert get_chapter_folders(str(tmp_path / "missing")) == {}


@pytest.mark.parametrize("returncode, saved", [(0, "ltr"), (1, None), (-15, None)])
def test_the_reading_direction_is_saved_only_after_a_finished_download(
    tmp_path, monkeypatch, returncode, saved
):
    chapter = tmp_path / "Some Manga" / "Ch. 1"

    class FakeProcessManager:
        process = None
        cancelled = False

        def monitor_terminal_output(self, *args, **kwargs):
            chapter.mkdir(parents=True)
            self.process = SimpleNamespace(returncode=returncode)

    asked_urls = fake_mangadex_api(monkeypatch, get_manga_attributes("zh"))
    monkeypatch.setattr(download_from_mangadex, "ProcessManager", FakeProcessManager)

    download_from_mangadex.download_from_mangadex(
        f"https://mangadex.org/title/{MANGA_ID}", str(tmp_path)
    )

    saved_file = chapter / READING_DIRECTION_FILE_NAME
    assert (saved_file.read_text() if saved_file.exists() else None) == saved
    assert bool(asked_urls) == (returncode == 0)


def make_chapter(output, series, chapter, page_count):
    folder = output / series / chapter
    folder.mkdir(parents=True)
    for number in range(page_count):
        (folder / f"{number:02d}.jpg").write_bytes(b"page")
    (folder / READING_DIRECTION_FILE_NAME).write_text("rtl")
    return str(folder)


def test_a_download_is_summed_up_in_one_line(tmp_path):
    from download_from_mangadex import get_chapter_folders, get_download_summary

    old = make_chapter(tmp_path, "Other Series", "Ch. 1", 9)
    before = get_chapter_folders(str(tmp_path))
    assert old in before

    # Nothing new yet.
    assert get_download_summary(str(tmp_path), before) is None

    make_chapter(tmp_path, "Slam Dunk", "Vol. 1 Ch. 3 - Blood", 20)
    assert (
        get_download_summary(str(tmp_path), before)
        == "Downloaded Slam Dunk Vol. 1 Ch. 3 - Blood · 20 pages"
    )

    make_chapter(tmp_path, "Slam Dunk", "Vol. 1 Ch. 4", 1)
    # Older downloads aren't counted, and the reading direction file isn't a page.
    assert (
        get_download_summary(str(tmp_path), before)
        == "Downloaded Slam Dunk: 2 chapters · 21 pages"
    )
    assert (
        get_download_summary(str(tmp_path), before, series_name="Slam Dunk!")
        == "Downloaded Slam Dunk!: 2 chapters · 21 pages"
    )


def run_fake_mangadex_download(
    tmp_path,
    monkeypatch,
    returncode=0,
    cancelled=False,
    make_chapter_folder=True,
    lines=(),
):
    class FakeProcessManager:
        process = None

        def __init__(self):
            self.cancelled = cancelled

        def monitor_terminal_output(self, *args, on_line=None, **kwargs):
            assert on_line is not None
            for line in lines:
                on_line(line)
            if make_chapter_folder:
                make_chapter(tmp_path, "Slam Dunk", "Vol. 1 Ch. 3", 5)
            self.process = SimpleNamespace(returncode=returncode)

    fake_mangadex_api(monkeypatch, get_manga_attributes("ja"))
    monkeypatch.setattr(download_from_mangadex, "ProcessManager", FakeProcessManager)
    return download_from_mangadex.download_from_mangadex(
        f"https://mangadex.org/title/{MANGA_ID}", str(tmp_path)
    )


def test_a_finished_mangadex_download_returns_what_was_downloaded(
    tmp_path, monkeypatch
):
    assert (
        run_fake_mangadex_download(tmp_path, monkeypatch)
        == "Downloaded Slam Dunk Vol. 1 Ch. 3 · 5 pages"
    )


def test_a_cancelled_mangadex_download_says_so(tmp_path, monkeypatch):
    from utils import DownloadCancelled

    with pytest.raises(DownloadCancelled):
        run_fake_mangadex_download(
            tmp_path, monkeypatch, returncode=-15, cancelled=True
        )


def test_a_mangadex_download_that_got_nothing_is_an_error(tmp_path, monkeypatch):
    with pytest.raises(RuntimeError, match="couldn't download anything from that link"):
        run_fake_mangadex_download(
            tmp_path, monkeypatch, returncode=1, make_chapter_folder=False
        )


def test_a_mangadex_link_that_is_already_downloaded_is_not_an_error(
    tmp_path, monkeypatch
):
    assert "Nothing new" in run_fake_mangadex_download(
        tmp_path, monkeypatch, make_chapter_folder=False
    )


def test_a_download_summary_is_a_line_of_text_that_knows_its_folder(tmp_path):
    from download_from_mangadex import get_chapter_folders, get_download_summary

    before = get_chapter_folders(str(tmp_path))
    one = make_chapter(tmp_path, "Slam Dunk", "Vol. 1 Ch. 3", 2)

    summary = get_download_summary(str(tmp_path), before)
    assert summary == "Downloaded Slam Dunk Vol. 1 Ch. 3 · 2 pages"
    assert isinstance(summary, DownloadSummary) and summary.folder == one

    make_chapter(tmp_path, "Slam Dunk", "Vol. 1 Ch. 4", 2)
    # Several chapters: the series' folder.
    summary = get_download_summary(str(tmp_path), before)
    assert isinstance(summary, DownloadSummary) and summary.folder == str(
        tmp_path / "Slam Dunk"
    )


def test_a_mangadex_link_that_is_already_downloaded_still_knows_its_folder(
    tmp_path, monkeypatch
):
    chapter = tmp_path / "Slam Dunk" / "Vol. 1 Ch. 3 - Goku's Charge"
    chapter.mkdir(parents=True)
    # What the downloader prints when everything is already there.
    series_line = f'[INFO] Download directory is set to "{tmp_path / "Slam Dunk"}"'

    one = run_fake_mangadex_download(
        tmp_path,
        monkeypatch,
        make_chapter_folder=False,
        lines=[
            series_line,
            "[INFO] 'Vol. 1 Ch. 3 - Goku's Charge' is verified. no need to re-download",
        ],
    )
    several = run_fake_mangadex_download(
        tmp_path,
        monkeypatch,
        make_chapter_folder=False,
        lines=[
            series_line,
            "[INFO] 'Vol. 1 Ch. 3' is verified. no need to re-download",
            "[INFO] 'Vol. 1 Ch. 4' is verified. no need to re-download",
        ],
    )

    # One chapter: its folder. Several: the series' folder (opened in Finder by the Download tab).
    assert isinstance(one, DownloadSummary) and isinstance(several, DownloadSummary)
    assert one.folder == str(chapter)
    assert several.folder == str(tmp_path / "Slam Dunk")
    # A MangaDex list of several series: the folder they're all in.
    (tmp_path / "Bleach").mkdir()
    listed = run_fake_mangadex_download(
        tmp_path,
        monkeypatch,
        make_chapter_folder=False,
        lines=[
            series_line,
            "[INFO] 'Vol. 1 Ch. 3' is verified.",
            f'[INFO] Download directory is set to "{tmp_path / "Bleach"}"',
        ],
    )
    assert isinstance(listed, DownloadSummary) and listed.folder == str(tmp_path)


def test_a_mangadex_download_that_stopped_partway_says_so(tmp_path, monkeypatch):
    summary = run_fake_mangadex_download(tmp_path, monkeypatch, returncode=1)

    assert (
        summary
        == "Downloaded Slam Dunk Vol. 1 Ch. 3 · 5 pages · stopped early, so the last chapter may be incomplete (see the Log)"
    )
    # Its folder is still opened, and filled in as the next tab's input.
    assert isinstance(summary, DownloadSummary) and summary.folder == str(
        tmp_path / "Slam Dunk" / "Vol. 1 Ch. 3"
    )
