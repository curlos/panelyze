import os
import re
import sys
import requests
from gui_classes.ProgressPanel import report_progress
from utils import (
    READING_DIRECTION_FILE_NAME,
    ProcessManager,
    is_running_as_packaged_app,
)
import flet as ft

MANGADEX_API_URL = "https://api.mangadex.org"
# Languages written right to left. Comics first made in one of these are read right to left too, like manga (MangaDex's "originalLanguage" codes).
RIGHT_TO_LEFT_LANGUAGES = ("ja", "ar", "he", "fa", "ur", "yi", "ps", "sd", "ug", "dv")

# Each manga is saved in its own folder, and each chapter in a folder named like "Vol. 1 Ch. 3 - Boss and The Panda". These are the downloader's own placeholders. Plain "-d <folder>" would replace its default manga folder, and "--use-chapter-title" doesn't change these folder names.
MANGA_FOLDER_NAME = "{manga.title}"
CHAPTER_FOLDER_NAME_WITH_TITLE = "{chapter.simple_name} - {chapter.title}"

all_options_with_terminal_command = {
    "use_chapter_title": ["--filename-chapter", CHAPTER_FOLDER_NAME_WITH_TITLE],
    "no_group_name": "--no-group-name",
    "language": ["--language", "en"],
    "start_page": 1,
    "end_page": 9999,  # Random max value just to show what the values could look like.
    "start_chapter": 1,
    "end_chapter": 9999,
    "replace_existing_manga": ["--replace", "-r"],
    "no_oneshot_chapters": "--no-oneshot-chapter",
    "use_chapter_cover": "--use-chapter-cover",
    "use_volume_cover": "--use-volume-cover",
}


def get_additional_terminal_options(flet_page_client_storage):
    if not flet_page_client_storage:
        return ["--filename-chapter", CHAPTER_FOLDER_NAME_WITH_TITLE, "--no-group-name"]

    additional_terminal_options = []

    use_start_and_end_pages = flet_page_client_storage.get("use_start_and_end_pages")
    use_start_and_end_chapters = flet_page_client_storage.get(
        "use_start_and_end_chapters"
    )

    for key, terminal_command in all_options_with_terminal_command.items():
        storage_value = flet_page_client_storage.get(key)

        print(f"{key}: {storage_value}")


        if key == "language":
            additional_terminal_options.extend(["--language", storage_value["code"]])
        elif key == "start_page" and storage_value:
            if use_start_and_end_pages:
                additional_terminal_options.extend(["--start-page", storage_value])
        elif key == "end_page" and storage_value:
            if use_start_and_end_pages:
                additional_terminal_options.extend(["--end-page", storage_value])
        elif key == "start_chapter" and storage_value:
            if use_start_and_end_chapters:
                additional_terminal_options.extend(["--start-chapter", storage_value])
        elif key == "end_chapter" and storage_value:
            if use_start_and_end_chapters:
                additional_terminal_options.extend(["--end-chapter", storage_value])
        elif storage_value:
            if isinstance(terminal_command, list):
                additional_terminal_options.extend(terminal_command)
            else:
                additional_terminal_options.append(terminal_command)

    print(additional_terminal_options)

    return additional_terminal_options


def get_download_folder(output_directory):
    """
    The "-d" value: the manga's own folder inside the output folder. The braces of the placeholder are the downloader's, so any braces in the output folder's own name are escaped.
    """
    escaped_output_directory = output_directory.replace("{", "{{").replace("}", "}}")

    return os.path.join(escaped_output_directory, MANGA_FOLDER_NAME)


def get_tidy_chapter_folder_name(folder_name):
    """
    A chapter without a title is named "Vol. 1 Ch. 3 - " by the chapter name template. This drops the dash that has nothing after it.
    """
    return re.sub(r"\s*-\s*$", "", folder_name)


def tidy_chapter_folder_names(output_directory):
    """
    Rename the chapter folders (<output>/<manga>/<chapter>) that end with a dash and no title. A folder that would end up with the same name as one that's already there is left alone.
    """
    if not os.path.isdir(output_directory):
        return

    for manga_folder_name in os.listdir(output_directory):
        manga_directory = os.path.join(output_directory, manga_folder_name)

        if not os.path.isdir(manga_directory):
            continue

        for chapter_folder_name in os.listdir(manga_directory):
            tidy_name = get_tidy_chapter_folder_name(chapter_folder_name)
            new_path = os.path.join(manga_directory, tidy_name)

            if tidy_name != chapter_folder_name and tidy_name and not os.path.exists(new_path):
                os.rename(os.path.join(manga_directory, chapter_folder_name), new_path)


def get_mangadex_downloader_command():
    """
    How to start "mangadex-downloader" in its own process (so it can be cancelled and its output shown line by line).
    """
    # In the packaged app, "sys.executable" is Panelyze itself, not Python. Panelyze runs only the downloader when it's started with "--run-mangadex" (see the top of "gui.py").
    if is_running_as_packaged_app():
        return [sys.executable, "--run-mangadex"]

    return [sys.executable, "-m", "mangadex_downloader"]


def parse_mangadex_progress_line(line):
    """
    What a line of "mangadex-downloader" output says about its progress: ("page", chapter name, page number) when it starts a page, ("finished", chapter number) when a chapter is done, or None for any other line. It doesn't say how many pages or chapters there will be, so only what's been done so far can be shown.
    """
    page_match = re.search(r"Downloading (.+) page (\d+)\s*$", line)
    if page_match:
        # The scanlation group, like "[Some Scans]", isn't needed.
        chapter_name = re.sub(r"^\[.*?\]\s*", "", page_match.group(1))
        return ("page", chapter_name, int(page_match.group(2)))

    finished_match = re.search(r"Finished download chapter (\S+)", line)
    if finished_match:
        return ("finished", finished_match.group(1))

    return None


def get_mangadex_progress_reporter():
    """
    A function to call with each line of "mangadex-downloader" output, which updates the progress panel.
    """
    chapters_downloaded = 0

    def report_line(line):
        nonlocal chapters_downloaded
        progress = parse_mangadex_progress_line(line)

        if not progress:
            return

        if progress[0] == "finished":
            chapters_downloaded += 1
            report_progress(detail=f"{chapters_downloaded} chapter(s) downloaded")
            return

        _, chapter_name, page_number = progress
        done_text = (
            f"{chapters_downloaded} chapter(s) downloaded · " if chapters_downloaded else ""
        )
        report_progress(
            detail=f"{done_text}Downloading {chapter_name}, page {page_number}"
        )

    return report_line


def get_reading_direction_from_manga(manga_attributes):
    """
    The reading direction of a series, from its MangaDex attributes: "webtoon" for the "Long Strip" tag, "4koma" for the "4-Koma" tag (or "ltr" if it wasn't first made in a right-to-left language), otherwise "rtl" or "ltr" from its original language. Translating a series only changes its text, not how its pages are laid out, so the chapter's own language doesn't matter.
    """
    tag_names = {tag["attributes"]["name"].get("en") for tag in manga_attributes.get("tags") or []}
    is_right_to_left = manga_attributes.get("originalLanguage") in RIGHT_TO_LEFT_LANGUAGES

    if "Long Strip" in tag_names:
        return "webtoon"
    if "4-Koma" in tag_names and is_right_to_left:
        return "4koma"
    return "rtl" if is_right_to_left else "ltr"


def get_reading_direction_from_mangadex(mangadex_url):
    """
    The reading direction of the series a MangaDex series or chapter URL belongs to (see "get_reading_direction_from_manga"), or None if it can't be found (another kind of URL, or no internet).
    """
    match = re.search(r"/(title|chapter)/([0-9a-f-]{36})", mangadex_url)
    if not match:
        return None

    kind, mangadex_id = match.groups()
    try:
        if kind == "chapter":
            chapter = requests.get(f"{MANGADEX_API_URL}/chapter/{mangadex_id}", timeout=10).json()
            mangadex_id = next(
                relationship["id"] for relationship in chapter["data"]["relationships"] if relationship["type"] == "manga"
            )
        manga = requests.get(f"{MANGADEX_API_URL}/manga/{mangadex_id}", timeout=10).json()
        return get_reading_direction_from_manga(manga["data"]["attributes"])
    except (requests.RequestException, ValueError, KeyError, TypeError, StopIteration) as error:
        print(f"Couldn't get the reading direction from MangaDex ({error}). It will be guessed from the images.")
        return None


def get_chapter_folders(output_directory):
    """
    Each chapter folder (<output>/<manga>/<chapter>) in the output folder, with when it was last changed.
    """
    if not os.path.isdir(output_directory):
        return {}

    chapter_folders = {}
    for manga_folder_name in os.listdir(output_directory):
        manga_directory = os.path.join(output_directory, manga_folder_name)
        if not os.path.isdir(manga_directory):
            continue

        for chapter_folder_name in os.listdir(manga_directory):
            chapter_directory = os.path.join(manga_directory, chapter_folder_name)
            if os.path.isdir(chapter_directory):
                chapter_folders[chapter_directory] = os.path.getmtime(chapter_directory)

    return chapter_folders


def save_reading_direction(output_directory, reading_direction, chapter_folders_before):
    """
    Save "reading_direction" next to the images of each chapter folder that's new or changed since "chapter_folders_before" (see "get_chapter_folders"). The output folder can hold other series too, so the chapters from earlier downloads are left alone.
    """
    for chapter_directory, changed_at in get_chapter_folders(output_directory).items():
        if chapter_folders_before.get(chapter_directory) != changed_at:
            with open(os.path.join(chapter_directory, READING_DIRECTION_FILE_NAME), "w", encoding="utf-8") as file:
                file.write(reading_direction)


def download_from_mangadex(
    mangadex_url_to_download_from: str = "",
    output_directory: str = "",
    terminal_output_list_view: ft.ListView = None,
    flet_page_client_storage=None,
    cancel_process_button=None,
) -> None:
    """
    @description Use the third-party "mangadex_downloader" command line tool to download manga from the given URL. URL must be a valid MangaDex URL.
    @IMPORTANT "mangadex_downloader" MUST be installed on your system to use this.
    """

    additional_terminal_options = get_additional_terminal_options(
        flet_page_client_storage
    )

    terminal_command = get_mangadex_downloader_command() + [
        mangadex_url_to_download_from,
        "-d",
        get_download_folder(output_directory),
    ]

    terminal_command.extend(additional_terminal_options)

    process_manager = ProcessManager()
    chapter_folders_before = get_chapter_folders(output_directory)

    if cancel_process_button:
        cancel_process_button.on_click = lambda _: process_manager.cancel_process()

    process_manager.monitor_terminal_output(
        terminal_command,
        terminal_output_list_view,
        output_directory,
        on_line=get_mangadex_progress_reporter(),
    )

    tidy_chapter_folder_names(output_directory)

    # Only after a download that finished (not one that was cancelled or failed).
    process = process_manager.process
    reading_direction = (
        get_reading_direction_from_mangadex(mangadex_url_to_download_from)
        if process and process.returncode == 0
        else None
    )
    if reading_direction:
        print(f"Reading direction from MangaDex: {reading_direction}")
        save_reading_direction(output_directory, reading_direction, chapter_folders_before)
