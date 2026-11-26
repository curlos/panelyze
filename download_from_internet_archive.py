import os
import re
import shutil
import tempfile
from urllib.parse import quote, urlparse

import requests

from download_pages_from_url import get_safe_folder_name
from gui_classes.ProgressPanel import report_progress
from utils import DownloadCancelled, extract_comic_files_to_folder

TIMEOUT_SECONDS = 60

# The comic file to download when an item has several, best first.
COMIC_FILE_PREFERENCE = (".cbz", ".zip", ".cbr", ".pdf")

# Files the Internet Archive makes itself from an item's scans: JPEG 2000 images (which can't be read as pages) and DAISY books.
IGNORED_FILE_ENDINGS = ("_jp2.zip", "_daisy.zip")


def is_internet_archive_url(url):
    return urlparse((url or "").strip()).hostname in ("archive.org", "www.archive.org")


def get_item_identifier(url):
    """
    "https://archive.org/details/hillman-pirates-comics-001" gives "hillman-pirates-comics-001".
    """
    match = re.match(r"^/details/([^/?#]+)", urlparse(url.strip()).path)
    if not is_internet_archive_url(url) or not match:
        raise ValueError(
            f"Not an Internet Archive item link (like https://archive.org/details/<item>): {url}"
        )
    return match.group(1)


def get_title(metadata, identifier):
    # An item with several titles has them as a list.
    title = metadata.get("title")
    if isinstance(title, list):
        title = title[0] if title else None
    return str(title or identifier)


def is_public_domain(metadata):
    # The Public Domain Mark (creativecommons.org/publicdomain/mark/1.0) or CC0 (creativecommons.org/publicdomain/zero/1.0).
    # (Like the title, it can be a list.)
    return "creativecommons.org/publicdomain/" in str(metadata.get("licenseurl") or "")


def pick_comic_file(files):
    """
    The name of the item's comic file to download: a .cbz first, then a .zip, a .cbr, and a .pdf. None if there's none.
    """
    names = [
        file.get("name", "")
        for file in files
        if file.get("source") != "metadata"
        and not file.get("name", "").lower().endswith(IGNORED_FILE_ENDINGS)
    ]
    for extension in COMIC_FILE_PREFERENCE:
        for name in names:
            if name.lower().endswith(extension):
                return name
    return None


def download_internet_archive_item(url, cancel_event=None):
    """
    Download a public-domain comic from the Internet Archive and save its pages into a new temporary folder (see "extract_comic_files_to_folder"), and return that folder. Delete the folder's parent when done. Raises "DownloadCancelled" when "cancel_event" is set.

    Items that aren't marked as public domain are refused: the Internet Archive also has unauthorized uploads of comics on sale.
    """
    identifier = get_item_identifier(url)

    print(f"Getting the Internet Archive item {identifier}")
    report_progress(detail="Getting the item's details...")
    response = requests.get(
        f"https://archive.org/metadata/{identifier}", timeout=TIMEOUT_SECONDS
    )
    response.raise_for_status()
    item = response.json()
    if not item:
        raise RuntimeError(f"No Internet Archive item called {identifier}")

    metadata = item.get("metadata", {})
    if not is_public_domain(metadata):
        raise RuntimeError(
            f"\"{get_title(metadata, identifier)}\" isn't marked as public domain on the Internet Archive, so it won't be downloaded (license: {metadata.get('licenseurl') or 'none'})."
        )

    file_name = pick_comic_file(item.get("files", []))
    if not file_name:
        raise RuntimeError(
            f"{identifier} has no comic file ({', '.join(COMIC_FILE_PREFERENCE)}) to download."
        )

    download_folder = tempfile.mkdtemp(prefix="panelyze-download-")
    try:
        # Named after the item's title (the pages' folder gets the same name), never a path from the item, so it can't be saved outside the download folder.
        comic_name = get_safe_folder_name(get_title(metadata, identifier))
        comic_path = os.path.join(
            download_folder, comic_name + os.path.splitext(file_name)[1].lower()
        )
        file_url = (
            f"https://archive.org/download/{quote(identifier)}/{quote(file_name)}"
        )
        print(f"Downloading {file_name}")
        with requests.get(
            file_url, stream=True, timeout=TIMEOUT_SECONDS
        ) as file_response:
            file_response.raise_for_status()
            total_bytes = int(file_response.headers.get("Content-Length") or 0)
            downloaded_bytes = 0
            with open(comic_path, "wb") as comic_file:
                for chunk in file_response.iter_content(chunk_size=1024 * 1024):
                    if cancel_event and cancel_event.is_set():
                        raise DownloadCancelled("Download cancelled")

                    comic_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    if total_bytes:
                        report_progress(
                            chapter=1,
                            chapters=1,
                            unit="MB",
                            detail=None,
                            pages_done=round(downloaded_bytes / 1_000_000),
                            pages_total=round(total_bytes / 1_000_000) or 1,
                        )

        report_progress(
            pages_done=None, pages_total=None, detail="Opening the comic file..."
        )
        return extract_comic_files_to_folder([comic_path])
    finally:
        shutil.rmtree(download_folder, ignore_errors=True)
