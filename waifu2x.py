import os
import shutil
import stat
import subprocess
import sys
import zipfile

from utils import (
    DOWNLOADED_WAIFU2X_FOLDER,
    PartialDownloadNotSupported,
    check_free_space,
    download_file,
    get_waifu2x_path,
    open_remote_zip,
    save_zip_files,
)

WAIFU2X_VERSION = "20250915"

# The waifu2x models (in folders next to the program). "fast" is the default: on manga panels it looks nearly the same as "better" and is about 2x faster.
WAIFU2X_MODELS = {
    "fast": "models-upconv_7_anime_style_art_rgb",
    "better": "models-cunet",
}


# The zip's photo model, which Panelyze doesn't use (it only has "Fast" and "Better", for drawings). Not downloaded.
UNUSED_MODELS_FOLDER = "models-upconv_7_photo"


def get_waifu2x_zip_url():
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    return f"https://github.com/nihui/waifu2x-ncnn-vulkan/releases/download/{WAIFU2X_VERSION}/waifu2x-ncnn-vulkan-{WAIFU2X_VERSION}-{system}.zip"


def download_waifu2x(report=print):
    """
    The path of waifu2x, downloaded from its GitHub releases the first time if it isn't installed (like the "Best" models, see "janai.py").
    """
    waifu2x_path = get_waifu2x_path()
    if waifu2x_path:
        return waifu2x_path

    from gui_classes.ProgressPanel import DOWNLOAD_ONCE_DETAIL, show_extra_stage

    with show_extra_stage("Downloading waifu2x (one time only)", DOWNLOAD_ONCE_DETAIL):
        return download_missing_waifu2x(report)


def download_missing_waifu2x(report=print):
    from gui_classes.ProgressPanel import format_size
    from storage import WAIFU2X_DOWNLOAD_BYTES

    report(
        f"Downloading waifu2x ({format_size(WAIFU2X_DOWNLOAD_BYTES)}, one time only)..."
    )
    check_free_space(
        os.path.dirname(DOWNLOADED_WAIFU2X_FOLDER), WAIFU2X_DOWNLOAD_BYTES, "waifu2x"
    )
    os.makedirs(os.path.dirname(DOWNLOADED_WAIFU2X_FOLDER), exist_ok=True)
    unzipped_folder = f"{DOWNLOADED_WAIFU2X_FOLDER}.tmp"
    zip_path = f"{DOWNLOADED_WAIFU2X_FOLDER}.zip.tmp"
    shutil.rmtree(unzipped_folder, ignore_errors=True)
    # A download that stopped half-way.
    shutil.rmtree(DOWNLOADED_WAIFU2X_FOLDER, ignore_errors=True)
    try:
        try:
            # Only the files Panelyze uses, straight out of the zip on GitHub (like the "Best" models, see "download_missing_model_file" in janai.py).
            with open_remote_zip(get_waifu2x_zip_url()) as waifu2x_zip:
                save_used_files(waifu2x_zip, unzipped_folder, progress_name="waifu2x")
        except PartialDownloadNotSupported:
            download_file(get_waifu2x_zip_url(), zip_path, name="waifu2x")
            with zipfile.ZipFile(zip_path) as waifu2x_zip:
                save_used_files(waifu2x_zip, unzipped_folder)
        # The zip has one folder (like "waifu2x-ncnn-vulkan-20250915-windows") with the program and its models. A zip made on a Mac can also have a "__MACOSX" folder, which is skipped.
        [folder_name] = [
            name
            for name in os.listdir(unzipped_folder)
            if os.path.isdir(os.path.join(unzipped_folder, name))
            and not name.startswith("__")
        ]
        extracted_folder = os.path.join(unzipped_folder, folder_name)
        # Unzipping doesn't keep the "can be run" permission on a Mac or Linux. It's set before the folder is moved into place, so a folder that's there is always ready to use.
        if sys.platform != "win32":
            program_path = os.path.join(extracted_folder, "waifu2x-ncnn-vulkan")
            os.chmod(
                program_path,
                os.stat(program_path).st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )
        os.replace(extracted_folder, DOWNLOADED_WAIFU2X_FOLDER)
    finally:
        shutil.rmtree(unzipped_folder, ignore_errors=True)
        if os.path.exists(zip_path):
            os.remove(zip_path)

    waifu2x_path = get_waifu2x_path()
    if not waifu2x_path:
        raise RuntimeError("The waifu2x download didn't have the program in it.")
    return waifu2x_path


def is_inside_folder(path, folder):
    folder = os.path.abspath(folder)
    return os.path.abspath(path).startswith(folder + os.sep)


def save_used_files(waifu2x_zip, folder, progress_name=None):
    """
    Everything in the waifu2x zip but the models Panelyze doesn't use (the photo model).
    """
    save_zip_files(
        waifu2x_zip,
        [
            (member, os.path.join(folder, member.filename))
            for member in waifu2x_zip.infolist()
            if not member.is_dir()
            and UNUSED_MODELS_FOLDER not in member.filename
            # Never outside "folder", like "extractall" makes sure (a zip can name a file "../something" or "/something").
            and is_inside_folder(os.path.join(folder, member.filename), folder)
        ],
        progress_name,
    )


def get_waifu2x_model(upscale_model, upscale_ratio):
    """
    The waifu2x model for the "Upscale Model" setting ("fast", "better" or "best"). "best" mostly uses MangaJaNai instead (see "janai.py"), and only uses waifu2x for images that aren't made bigger.
    """
    # The fast model can only make images bigger. Images that aren't made bigger (only cleaned up) need cunet.
    if upscale_model == "fast" and int(upscale_ratio) > 1:
        return "fast"

    return "better"


def upscale_with_waifu2x(
    input_image,
    output_image,
    upscale_ratio=4,
    noise_level=1,
    image_format="ext/png",
    terminal_output_list_view=None,
    process_manager=None,
    model="better",
    on_line=None,
):
    """
    Upscale one image, or every image in a folder ("input_image" and "output_image" are then folders). A whole folder in one go is about 2x faster than one image at a time, because waifu2x only starts up and loads its model once.
    """

    # The real file, even if it's reached through a shortcut (symlink), so its models folder is found next to it.
    waifu2x_path = get_waifu2x_path()
    if not waifu2x_path:
        raise RuntimeError('"waifu2x-ncnn-vulkan" was not found.')
    waifu2x_path = os.path.realpath(waifu2x_path)

    terminal_command = [
        waifu2x_path,
        "-i",
        input_image,
        "-o",
        output_image,
        "-s",
        str(upscale_ratio),
        "-n",
        str(noise_level),
        "-f",
        str(image_format),
        # The model that comes with waifu2x, next to the program (so it's found no matter which folder the app runs from).
        "-m",
        os.path.join(os.path.dirname(waifu2x_path), WAIFU2X_MODELS[model]),
        # Prints a "... done" line for each finished image, so the progress can be shown.
        "-v",
    ]

    if process_manager and terminal_output_list_view:
        process_manager.monitor_terminal_output(
            terminal_command, terminal_output_list_view, on_line=on_line
        )
    else:
        subprocess.run(terminal_command, check=True)
    print(f"Upscaled image saved to: {output_image}")
