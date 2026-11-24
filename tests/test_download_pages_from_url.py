import io
import os
import shutil
from types import SimpleNamespace

import pytest
from PIL import Image

import download_pages_from_url as module
from download_pages_from_url import download_pages_from_url, get_largest_srcset_url


def make_image_bytes(width, height, color="white", image_format="PNG"):
    image_bytes = io.BytesIO()
    Image.new("RGB", (width, height), color).save(image_bytes, image_format)
    return image_bytes.getvalue()


class FakeResponse:
    """
    What "requests.get(..., stream=True)" returns, for content given as text or bytes.
    """

    def __init__(self, content, error=None):
        self.content = content.encode("utf-8") if isinstance(content, str) else content
        self.headers = {}
        self.encoding = "utf-8"
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def iter_content(self, chunk_size):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def fake_internet(monkeypatch, responses):
    """
    "requests.get" returns the content in "responses" for each URL, without using the internet.
    """
    requested_urls = []

    def fake_get(url, headers=None, timeout=None, stream=False):
        requested_urls.append(url)
        return FakeResponse(responses[url])

    monkeypatch.setattr(module.requests, "get", fake_get)
    return requested_urls


def test_an_image_bigger_than_the_limit_is_skipped_and_the_others_are_kept(monkeypatch):
    # A broken or hostile site can't fill the memory with one huge "image".
    big_image = make_image_bytes(300, 300, "red")
    small_image = make_image_bytes(10, 10, "blue")
    monkeypatch.setattr(module, "MAX_IMAGE_BYTES", len(big_image) - 1)
    fake_internet(
        monkeypatch,
        {
            "https://example.com/preview": '<html><body><img src="/big.png"><img src="/small.png"></body></html>',
            "https://example.com/big.png": big_image,
            "https://example.com/small.png": small_image,
        },
    )

    folder = download_pages_from_url("https://example.com/preview")

    assert read_page_colors(folder) == [("001.png", (0, 0, 255))]
    shutil.rmtree(os.path.dirname(folder))


def test_a_page_bigger_than_the_limit_isn_t_read(monkeypatch):
    monkeypatch.setattr(module, "MAX_PAGE_BYTES", 100)
    fake_internet(monkeypatch, {"https://example.com/huge": "<html>" + "x" * 200 + "</html>"})

    with pytest.raises(RuntimeError, match="This page is bigger than"):
        download_pages_from_url("https://example.com/huge")


@pytest.mark.parametrize(
    "encoding, page_bytes",
    [
        # A misspelled charset from the site: read as UTF-8 instead of failing.
        ("bogus", '<html><head><title>Café chapter one</title></head><body><img src="/a.png"></body></html>'.encode("utf-8")),
        # No charset at all: guessed from the bytes (here Windows' Western European).
        (None, '<html><head><title>Café chapter one, where the story begins again</title></head><body><img src="/a.png"></body></html>'.encode("cp1252")),
    ],
)
def test_the_page_s_text_is_read_even_with_a_wrong_or_missing_charset(monkeypatch, encoding, page_bytes):
    def fake_get(url, headers=None, timeout=None, stream=False):
        response = FakeResponse(page_bytes if url.endswith("/page") else make_image_bytes(10, 10))
        response.encoding = encoding
        return response

    monkeypatch.setattr(module.requests, "get", fake_get)

    folder = download_pages_from_url("https://example.com/page")

    # The page's title, read correctly, is the folder's name.
    assert os.path.basename(folder).startswith("Café chapter one")
    shutil.rmtree(os.path.dirname(folder))


def read_page_colors(folder):
    colors = []
    for file_name in sorted(os.listdir(folder)):
        with Image.open(os.path.join(folder, file_name)) as image:
            colors.append((file_name, image.convert("RGB").getpixel((0, 0))))
    return colors


PAGE_WITH_AN_AD = """
    <html><head><title>DC Preview: Absolute Batman #1</title></head><body>
    <img src="/cover.jpg">
    <img src="/ad.png">
    <img src="placeholder.gif" data-src="https://cdn.example.com/page2.png">
    <img src="/page3-small.png" srcset="/page3-small.png 480w, /page3-big.png 1200w">
    <img src="/cover.jpg">
    </body></html>
"""


def fake_page_with_an_ad(monkeypatch):
    return fake_internet(
        monkeypatch,
        {
            "https://comics.example.com/preview": PAGE_WITH_AN_AD,
            "https://comics.example.com/cover.jpg": make_image_bytes(700, 1000, "red", "JPEG"),
            "https://comics.example.com/ad.png": make_image_bytes(300, 250, "yellow"),
            "https://cdn.example.com/page2.png": make_image_bytes(700, 1000, "lime"),
            "https://comics.example.com/page3-big.png": make_image_bytes(700, 1000, "blue"),
        },
    )


def test_every_image_on_the_page_is_saved_in_page_order(monkeypatch):
    requested_urls = fake_page_with_an_ad(monkeypatch)

    folder = download_pages_from_url("https://comics.example.com/preview")

    assert os.path.basename(folder) == "DC Preview Absolute Batman #1"
    # The ad too: everything on the page is kept unless a minimum size is asked for.
    assert [name for name, _ in read_page_colors(folder)] == ["001.jpg", "002.png", "003.png", "004.png"]
    # (The first is a JPEG, whose colors are a little off.)
    assert [color for _, color in read_page_colors(folder)][1:] == [(255, 255, 0), (0, 255, 0), (0, 0, 255)]
    # The same image twice is only downloaded once, and the srcset's small image isn't downloaded at all.
    assert requested_urls.count("https://comics.example.com/cover.jpg") == 1
    assert "https://comics.example.com/page3-small.png" not in requested_urls
    shutil.rmtree(os.path.dirname(folder))


def test_with_a_minimum_size_the_small_images_are_left_out(monkeypatch):
    fake_page_with_an_ad(monkeypatch)

    folder = download_pages_from_url("https://comics.example.com/preview", min_side=600)

    assert [name for name, _ in read_page_colors(folder)] == ["001.jpg", "002.png", "003.png"]
    assert [color for _, color in read_page_colors(folder)][1:] == [(0, 255, 0), (0, 0, 255)]
    shutil.rmtree(os.path.dirname(folder))


def test_a_page_without_images_gives_a_clear_error(monkeypatch):
    fake_internet(monkeypatch, {"https://example.com/": "<title>Example Domain</title><p>No pictures here.</p>"})

    with pytest.raises(RuntimeError, match="No images found on this page"):
        download_pages_from_url("https://example.com/")


def test_a_page_with_only_small_images_is_saved_unless_a_minimum_size_is_asked_for(monkeypatch):
    fake_internet(
        monkeypatch,
        {
            "https://example.com/news": '<title>News</title><img src="/icon.png">',
            "https://example.com/icon.png": make_image_bytes(64, 64),
        },
    )

    folder = download_pages_from_url("https://example.com/news")
    assert os.listdir(folder) == ["001.png"]
    shutil.rmtree(os.path.dirname(folder))

    with pytest.raises(RuntimeError, match="None of the 1 images on this page have a shorter side of at least 600 px"):
        download_pages_from_url("https://example.com/news", min_side=600)


@pytest.mark.parametrize(
    "settings, expected",
    [
        ({}, 0),
        ({"use_web_page_min_size": False, "web_page_min_size": "600"}, 0),
        ({"use_web_page_min_size": True, "web_page_min_size": "600"}, 600),
        ({"use_web_page_min_size": True, "web_page_min_size": "450.5"}, 450),
        ({"use_web_page_min_size": True, "web_page_min_size": ""}, 0),
        ({"use_web_page_min_size": True, "web_page_min_size": "abc"}, 0),
    ],
)
def test_the_minimum_size_is_only_used_when_it_is_turned_on(settings, expected):
    from download_pages_from_url import get_min_image_side

    assert get_min_image_side(settings) == expected
    assert get_min_image_side(None) == 0


def test_only_web_page_urls_are_opened():
    with pytest.raises(ValueError, match="Not a web page URL"):
        download_pages_from_url("file:///etc/passwd")


def test_a_long_title_cut_to_100_letters_never_ends_in_a_space():
    # Windows drops a space at the end of a folder name, and then can't find the pages inside it.
    assert module.get_safe_folder_name("x" * 99 + " Read it online for free") == "x" * 99


def test_the_largest_srcset_image_is_picked():
    assert get_largest_srcset_url("a.jpg 480w, b.jpg 1200w, c.jpg 800w") == "b.jpg"
    assert get_largest_srcset_url("a.jpg 1x, b.jpg 2x") == "b.jpg"
    assert get_largest_srcset_url("") is None


def fake_preview_with_an_ad(monkeypatch):
    fake_internet(
        monkeypatch,
        {
            "https://example.com/preview": '<title>Preview</title><img src="/a.png"><img src="/b.png"><img src="/ad.png">',
            "https://example.com/a.png": make_image_bytes(700, 1000),
            "https://example.com/b.png": make_image_bytes(700, 1000, "blue"),
            "https://example.com/ad.png": make_image_bytes(300, 250),
        },
    )


def get_counts(reports):
    return [(report["pages_done"], report["pages_total"], report["unit"], report["detail"]) for report in reports if "unit" in report]


def test_the_images_are_counted_as_progress(monkeypatch):
    reports = []
    monkeypatch.setattr(module, "report_progress", lambda **fields: reports.append(fields))
    fake_preview_with_an_ad(monkeypatch)

    folder = download_pages_from_url("https://example.com/preview")

    # "Images", not "pages": a web page could have anything on it.
    assert get_counts(reports) == [(0, 3, "images", None), (1, 3, "images", None), (2, 3, "images", None)]
    assert reports[-1] == {"pages_done": 3}
    shutil.rmtree(os.path.dirname(folder))


def test_with_a_minimum_size_the_progress_says_how_many_were_kept(monkeypatch):
    reports = []
    monkeypatch.setattr(module, "report_progress", lambda **fields: reports.append(fields))
    fake_preview_with_an_ad(monkeypatch)

    folder = download_pages_from_url("https://example.com/preview", min_side=600)

    # The ad is looked at too (and left out), so it counts the images checked.
    assert get_counts(reports) == [
        (0, 3, "images checked", "0 kept so far"),
        (1, 3, "images checked", "1 kept so far"),
        (2, 3, "images checked", "2 kept so far"),
    ]
    shutil.rmtree(os.path.dirname(folder))


def test_cancelling_a_page_download_leaves_nothing_behind(monkeypatch):
    import tempfile
    import threading

    from utils import DownloadCancelled

    cancel_event = threading.Event()
    requested_urls = fake_internet(
        monkeypatch,
        {
            "https://example.com/preview": '<title>Preview</title><img src="/a.png"><img src="/b.png">',
            "https://example.com/a.png": make_image_bytes(700, 1000),
            "https://example.com/b.png": make_image_bytes(700, 1000, "blue"),
        },
    )
    made_folders = []
    real_mkdtemp = tempfile.mkdtemp
    monkeypatch.setattr(module.tempfile, "mkdtemp", lambda *args, **kwargs: made_folders.append(real_mkdtemp(*args, **kwargs)) or made_folders[-1])
    # Cancelled after the first image.
    real_get = module.requests.get

    def get_and_cancel_after_the_first_image(url, **kwargs):
        response = real_get(url, **kwargs)
        if url.endswith("a.png"):
            cancel_event.set()
        return response

    monkeypatch.setattr(module.requests, "get", get_and_cancel_after_the_first_image)

    with pytest.raises(DownloadCancelled):
        download_pages_from_url("https://example.com/preview", cancel_event)

    assert "https://example.com/b.png" not in requested_urls
    assert made_folders and not os.path.exists(made_folders[0])


def test_an_image_that_cannot_be_opened_is_skipped_and_an_error_leaves_nothing_behind(monkeypatch):
    import tempfile

    fake_internet(
        monkeypatch,
        {
            "https://example.com/preview": '<title>Preview</title><img src="/huge.png"><img src="/a.png"><img src="/b.png">',
            "https://example.com/huge.png": make_image_bytes(10, 10),
            "https://example.com/a.png": make_image_bytes(700, 1000),
            "https://example.com/b.png": make_image_bytes(700, 1000, "blue"),
        },
    )
    real_open = module.Image.open

    def open_image(data):
        image = real_open(data)
        if image.size == (10, 10):
            # What Pillow raises for an image too big to open safely (it isn't an OSError).
            raise Image.DecompressionBombError("too big")
        return image

    monkeypatch.setattr(module.Image, "open", open_image)

    folder = download_pages_from_url("https://example.com/preview")

    # Skipped, and the next image takes its number.
    assert [name for name, _ in read_page_colors(folder)] == ["001.png", "002.png"]
    shutil.rmtree(os.path.dirname(folder))

    # Any other error: the temporary folder isn't left behind.
    made_folders = []
    real_mkdtemp = tempfile.mkdtemp
    monkeypatch.setattr(module.tempfile, "mkdtemp", lambda *args, **kwargs: made_folders.append(real_mkdtemp(*args, **kwargs)) or made_folders[-1])
    monkeypatch.setattr(module, "download_image", lambda image_url, page_url: (_ for _ in ()).throw(MemoryError()))

    with pytest.raises(MemoryError):
        download_pages_from_url("https://example.com/preview")
    assert made_folders and not os.path.exists(made_folders[0])
