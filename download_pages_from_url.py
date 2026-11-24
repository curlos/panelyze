import io
import os
import re
import shutil
import tempfile
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests
from PIL import Image

from gui_classes.ProgressPanel import report_progress
from utils import DownloadCancelled

# Some sites refuse requests that don't look like they come from a normal web browser.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}
TIMEOUT_SECONDS = 30
# The most that's downloaded for the page itself (its HTML, usually under 2 MB) and for each image, so a broken or hostile site can't fill the memory with one huge "page" or "image".
MAX_PAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_BYTES = 50 * 1024 * 1024


def read_at_most(response, max_bytes):
    """
    The bytes of a response opened with "stream=True", or None when it's bigger than "max_bytes" (it stops reading as soon as it is).
    """
    data = bytearray()
    for chunk in response.iter_content(1024 * 1024):
        data += chunk
        if len(data) > max_bytes:
            return None
    return bytes(data)

# The image types every tool can read, as the extension to save them with. Others (e.g. GIF) are saved as PNG.
SAVED_IMAGE_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def get_largest_srcset_url(srcset):
    """
    The biggest image in a "srcset" ("small.jpg 480w, big.jpg 1200w"), or None if it's empty.
    """
    best_url, best_size = None, -1
    for candidate in srcset.split(","):
        parts = candidate.split()
        if not parts:
            continue
        size = 0
        if len(parts) > 1:
            number = re.match(r"[\d.]+", parts[1])
            size = float(number.group()) if number else 0
        if size > best_size:
            best_url, best_size = parts[0], size
    return best_url


class PageImagesParser(HTMLParser):
    """
    Collects the page's title and one image URL for each <img>, in the order they're on the page.
    """

    def __init__(self):
        super().__init__()
        self.title = ""
        self.image_urls = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if tag != "img":
            return

        attrs = dict(attrs)
        # Lazy-loaded images keep the real image in "data-src" and a tiny placeholder in "src". "srcset" has the biggest version.
        srcset = attrs.get("data-srcset") or attrs.get("srcset") or ""
        candidates = [
            get_largest_srcset_url(srcset),
            attrs.get("data-src"),
            attrs.get("data-lazy-src"),
            attrs.get("src"),
        ]
        image_url = next(
            (url for url in candidates if url and not url.startswith("data:")), None
        )
        if image_url:
            self.image_urls.append(image_url)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def get_safe_folder_name(name):
    name = re.sub(r'[\\/:*?"<>|]+', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    # Strip again after cutting: Windows drops a space or dot at the end of a folder name, and then can't find the files inside it.
    return name[:100].rstrip(" .") or "Downloaded pages"


def get_min_image_side(storage):
    """
    The "Only keep bigger images" setting of the Download tab: how many pixels the shorter side of an image has to be to be kept, or 0 when it's off (every image is kept).
    """
    if not (storage and storage.get("use_web_page_min_size")):
        return 0

    try:
        return max(0, int(float(storage.get("web_page_min_size") or 0)))
    except ValueError:
        return 0


def download_pages_from_url(url, cancel_event=None, min_side=0):
    """
    Save every image on a web page as 001.jpg, 002.jpg, ... in a new temporary folder named after the page's title, and return that folder. Delete the folder's parent when done. Raises "DownloadCancelled" (and leaves nothing behind) when "cancel_event" is set. With "min_side", the images whose shorter side is smaller than that many pixels (icons, avatars, ads) are left out.

    Only works for pages that show their images in the HTML. Pages that load them with JavaScript or need a login give none.
    """
    if urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"Not a web page URL: {url}")

    print(f"Opening {url}")
    report_progress(detail="Opening the page...")
    with requests.get(url, headers=BROWSER_HEADERS, timeout=TIMEOUT_SECONDS, stream=True) as response:
        response.raise_for_status()
        page_bytes = read_at_most(response, MAX_PAGE_BYTES)
        encoding = response.encoding
    if page_bytes is None:
        raise RuntimeError(
            f"This page is bigger than {MAX_PAGE_BYTES // (1024 * 1024)} MB, so it wasn't read (a web page is usually under 2 MB)."
        )

    # Like "requests"' own ".text": the page's charset, or a guess when it gives none, and never an error for a misspelled one.
    try:
        page_text = str(page_bytes, encoding or requests.compat.chardet.detect(page_bytes)["encoding"] or "utf-8", errors="replace")
    except (LookupError, TypeError):
        page_text = str(page_bytes, "utf-8", errors="replace")

    parser = PageImagesParser()
    parser.feed(page_text)

    # Absolute URLs, without the same image twice.
    image_urls = list(dict.fromkeys(urljoin(url, image_url) for image_url in parser.image_urls))
    print(f"Found {len(image_urls)} image(s) on the page." + (f" Keeping the ones with a shorter side of at least {min_side} px." if min_side else ""))

    folder_name = get_safe_folder_name(parser.title or urlparse(url).netloc)
    pages_folder = os.path.join(tempfile.mkdtemp(prefix="panelyze-"), folder_name)
    os.makedirs(pages_folder)

    page_number = 0
    try:
        for position, image_url in enumerate(image_urls, start=1):
            if cancel_event and cancel_event.is_set():
                raise DownloadCancelled("Download cancelled")

            # With a minimum size, some images are left out once they're looked at, so it counts the images checked and says how many were kept.
            report_progress(
                chapter=1, chapters=1, pages_done=position - 1, pages_total=len(image_urls),
                unit="images checked" if min_side else "images",
                detail=f"{page_number} kept so far" if min_side else None,
            )
            image_bytes = download_image(image_url, url)
            if image_bytes is None:
                continue

            try:
                with Image.open(io.BytesIO(image_bytes)) as image:
                    if min(image.size) < min_side:
                        continue

                    extension = SAVED_IMAGE_EXTENSIONS.get(image.format)
                    page_path = os.path.join(pages_folder, f"{page_number + 1:03d}{extension or '.png'}")
                    if extension:
                        with open(page_path, "wb") as page_file:
                            page_file.write(image_bytes)
                    else:
                        image.convert("RGB").save(page_path)
            except Exception as error:
                # Not an image Pillow can read (e.g. an SVG icon), or one too big to open safely. The next image is saved under the same number.
                print(f"Skipped an image that couldn't be opened ({error}): {image_url}")
                continue

            page_number += 1
            print(f"Saved image {page_number}: {image_url}")
    except BaseException:
        # Cancelled, or something went wrong: nothing is left behind.
        shutil.rmtree(os.path.dirname(pages_folder), ignore_errors=True)
        raise

    report_progress(pages_done=len(image_urls))

    if page_number == 0:
        shutil.rmtree(os.path.dirname(pages_folder), ignore_errors=True)
        if image_urls and min_side:
            raise RuntimeError(
                f"None of the {len(image_urls)} images on this page have a shorter side of at least {min_side} px. Turn off \"Only keep bigger images\" to save all of them."
            )
        raise RuntimeError(
            "No images found on this page. Pages that load their images with JavaScript or need a login aren't supported."
        )

    print(f"Saved {page_number} image(s) from {url}")
    return pages_folder


def download_image(image_url, page_url):
    if urlparse(image_url).scheme not in ("http", "https"):
        return None

    try:
        # Some sites only send their images to their own pages.
        with requests.get(
            image_url,
            headers={**BROWSER_HEADERS, "Referer": page_url},
            timeout=TIMEOUT_SECONDS,
            stream=True,
        ) as response:
            response.raise_for_status()
            image_bytes = read_at_most(response, MAX_IMAGE_BYTES)
    except requests.RequestException as error:
        print(f"Skipped an image that couldn't be downloaded ({error}): {image_url}")
        return None

    if image_bytes is None:
        print(f"Skipped an image bigger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB: {image_url}")
    return image_bytes
