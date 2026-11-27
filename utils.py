from collections.abc import Callable
import contextlib
import errno
from functools import wraps
import io
import json
import re
import tempfile
import shutil
import time
import subprocess
import sys
import os
import platform
import threading
import zipfile
import flet as ft
import math
from dotenv import load_dotenv

# Newer versions of Hugging Face's "transformers" also download a converted copy of a model ("model.safetensors", made by Hugging Face) next to the one Panelyze asks for, in the background. Panelyze never uses it, and it doubles the download (2 GB more for Magi). This is the library's own switch to turn that off, for every model (Magi, the emotion model, and any later one). Set here because every part of the app imports this file first.
os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "true")


def open_directory(path):
    if platform.system() == "Darwin":  # macOS
        subprocess.run(["open", path])
    elif platform.system() == "Windows":  # Windows
        os.startfile(path)  # pyright: ignore[reportAttributeAccessIssue]
    elif platform.system() == "Linux":  # Linux
        subprocess.run(["xdg-open", path])
    else:
        raise OSError(f"Unsupported operating system: {platform.system()}")


def add_line_to_terminal_output_list_view(
    terminal_output_list_view, text, color="white"
):
    # Imported here to avoid a circular import (gui_classes imports utils).
    from gui_classes import AppOutput

    # Normally everything goes through "AppOutput" so it's also saved to the log file and shown in the right order.
    if AppOutput.current_app_output:
        AppOutput.current_app_output.add_line(text, color)
    elif terminal_output_list_view:
        line = ft.Text(color=color)
        set_text_with_links(line, text)
        terminal_output_list_view.controls.append(line)
        terminal_output_list_view.update()


# A web link in a line of text. A "." or ")" right after it (the end of the sentence), or a quote or "]" around it, isn't part of it.
WEB_LINK = re.compile(r"https?://[^\s()<>'\"\]]+?(?=[.,;:!?)'\"\]]*(?:\s|$))")


def set_text_with_links(text_control, text):
    """
    Show "text" in "text_control" (an "ft.Text"), with any web link in it (e.g. where a model is downloaded from) clickable: it opens in the browser.
    """
    from gui_classes import Nord

    if not WEB_LINK.search(text):
        text_control.value = text
        text_control.spans = None
        return

    spans = []
    position = 0
    for match in WEB_LINK.finditer(text):
        if match.start() > position:
            spans.append(ft.TextSpan(text[position : match.start()]))
        url = match.group()
        link_style = ft.TextStyle(
            color=Nord.ACCENT, decoration=ft.TextDecoration.UNDERLINE
        )
        # "page.launch_url" opens it in the browser (the desktop app's default browser).
        spans.append(
            ft.TextSpan(
                url,
                style=link_style,
                on_click=lambda e, url=url: e.page.launch_url(url),
            )
        )
        position = match.end()
    if position < len(text):
        spans.append(ft.TextSpan(text[position:]))
    text_control.value = None
    text_control.spans = spans


def get_newest_subfolder(directory):
    """
    The folder inside "directory" that was changed most recently, or None if there isn't one.
    """
    if not os.path.isdir(directory):
        return None

    subfolders = [
        entry.path
        for entry in os.scandir(directory)
        if entry.is_dir() and not entry.name.startswith(".")
    ]

    return max(subfolders, key=os.path.getmtime, default=None)


def get_last_directory(directory_path):
    return os.path.basename(directory_path.rstrip("/\\"))


# 4K: the longest side an upscaled image can have when "Don't upscale past 4K" is on.
MAX_UPSCALED_IMAGE_SIDE = 3840
# The most pixels an upscaled image can have, even with the 4K limit off: 16,384 x 16,384 (268 megapixels, the biggest canvas of drawing apps like Procreate). An image has to fit in memory as it's upscaled (about 3 GB at this size), and a 4K page at 32x would be 8.5 billion pixels (about 25 GB).
MAX_UPSCALED_PIXELS = 16_384 * 16_384


class NotEnoughSpace(OSError):
    """
    There isn't enough free space on the computer for something (see "check_free_space").
    """


def get_closest_existing_folder(path):
    """
    "path", or the closest folder above it that's there (e.g. the models folder before the first download). None when even its drive isn't there (e.g. an unplugged USB drive on Windows, whose root is its own parent).
    """
    folder = os.path.abspath(path)
    while not os.path.exists(folder):
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent
    return folder


def get_free_space(path):
    """
    The free bytes on the disk "path" is on, or None when that can't be told (its drive isn't there, or the disk can't be asked).
    """
    folder = get_closest_existing_folder(path)
    if folder is None:
        return None
    try:
        return shutil.disk_usage(folder).free
    except OSError:
        return None


def check_free_space(folder, needed_size, what):
    """
    Raise "NotEnoughSpace" (with a message that says how much is needed and free) if the disk "folder" is on has less than "needed_size" bytes free. "folder" doesn't have to exist yet.
    """
    from gui_classes.ProgressPanel import format_size

    free_size = get_free_space(folder)
    # When it can't be told, the job just tries (and a full disk still gets a clear message, see "get_error_text").
    if free_size is not None and free_size < needed_size:
        error = NotEnoughSpace(
            f"Not enough space on this computer for {what}: it needs {format_size(needed_size)}, and {format_size(free_size)} is free. Settings → Storage shows what Panelyze keeps, and what can be deleted."
        )
        error.errno = errno.ENOSPC
        raise error


def get_error_text(error):
    """
    The message to show for an error that stopped a job. Running out of disk space (raised by Python as "[Errno 28] No space left on device", sometimes inside another error, like a failed download) gets a clear message instead.
    """
    cause = error
    seen = set()
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if isinstance(cause, NotEnoughSpace):
            return str(cause)
        if getattr(cause, "errno", None) == errno.ENOSPC:
            return "The computer ran out of space while saving. Free up some space (Settings → Storage shows what Panelyze keeps, and what can be deleted), then try again."
        cause = cause.__cause__ or cause.__context__
    return str(error)


def get_capped_upscale_ratio(
    width, height, upscale_ratio, max_side=MAX_UPSCALED_IMAGE_SIDE
):
    """
    The upscale ratio to actually run waifu2x with, so it doesn't waste time making an image far bigger than "max_side" (e.g. upscaling an 8000px image 16x would take forever for no visible gain).

    Returns the smallest ratio (1, 2, 4, ... up to "upscale_ratio") that makes the longest side reach "max_side". The result can still be a bit bigger than "max_side" (e.g. 1000px x 4 = 4000px), so it's shrunk to "max_side" afterwards. An image that's already "max_side" or bigger isn't upscaled at all (ratio 1).
    """
    longest_side = max(width, height)
    capped_ratio = 1

    while capped_ratio < int(upscale_ratio) and longest_side * capped_ratio < max_side:
        capped_ratio *= 2

    return capped_ratio


# "Best" can stop one 2x pass early when the image is then at most this much under 4K. Its last pass is by far the slowest (4x the pixels of the one before). The image stays a bit under 4K: stretching it up afterwards would add no detail.
MAX_SHORT_OF_4K_AFTER_BEST = 1.5


def get_best_upscale_ratio(
    width, height, upscale_ratio, max_side=MAX_UPSCALED_IMAGE_SIDE
):
    """
    Like "get_capped_upscale_ratio", for "Best": one 2x pass less when the last pass would go far past "max_side" (e.g. a 429px panel: 8x is 3432px, 16x would be 6864px), as long as "Best" still does at least one pass. The image then stays a bit under "max_side" (at least "max_side" / MAX_SHORT_OF_4K_AFTER_BEST).
    """
    capped_ratio = get_capped_upscale_ratio(width, height, upscale_ratio, max_side)
    if (
        capped_ratio > 2
        and max_side / (max(width, height) * capped_ratio // 2)
        <= MAX_SHORT_OF_4K_AFTER_BEST
    ):
        return capped_ratio // 2
    return capped_ratio


def copy_picked_images_to_folder(image_paths):
    """
    When individual images are picked instead of a folder, copy them into a new temporary folder so every tool can process them exactly like a picked folder.

    The folder is named after the images (e.g. "Ch 1 - page_05" or "Ch 1 - 3 images"), so their output goes into its own folder and never overwrites the output of the whole chapter. Delete the returned folder's parent when done.
    """
    parent_folder_name = get_last_directory(os.path.dirname(image_paths[0]))

    if len(image_paths) == 1:
        image_name = os.path.splitext(os.path.basename(image_paths[0]))[0]
        # Windows drops a space or dot at the end of a folder name ("page .png"), and then can't find the files inside it.
        folder_name = f"{parent_folder_name} - {image_name}".rstrip(" .")
    else:
        folder_name = f"{parent_folder_name} - {len(image_paths)} images"

    picked_images_folder = os.path.join(
        tempfile.mkdtemp(prefix="panelyze-"), folder_name
    )
    os.makedirs(picked_images_folder)

    for image_path in image_paths:
        shutil.copy2(image_path, picked_images_folder)

    return picked_images_folder


# Comic files that can be picked as input. .cbz, .zip and .epub are zip files with the pages inside, and .cbr is a RAR file.
COMIC_FILE_EXTENSIONS = (".cbz", ".zip", ".epub", ".cbr", ".pdf")

# How sharp PDF pages are rendered (most comic PDFs are made for about 150-300 DPI).
PDF_RENDER_DPI = 200


def is_comic_file(file_name):
    return file_name.lower().endswith(COMIC_FILE_EXTENSIONS)


def pluralize(count, word):
    # With commas in the thousands, like the Status view: "5,497 pages".
    return f"{count:,} {word}" if count == 1 else f"{count:,} {word}s"


def count_comic_file_pages(comic_path):
    """
    The number of pages in a comic file, or None when that can't be told cheaply (.cbr files are RAR files, which are only opened when they're processed).
    """
    try:
        if comic_path.lower().endswith(".pdf"):
            import pypdfium2

            pdf = pypdfium2.PdfDocument(comic_path)
            try:
                return len(pdf)
            finally:
                pdf.close()

        if comic_path.lower().endswith(".cbr"):
            return None

        with zipfile.ZipFile(comic_path) as comic_file:
            return sum(
                1
                for name in comic_file.namelist()
                if not name.startswith("__MACOSX/")
                and is_comic_page_file(os.path.basename(name))
            )
    except Exception:
        return None


def get_input_summary(input_directory="", image_paths=(), comic_paths=()):
    """
    A short description of what was picked, shown under it: "3 chapters · 87 pages", "12 images", or a warning when a folder has no images.
    """
    if image_paths:
        return pluralize(len(image_paths), "image")

    if comic_paths:
        # Each comic file becomes a chapter.
        summary = pluralize(len(comic_paths), "chapter")
        page_counts = [count_comic_file_pages(comic_path) for comic_path in comic_paths]
        if None not in page_counts:
            summary += (
                f" · {pluralize(sum(count or 0 for count in page_counts), 'page')}"
            )
        return summary

    image_folders = (
        list(get_image_folders(input_directory))
        if os.path.isdir(input_directory)
        else []
    )
    page_count = sum(len(images) for _, images in image_folders)

    if not page_count:
        return "No images found in this folder"
    # A single folder of images isn't worth calling "1 chapter".
    if len(image_folders) == 1:
        return pluralize(page_count, "page")
    return (
        f"{pluralize(len(image_folders), 'chapter')} · {pluralize(page_count, 'page')}"
    )


def extract_comic_files_to_folder(comic_paths):
    """
    Like "copy_picked_images_to_folder", but for comic files (.cbz, .zip, .epub, .pdf): their pages are saved into a new temporary folder, so every tool can process them exactly like a picked folder.

    One file gives a folder named after it with its pages ("Invincible 001/001.jpg"). Several files give a folder with one chapter folder for each of them ("Comics - 2 comic files/Invincible 001/001.jpg"). Delete the returned folder's parent when done.
    """
    for comic_path in comic_paths:
        if not is_comic_file(comic_path):
            raise ValueError(f"Not a comic file: {comic_path}")

    def get_name(comic_path):
        # Windows drops a space or dot at the end of a folder name ("Issue 1 .cbz"), and then can't find the pages inside it.
        return os.path.splitext(os.path.basename(comic_path))[0].rstrip(" .") or "Comic"

    if len(comic_paths) == 1:
        folder_name = get_name(comic_paths[0])
    else:
        parent_folder_name = get_last_directory(os.path.dirname(comic_paths[0]))
        folder_name = f"{parent_folder_name} - {len(comic_paths)} comic files"

    comic_files_folder = os.path.join(tempfile.mkdtemp(prefix="panelyze-"), folder_name)

    try:
        for comic_path in comic_paths:
            if len(comic_paths) == 1:
                chapter_folder = comic_files_folder
            else:
                # Files with the same name but another extension (e.g. "Issue 1.cbz" and "Issue 1.pdf") must not overwrite each other's pages.
                chapter_folder = os.path.join(comic_files_folder, get_name(comic_path))
                number = 2
                while os.path.exists(chapter_folder):
                    chapter_folder = os.path.join(
                        comic_files_folder, f"{get_name(comic_path)} ({number})"
                    )
                    number += 1
            os.makedirs(chapter_folder)
            extract_comic_file(comic_path, chapter_folder)
    except BaseException:
        # A file that couldn't be opened: the pages saved so far aren't left behind.
        shutil.rmtree(os.path.dirname(comic_files_folder), ignore_errors=True)
        raise

    return comic_files_folder


def extract_comic_file(comic_path, folder):
    """
    Save the pages of one comic file into "folder" as 001.jpg, 002.png, ... in reading order.
    """
    if comic_path.lower().endswith(".pdf"):
        save_pdf_pages(comic_path, folder)
    elif comic_path.lower().endswith(".cbr"):
        save_rar_pages(comic_path, folder)
    else:
        with zipfile.ZipFile(comic_path) as comic_file:
            save_pages_in_order(
                [
                    (entry.filename, lambda entry=entry: comic_file.read(entry))
                    for entry in comic_file.infolist()
                    if not entry.is_dir()
                ],
                folder,
            )


def save_pages_in_order(entries, folder):
    """
    Save the images among "entries" ((path inside the comic file, function that reads it)) into "folder" as 001.jpg, 002.png, ... in natural order of their paths.
    """
    image_entries = sorted(
        (
            (name, read)
            for name, read in entries
            if not name.startswith("__MACOSX/")
            and is_comic_page_file(os.path.basename(name))
        ),
        key=lambda entry: [natural_sort_key(part) for part in entry[0].split("/")],
    )

    # Only the page number and the extension are used as the file name, never the path inside the file, so a file can't write outside "folder" (e.g. an entry named "../../page.png").
    for number, (name, read) in enumerate(image_entries, start=1):
        extension = os.path.splitext(name)[1].lower()
        if extension in CONVERTED_PAGE_EXTENSIONS:
            from PIL import Image

            from janai import get_8_bit_rgb_image

            # The first frame of a GIF. 16-bit scans keep their grays and see-through parts turn white, like for upscaling.
            with Image.open(io.BytesIO(read())) as image:
                get_8_bit_rgb_image(image).save(
                    os.path.join(folder, f"{number:03d}.png")
                )
            continue
        with open(os.path.join(folder, f"{number:03d}{extension}"), "wb") as page_file:
            page_file.write(read())


def save_rar_pages(cbr_path, folder):
    """
    .cbr files are RAR files, which Python can't open. bsdtar can: it's built into macOS, and into Windows 10 and 11 as "System32\\tar.exe" (another "tar" on the PATH, like Git's, may be GNU tar, which can't open RAR).
    """
    windows_tar_path = os.path.join(
        os.environ.get("SystemRoot", "C:\\Windows"), "System32", "tar.exe"
    )
    bsdtar_path = shutil.which("bsdtar") or (
        windows_tar_path if sys.platform == "win32" else "/usr/bin/bsdtar"
    )
    if not os.path.exists(bsdtar_path):
        raise RuntimeError(
            ".cbr files need bsdtar, which wasn't found (it comes with macOS and Windows)."
        )

    working_folder = tempfile.mkdtemp(prefix="panelyze-cbr-")
    extracted_folder = os.path.join(working_folder, "pages")
    try:
        # Windows' tar.exe can't read Japanese (or other non-English) letters in its arguments, so it's given a copy with a plain name, in its own folder.
        shutil.copyfile(cbr_path, os.path.join(working_folder, "comic.cbr"))
        os.makedirs(extracted_folder)
        # bsdtar refuses paths with ".." or starting with "/", so nothing is written outside "extracted_folder".
        result = subprocess.run(
            [bsdtar_path, "-xf", "comic.cbr", "-C", "pages"],
            cwd=working_folder,
            capture_output=True,
            text=True,
            errors="replace",
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Couldn't open {os.path.basename(cbr_path)}: {result.stderr.strip()}"
            )

        entries = []
        for directory, _, file_names in os.walk(extracted_folder):
            for file_name in file_names:
                path = os.path.join(directory, file_name)
                # A link could point to a file outside the comic.
                if os.path.islink(path):
                    continue
                name = os.path.relpath(path, extracted_folder).replace(os.sep, "/")
                entries.append((name, lambda path=path: open(path, "rb").read()))

        save_pages_in_order(entries, folder)
    finally:
        shutil.rmtree(working_folder, ignore_errors=True)


def save_pdf_pages(pdf_path, folder):
    import pypdfium2

    pdf = pypdfium2.PdfDocument(pdf_path)
    try:
        for number, page in enumerate(pdf, start=1):
            image = page.render(scale=PDF_RENDER_DPI / 72).to_pil()  # pyright: ignore[reportArgumentType]
            image.save(os.path.join(folder, f"{number:03d}.png"))
            page.close()
    finally:
        pdf.close()


def list_images(directory):
    """
    Full paths of the images directly inside "directory", in natural order (page_2 before page_10).
    """
    image_file_names = sorted(
        (file_name for file_name in os.listdir(directory) if is_image_file(file_name)),
        key=natural_sort_key,
    )
    return [os.path.join(directory, file_name) for file_name in image_file_names]


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
# Page formats the tools don't read, which comic files sometimes have. They're saved as PNG when a comic file is opened.
CONVERTED_PAGE_EXTENSIONS = (".gif", ".bmp", ".tif", ".tiff")

# The dialogue Panel-By-Panel read on the pages, saved next to the panels as a list of lines for each panel (in the same order as the images). Images To Video uses it instead of reading the text on every panel again.
PANEL_TEXT_FILE_NAME = "panel-text.json"
# What a chapter's panels were made from (its pages and the settings), so a chapter that's already split can be skipped (see "get_panels_info").
PANELS_INFO_FILE_NAME = "panels-info.json"

# The reading direction ("rtl", "ltr", "4koma" or "webtoon") the MangaDex download found for a chapter, saved next to its images. Panel-By-Panel and Images To Video use it when the Reading Direction is "Automatic".
READING_DIRECTION_FILE_NAME = "reading-direction.txt"


def is_image_file(file_name):
    # Skip hidden files like macOS "._page_1.jpg" metadata files. They end in an image extension but aren't real images.
    if file_name.startswith("."):
        return False

    return file_name.lower().endswith(IMAGE_EXTENSIONS)


def is_comic_page_file(file_name):
    """
    An image in a comic file: one the tools read, or one saved as PNG when it's opened ("CONVERTED_PAGE_EXTENSIONS").
    """
    return is_image_file(file_name) or (
        not file_name.startswith(".")
        and file_name.lower().endswith(CONVERTED_PAGE_EXTENSIONS)
    )


def construct_directory_structure(path):
    def traverse_directory(current_path):
        directory_content = {}

        # List all entries in the current directory
        try:
            entries = os.listdir(current_path)
        except PermissionError:
            return {}  # Skip directories without permissions

        images = []
        for entry in entries:
            entry_path = os.path.join(current_path, entry)

            # Skip hidden files and folders (".DS_Store", "._page_1.jpg", ".git", etc.)
            if entry.startswith("."):
                continue

            if os.path.isdir(entry_path):
                # Recursively traverse subdirectories
                directory_content[entry] = traverse_directory(entry_path)
            # "isfile" also skips a shortcut (symlink) to an image that's gone.
            elif is_image_file(entry) and os.path.isfile(entry_path):
                # Add image files and their sizes to the list
                image_size = os.path.getsize(entry_path)
                images.append({"name": entry, "size": image_size})

        if images:
            # Sort images by their filenames
            images.sort(key=lambda x: natural_sort_key(x["name"]))
            directory_content["__images__"] = images

        # Sort the keys of the current directory level
        sorted_directory_content = dict(sorted(directory_content.items()))
        return sorted_directory_content

    # Start traversal from the given path
    root_name = os.path.basename(path)
    return {root_name: traverse_directory(path)}


def is_showing_all_output_in_app():
    from gui_classes import AppOutput

    return AppOutput.current_app_output is not None


# A small file in each folder that was downloaded, saying where it's from and how many pages (or images) it has. A download is only skipped as "already downloaded" when this is still true of the folder, so deleting the folder or some of its pages means it's downloaded again.
DOWNLOAD_INFO_FILE_NAME = "download-info.json"


def count_images(folder):
    return sum(1 for file_name in os.listdir(folder) if is_image_file(file_name))


def write_download_info(folder, **info):
    with open(
        os.path.join(folder, DOWNLOAD_INFO_FILE_NAME), "w", encoding="utf-8"
    ) as info_file:
        json.dump(info, info_file)


def read_download_info(folder):
    """
    What "write_download_info" saved in the folder, or None if there's none.
    """
    try:
        with open(
            os.path.join(folder, DOWNLOAD_INFO_FILE_NAME), encoding="utf-8"
        ) as info_file:
            info = json.load(info_file)
    except (OSError, ValueError):
        return None
    return info if isinstance(info, dict) else None


def is_download_intact(folder, info):
    """
    Whether the folder still has all the pages its download info says it had. Images added to it later (by the user) don't count against it, so the folder isn't downloaded again and replaced, which would delete them.
    """
    return (
        bool(info.get("pages"))
        and os.path.isdir(folder)
        and count_images(folder) >= info["pages"]
    )


def find_downloaded_folder(directory, only_if_intact=True, **match):
    """
    The folder inside "directory" whose download info has all of "match", as (folder, info), or None. With "only_if_intact" (the default) that's only a folder that still has all its pages; without it a folder with pages missing is found too (to be replaced).
    """
    if not os.path.isdir(directory):
        return None

    for name in sorted(os.listdir(directory)):
        folder = os.path.join(directory, name)
        info = read_download_info(folder) if os.path.isdir(folder) else None
        if info and all(info.get(key) == value for key, value in match.items()):
            if not only_if_intact or is_download_intact(folder, info):
                return folder, info
    return None


def get_library_directory(output_directory, storage):
    """
    The Download tab's folder when "output_directory" is another one (a Pipeline's Download step), so what was already downloaded there can be copied instead of downloaded again. None when they're the same folder.
    """
    from default_settings import get_output_directory

    if not storage:
        return None
    library_directory = get_output_directory(storage, "output_directory_mangadex")
    if get_comparable_path(library_directory) == get_comparable_path(output_directory):
        return None
    return library_directory


def copy_from_library(folder, library_directory, output_directory, replace=False):
    """
    Copies a downloaded folder (inside "library_directory") to the same place inside "output_directory", and returns the copy's path. A folder with the same name already there is never mixed with it: it gets " (2)", " (3)", ... added, or with "replace" (a comix.to chapter's own folder, holding an unfinished copy of it), the old one is replaced.
    """
    destination = os.path.join(
        output_directory, os.path.relpath(folder, library_directory)
    )
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    if (
        replace
        and os.path.exists(destination)
        and not paths_overlap(destination, folder)
    ):
        shutil.rmtree(destination)
    name, number = destination, 2
    while os.path.exists(destination):
        destination = f"{name} ({number})"
        number += 1
    shutil.copytree(folder, destination)
    return destination


class DownloadSummary(str):
    """
    What a download saved, in one line (it's a string, to show), and the folder it was saved in ("folder", to open it in Finder when it's done).
    """

    folder: str | None

    def __new__(cls, text, folder=None):
        summary = super().__new__(cls, text)
        summary.folder = folder
        return summary


class DownloadCancelled(Exception):
    """
    Raised when the user cancels a download. It's not an error, so it's shown as "cancelled" instead.
    """


CANCEL_TEXT = "Cancel"
CANCELLING_TEXT = "Cancelling..."


def set_cancel_click(
    cancel_button, stop, message: str | Callable[[], str] = "Cancelling..."
):
    """
    What clicking "cancel_button" does: "stop" (what stops the job), and right away it can't be clicked again, says "Cancelling..." and shows "message" (when it will stop, e.g. "Cancelling after the image being upscaled...") in the Status view. The job's tab puts the button back with "reset_cancel_button" when the job is over.
    """

    def handle_click(e):
        if getattr(cancel_button, "disabled", False):
            return
        cancel_button.disabled = True
        cancel_button.text = CANCELLING_TEXT
        try:
            cancel_button.update()
        except Exception:
            pass

        from gui_classes.ProgressPanel import report_cancelling

        report_cancelling(message() if callable(message) else message)
        stop()

    cancel_button.on_click = handle_click
    # Cancel was already clicked before the job said what it stops (e.g. while a download was starting), so it's stopped now instead of never.
    if getattr(cancel_button, "text", None) == CANCELLING_TEXT:
        stop()


def reset_cancel_button(cancel_button):
    cancel_button.disabled = False
    cancel_button.text = CANCEL_TEXT


def get_cancel_event(cancel_button=None, message="Cancelling the download..."):
    """
    A flag that's set when "cancel_button" is clicked, for a download to check as it goes.
    """
    cancel_event = threading.Event()
    if cancel_button:
        set_cancel_click(cancel_button, cancel_event.set, message)
    return cancel_event


class ProcessManager:
    def __init__(self):
        self.process = None  # To store the running process
        self.cancelled = False

    def monitor_terminal_output(
        self,
        terminal_command: list[str],
        terminal_output_list_view: ft.ListView | None = None,
        output_directory: str = "",
        on_line=None,
    ):
        lines = []

        # Make a shallow copy of the OS environment variables.
        env = os.environ.copy()

        # Ensures that the subprocess writes output immediately to stdout/stderr without buffering so we data can be processed line-by-line in real-time programatically.
        # We need to take of the two running process with BOTH "PYTHONUNBUFFERED" (parent process - the running "download_from_mangadex.py" file) and bufsize=1 (subprocess) below.
        env["PYTHONUNBUFFERED"] = "1"
        # The output is read as UTF-8 below. Without this, Python on Windows writes it in an older encoding, and Japanese titles come out as "呪術".
        env["PYTHONIOENCODING"] = "utf-8"

        # Open a child "process" (it's a child because it's opened within the parent process, the process that executes the "download_from_mangadex.py" file)
        self.process = subprocess.Popen(
            terminal_command,
            stdout=subprocess.PIPE,  # Redirected to a PIPE so that the parent process (this python file) can manipulate the output and error lines in the code below instead of in the terminal.
            stderr=subprocess.STDOUT,  # Merge errors into the same stream so they're read in order with the normal output.
            bufsize=0,  # Don't wait for a buffer to fill up. Read the output as soon as it's written.
            env=env,  # Use the modified "env" variable so that it takes "PYTHONUNBUFFERED" which will give us access to each line output immediately instead of after the program is done executing.
        )
        # Cancelled while it was being started.
        if self.cancelled:
            self.process.terminate()
        # newline="" keeps "\r" as it is (instead of turning it into a new line), so progress bars that redraw themselves with "\r" show up as one live line instead of hundreds of lines.
        assert self.process.stdout, "The command's output wasn't piped."
        process_output = io.TextIOWrapper(
            self.process.stdout, encoding="utf-8", errors="replace", newline=""
        )

        try:
            # Read line-by-line until the process closes its output. Unlike stopping as soon as the process exits, this never drops the last lines that were still sitting in the pipe.
            for line in process_output:
                # Printed output shows up in the real terminal, the app's terminal and the log file (see "AppOutput").
                print(line, end="", flush=True)

                if not is_showing_all_output_in_app():
                    add_line_to_terminal_output_list_view(
                        terminal_output_list_view, line.strip()
                    )

                lines.append(line)

                if on_line:
                    on_line(line)

            self.process.wait()
        except Exception as e:
            exception_str = f"An error occurred: {e}"

            print(exception_str)
            # Not left running on its own (e.g. waifu2x still reading a folder that's about to be deleted).
            self.process.kill()
            self.process.wait()
        finally:
            if self.process.returncode == 0:
                print("Command executed successfully!")

                if output_directory:
                    # Open the directory that contains the downloads.
                    open_directory(output_directory)

            else:
                print(f"Command failed with return code {self.process.returncode}")

        return lines

    def cancel_process(self):
        # Also before the process has started: "monitor_terminal_output" then stops it as soon as it starts.
        self.cancelled = True
        if self.process:
            self.process.terminate()  # Gracefully terminate the process
            print("Process terminated by user.")


def download_file(url, path, name="the file"):
    """
    Save "url" to "path". Uses certifi's list of certificates, like "requests" does: on Windows, Python's own check can fail for a site Windows hasn't fully trusted yet ("CERTIFICATE_VERIFY_FAILED"). The Status view shows how much of "name" is downloaded ("Downloading waifu2x: 12 MB of 40 MB").
    """
    import ssl
    import urllib.request

    import certifi

    from gui_classes.ProgressPanel import (
        format_size,
        get_download_detail,
        report_progress,
    )

    context = ssl.create_default_context(cafile=certifi.where())
    # The timeout is for each read, not the whole download: a connection that stops answering fails after a minute instead of hanging forever.
    try:
        with (
            urllib.request.urlopen(url, context=context, timeout=60) as response,
            open(path, "wb") as file,
        ):
            # 0 when the server doesn't say how big it is.
            total_size = int(response.headers.get("Content-Length") or 0)
            downloaded_size = 0
            while chunk := response.read(1024 * 1024):
                file.write(chunk)
                downloaded_size += len(chunk)
                of_total = f" of {format_size(total_size)}" if total_size else ""
                report_progress(
                    detail=get_download_detail(
                        f"Downloading {name}: {format_size(downloaded_size)}{of_total}"
                    ),
                    fraction_done=downloaded_size / total_size if total_size else None,
                )
    finally:
        # Also when it fails, so the Status view doesn't keep saying it's downloading.
        report_progress(detail=None, fraction_done=None)


class PartialDownloadNotSupported(Exception):
    """
    The server sends whole files only (see "RemoteFile").
    """


class RemoteFile(io.RawIOBase):
    """
    A file on a web server, read like a file on the disk: each read downloads only the bytes it asks for (an HTTP "Range" request). With it, "zipfile" can take a few files out of a big zip on GitHub without downloading the rest. Raises "PartialDownloadNotSupported" if the server only sends whole files.
    """

    def __init__(self, url):
        import requests

        # One connection for every read (each one is a request).
        self.session = requests.Session()
        # "stream", so a server that sends the whole file instead isn't downloaded here just to find that out.
        with self.session.get(
            url, headers={"Range": "bytes=0-0"}, timeout=60, stream=True
        ) as response:
            response.raise_for_status()
            # "bytes 0-0/433383160" (or ".../*" when the server doesn't know the size).
            total_size = response.headers.get("Content-Range", "").split("/")[-1]
            if response.status_code != 206 or not total_size.isdigit():
                raise PartialDownloadNotSupported(url)
            # Where GitHub sent it (a download link that's good for about an hour).
            self.url = response.url
        self.size = int(total_size)
        self.position = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        start = {io.SEEK_SET: 0, io.SEEK_CUR: self.position, io.SEEK_END: self.size}
        self.position = start[whence] + offset
        return self.position

    def readinto(self, buffer):
        end = min(self.position + len(buffer), self.size) - 1
        if end < self.position:
            return 0
        import requests

        # A few tries, so one dropped connection doesn't stop a download of many parts.
        for _ in range(2):
            try:
                response = self.get_part(end)
                break
            except requests.RequestException:
                time.sleep(2)
        else:
            response = self.get_part(end)
        if response.status_code != 206:
            raise OSError("The server stopped sending parts of the file.")
        data = response.content
        buffer[: len(data)] = data
        self.position += len(data)
        return len(data)

    def get_part(self, end):
        response = self.session.get(
            self.url, headers={"Range": f"bytes={self.position}-{end}"}, timeout=60
        )
        response.raise_for_status()
        return response


def open_remote_zip(url):
    """
    A zip on a web server, opened without downloading it (see "RemoteFile"): only the list of its files is read, and then only the files that are opened.
    """
    # Reads of at least 1 MB, so the small reads "zipfile" makes aren't each a request.
    return zipfile.ZipFile(io.BufferedReader(RemoteFile(url), buffer_size=1024 * 1024))


def save_zip_files(zip_file, files, progress_name=None):
    """
    Save some of a zip's files: "files" is a list of (the file in the zip, the path to save it at). With "progress_name", the Status view shows how much is saved, unzipped, as for a download (for a zip on a server, see "open_remote_zip", saving is the download): "Downloading waifu2x: 12 MB of 54 MB", with the bar. Each file is saved under a temporary name first, so one that stops half-way is never left behind.
    """
    from gui_classes.ProgressPanel import (
        format_size,
        get_download_detail,
        report_progress,
    )

    total_size = sum(member.file_size for member, _ in files)
    done_size = 0
    try:
        for member, path in files:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with zip_file.open(member) as source, open(f"{path}.tmp", "wb") as target:
                while chunk := source.read(8 * 1024 * 1024):
                    target.write(chunk)
                    done_size += len(chunk)
                    if progress_name:
                        report_progress(
                            detail=get_download_detail(
                                f"Downloading {progress_name}: {format_size(done_size)} of {format_size(total_size)}"
                            ),
                            fraction_done=done_size / total_size,
                        )
            os.replace(f"{path}.tmp", path)
    finally:
        if progress_name:
            report_progress(detail=None, fraction_done=None)
        for _, path in files:
            if os.path.exists(f"{path}.tmp"):
                os.remove(f"{path}.tmp")


def get_folder_size(folder):
    total = 0
    for directory, _, file_names in os.walk(folder):
        for file_name in file_names:
            try:
                # A link counts as itself, not what it points to: the Hugging Face cache links each file to its copy in the same folder, which would be counted twice.
                total += os.lstat(os.path.join(directory, file_name)).st_size
            except OSError:
                # E.g. a temporary file that was just renamed.
                continue
    return total


@contextlib.contextmanager
def report_folder_download(name, folder, total_size, interval=1.0):
    """
    For a download done by another library (e.g. Hugging Face's download of Magi): while it runs, the Status view shows how much of "name" is downloaded, like "download_file" does, by watching "folder" grow. Nothing is shown when nothing is downloaded (it was already there).
    """
    from gui_classes.ProgressPanel import (
        format_size,
        get_download_detail,
        report_progress,
    )

    start_size = get_folder_size(folder)
    stop = threading.Event()

    def watch():
        while not stop.wait(interval):
            downloaded_size = get_folder_size(folder) - start_size
            if downloaded_size > 0:
                report_progress(
                    detail=get_download_detail(
                        f"Downloading {name}: {format_size(downloaded_size)} of {format_size(total_size)}"
                    ),
                    fraction_done=min(downloaded_size / total_size, 1),
                )

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        yield
    finally:
        stop.set()
        watcher.join()
        report_progress(detail=None, fraction_done=None)


# Where waifu2x is downloaded the first time it's needed, if it isn't installed (see "download_waifu2x" in waifu2x.py).
DOWNLOADED_WAIFU2X_FOLDER = os.path.expanduser(
    "~/Library/Application Support/Panelyze/waifu2x"
)


def get_waifu2x_path():
    """
    Where the "waifu2x-ncnn-vulkan" program is: inside the packaged app (bundled by "build_mac_app.sh"), or downloaded by the app (from source). None if it isn't downloaded yet. A copy installed on the computer (e.g. on the PATH) isn't used: everyone gets the same version, and Settings → Storage can show and delete the app's own copy.
    """
    bundled_waifu2x_path = os.path.join(
        getattr(sys, "_MEIPASS", ""), "waifu2x", "waifu2x-ncnn-vulkan"
    )

    if is_running_as_packaged_app() and os.path.exists(bundled_waifu2x_path):
        return bundled_waifu2x_path

    program_name = (
        "waifu2x-ncnn-vulkan.exe" if sys.platform == "win32" else "waifu2x-ncnn-vulkan"
    )
    downloaded_waifu2x_path = os.path.join(DOWNLOADED_WAIFU2X_FOLDER, program_name)
    return downloaded_waifu2x_path if os.path.exists(downloaded_waifu2x_path) else None


def is_running_as_packaged_app():
    """
    True when running from an app packaged with "flet pack" (PyInstaller). In that case "sys.executable" is the app itself, not Python, so "sys.executable -m <module>" would open another copy of the app instead of running the module.
    """
    return getattr(sys, "frozen", False)


def get_all_mangadex_languages():
    """
    The languages MangaDex Downloader can download in, read straight from its code. This is instant and needs no internet (it used to run "mangadex-downloader --list-language" in a separate process on every startup).
    """
    from mangadex_downloader.language import Language

    mangadex_languages = [
        {"name": language.name, "code": language.value}
        for language in Language
        # "Other" has no language code, so it can't be passed to "--language".
        if language.value
    ]

    mangadex_languages_by_name = {lang["name"]: lang for lang in mangadex_languages}

    return {
        "mangadex_languages": mangadex_languages,
        "mangadex_languages_by_name": mangadex_languages_by_name,
    }


def replace_extension(file_name: str, new_extension: str) -> str:
    """
    Replace the extension of a given file name with a new extension.

    Args:
        file_name (str): The original file name.
        new_extension (str): The new extension to replace with (e.g., "jpg" or ".jpg").

    Returns:
        str: The file name with the new extension.
    """
    # Ensure the new extension starts with a dot
    formatted_extension = f".{new_extension.lstrip('.')}"

    # Split the file name and replace the extension
    base_name = os.path.splitext(file_name)[0]
    return base_name + formatted_extension


def get_input_and_output_error(input_directory, output_directory):
    """
    What's wrong with the picked input and output directories, or None if they're fine.
    """
    if not input_directory and not output_directory:
        return "ERROR: Please enter valid input and output directories."
    elif not input_directory:
        return "ERROR: Please enter a valid input directory."
    elif not output_directory:
        return "ERROR: Please enter a valid output directory."
    elif not os.path.isdir(input_directory):
        return f"ERROR: The input directory no longer exists: {input_directory}"
    elif output_dir_would_overwrite_input(input_directory, output_directory):
        return "ERROR: The output directory can't be inside the input directory or be its parent directory. Otherwise, the original images could be overwritten. Please pick a different output directory."

    return None


def get_image_folders(input_directory):
    """
    Every folder inside "input_directory" (including itself) that has images, as (folder path, list of its images), in natural order.
    """
    input_parent_directory = os.path.dirname(os.path.normpath(input_directory))

    def walk(level, relative_path):
        for key, value in level.items():
            if key == "__images__":
                yield os.path.join(input_parent_directory, relative_path), value
            else:
                yield from walk(
                    value, os.path.join(relative_path, key) if relative_path else key
                )

    yield from walk(construct_directory_structure(input_directory), "")


def output_dir_would_overwrite_input(input_directory, output_directory):
    """
    Outputs are saved to "output_directory/<input folder name>/...". So, if the output directory is the input directory's parent, the output paths would be the exact same as the input paths and the original images would be overwritten. If the output directory is inside the input directory, then the outputs would get processed again the next time.
    """
    input_directory = get_comparable_path(input_directory)
    output_directory = get_comparable_path(output_directory)

    output_is_parent_of_input = output_directory == os.path.dirname(input_directory)

    return output_is_parent_of_input or is_same_or_inside(
        output_directory, input_directory
    )


def get_comparable_path(path):
    """
    The real path, in lower case on Mac and Windows, where disks ignore case ("Manga" and "manga" are the same folder).
    """
    path = os.path.normcase(os.path.realpath(path))
    return path.casefold() if sys.platform == "darwin" else path


def is_same_or_inside(path, parent_path):
    """
    Returns True if "path" is "parent_path" itself or somewhere inside it.
    """
    path = get_comparable_path(path)
    parent_path = get_comparable_path(parent_path)

    try:
        return os.path.commonpath([path, parent_path]) == parent_path
    except ValueError:
        # On Windows, paths on different drives (C:\ vs D:\) have no common path.
        return False


def paths_overlap(path_a, path_b):
    """
    Returns True if the two paths are the same or one is inside the other.
    """
    return is_same_or_inside(path_a, path_b) or is_same_or_inside(path_b, path_a)


def get_panels_folder(output_directory, relative_path, group_by_page=False):
    """
    Where Panel-By-Panel saves a chapter's panels: "<output>/One Piece/Ch 1", like every other tab, or "<output>/One Piece (grouped by page)/Ch 1" with a folder for each page. The two never mix, also not in the series' folder that the next tab reads.
    """
    if group_by_page:
        first_folder, *other_folders = os.path.normpath(relative_path).split(os.sep)
        relative_path = os.path.join(
            f"{first_folder} (grouped by page)", *other_folders
        )
    return os.path.join(output_directory, relative_path)


def remove_old_panels(folder):
    """
    Delete what an earlier Panel-By-Panel run saved in "folder" (its panels, page folders, their text and reading direction), so leftovers don't mix with new panels. Only those: the output folder can be picked, so this folder might also hold other files (e.g. a downloaded chapter's pages), which are kept.
    """
    if not os.path.isdir(folder):
        return
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if name.startswith("page_") and os.path.isdir(path):
            shutil.rmtree(path)
        # Also the reading direction an earlier run saved: Magi only writes it when a download saved one, so an old one would be used for panels made in another order.
        elif (name.startswith("panel_") and is_image_file(name)) or name in (
            PANEL_TEXT_FILE_NAME,
            PANELS_INFO_FILE_NAME,
            READING_DIRECTION_FILE_NAME,
        ):
            os.remove(path)


def get_relative_output_path(chapter_directory, input_directory):
    """
    Get the path of "chapter_directory" relative to the parent of the selected "input_directory". For example, if the input directory is "/Manga/One Piece" and the chapter directory is "/Manga/One Piece/Vol 1/Ch 1", this returns "One Piece/Vol 1/Ch 1". This keeps outputs from different series apart, unlike only taking the last two directories.
    """
    input_parent_directory = os.path.dirname(os.path.normpath(input_directory))
    return os.path.relpath(chapter_directory, input_parent_directory)


def time_it(custom_execution_time_name=None):
    """Decorator to measure execution time and optionally print a custom message."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            print(f"Starting '{custom_execution_time_name or func.__name__}'...")

            result = func(*args, **kwargs)  # Call the wrapped function

            end_time = time.time()
            total_time = end_time - start_time
            print(
                f"'{custom_execution_time_name or func.__name__}' execution time: {total_time:.2f} seconds"
            )

            return result  # Return the result of the wrapped function

        return wrapper

    return decorator


def natural_sort_key(filename):
    """
    Extracts numbers from filenames for natural sorting.
    For example, 'panel_10.jpg' -> [10], so it can be sorted correctly.
    """
    return [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", filename)]


# The longest a "small" comic file image can be: sharp on any iPad (even a 12.9" iPad Pro) and on phones, while about 10x smaller than full PNGs.
SMALL_COMIC_FILE_IMAGE_SIZE = (2048, 2732)


def save_folder_as_cbz(
    folder, size="full", reading_direction=None, one_image_at_a_time=False
):
    """
    Save the images in "folder" (and its folders, e.g. one for each page) as a comic file, "<folder>.cbz" next to it, in reading order. Comic reader apps (e.g. Panels on iPhone and iPad, Mihon on Android) open it like a book. Returns its path, or None if there were no images.

    "size" is "full" (the images as they are) or "small" (WebP sized for phones and tablets, and grayscale for black and white pages: a chapter is about 15-25 MB instead of 150-250 MB).

    A "ComicInfo.xml" inside tells reader apps that read it how to show the images (see "get_comic_info"). "reading_direction" is the one picked in the app, or for "auto" (or None), the one saved next to the images.
    """
    image_paths = sorted(
        (
            os.path.join(directory, file_name)
            for directory, _, file_names in os.walk(folder)
            for file_name in file_names
            if is_image_file(file_name)
        ),
        key=lambda path: [
            natural_sort_key(part)
            for part in os.path.relpath(path, folder).split(os.sep)
        ],
    )
    if not image_paths:
        return None

    cbz_path = f"{folder.rstrip(os.sep)}.cbz"
    # Written to a temporary file first, so a half-written comic file is never left behind.
    try:
        with zipfile.ZipFile(f"{cbz_path}.tmp", "w", zipfile.ZIP_STORED) as cbz:
            for number, image_path in enumerate(image_paths, start=1):
                # Numbered with zeros in front (0001, 0002, ...), so every reader app keeps them in order.
                if size == "small":
                    cbz.writestr(
                        f"{number:04d}.webp", get_small_comic_file_image(image_path)
                    )
                else:
                    cbz.write(
                        image_path, f"{number:04d}{os.path.splitext(image_path)[1]}"
                    )
            if reading_direction in (None, "auto"):
                reading_direction = read_saved_reading_direction(folder)
            comic_info = get_comic_info(
                len(image_paths), reading_direction, one_image_at_a_time
            )
            if comic_info:
                cbz.writestr("ComicInfo.xml", comic_info)
    except BaseException:
        if os.path.exists(f"{cbz_path}.tmp"):
            os.remove(f"{cbz_path}.tmp")
        raise
    os.replace(f"{cbz_path}.tmp", cbz_path)

    print(f"Saved a comic file to read in comic reader apps: {cbz_path}")
    return cbz_path


def read_saved_reading_direction(folder):
    path = os.path.join(folder, READING_DIRECTION_FILE_NAME)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as file:
        return file.read().strip()


def get_comic_info(image_count, reading_direction, one_image_at_a_time):
    """
    The "ComicInfo.xml" for a comic file, or None if it has nothing to say. Manga (and 4-koma) is marked right to left, so pages turn the right way. With "one_image_at_a_time" (panels), every image is marked as a two-page spread, so apps in two-page view still show one panel at a time instead of putting two narrow panels side by side.
    """
    parts = []
    if reading_direction in ("rtl", "4koma"):
        parts.append("<Manga>YesAndRightToLeft</Manga>")
    if one_image_at_a_time:
        pages = "".join(
            f'<Page Image="{number}" DoublePage="true"/>'
            for number in range(image_count)
        )
        parts.append(f"<Pages>{pages}</Pages>")
    if not parts:
        return None
    return f'<?xml version="1.0" encoding="utf-8"?>\n<ComicInfo>{"".join(parts)}</ComicInfo>\n'


def get_small_comic_file_image(image_path):
    """
    The image as a small WebP for a comic file: no bigger than a tablet's screen, and grayscale if it's black and white.
    """
    from PIL import Image
    from janai import is_color_image

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        is_color = is_color_image(image)
        image.thumbnail(SMALL_COMIC_FILE_IMAGE_SIZE, Image.Resampling.LANCZOS)
        if not is_color:
            image = image.convert("L")

        output = io.BytesIO()
        image.save(output, "WEBP", quality=85, method=6)
        return output.getvalue()


def is_valid_number(value):
    """
    Checks if the input value is a valid number (int or float).
    Returns True if valid, False otherwise.
    """
    try:
        # Try converting to float (covers both int and float cases). "nan" and "inf" convert too, so reject them.
        return math.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def utils_load_dotenv():
    env_path = ".env"
    load_dotenv(env_path)


def modify_filename(filepath, suffix):
    # Get the file directory, base name without extension, and extension
    directory, filename = os.path.split(filepath)
    basename, ext = os.path.splitext(filename)

    # Create the new file name by adding the suffix
    new_filename = f"{basename}-{suffix}{ext}"

    # Combine the directory with the new file name
    return os.path.join(directory, new_filename)
