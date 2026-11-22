"""
Every kind of link, downloaded for real (slow, and needs the internet): "pytest -m e2e tests/test_e2e_links.py". The same list is in "tests/manual-test-links.md" to try by hand in the app. The tests without the internet are in "test_every_input.py".
"""
import os

import pytest

from default_settings import DEFAULT_SETTINGS
from gui_classes.MangaDexDownloaderView import get_downloader
from tests.fake_gui import FakeClientStorage
from utils import DownloadCancelled  # noqa: F401 (a cancelled download raises this)

pytestmark = pytest.mark.e2e


def download(url, output_directory, **settings):
    storage = FakeClientStorage()
    storage.values.update(DEFAULT_SETTINGS)
    storage.values.update(settings)
    source, downloader = get_downloader(url)
    return downloader(url, str(output_directory), None, storage)


def test_a_web_page_with_comic_pages(tmp_path):
    summary = download("https://comicbookclublive.com/2024/10/04/dc-comics-preview-absolute-batman-1", tmp_path)

    # DC's preview pages: the article's banner and the story pages.
    assert summary.startswith("Downloaded ") and summary.endswith(" images from comicbookclublive.com")
    assert len(os.listdir(next(tmp_path.iterdir()))) >= 5


def test_a_random_web_page_has_no_comic_pages(tmp_path):
    with pytest.raises(RuntimeError, match="No images found on this page"):
        download("https://example.com", tmp_path)


def test_a_web_page_that_blocks_plain_downloads_says_so(tmp_path):
    import requests

    # Whether this site blocks us changes from time to time (it did on 2026-11-20, but not always), so this only checks the message when it does.
    try:
        download("https://aiptcomics.com/2024/10/03/dc-preview-absolute-batman-1/", tmp_path)
    except requests.HTTPError as error:
        assert "403" in str(error)
    else:
        pytest.skip("aiptcomics.com didn't block this download")


def test_a_public_domain_comic_from_the_internet_archive(tmp_path):
    summary = download("https://archive.org/details/hillman-pirates-comics-001", tmp_path)

    assert summary == "Downloaded Hillman Pirates Comics 001: 52 pages"


def test_a_comic_on_the_internet_archive_that_is_not_public_domain_is_refused(tmp_path):
    with pytest.raises(RuntimeError, match="isn't marked as public domain"):
        download("https://archive.org/details/invincible-compendiums", tmp_path)

    assert not any(tmp_path.iterdir())


def test_a_mangadex_chapter(tmp_path):
    # Eleceed ch. 2, a webtoon with 5 pages.
    summary = download("https://mangadex.org/chapter/87c3b804-a119-4285-b2f7-74d9d807ac93", tmp_path)

    assert summary.startswith("Downloaded Eleceed") and summary.endswith("· 5 pages")


def test_a_comix_to_chapter(tmp_path):
    from download_from_comix import find_browser

    try:
        find_browser()
    except RuntimeError:
        pytest.skip("Google Chrome, Chromium or Microsoft Edge isn't installed")

    # Slam Dunk ch. 1, the VIZ Media upload: 35 pages. It takes about a minute.
    summary = download("https://comix.to/title/w25zn-slam-dunk/9071380-chapter-1", tmp_path)

    assert summary == "Downloaded Slam Dunk chapter 1 · 35 pages"
