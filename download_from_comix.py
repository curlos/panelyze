import os
import re
import sys
import threading
from urllib.parse import urlparse

from gui_classes.ProgressPanel import report_progress
from utils import (
    READING_DIRECTION_FILE_NAME,
    DownloadCancelled,
    DownloadSummary,
    copy_from_library,
    count_images,
    find_downloaded_folder,
    get_cancel_event,
    set_cancel_click,
    get_library_directory,
    is_download_intact,
    pluralize,
    read_download_info,
    write_download_info,
)

COMIX_SOURCE = "comix.to"

# The comix.to code is a copy of comix-downloader's (see comix_downloader/README.md). Its package is named "src", so its folder has to be on the import path.
COMIX_DOWNLOADER_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "comix_downloader"
)
if COMIX_DOWNLOADER_FOLDER not in sys.path:
    sys.path.insert(0, COMIX_DOWNLOADER_FOLDER)

# comix.to only lets real browsers through, so the downloader drives one (hidden). The first one found is used. Not Brave: its shields stop comix.to's bot check from passing (tested 2026-11-20).
BROWSER_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    # Windows: Chrome, then Chrome installed for one user only (found inside the home folder, see "find_browser").
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "AppData\\Local\\Google\\Chrome\\Application\\chrome.exe",
    # Edge comes with Windows 10 and 11.
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
]


def is_comix_url(url):
    return urlparse((url or "").strip()).hostname in ("comix.to", "www.comix.to")


def parse_comix_url(url):
    """
    The series code and, for a chapter link, the chapter id: "https://comix.to/title/w25zn-slam-dunk" gives ("w25zn", None) and ".../title/w25zn-slam-dunk/2256865-chapter-274" gives ("w25zn", 2256865).
    """
    if not is_comix_url(url):
        raise ValueError(f"Not a comix.to link: {url}")

    match = re.match(
        r"^/title/([a-z0-9]+)(?:-[^/]*)?(?:/(\d+)-chapter-[^/]+)?/?$",
        urlparse(url.strip()).path,
    )
    if not match:
        raise ValueError(
            f"Not a comix.to series or chapter link (like https://comix.to/title/w25zn-slam-dunk): {url}"
        )

    chapter_id = int(match.group(2)) if match.group(2) else None
    return match.group(1), chapter_id


def find_browser(browser_paths=BROWSER_PATHS):
    home = os.path.expanduser("~")
    for path in browser_paths:
        # Apps can also be in the user's own folder (~/Applications on a Mac, AppData on Windows).
        for candidate in (path, os.path.join(home, path.lstrip("/"))):
            if os.access(candidate, os.X_OK):
                return candidate

    raise RuntimeError(
        "Downloading from comix.to needs Google Chrome, Chromium or Microsoft Edge installed (comix.to only lets real web browsers through)."
    )


def get_chapter_number(chapter):
    try:
        return float(chapter.number)
    except (TypeError, ValueError):
        # Not a number (e.g. a oneshot).
        return None


def select_chapters_in_range(chapters, start_chapter="", end_chapter=""):
    """
    The chapters from "start_chapter" to "end_chapter" (both included). An empty one means the first or the last chapter. Chapters without a number (e.g. a oneshot) are only kept when there's no range.
    """
    if not start_chapter and not end_chapter:
        return list(chapters)

    try:
        start = float(start_chapter) if start_chapter else float("-inf")
        end = float(end_chapter) if end_chapter else float("inf")
    except ValueError:
        raise ValueError(
            f'The Start and End Chapters must be numbers (they are "{start_chapter}" and "{end_chapter}").'
        ) from None
    return [
        chapter
        for chapter in chapters
        if (number := get_chapter_number(chapter)) is not None
        and start <= number <= end
    ]


def pick_best_upload(uploads):
    """
    The best of several uploads of the same chapter: an official one (e.g. VIZ Media, usually the best scans) first, then the one with the most likes, then the first one listed.
    """
    # "max" keeps the first of equally good uploads.
    return max(uploads, key=lambda upload: (bool(upload.official), upload.votes or 0))


def pick_best_upload_of_each_chapter(chapters):
    uploads_by_number = {}
    for chapter in chapters:
        uploads_by_number.setdefault(str(chapter.number), []).append(chapter)

    return [pick_best_upload(uploads) for uploads in uploads_by_number.values()]


def get_upload_description(chapter):
    group = chapter.group_name or "no group"
    # An official upload without a group name is already called "Official".
    if chapter.official and group != "Official":
        group += " (official)"
    return f"{group}, {chapter.votes or 0} likes"


def get_reading_direction_from_comix(manga):
    """
    The reading direction of a comix.to series, from its original language and type: right to left for manga, "webtoon" for Korean and Chinese comics (on comix.to they're almost all long strips), and left to right for everything else (e.g. American and French comics). comix.to has no "Long Strip" tag like MangaDex, so a Korean or Chinese series drawn as pages is read as a webtoon too.
    """
    from download_from_mangadex import RIGHT_TO_LEFT_LANGUAGES

    if manga.original_language in RIGHT_TO_LEFT_LANGUAGES:
        return "rtl"
    if manga.manga_type in ("manhwa", "manhua") or manga.original_language in (
        "ko",
        "zh",
        "zh-hk",
    ):
        return "webtoon"
    return "ltr"


class ChapterProgressReporter:
    """
    Stands in for the "rich" progress object the copied comix.to code reports to (it calls "add_task", "advance" and "update"), and reports to the Status view instead: "Chapter 2 of 5 · 37 pages downloaded", or "12 of 25 pages" for a single chapter.
    """

    def __init__(self, chapter_count):
        self.chapter_count = chapter_count
        self.chapters_done = 0
        self.pages_downloaded = 0
        # How many pages the chapter has, when it's the only one (the chapters are downloaded together otherwise).
        self.page_total = None
        self.main_task_id = None
        self.next_task_id = 0
        # The chapters are downloaded on several threads at once.
        self.lock = threading.Lock()

    def add_task(self, description, total=None, **fields):
        with self.lock:
            task_id = self.next_task_id
            self.next_task_id += 1
            # The first one counts the chapters, and the others count each chapter's pages.
            if self.main_task_id is None:
                self.main_task_id = task_id
            else:
                self.page_total = total
                self.report()
            return task_id

    def advance(self, task_id, advance=1):
        with self.lock:
            if task_id == self.main_task_id:
                self.chapters_done += 1
            else:
                self.pages_downloaded += advance
            self.report()

    def update(self, task_id, **fields):
        # It's only told here that a chapter is complete, which "advance" already counted.
        pass

    def report(self):
        if self.chapter_count == 1:
            report_progress(
                chapter=1,
                chapters=1,
                unit="pages",
                detail=None,
                pages_done=self.pages_downloaded,
                pages_total=self.page_total,
            )
        else:
            report_progress(
                chapter=min(self.chapters_done + 1, self.chapter_count),
                chapters=self.chapter_count,
                pages_done=None,
                pages_total=None,
                detail=f"{pluralize(self.pages_downloaded, 'page')} downloaded",
            )


def get_comix_summary(
    manga, downloaded_chapters, page_count, already_there=(), failed_count=0
):
    """
    What was downloaded in one line: "Downloaded Absolute Batman chapter 25 · 25 pages" for one chapter, or "Downloaded Slam Dunk: 3 chapters · 77 pages". "already_there" are the chapters (and their page counts) that were downloaded before and skipped, as (chapter, pages).
    """
    if not downloaded_chapters:
        pages = sum(chapter_pages for _, chapter_pages in already_there)
        if len(already_there) == 1:
            return f"Already downloaded: {manga.title} chapter {already_there[0][0].number} · {pluralize(pages, 'page')}"
        return f"Already downloaded: {manga.title}: {pluralize(len(already_there), 'chapter')} · {pluralize(pages, 'page')}"

    if len(downloaded_chapters) == 1:
        summary = f"Downloaded {manga.title} chapter {downloaded_chapters[0].number} · {pluralize(page_count, 'page')}"
    else:
        summary = f"Downloaded {manga.title}: {pluralize(len(downloaded_chapters), 'chapter')} · {pluralize(page_count, 'page')}"
    if already_there:
        summary += (
            f" · {pluralize(len(already_there), 'more chapter')} already downloaded"
        )
    if failed_count:
        summary += f" · {pluralize(failed_count, 'chapter')} failed (see the Log)"
    return summary


# The pages the comix.to downloader saves: "001.jpg", "002.png", ... (or ".gif", see "convert_gif_pages").
COMIX_PAGE_NAME = re.compile(r"^\d{3,}\.(jpe?g|png|webp|gif)$", re.IGNORECASE)


def get_page_times(folder):
    """
    When each page the downloader saved in "folder" was last changed, by file name (none when there's no folder yet). Only its own pages ("COMIX_PAGE_NAME"), so images the user added there are never taken for old pages.
    """
    if not os.path.isdir(folder):
        return {}
    return {
        name: os.stat(os.path.join(folder, name)).st_mtime_ns
        for name in os.listdir(folder)
        if COMIX_PAGE_NAME.match(name)
    }


def convert_gif_pages(folder):
    """
    comix.to can serve a page as a GIF, which the other tools don't read (and the page count would miss). It's saved as a PNG instead (its first frame).
    """
    from PIL import Image

    for name in os.listdir(folder):
        if COMIX_PAGE_NAME.match(name) and name.lower().endswith(".gif"):
            gif_path = os.path.join(folder, name)
            with Image.open(gif_path) as image:
                image.convert("RGB").save(os.path.splitext(gif_path)[0] + ".png")
            os.remove(gif_path)


def get_chapter_folder(output_directory, manga, chapter):
    return os.path.join(
        output_directory, manga.get_safe_title(), chapter.get_safe_folder_name()
    )


def get_earlier_download(output_directory, manga, chapter, library_directory=None):
    """
    What was saved in the chapter's folder by an earlier download of this very chapter, if the folder still has all its pages. None otherwise (it's downloaded again).
    """
    folder = get_chapter_folder(output_directory, manga, chapter)
    info = read_download_info(folder)
    if (
        info
        and info.get("source") == COMIX_SOURCE
        and info.get("chapter_id") == chapter.chapter_id
        and is_download_intact(folder, info)
    ):
        return info
    if library_directory:
        # A Pipeline's Download step: a chapter that's still all there in the Download tab's folder is copied.
        library_folder = get_chapter_folder(library_directory, manga, chapter)
        library_info = read_download_info(library_folder)
        if (
            library_info
            and library_info.get("source") == COMIX_SOURCE
            and library_info.get("chapter_id") == chapter.chapter_id
            and is_download_intact(library_folder, library_info)
        ):
            copy_from_library(
                library_folder, library_directory, output_directory, replace=True
            )
            return library_info
    return None


def forget_saved_cookies():
    """
    Cloudflare cookies saved by an earlier download go stale, and then every page waits for 60 seconds and fails ("Comix page did not become ready"). So each download starts without them. The copied code saves them again while it runs, for the several browsers it starts during one download.
    """
    from src.api import comix

    try:
        comix._CANONICAL_COOKIE_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def download_from_comix(
    comix_url_to_download_from: str = "",
    output_directory: str = "",
    terminal_output_list_view=None,
    flet_page_client_storage=None,
    cancel_button=None,
) -> str:
    """
    Download a comix.to series (or one chapter) into "output_directory/<Title>/Chapter_<number>_<title>/001.webp". Uses the Downloader's "Start and End Chapters" settings, and only the best upload of each chapter (see "pick_best_upload"). Like a MangaDex download, it saves the reading direction next to each chapter (see "get_reading_direction_from_comix"). Returns what was downloaded in one line. Clicking "cancel_button" stops it once the chapter being loaded in the browser is done (raising "DownloadCancelled"); chapters that were already downloaded are kept.
    """
    from src.api import comix
    from src.api.comix import ComixAPI
    from src.core.downloader import MangaDownloader, cancel_downloads, reset_downloads
    from src.core.models import DownloadConfig, OutputFormat
    from src.utils import nodriver_browser

    cancel_event = get_cancel_event()
    # A Cancel of an earlier download mustn't stop this one. (The copied code used to do this when the chapters start downloading, which forgot a Cancel clicked just before.)
    reset_downloads()
    if cancel_button:
        set_cancel_click(
            cancel_button,
            lambda: (cancel_event.set(), cancel_downloads()),
            "Cancelling after the chapter being loaded in the browser (the finished chapters are kept)...",
        )

    def stop_if_cancelled(message="Download cancelled"):
        if cancel_event.is_set():
            raise DownloadCancelled(message)

    manga_code, chapter_id = parse_comix_url(comix_url_to_download_from)
    forget_saved_cookies()
    nodriver_browser.BROWSER_EXECUTABLE_PATH = find_browser()
    print(
        f"Using {os.path.basename(nodriver_browser.BROWSER_EXECUTABLE_PATH)} (hidden) to open comix.to"
    )

    replace_existing = bool(
        flet_page_client_storage
        and flet_page_client_storage.get("replace_existing_manga")
    )

    report_progress(detail="Opening comix.to in a hidden browser...")
    manga = ComixAPI.get_manga_info(manga_code, headless=True)
    stop_if_cancelled()

    library_directory = (
        None
        if replace_existing
        else get_library_directory(output_directory, flet_page_client_storage)
    )

    if chapter_id is not None and not replace_existing:
        # A link to a chapter that's already downloaded needs no chapter list (which can take minutes) and no pages.
        found = find_downloaded_folder(
            os.path.join(output_directory, manga.get_safe_title()),
            source=COMIX_SOURCE,
            chapter_id=chapter_id,
        )
        if not found and library_directory:
            found = find_downloaded_folder(
                os.path.join(library_directory, manga.get_safe_title()),
                source=COMIX_SOURCE,
                chapter_id=chapter_id,
            )
            if found:
                found = (
                    copy_from_library(
                        found[0], library_directory, output_directory, replace=True
                    ),
                    found[1],
                )
        if found:
            folder, info = found
            print(
                f"{manga.title} chapter {info.get('chapter_number')} is already downloaded."
            )
            return DownloadSummary(
                f"Already downloaded: {manga.title} chapter {info.get('chapter_number')} · {pluralize(info['pages'], 'page')}",
                folder,
            )
    print(f"Found {manga.title}. Getting its chapter list (this can take a minute)...")
    report_progress(
        detail=f"Getting the chapter list of {manga.title} (this can take a few minutes for a long series)..."
    )
    comix.CHAPTER_LIST_PROGRESS_CALLBACK = lambda page_number, uploads: report_progress(
        detail=f"Reading the chapter list: page {page_number} ({pluralize(uploads, 'upload')} so far)..."
    )
    try:
        chapters = ComixAPI.get_all_chapters(manga_code, headless=True)
    finally:
        comix.CHAPTER_LIST_PROGRESS_CALLBACK = None
    stop_if_cancelled()

    if chapter_id is not None:
        chapters = [chapter for chapter in chapters if chapter.chapter_id == chapter_id]
    else:
        storage = flet_page_client_storage
        if storage and storage.get("use_start_and_end_chapters"):
            chapters = select_chapters_in_range(
                chapters,
                str(storage.get("start_chapter") or "").strip(),
                str(storage.get("end_chapter") or "").strip(),
            )
        chapters = pick_best_upload_of_each_chapter(chapters)

    if not chapters:
        raise RuntimeError(
            f"No chapters of {manga.title} to download (check the link and the Start and End Chapters)."
        )

    # Chapters that are already downloaded (and still have all their pages) aren't downloaded again, unless "Replace What's Already Downloaded" is on.
    already_there = []
    if not replace_existing:
        chapters_to_download = []
        for chapter in chapters:
            earlier_download = get_earlier_download(
                output_directory, manga, chapter, library_directory
            )
            if earlier_download:
                already_there.append((chapter, earlier_download["pages"]))
            else:
                chapters_to_download.append(chapter)
        if already_there:
            print(
                f"{pluralize(len(already_there), 'chapter')} already downloaded, so not downloaded again."
            )
        chapters = chapters_to_download

    series_folder = os.path.join(output_directory, manga.get_safe_title())
    if not chapters:
        only_folder = (
            get_chapter_folder(output_directory, manga, already_there[0][0])
            if len(already_there) == 1
            else series_folder
        )
        return DownloadSummary(
            get_comix_summary(manga, [], 0, already_there), only_folder
        )

    print(f"Downloading {len(chapters)} chapter(s) of {manga.title}:")
    for chapter in chapters:
        print(f"  {chapter.get_display_name()} ({get_upload_description(chapter)})")

    # The chapters that were saved this time (also when they were already in the folder, which is then written over).
    downloaded_chapters = []
    # The pages already in the chapters' folders, from an earlier download (of another upload, or one that's being replaced).
    pages_before = {
        chapter.chapter_id: get_page_times(
            get_chapter_folder(output_directory, manga, chapter)
        )
        for chapter in chapters
    }

    def on_chapter_complete(chapter, success, message):
        if success:
            downloaded_chapters.append(chapter)
            chapter_folder = get_chapter_folder(output_directory, manga, chapter)
            # The new pages are saved over the old ones, so the old pages that weren't written over (e.g. the old upload had more pages) go, or the two would be mixed.
            for name, changed_at in pages_before[chapter.chapter_id].items():
                page_path = os.path.join(chapter_folder, name)
                if (
                    os.path.exists(page_path)
                    and os.stat(page_path).st_mtime_ns == changed_at
                ):
                    os.remove(page_path)
            if os.path.isdir(chapter_folder):
                convert_gif_pages(chapter_folder)
                # So the next download of this chapter can see that it's there, as long as this folder is.
                write_download_info(
                    chapter_folder,
                    source=COMIX_SOURCE,
                    chapter_id=chapter.chapter_id,
                    chapter_number=chapter.number,
                    pages=count_images(chapter_folder),
                )
        # The message already names the chapter (e.g. "Downloaded Chapter 1: Sakuragi (35 pages)").
        print(
            message
            or f"{'Downloaded' if success else 'FAILED'}: {chapter.get_display_name()}"
        )

    config = DownloadConfig(
        output_format=OutputFormat.IMAGES,
        download_path=output_directory,
        headless=True,
    )
    report_progress(
        detail=f"Loading the pages of {pluralize(len(chapters), 'chapter')} in the browser (this can take a minute for each)..."
    )
    progress_reporter = ChapterProgressReporter(len(chapters))
    stop_if_cancelled()
    successful, failed = MangaDownloader(config).download_chapters(
        manga,
        chapters,
        progress_reporter,  # pyright: ignore[reportArgumentType]
        on_chapter_complete=on_chapter_complete,
    )

    print(
        f"comix.to download finished: {successful} chapter(s) downloaded, {failed} failed."
    )
    if cancel_event.is_set():
        kept = (
            f" {pluralize(successful, 'chapter')} already downloaded {'was' if successful == 1 else 'were'} kept."
            if successful
            else ""
        )
        raise DownloadCancelled(f"Download cancelled.{kept}")
    if not successful:
        raise RuntimeError(
            "No chapters could be downloaded from comix.to (see the errors above)."
        )

    reading_direction = get_reading_direction_from_comix(manga)
    print(
        f"Reading direction from comix.to ({manga.original_language}, {manga.manga_type}): {reading_direction}"
    )
    for chapter in downloaded_chapters:
        chapter_folder = os.path.join(
            output_directory, manga.get_safe_title(), chapter.get_safe_folder_name()
        )
        if os.path.isdir(chapter_folder):
            with open(
                os.path.join(chapter_folder, READING_DIRECTION_FILE_NAME),
                "w",
                encoding="utf-8",
            ) as direction_file:
                direction_file.write(reading_direction)

    # One chapter: its own folder. Several: the series' folder.
    downloaded_folder = (
        get_chapter_folder(output_directory, manga, downloaded_chapters[0])
        if len(downloaded_chapters) == 1 and not already_there
        else series_folder
    )
    # The pages really saved: the copied code also counts the pages it couldn't download, and those of chapters that failed.
    chapter_folders = [
        get_chapter_folder(output_directory, manga, chapter)
        for chapter in downloaded_chapters
    ]
    page_count = sum(
        count_images(folder) for folder in chapter_folders if os.path.isdir(folder)
    )
    return DownloadSummary(
        get_comix_summary(
            manga, downloaded_chapters, page_count, already_there, failed
        ),
        downloaded_folder,
    )
