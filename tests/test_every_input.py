"""
One test for each kind of input Panelyze takes, all made artificially (see "make_test_inputs.py") and without the internet: a comic file in every format, loose images in every format, folders, files that are broken, and every kind of link (with the internet faked).
"""
import os
import shutil
from types import SimpleNamespace

import pytest
import requests
from PIL import Image

import download_from_internet_archive as internet_archive_module
import utils
from gui_classes import MangaDexDownloaderView
from gui_classes.MangaDexDownloaderView import get_downloader
from tests.fake_gui import fake_event
from tests.make_test_inputs import PAGE_COUNT, get_page_color, make_test_inputs
from tests.test_download_pages_from_url import fake_internet, make_image_bytes
from tests.test_internet_archive import ITEM_FILES, fake_internet_archive

COMIC_FILE_NAMES = ["sample.cbz", "sample.zip", "sample.epub", "sample.pdf", "sample.cbr"]


@pytest.fixture
def inputs(tmp_path):
    return make_test_inputs(str(tmp_path / "inputs"))


def get_page_numbers(folder):
    """
    Which sample page each image in the folder is (1 to 5), in the order of their file names, worked out from the color of the corner.
    """
    page_numbers = []
    for file_name in sorted(os.listdir(folder)):
        with Image.open(os.path.join(folder, file_name)) as image:
            corner = image.convert("RGB").getpixel((5, 5))
        page_numbers.append(
            next(
                number
                for number in range(1, PAGE_COUNT + 1)
                if all(abs(found - expected) <= 16 for found, expected in zip(corner, get_page_color(number)))
            )
        )
    return page_numbers


def get_input_tab(gui, view_name="UpscaleImagesView"):
    """
    A tab's input and output picker, with a fake job that records the folder it's given and the pages in it.
    """
    directories = getattr(gui, view_name).pick_input_output_directories_container
    directories.jobs = []

    def fake_job(input_directory, output_directory):
        pages = sorted(
            os.path.relpath(os.path.join(directory, file_name), input_directory)
            for directory, _, file_names in os.walk(input_directory)
            for file_name in file_names
        )
        directories.jobs.append((input_directory, pages))

    directories.on_submit = fake_job
    return directories


# Comic files ----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", COMIC_FILE_NAMES)
def test_every_comic_file_format_gives_its_pages_in_order(inputs, name):
    folder = utils.extract_comic_files_to_folder([inputs["comic files"][name]])

    assert os.path.basename(folder) == "sample"
    assert [file_name[:3] for file_name in sorted(os.listdir(folder))] == ["001", "002", "003", "004", "005"]
    assert get_page_numbers(folder) == [1, 2, 3, 4, 5]
    # Only the pages: the comic info, the macOS metadata and the epub's book files are left out.
    assert all(utils.is_image_file(file_name) for file_name in os.listdir(folder))
    shutil.rmtree(os.path.dirname(folder))


def test_every_comic_file_format_at_once_gives_a_chapter_folder_each(inputs):
    # They have the same name, so they mustn't overwrite each other's pages.
    folder = utils.extract_comic_files_to_folder([inputs["comic files"][name] for name in COMIC_FILE_NAMES])

    assert sorted(os.listdir(folder)) == ["sample", "sample (2)", "sample (3)", "sample (4)", "sample (5)"]
    for chapter in os.listdir(folder):
        assert get_page_numbers(os.path.join(folder, chapter)) == [1, 2, 3, 4, 5]
    shutil.rmtree(os.path.dirname(folder))


@pytest.mark.parametrize(
    "name, summary",
    [
        ("sample.cbz", "1 chapter · 5 pages"),
        ("sample.zip", "1 chapter · 5 pages"),
        ("sample.epub", "1 chapter · 5 pages"),
        ("sample.pdf", "1 chapter · 5 pages"),
        # A .cbr's pages can't be counted without opening it.
        ("sample.cbr", "1 chapter"),
    ],
)
def test_every_comic_file_format_can_be_picked_in_a_tab_and_says_what_was_found(make_gui, inputs, tmp_path, name, summary):
    gui = make_gui()
    directories = get_input_tab(gui)
    directories.output_directory = str(tmp_path / "out")

    directories.pick_input_comic_files_result(fake_event(files=[SimpleNamespace(path=inputs["comic files"][name])]))
    assert directories.input_directory_row_text.value == name
    assert directories.input_summary_text.value == summary
    directories.handle_submit(fake_event())

    [(input_directory, pages)] = directories.jobs
    assert [os.path.basename(page)[:3] for page in pages] == ["001", "002", "003", "004", "005"]
    # The temporary folder is deleted afterwards.
    assert not os.path.exists(input_directory)


# Loose images ---------------------------------------------------------------------------------------------------------


def test_images_in_every_image_format_can_be_picked(make_gui, inputs, tmp_path):
    assert [os.path.splitext(path)[1] for path in inputs["loose images"]] == [".png", ".jpg", ".jpeg", ".webp"]
    assert all(utils.is_image_file(os.path.basename(path)) for path in inputs["loose images"])
    gui = make_gui()
    directories = get_input_tab(gui)
    directories.output_directory = str(tmp_path / "out")

    directories.pick_input_images_result(
        fake_event(files=[SimpleNamespace(path=path) for path in inputs["loose images"]])
    )
    assert directories.input_summary_text.value == "4 images"
    directories.handle_submit(fake_event())

    [(input_directory, pages)] = directories.jobs
    assert pages == ["page_1.png", "page_2.jpg", "page_3.jpeg", "page_4.webp"]
    assert not os.path.exists(input_directory)


# Folders --------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "folder_name, summary",
    [
        ("one chapter", "4 pages"),
        ("series with 2 chapters", "2 chapters · 5 pages"),
        ("natural order", "3 pages"),
        ("no images", "No images found in this folder"),
    ],
)
def test_every_kind_of_folder_can_be_picked_and_says_what_was_found(make_gui, inputs, folder_name, summary):
    gui = make_gui()
    directories = get_input_tab(gui)

    directories.pick_input_files_result(fake_event(path=inputs["folders"][folder_name]))

    assert directories.input_directory_row_text.value == folder_name
    assert directories.input_summary_text.value == summary


def test_pages_are_in_natural_order_so_page_10_comes_after_page_2(inputs):
    pages = [os.path.basename(path) for path in utils.list_images(inputs["folders"]["natural order"])]

    assert pages == ["page_1.png", "page_2.png", "page_10.png"]


def test_a_series_folder_is_processed_chapter_by_chapter(inputs):
    chapters = [
        (os.path.basename(folder), len(images))
        for folder, images in utils.get_image_folders(inputs["folders"]["series with 2 chapters"])
    ]

    assert chapters == [("Ch 1", 3), ("Ch 2", 2)]


# Files that can't be used ---------------------------------------------------------------------------------------------


def test_a_broken_comic_file_shows_an_error_and_leaves_nothing_behind(make_gui, inputs, tmp_path, monkeypatch):
    gui = make_gui()
    directories = get_input_tab(gui)
    directories.output_directory = str(tmp_path / "out")
    errors = []
    monkeypatch.setattr(gui.terminal_output, "update_terminal_with_error_message", errors.append)

    directories.pick_input_comic_files_result(fake_event(files=[SimpleNamespace(path=inputs["broken"]["broken.cbz"])]))
    directories.handle_submit(fake_event())

    assert errors == ["ERROR: File is not a zip file"]
    assert directories.jobs == []
    assert gui.is_job_running is False


def test_a_file_that_is_not_a_comic_file_can_not_be_picked_as_one(make_gui, inputs, monkeypatch):
    gui = make_gui()
    directories = get_input_tab(gui)
    errors = []
    monkeypatch.setattr(gui.terminal_output, "update_terminal_with_error_message", errors.append)

    directories.pick_input_comic_files_result(fake_event(files=[SimpleNamespace(path=inputs["broken"]["notes.txt"])]))

    assert errors == ["ERROR: Please pick comic files (.cbz, .zip, .epub, .cbr, .pdf)."]
    assert directories.input_comic_paths == []
    with pytest.raises(ValueError, match="Not a comic file"):
        utils.extract_comic_files_to_folder([inputs["broken"]["notes.txt"]])


# Links ----------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url, site",
    [
        ("https://comix.to/title/w25zn-slam-dunk", "comix.to"),
        ("https://comix.to/title/w25zn-slam-dunk/9071380-chapter-1", "comix.to"),
        ("https://mangadex.org/title/7991e715-40ae-4c3e-b0e0-aa8bee90ece7", "MangaDex"),
        ("https://mangadex.org/chapter/ac33cc50-a1b2-49b0-a388-0d0ee4ebce18", "MangaDex"),
        ("https://archive.org/details/hillman-pirates-comics-001", "the Internet Archive"),
        ("https://comicbookclublive.com/2024/10/04/dc-comics-preview-absolute-batman-1", "the web page"),
        ("https://example.com", "the web page"),
        # Not the real sites, so they're just web pages.
        ("https://mangadex.org.evil.com/title/x", "the web page"),
        ("https://comix.to.evil.com/title/x", "the web page"),
    ],
)
def test_every_kind_of_link_goes_to_the_right_downloader(url, site):
    assert get_downloader(url)[0] == site


@pytest.mark.parametrize("text", ["slam dunk", "comix.to/title/w25zn-slam-dunk", "file:///Users/me/page.html", ""])
def test_text_that_is_not_a_web_link_is_refused(text):
    with pytest.raises(ValueError):
        get_downloader(text)


def download_in_the_tab(make_gui, tmp_path, url, **settings):
    gui = make_gui()
    downloads = tmp_path / "Downloads"
    gui.page.client_storage.set("output_directory_mangadex", str(downloads))
    # The test pages' images are tiny, so every image is kept unless a test asks for the size limit (on by default).
    for setting, value in {"use_web_page_min_size": False, **settings}.items():
        gui.page.client_storage.set(setting, value)
    tab = gui.MangaDexDownloaderView
    tab.mangadex_url_text_field.value = url
    tab.handle_download(fake_event())
    panel = gui.terminal_output.progress_panel
    return gui, downloads, panel


COMIC_PAGE_WITH_AN_AD = {
    "https://comics.example.com/preview": '<title>Absolute Batman #1</title><img src="/1.png"><img src="/2.png"><img src="/3.png"><img src="/ad.png">',
    "https://comics.example.com/1.png": make_image_bytes(700, 1000, "red"),
    "https://comics.example.com/2.png": make_image_bytes(700, 1000, "lime"),
    "https://comics.example.com/3.png": make_image_bytes(700, 1000, "blue"),
    "https://comics.example.com/ad.png": make_image_bytes(300, 250),
}


def test_every_image_on_a_web_page_is_downloaded(make_gui, tmp_path, monkeypatch):
    fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, "https://comics.example.com/preview")

    assert (panel.state, panel.title_text.value) == ("finished", "Downloaded 4 images from comics.example.com")
    assert sorted(os.listdir(downloads / "Absolute Batman #1")) == ["001.png", "002.png", "003.png", "004.png", "download-info.json"]
    # Panel-By-Panel starts with what was just downloaded.
    picker = gui.MagiPanelByPanelView.pick_input_output_directories_container
    assert picker.input_directory == str(downloads / "Absolute Batman #1")


def test_a_web_page_can_be_downloaded_with_only_the_bigger_images(make_gui, tmp_path, monkeypatch):
    fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)

    gui, downloads, panel = download_in_the_tab(
        make_gui, tmp_path, "https://comics.example.com/preview", use_web_page_min_size=True, web_page_min_size="600"
    )

    assert (panel.state, panel.title_text.value) == ("finished", "Downloaded 3 images from comics.example.com")
    assert sorted(os.listdir(downloads / "Absolute Batman #1")) == ["001.png", "002.png", "003.png", "download-info.json"]


def test_a_random_web_page_without_images_says_so(make_gui, tmp_path, monkeypatch):
    fake_internet(monkeypatch, {"https://example.com/": "<title>Example Domain</title><p>No pictures here.</p>"})

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, "https://example.com/")

    assert (panel.state, panel.title_text.value) == ("failed", "Download from the web page failed.")
    assert panel.status_text.value.startswith("No images found on this page")
    assert not downloads.exists() or not os.listdir(downloads)


def test_a_web_page_with_only_small_images_says_why_nothing_was_kept(make_gui, tmp_path, monkeypatch):
    fake_internet(
        monkeypatch,
        {
            "https://example.com/": '<title>Example Domain</title><img src="/logo.png">',
            "https://example.com/logo.png": make_image_bytes(120, 40),
        },
    )

    gui, downloads, panel = download_in_the_tab(
        make_gui, tmp_path, "https://example.com/", use_web_page_min_size=True, web_page_min_size="600"
    )

    assert panel.state == "failed"
    assert panel.status_text.value.startswith("None of the 1 images on this page have a shorter side of at least 600 px")


def test_a_web_page_that_blocks_us_shows_why(make_gui, tmp_path, monkeypatch):
    from tests.test_download_pages_from_url import FakeResponse

    def blocked(url, headers=None, timeout=None, stream=False):
        return FakeResponse(b"", error=requests.HTTPError(f"403 Client Error: Forbidden for url: {url}"))

    monkeypatch.setattr(requests, "get", blocked)

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, "https://aiptcomics.com/2024/10/03/dc-preview-absolute-batman-1/")

    assert panel.state == "failed"
    assert "403 Client Error: Forbidden" in panel.status_text.value


def test_a_public_domain_internet_archive_comic_is_downloaded(make_gui, tmp_path, monkeypatch):
    fake_internet_archive(monkeypatch, "https://creativecommons.org/publicdomain/mark/1.0/", ITEM_FILES)
    monkeypatch.setattr(MangaDexDownloaderView, "download_internet_archive_item", internet_archive_module.download_internet_archive_item)

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, "https://archive.org/details/hillman-pirates-comics-001")

    assert (panel.state, panel.title_text.value) == ("finished", "Downloaded Pirates Comics #1: 2 pages")
    assert sorted(os.listdir(downloads / "Pirates Comics #1")) == ["001.jpg", "002.jpg", "download-info.json"]


def test_an_internet_archive_comic_that_is_not_public_domain_is_refused(make_gui, tmp_path, monkeypatch):
    fake_internet_archive(monkeypatch, None, ITEM_FILES)

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, "https://archive.org/details/invincible-compendiums")

    assert (panel.state, panel.title_text.value) == ("failed", "Download from the Internet Archive failed.")
    assert "isn't marked as public domain" in panel.status_text.value
    assert not downloads.exists() or not os.listdir(downloads)


def test_text_that_is_not_a_link_is_refused_in_the_tab_before_anything_starts(make_gui, tmp_path):
    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, "slam dunk")

    assert (panel.state, panel.title_text.value) == ("failed", "Something went wrong")
    assert panel.status_text.value == "Not a web link (it should start with https://): slam dunk"
    assert gui.is_job_running is False


# Showing the files when a download is done ------------------------------------------------------------------------------


def watch_finder(monkeypatch):
    """
    The folders the Download tab opens in Finder (and no real window opens).
    """
    opened = []
    monkeypatch.setattr(MangaDexDownloaderView, "open_directory", opened.append)
    return opened


def test_a_finished_web_page_download_opens_its_folder_in_finder(make_gui, tmp_path, monkeypatch):
    opened = watch_finder(monkeypatch)
    fake_internet(
        monkeypatch,
        {
            "https://comics.example.com/preview": '<title>Absolute Batman #1</title><img src="/1.png">',
            "https://comics.example.com/1.png": make_image_bytes(700, 1000),
        },
    )

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, "https://comics.example.com/preview")

    assert opened == [str(downloads / "Absolute Batman #1")]


def test_a_finished_internet_archive_download_opens_its_folder_in_finder(make_gui, tmp_path, monkeypatch):
    opened = watch_finder(monkeypatch)
    fake_internet_archive(monkeypatch, "https://creativecommons.org/publicdomain/mark/1.0/", ITEM_FILES)

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, "https://archive.org/details/hillman-pirates-comics-001")

    assert opened == [str(downloads / "Pirates Comics #1")]


@pytest.mark.parametrize(
    "downloader, url",
    [("download_from_comix", "https://comix.to/title/x"), ("download_from_mangadex", "https://mangadex.org/title/x")],
)
def test_a_finished_chapter_download_opens_its_folder_and_fills_in_panel_by_panel(make_gui, tmp_path, monkeypatch, downloader, url):
    from utils import DownloadSummary

    opened = watch_finder(monkeypatch)
    gui = make_gui()
    downloads = tmp_path / "Downloads"
    gui.page.client_storage.set("output_directory_mangadex", str(downloads))
    # An older folder that was changed more recently than the chapter that's downloaded again (its pages are written over, which doesn't change its folder).
    chapter = downloads / "Absolute Batman" / "Chapter_25"
    chapter.mkdir(parents=True)
    (downloads / "Slam Dunk").mkdir()
    monkeypatch.setattr(
        MangaDexDownloaderView, downloader,
        lambda *arguments: DownloadSummary("Downloaded Absolute Batman chapter 25 · 36 pages", str(chapter)),
    )
    tab = gui.MangaDexDownloaderView
    tab.mangadex_url_text_field.value = url

    tab.handle_download(fake_event())

    assert opened == [str(chapter)]
    # Panel-By-Panel gets the series that was downloaded, not just the newest folder.
    assert gui.MagiPanelByPanelView.pick_input_output_directories_container.input_directory == str(downloads / "Absolute Batman")


@pytest.mark.parametrize("outcome", ["failed", "cancelled", "nothing new"])
def test_nothing_opens_in_finder_when_a_download_did_not_give_anything(make_gui, tmp_path, monkeypatch, outcome):
    from utils import DownloadCancelled

    opened = watch_finder(monkeypatch)

    def download(*arguments):
        if outcome == "failed":
            raise RuntimeError("It broke.")
        if outcome == "cancelled":
            raise DownloadCancelled("Download cancelled")
        # A plain line, without a folder.
        return "Nothing new to download: it's already in the folder."

    monkeypatch.setattr(MangaDexDownloaderView, "download_from_mangadex", download)

    download_in_the_tab(make_gui, tmp_path, "https://mangadex.org/title/x")

    assert opened == []


def test_the_pipeline_does_not_open_finder_in_the_middle_of_a_run(make_gui, tmp_path, monkeypatch):
    from gui_classes import PipelineView

    opened = watch_finder(monkeypatch)
    pipeline_opened = []
    monkeypatch.setattr(PipelineView, "open_directory", pipeline_opened.append)

    def download(url, output_directory, *arguments):
        from utils import DownloadSummary

        folder = os.path.join(output_directory, "Absolute Batman")
        os.makedirs(folder)
        return DownloadSummary("Downloaded something", folder)

    monkeypatch.setattr(MangaDexDownloaderView, "download_from_mangadex", download)
    gui = make_gui()
    pipeline = gui.PipelineView
    pipeline.step_checkboxes["Download"].value = True
    pipeline.mangadex_url_text_field.value = "https://mangadex.org/title/x"
    pipeline.output_directory = str(tmp_path / "out")
    gui.terminal_output.update_terminal_with_error_message = lambda message: None

    pipeline.run_step("Download", "", str(tmp_path / "out" / "1-download"))

    assert opened == [] and pipeline_opened == []


def test_the_mangadex_downloader_does_not_open_finder_by_itself(tmp_path, monkeypatch):
    import download_from_mangadex as module
    from tests.test_mangadex_folders import MANGA_ID, fake_mangadex_api, get_manga_attributes

    arguments_seen = []

    class FakeProcessManager:
        process = None
        cancelled = False

        def monitor_terminal_output(self, *args, **kwargs):
            arguments_seen.append(args)
            (tmp_path / "Some Manga" / "Ch. 1").mkdir(parents=True)
            self.process = SimpleNamespace(returncode=0)

    fake_mangadex_api(monkeypatch, get_manga_attributes("ja"))
    monkeypatch.setattr(module, "ProcessManager", FakeProcessManager)

    summary = module.download_from_mangadex(f"https://mangadex.org/title/{MANGA_ID}", str(tmp_path))

    # The command and the terminal output, but no output folder: that's what would open Finder.
    assert len(arguments_seen[0]) == 2
    assert summary.folder == str(tmp_path / "Some Manga" / "Ch. 1")


# Not downloading what's already downloaded ------------------------------------------------------------------------------


PAGE_URL = "https://comics.example.com/preview"


def get_web_page_folders(downloads):
    return sorted(name for name in os.listdir(downloads) if os.path.isdir(downloads / name))


def test_a_web_page_that_was_already_downloaded_is_not_downloaded_again(make_gui, tmp_path, monkeypatch):
    requested_urls = fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)
    download_in_the_tab(make_gui, tmp_path, PAGE_URL)
    requested_before = len(requested_urls)

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL)

    assert (panel.state, panel.title_text.value) == ("finished", "Already downloaded: 4 images from comics.example.com")
    # Nothing was asked of the internet, and there's no "(2)" copy.
    assert len(requested_urls) == requested_before
    assert get_web_page_folders(downloads) == ["Absolute Batman #1"]


def test_a_web_page_is_downloaded_again_when_its_folder_was_deleted(make_gui, tmp_path, monkeypatch):
    fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)
    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL)
    shutil.rmtree(downloads / "Absolute Batman #1")

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL)

    assert panel.title_text.value == "Downloaded 4 images from comics.example.com"
    assert get_web_page_folders(downloads) == ["Absolute Batman #1"]


def test_a_web_page_that_lost_images_is_downloaded_again_and_replaces_the_folder(make_gui, tmp_path, monkeypatch):
    fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)
    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL)
    (downloads / "Absolute Batman #1" / "002.png").unlink()

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL)

    assert panel.title_text.value == "Downloaded 4 images from comics.example.com"
    # The damaged folder is replaced, not left next to a "(2)".
    assert get_web_page_folders(downloads) == ["Absolute Batman #1"]
    assert len(os.listdir(downloads / "Absolute Batman #1")) == 5


def test_a_web_page_is_downloaded_again_with_another_minimum_size(make_gui, tmp_path, monkeypatch):
    fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)
    download_in_the_tab(make_gui, tmp_path, PAGE_URL)

    gui, downloads, panel = download_in_the_tab(
        make_gui, tmp_path, PAGE_URL, use_web_page_min_size=True, web_page_min_size="600"
    )

    # Another set of images, so another folder.
    assert panel.title_text.value == "Downloaded 3 images from comics.example.com"
    assert get_web_page_folders(downloads) == ["Absolute Batman #1", "Absolute Batman #1 (2)"]


def test_a_web_page_that_was_already_downloaded_is_replaced_when_asked_for(make_gui, tmp_path, monkeypatch):
    requested_urls = fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)
    download_in_the_tab(make_gui, tmp_path, PAGE_URL)
    requested_before = len(requested_urls)

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL, replace_existing_manga=True)

    assert panel.title_text.value == "Downloaded 4 images from comics.example.com"
    assert len(requested_urls) > requested_before
    assert get_web_page_folders(downloads) == ["Absolute Batman #1"]


def test_a_pipeline_copies_a_web_page_from_the_download_tabs_folder_instead_of_downloading_it(make_gui, tmp_path, monkeypatch):
    requested_urls = fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)
    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL)
    requested_before = len(requested_urls)
    # The Download tab's folder is the library; a Pipeline's Download step saves somewhere else.
    pipeline_folder = tmp_path / "Pipeline" / "1-download"
    monkeypatch.setattr("default_settings.get_output_directory", lambda storage, key: str(downloads))

    summary = MangaDexDownloaderView.download_web_page(PAGE_URL, str(pipeline_folder), None, gui.page.client_storage)

    assert summary == "Already downloaded (copied): 4 images from comics.example.com"
    assert len(requested_urls) == requested_before
    assert summary.folder == str(pipeline_folder / "Absolute Batman #1")
    assert len(os.listdir(summary.folder)) == 4 + 1  # the images and download-info.json


ARCHIVE_URL = "https://archive.org/details/hillman-pirates-comics-001"


def test_an_internet_archive_comic_that_was_already_downloaded_is_not_downloaded_again(make_gui, tmp_path, monkeypatch):
    requested_urls = fake_internet_archive(monkeypatch, "https://creativecommons.org/publicdomain/mark/1.0/", ITEM_FILES)
    monkeypatch.setattr(MangaDexDownloaderView, "download_internet_archive_item", internet_archive_module.download_internet_archive_item)
    download_in_the_tab(make_gui, tmp_path, ARCHIVE_URL)
    requested_before = len(requested_urls)

    # Another way of writing the link to the same item.
    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, ARCHIVE_URL + "/page/n5")

    assert (panel.state, panel.title_text.value) == ("finished", "Already downloaded: Pirates Comics #1: 2 pages")
    assert len(requested_urls) == requested_before
    assert get_web_page_folders(downloads) == ["Pirates Comics #1"]


def test_a_pipeline_copies_an_internet_archive_comic_from_the_download_tabs_folder(make_gui, tmp_path, monkeypatch):
    requested_urls = fake_internet_archive(monkeypatch, "https://creativecommons.org/publicdomain/mark/1.0/", ITEM_FILES)
    monkeypatch.setattr(MangaDexDownloaderView, "download_internet_archive_item", internet_archive_module.download_internet_archive_item)
    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, ARCHIVE_URL)
    requested_before = len(requested_urls)
    pipeline_folder = tmp_path / "Pipeline" / "1-download"
    monkeypatch.setattr("default_settings.get_output_directory", lambda storage, key: str(downloads))

    summary = MangaDexDownloaderView.download_from_internet_archive(ARCHIVE_URL, str(pipeline_folder), None, gui.page.client_storage)

    assert summary == "Already downloaded (copied): Pirates Comics #1: 2 pages"
    assert len(requested_urls) == requested_before
    assert summary.folder == str(pipeline_folder / "Pirates Comics #1")


def test_nothing_is_copied_when_the_folders_are_the_same_or_replacing_is_asked_for(make_gui, tmp_path, monkeypatch):
    requested_urls = fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)
    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL)
    storage = gui.page.client_storage
    monkeypatch.setattr("default_settings.get_output_directory", lambda storage, key: str(downloads))

    assert utils.get_library_directory(str(downloads), storage) is None

    storage.set("replace_existing_manga", True)
    pipeline_folder = tmp_path / "Pipeline" / "1-download"
    requested_before = len(requested_urls)
    MangaDexDownloaderView.download_web_page(PAGE_URL, str(pipeline_folder), None, storage)

    # Downloaded for real: the internet was asked again.
    assert len(requested_urls) > requested_before


def test_an_internet_archive_comic_is_downloaded_again_when_its_folder_lost_pages_or_replacing_is_asked_for(make_gui, tmp_path, monkeypatch):
    requested_urls = fake_internet_archive(monkeypatch, "https://creativecommons.org/publicdomain/mark/1.0/", ITEM_FILES)
    monkeypatch.setattr(MangaDexDownloaderView, "download_internet_archive_item", internet_archive_module.download_internet_archive_item)
    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, ARCHIVE_URL)
    (downloads / "Pirates Comics #1" / "001.jpg").unlink()

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, ARCHIVE_URL)
    assert panel.title_text.value == "Downloaded Pirates Comics #1: 2 pages"
    assert get_web_page_folders(downloads) == ["Pirates Comics #1"]

    requested_before = len(requested_urls)
    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, ARCHIVE_URL, replace_existing_manga=True)
    assert panel.title_text.value == "Downloaded Pirates Comics #1: 2 pages"
    assert len(requested_urls) > requested_before
    assert get_web_page_folders(downloads) == ["Pirates Comics #1"]


# The folder check itself ------------------------------------------------------------------------------------------------


def make_downloaded_folder(directory, name, pages, **info):
    folder = directory / name
    folder.mkdir(parents=True)
    for number in range(pages):
        (folder / f"{number + 1:03d}.jpg").write_bytes(b"page")
    utils.write_download_info(str(folder), pages=pages, **info)
    return str(folder)


def test_a_folder_is_only_found_while_it_still_has_all_its_pages(tmp_path):
    folder = make_downloaded_folder(tmp_path, "Chapter", 3, source="comix.to", chapter_id=7)

    found_folder, info = utils.find_downloaded_folder(str(tmp_path), source="comix.to", chapter_id=7)
    assert found_folder == folder and info["pages"] == 3
    # Another chapter, or another source, isn't it.
    assert utils.find_downloaded_folder(str(tmp_path), source="comix.to", chapter_id=8) is None
    assert utils.find_downloaded_folder(str(tmp_path), source="archive.org", chapter_id=7) is None

    os.remove(os.path.join(folder, "002.jpg"))
    assert utils.find_downloaded_folder(str(tmp_path), source="comix.to", chapter_id=7) is None
    # With a page missing it can still be found, to be replaced.
    assert utils.find_downloaded_folder(str(tmp_path), only_if_intact=False, source="comix.to", chapter_id=7)[0] == folder


def test_a_folder_with_an_image_the_user_added_still_counts_as_downloaded_but_a_broken_info_file_is_not_trusted(tmp_path):
    folder = make_downloaded_folder(tmp_path, "Chapter", 2, source="comix.to")
    # Added by the user: the folder isn't downloaded again and replaced, which would delete it.
    (tmp_path / "Chapter" / "003.jpg").write_bytes(b"page")
    assert utils.find_downloaded_folder(str(tmp_path), source="comix.to")[0] == str(tmp_path / "Chapter")

    # A page missing is still a broken download.
    (tmp_path / "Chapter" / "001.jpg").unlink()
    (tmp_path / "Chapter" / "002.jpg").unlink()
    assert utils.find_downloaded_folder(str(tmp_path), source="comix.to") is None

    (tmp_path / "Other").mkdir()
    (tmp_path / "Other" / "download-info.json").write_text("{ not json")
    assert utils.read_download_info(str(tmp_path / "Other")) is None
    # A broken info file, or a file where a folder would be, doesn't stop it from looking through the others.
    (tmp_path / "A file").write_text("not a folder")
    assert utils.find_downloaded_folder(str(tmp_path), source="comix.to") is None
    assert utils.find_downloaded_folder(str(tmp_path / "Gone"), source="comix.to") is None


def test_a_download_is_also_saved_as_a_comic_file_with_the_setting_but_only_once(make_gui, tmp_path, monkeypatch):
    fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)
    made = []
    real_save = MangaDexDownloaderView.save_folder_as_cbz
    monkeypatch.setattr(MangaDexDownloaderView, "save_folder_as_cbz", lambda folder, size: made.append(size) or real_save(folder, size))

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL, save_as_cbz="full")
    assert (downloads / "Absolute Batman #1.cbz").exists()

    download_in_the_tab(make_gui, tmp_path, PAGE_URL, save_as_cbz="full")
    assert made == ["full"]


def test_a_download_makes_no_comic_file_without_the_setting(make_gui, tmp_path, monkeypatch):
    fake_internet(monkeypatch, COMIC_PAGE_WITH_AN_AD)

    gui, downloads, panel = download_in_the_tab(make_gui, tmp_path, PAGE_URL)

    assert not list(downloads.glob("*.cbz"))


def test_comic_files_are_made_for_each_chapter_of_a_series_but_not_for_the_series_folder(tmp_path):
    from PIL import Image

    series = tmp_path / "Series"
    Image.new("RGB", (10, 10)).save(series.mkdir() or series / "cover.jpg")
    for chapter in ("Ch 1", "Ch 2"):
        (series / chapter).mkdir()
        Image.new("RGB", (10, 10)).save(series / chapter / "1.png")

    MangaDexDownloaderView.save_downloads_as_comic_files(str(series), "full")

    assert sorted(path.name for path in tmp_path.rglob("*.cbz")) == ["Ch 1.cbz", "Ch 2.cbz"]

    # A chapter downloaded again (its pages are newer than its comic file) gets a new one, the other is kept.
    made_before = (series / "Ch 2.cbz").stat().st_mtime
    os.utime(series / "Ch 1" / "1.png", (made_before + 60, made_before + 60))
    remade = []
    real_save = MangaDexDownloaderView.save_folder_as_cbz
    MangaDexDownloaderView.save_folder_as_cbz = lambda folder, size: remade.append(os.path.basename(folder)) or real_save(folder, size)
    try:
        MangaDexDownloaderView.save_downloads_as_comic_files(str(series), "full")
    finally:
        MangaDexDownloaderView.save_folder_as_cbz = real_save
    assert remade == ["Ch 1"]
