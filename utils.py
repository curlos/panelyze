from functools import wraps
import io
import re
import tempfile
import shutil
import time
import subprocess
import sys
import os
import platform
import zipfile
import flet as ft
import math
from dotenv import load_dotenv


def open_directory(path):
    if platform.system() == "Darwin":  # macOS
        subprocess.run(["open", path])
    elif platform.system() == "Windows":  # Windows
        os.startfile(path)
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
        terminal_output_list_view.controls.append(ft.Text(text, color=color))
        terminal_output_list_view.update()


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


def get_capped_upscale_ratio(width, height, upscale_ratio, max_side=MAX_UPSCALED_IMAGE_SIDE):
    """
    The upscale ratio to actually run waifu2x with, so it doesn't waste time making an image far bigger than "max_side" (e.g. upscaling an 8000px image 16x would take forever for no visible gain).

    Returns the smallest ratio (1, 2, 4, ... up to "upscale_ratio") that makes the longest side reach "max_side". The result can still be a bit bigger than "max_side" (e.g. 1000px x 4 = 4000px), so it's shrunk to "max_side" afterwards. An image that's already "max_side" or bigger isn't upscaled at all (ratio 1).
    """
    longest_side = max(width, height)
    capped_ratio = 1

    while capped_ratio < int(upscale_ratio) and longest_side * capped_ratio < max_side:
        capped_ratio *= 2

    return capped_ratio


def copy_picked_images_to_folder(image_paths):
    """
    When individual images are picked instead of a folder, copy them into a new temporary folder so every tool can process them exactly like a picked folder.

    The folder is named after the images (e.g. "Ch 1 - page_05" or "Ch 1 - 3 images"), so their output goes into its own folder and never overwrites the output of the whole chapter. Delete the returned folder's parent when done.
    """
    parent_folder_name = get_last_directory(os.path.dirname(image_paths[0]))

    if len(image_paths) == 1:
        image_name = os.path.splitext(os.path.basename(image_paths[0]))[0]
        folder_name = f"{parent_folder_name} - {image_name}"
    else:
        folder_name = f"{parent_folder_name} - {len(image_paths)} images"

    picked_images_folder = os.path.join(tempfile.mkdtemp(prefix="panelyze-"), folder_name)
    os.makedirs(picked_images_folder)

    for image_path in image_paths:
        shutil.copy2(image_path, picked_images_folder)

    return picked_images_folder


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

# The dialogue Panel-By-Panel read on the pages, saved next to the panels as a list of lines for each panel (in the same order as the images). Images To Video uses it instead of reading the text on every panel again.
PANEL_TEXT_FILE_NAME = "panel-text.json"


def is_image_file(file_name):
    # Skip hidden files like macOS "._page_1.jpg" metadata files. They end in an image extension but aren't real images.
    if file_name.startswith("."):
        return False

    return file_name.lower().endswith(IMAGE_EXTENSIONS)


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
            elif is_image_file(entry):
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


class ProcessManager:
    def __init__(self):
        self.process = None  # To store the running process

    def monitor_terminal_output(
        self,
        terminal_command: list[str],
        terminal_output_list_view: ft.ListView = None,
        output_directory: str = "",
        on_line=None,
    ):
        lines = []

        # Make a shallow copy of the OS environment variables.
        env = os.environ.copy()

        # Ensures that the subprocess writes output immediately to stdout/stderr without buffering so we data can be processed line-by-line in real-time programatically.
        # We need to take of the two running process with BOTH "PYTHONUNBUFFERED" (parent process - the running "download_from_mangadex.py" file) and bufsize=1 (subprocess) below.
        env["PYTHONUNBUFFERED"] = "1"

        # Open a child "process" (it's a child because it's opened within the parent process, the process that executes the "download_from_mangadex.py" file)
        self.process = subprocess.Popen(
            terminal_command,
            stdout=subprocess.PIPE,  # Redirected to a PIPE so that the parent process (this python file) can manipulate the output and error lines in the code below instead of in the terminal.
            stderr=subprocess.STDOUT,  # Merge errors into the same stream so they're read in order with the normal output.
            bufsize=0,  # Don't wait for a buffer to fill up. Read the output as soon as it's written.
            env=env,  # Use the modified "env" variable so that it takes "PYTHONUNBUFFERED" which will give us access to each line output immediately instead of after the program is done executing.
        )
        # newline="" keeps "\r" as it is (instead of turning it into a new line), so progress bars that redraw themselves with "\r" show up as one live line instead of hundreds of lines.
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

        if self.process:
            self.process.terminate()  # Gracefully terminate the process
            print("Process terminated by user.")


def get_waifu2x_path():
    """
    Where the "waifu2x-ncnn-vulkan" program is: inside the packaged app (bundled by "build_mac_app.sh"), or on the PATH when running from source. None if it can't be found.
    """
    bundled_waifu2x_path = os.path.join(
        getattr(sys, "_MEIPASS", ""), "waifu2x", "waifu2x-ncnn-vulkan"
    )

    if is_running_as_packaged_app() and os.path.exists(bundled_waifu2x_path):
        return bundled_waifu2x_path

    return shutil.which("waifu2x-ncnn-vulkan")


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
                yield from walk(value, os.path.join(relative_path, key) if relative_path else key)

    yield from walk(construct_directory_structure(input_directory), "")


def output_dir_would_overwrite_input(input_directory, output_directory):
    """
    Outputs are saved to "output_directory/<input folder name>/...". So, if the output directory is the input directory's parent, the output paths would be the exact same as the input paths and the original images would be overwritten. If the output directory is inside the input directory, then the outputs would get processed again the next time.
    """
    input_directory = os.path.realpath(input_directory)
    output_directory = os.path.realpath(output_directory)

    output_is_parent_of_input = output_directory == os.path.dirname(input_directory)

    return output_is_parent_of_input or is_same_or_inside(
        output_directory, input_directory
    )


def is_same_or_inside(path, parent_path):
    """
    Returns True if "path" is "parent_path" itself or somewhere inside it.
    """
    path = os.path.realpath(path)
    parent_path = os.path.realpath(parent_path)

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


def save_folder_as_cbz(folder, size="full"):
    """
    Save the images in "folder" (and its folders, e.g. one for each page) as a comic file, "<folder>.cbz" next to it, in reading order. Comic reader apps (e.g. Panels on iPhone and iPad, Mihon on Android) open it like a book. Returns its path, or None if there were no images.

    "size" is "full" (the images as they are) or "small" (WebP sized for phones and tablets, and grayscale for black and white pages: a chapter is about 15-25 MB instead of 150-250 MB).
    """
    image_paths = sorted(
        (
            os.path.join(directory, file_name)
            for directory, _, file_names in os.walk(folder)
            for file_name in file_names
            if is_image_file(file_name)
        ),
        key=lambda path: [
            natural_sort_key(part) for part in os.path.relpath(path, folder).split(os.sep)
        ],
    )
    if not image_paths:
        return None

    cbz_path = f"{folder.rstrip(os.sep)}.cbz"
    # Written to a temporary file first, so a half-written comic file is never left behind.
    with zipfile.ZipFile(f"{cbz_path}.tmp", "w", zipfile.ZIP_STORED) as cbz:
        for number, image_path in enumerate(image_paths, start=1):
            # Numbered with zeros in front (0001, 0002, ...), so every reader app keeps them in order.
            if size == "small":
                cbz.writestr(f"{number:04d}.webp", get_small_comic_file_image(image_path))
            else:
                cbz.write(image_path, f"{number:04d}{os.path.splitext(image_path)[1]}")
    os.replace(f"{cbz_path}.tmp", cbz_path)

    print(f"Saved a comic file to read in comic reader apps: {cbz_path}")
    return cbz_path


def get_small_comic_file_image(image_path):
    """
    The image as a small WebP for a comic file: no bigger than a tablet's screen, and grayscale if it's black and white.
    """
    from PIL import Image
    from janai import is_color_image

    with Image.open(image_path) as image:
        image = image.convert("RGB")
        is_color = is_color_image(image)
        image.thumbnail(SMALL_COMIC_FILE_IMAGE_SIZE, Image.LANCZOS)
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


