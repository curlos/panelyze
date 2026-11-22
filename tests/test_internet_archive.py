import io
import os
import shutil
import zipfile
from types import SimpleNamespace

import pytest

import download_from_internet_archive as module
from download_from_internet_archive import download_internet_archive_item, get_item_identifier, pick_comic_file


def make_cbz_bytes():
    cbz = io.BytesIO()
    with zipfile.ZipFile(cbz, "w") as comic_file:
        comic_file.writestr("page_1.jpg", b"1")
        comic_file.writestr("page_2.jpg", b"2")
    return cbz.getvalue()


def fake_internet_archive(monkeypatch, licenseurl, files):
    requested_urls = []

    class FakeFileResponse:
        headers = {"Content-Length": "2000000"}

        # Used as "with requests.get(...) as response".
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            return [make_cbz_bytes()]

    def fake_get(url, stream=False, timeout=None):
        requested_urls.append(url)
        if "/metadata/" not in url:
            return FakeFileResponse()

        item = {"metadata": {"title": "Pirates Comics #1", "licenseurl": licenseurl}, "files": files}
        return SimpleNamespace(json=lambda: item, raise_for_status=lambda: None)

    monkeypatch.setattr(module.requests, "get", fake_get)
    return requested_urls


ITEM_FILES = [
    {"name": "Pirates_Comics_001.pdf", "source": "derivative"},
    {"name": "Pirates_Comics_001.cbz", "source": "original"},
    {"name": "Pirates_Comics_001_meta.xml", "source": "metadata"},
]


def test_a_public_domain_item_downloads_its_cbz_rather_than_its_pdf(monkeypatch):
    requested_urls = fake_internet_archive(
        monkeypatch, "https://creativecommons.org/publicdomain/mark/1.0/", ITEM_FILES
    )

    folder = download_internet_archive_item("https://archive.org/details/hillman-pirates-comics-001")

    assert requested_urls[-1] == "https://archive.org/download/hillman-pirates-comics-001/Pirates_Comics_001.cbz"
    # Named after the item's title, not its file.
    assert os.path.basename(folder) == "Pirates Comics #1"
    assert sorted(os.listdir(folder)) == ["001.jpg", "002.jpg"]
    shutil.rmtree(os.path.dirname(folder))


@pytest.mark.parametrize("licenseurl", [None, "https://creativecommons.org/licenses/by-nc/4.0/"])
def test_an_item_that_is_not_public_domain_is_not_downloaded(monkeypatch, licenseurl):
    requested_urls = fake_internet_archive(monkeypatch, licenseurl, ITEM_FILES)

    with pytest.raises(RuntimeError, match="isn't marked as public domain"):
        download_internet_archive_item("https://archive.org/details/invincible-compendiums")

    assert len(requested_urls) == 1


def test_an_item_without_a_comic_file_gives_a_clear_error(monkeypatch):
    fake_internet_archive(
        monkeypatch, "https://creativecommons.org/publicdomain/zero/1.0/", [{"name": "movie.mp4"}]
    )

    with pytest.raises(RuntimeError, match="has no comic file"):
        download_internet_archive_item("https://archive.org/details/a-movie")


def test_the_comic_file_preference():
    assert pick_comic_file([{"name": "a.pdf"}, {"name": "a.zip"}]) == "a.zip"
    assert pick_comic_file([{"name": "a.pdf"}, {"name": "a.cbr"}]) == "a.cbr"
    assert pick_comic_file([{"name": "a.pdf"}]) == "a.pdf"
    assert pick_comic_file([{"name": "a.mp4"}]) is None


def test_only_internet_archive_item_links_are_accepted():
    assert get_item_identifier("https://archive.org/details/hillman-pirates-comics-001/page/n5") == "hillman-pirates-comics-001"
    for url in ["https://archive.org/search?query=comics", "https://archive.org.evil.com/details/x"]:
        with pytest.raises(ValueError, match="Not an Internet Archive item link"):
            get_item_identifier(url)



def test_the_download_size_is_reported_and_it_can_be_cancelled(monkeypatch):
    import threading

    from utils import DownloadCancelled

    reports = []
    monkeypatch.setattr(module, "report_progress", lambda **fields: reports.append(fields))
    fake_internet_archive(monkeypatch, "https://creativecommons.org/publicdomain/mark/1.0/", ITEM_FILES)

    folder = download_internet_archive_item("https://archive.org/details/hillman-pirates-comics-001")
    shutil.rmtree(os.path.dirname(folder))

    sizes = [(report["pages_done"], report["pages_total"], report["unit"]) for report in reports if report.get("unit") == "MB"]
    # The file is 2 MB in the fake.
    assert sizes and sizes[-1][1:] == (2, "MB")

    cancel_event = threading.Event()
    cancel_event.set()
    with pytest.raises(DownloadCancelled):
        download_internet_archive_item("https://archive.org/details/hillman-pirates-comics-001", cancel_event)


def test_the_files_the_internet_archive_makes_itself_are_not_picked():
    # The real files of "Hollywood Detective" (1944): a .cbr, a .pdf and a JPEG 2000 zip the Archive made from the scans.
    files = [
        {"name": "Hollywood Detective v03 n06 [1944-04]_jp2.zip", "source": "derivative"},
        {"name": "Hollywood Detective v03 n06 [1944-04].pdf", "source": "derivative"},
        {"name": "Hollywood Detective v03 n06 [1944-04].cbr", "source": "original"},
        {"name": "Hollywood Detective v03 n06 [1944-04]_daisy.zip", "source": "derivative"},
    ]

    assert pick_comic_file(files) == "Hollywood Detective v03 n06 [1944-04].cbr"
    # An item with only a PDF and those files still gets its PDF.
    assert pick_comic_file([files[0], files[1], files[3]]) == "Hollywood Detective v03 n06 [1944-04].pdf"


def test_an_item_with_several_titles_is_named_after_the_first(monkeypatch):
    fake_internet_archive(monkeypatch, "https://creativecommons.org/publicdomain/mark/1.0/", ITEM_FILES)
    real_get = module.requests.get

    def get_with_two_titles(url, **kwargs):
        response = real_get(url, **kwargs)
        if "/metadata/" in url:
            item = response.json()
            item["metadata"]["title"] = ["Pirates Comics #1", "Pirates Comics (1950)"]
            response.json = lambda: item
        return response

    monkeypatch.setattr(module.requests, "get", get_with_two_titles)

    folder = download_internet_archive_item("https://archive.org/details/hillman-pirates-comics-001")

    assert os.path.basename(folder) == "Pirates Comics #1"
    shutil.rmtree(os.path.dirname(folder))


def test_a_license_given_as_a_list_is_still_read():
    assert module.is_public_domain({"licenseurl": ["https://creativecommons.org/publicdomain/mark/1.0/"]})
    assert not module.is_public_domain({"licenseurl": ["https://creativecommons.org/licenses/by-nc/4.0/"]})
