"""
Everywhere Panelyze keeps files on this computer (what the tabs saved, and the models it downloaded), for Settings → Storage. Every path comes from the app's own constants, never from what the user types, and deleting a row only deletes that row's own paths.
"""

import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

import janai
from EmotionAnalyzer import (
    EMOTION_CACHE_FOLDER,
    EMOTION_MODEL_NAME,
    EMOTION_MODEL_REVISION,
)
import utils
from gui_classes.ProgressPanel import format_size
import default_settings
from default_settings import OUTPUT_SUBFOLDERS, get_output_directory

# How much each download takes on disk (unzipped; checked 2026-11-26), shown before it's downloaded. The same as what Storage shows once it's there. Kept here instead of asked for online, so Settings shows them right away and without internet.
# waifu2x for this computer, without the photo model it doesn't use (see "download_missing_waifu2x" in waifu2x.py).
WAIFU2X_DOWNLOAD_BYTES = {"darwin": 54_085_110, "win32": 35_850_701}.get(
    sys.platform, 38_837_190
)
# Only the 2x models, taken out of the zips on GitHub (the whole zips are 433 MB and 159 MB, see "download_missing_model_file" in janai.py). On a Mac, a Core ML copy of each model is added the first time it's used.
MANGA_MODELS_DOWNLOAD_BYTES = 235_960_402
COLOR_MODEL_DOWNLOAD_BYTES = 16_198_963
# Magi's model file, and the emotion model's file and settings. They can't change: each is pinned to one commit ("MAGI_MODEL_REVISION" in magi.py, "EMOTION_MODEL_REVISION" in EmotionAnalyzer.py).
MAGI_DOWNLOAD_BYTES = 2_063_693_064
# What Magi takes on disk once downloaded: its model file, plus TrOCR's text settings and Hugging Face's own small files (measured). Shown in Storage, so the number is the same before and after.
MAGI_DISK_BYTES = 2_065_050_694
EMOTION_DOWNLOAD_BYTES = 331_156_595
EMOTION_PAGE_URL = (
    "https://huggingface.co/j-hartmann/emotion-english-distilroberta-base"
)

WAIFU2X_PAGE_URL = "https://github.com/nihui/waifu2x-ncnn-vulkan/releases"
# The same as "MAGI_MODEL_PAGE_URL" in magi.py, which isn't imported here: it loads PyTorch (slow), and Settings is built when the app starts.
MAGI_PAGE_URL = "https://huggingface.co/ragavsachdeva/magiv2"
# The same as "MAGI_MODEL_REVISION" in magi.py (see "MAGI_PAGE_URL").
MAGI_MODEL_REVISION = "fbc890fec52977142e8ee00bfe26e9458b65517c"
# Magi's folders in the Hugging Face cache: Magi itself, and TrOCR's text settings it loads with it (see "magi_model/processing_magiv2.py"). Its ResNet-50 part comes with Magi's own file ("use_pretrained_backbone" is false in "magi_model/full_config.json"), so it isn't downloaded separately. Other apps share the cache, so nothing else in it is ever touched.
MAGI_CACHE_FOLDERS = (
    "models--ragavsachdeva--magiv2",
    "models--microsoft--trocr-base-printed",
)
# The same as "PANELS_MODEL_FILE" in magi.py (see "MAGI_PAGE_URL").
PANELS_MODEL_FILE = os.path.join(
    default_settings.CODE_FOLDER, "magi_model", "panels_fp16.safetensors"
)

# What a model row's status is.
DOWNLOADED, NOT_DOWNLOADED, BUILT_IN = (
    "downloaded",
    "not downloaded",
    "built in",
)


@dataclass
class StorageRow:
    name: str
    # The files and folders the row's size is counted from, and the only ones its Delete deletes.
    paths: list = field(default_factory=list)
    # The folder its Open button opens. None for no Open button.
    folder_to_open: str | None = None
    can_delete: bool = False
    # For a model: what it's for, where it comes from, its status, how big its download is, and what downloads it.
    description: str = ""
    url: str = ""
    status: str = ""
    # In bytes (0 for none).
    download_size: int = 0
    # For a model: what it's for ("Upscaling", ...), shown as a small label over the models of each kind.
    group: str = ""
    download: Callable[[], None] | None = None


def get_hugging_face_cache():
    """
    Where Hugging Face keeps its downloads: "~/.cache/huggingface/hub", unless HF_HOME (or another of Hugging Face's settings) says otherwise.
    """
    from huggingface_hub import constants

    # The pinned huggingface-hub 0.17.3 (what the app ships with) only has "HUGGINGFACE_HUB_CACHE". Newer versions have "HF_HUB_CACHE", which is what their transformers downloads to (it also follows an HF_HUB_CACHE setting), so that one is used when it's there.
    return getattr(constants, "HF_HUB_CACHE", constants.HUGGINGFACE_HUB_CACHE)


def get_size(paths):
    """
    The size of the files and folders in "paths" (0 for one that isn't there). A link counts as the link itself, not what it points to: the Hugging Face cache links each file to a copy of it in the same folder, which would otherwise be counted twice.
    """
    total = 0
    for path in paths:
        if os.path.isdir(path) and not os.path.islink(path):
            total += utils.get_folder_size(path)
        else:
            try:
                total += os.lstat(path).st_size
            except OSError:
                # Not there (anymore), or can't be read: it counts as nothing, so the sizes never get stuck.
                continue
    return total


def get_disk(path):
    """
    Where the disk "path" is on starts (e.g. "/" or "E:\\"), or None when it isn't there.
    """
    folder = utils.get_closest_existing_folder(path)
    while folder is not None and not os.path.ismount(folder):
        parent = os.path.dirname(folder)
        if parent == folder:
            break
        folder = parent
    return folder


def get_disks(paths):
    """
    Each disk "paths" are on (the saved files and the models), as (its name, its free bytes, its total bytes): ("This computer", 50.4 GB, 494 GB). A Panelyze folder picked on an external drive gets one of its own, named after the drive.
    """
    disks = {}
    for path in paths:
        disk = get_disk(path)
        # A drive that isn't there (e.g. unplugged) or can't be asked gets no line.
        if disk is None or disk in disks:
            continue
        try:
            disks[disk] = shutil.disk_usage(disk)
        except OSError:
            continue

    home_disk = get_disk(os.path.expanduser("~"))
    return [
        (
            "This computer"
            if disk == home_disk
            else os.path.basename(disk.rstrip("\\/")) or disk,
            usage.free,
            usage.total,
        )
        for disk, usage in disks.items()
    ]


def get_model_folders():
    """
    Where the downloaded models are kept (for "get_disks").
    """
    return [
        utils.DOWNLOADED_WAIFU2X_FOLDER,
        janai.MODELS_FOLDER,
        get_hugging_face_cache(),
    ]


def delete_paths(row):
    """
    Delete the row's files and folders, and nothing else.
    """
    # A JaNai model that's loaded is forgotten too (first, so it's also forgotten if a delete fails half-way), so the next upscale downloads, converts and loads it again, as after reopening the app (instead of using the one in memory without its files).
    for key in [key for key in janai._loaded_upscalers if key[0] in row.paths]:
        del janai._loaded_upscalers[key]
    for path in row.paths:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        elif os.path.lexists(path):
            os.remove(path)


def get_panelyze_folder(storage):
    return (
        default_settings.DEV_OUTPUT_FOLDER
        or storage.get("panelyze_folder")
        or default_settings.PANELYZE_FOLDER
    )


def get_saved_files_rows(storage):
    """
    One row for each tool's folder. When running from source, they're all in this repo's or worktree's own folder (see "get_dev_output_folder"), never another one's.
    """
    rows = []
    for setting_key, subfolder in OUTPUT_SUBFOLDERS.items():
        folder = get_output_directory(storage, setting_key)
        rows.append(
            StorageRow(
                # The folder's own name (e.g. "Upscaled Images"), so it matches what's in Finder.
                name=subfolder,
                paths=[folder],
                folder_to_open=folder,
                # A folder picked in a tab could be any folder (even the Desktop), so only the tool's own folder inside the Panelyze folder can be deleted here.
                can_delete=folder
                == os.path.join(get_panelyze_folder(storage), subfolder),
            )
        )
    return rows


def get_model_files(prefix):
    """
    The model files in the models folder whose names start with "prefix", and their Core ML copies (".mlpackage" folders, made the first time they run on a Mac).
    """
    if not os.path.isdir(janai.MODELS_FOLDER):
        return []
    return [
        os.path.join(janai.MODELS_FOLDER, name)
        for name in sorted(os.listdir(janai.MODELS_FOLDER))
        if name.startswith(prefix)
    ]


def download_manga_models():
    # One zip has all 7 models, so asking for any missing one downloads them all.
    missing_files = [
        file_name
        for file_name in janai.MANGA_MODEL_FILES.values()
        if not os.path.exists(os.path.join(janai.MODELS_FOLDER, file_name))
    ]
    if missing_files:
        janai.download_model_file(missing_files[0], janai.MANGA_MODELS_ZIP_URL)


def download_color_model():
    janai.download_model_file(janai.COLOR_MODEL_FILE, janai.COLOR_MODEL_ZIP_URL)


def download_waifu2x():
    from waifu2x import download_waifu2x

    download_waifu2x()


def download_magi():
    # Its progress shows in the Status view (see "load_full_magi_model").
    print(
        f"Downloading the Magi model ({format_size(MAGI_DOWNLOAD_BYTES)}) from {MAGI_PAGE_URL}..."
    )
    from magi import load_full_magi_model

    # Loading it downloads it the first time. The loaded model isn't kept.
    load_full_magi_model()


def get_waifu2x_row():
    row = StorageRow(
        name="waifu2x",
        description='Upscales images with the "Fast" and "Better" models.',
        url=WAIFU2X_PAGE_URL,
        download_size=WAIFU2X_DOWNLOAD_BYTES,
        download=download_waifu2x,
    )
    if os.path.isdir(utils.DOWNLOADED_WAIFU2X_FOLDER):
        row.status = DOWNLOADED
        row.paths = [utils.DOWNLOADED_WAIFU2X_FOLDER]
        row.folder_to_open = utils.DOWNLOADED_WAIFU2X_FOLDER
        row.can_delete = True
    elif utils.is_running_as_packaged_app():
        # The packaged app comes with it (its self-test checks it's there).
        row.status = BUILT_IN
    else:
        row.status = NOT_DOWNLOADED
    return row


def get_janai_row(name, description, prefix, needed_files, download_size, download):
    paths = get_model_files(prefix)
    is_downloaded = all(
        os.path.exists(os.path.join(janai.MODELS_FOLDER, file_name))
        for file_name in needed_files
    )
    return StorageRow(
        name=name,
        description=description,
        url=janai.MODELS_PAGE_URL,
        paths=paths,
        folder_to_open=janai.MODELS_FOLDER if paths else None,
        # Also when only some of its files are there (e.g. a download that stopped half-way).
        can_delete=bool(paths),
        status=DOWNLOADED if is_downloaded else NOT_DOWNLOADED,
        download_size=download_size,
        download=download,
    )


def is_hugging_face_model_downloaded(repo, revision):
    """
    Whether the model file of that exact version is in the Hugging Face cache. Its folder alone isn't enough: a download that stopped half-way leaves one too.
    """
    from huggingface_hub import try_to_load_from_cache

    return isinstance(
        try_to_load_from_cache(
            repo,
            "pytorch_model.bin",
            revision=revision,
            cache_dir=get_hugging_face_cache(),
        ),
        str,
    )


def get_magi_row():
    cache = get_hugging_face_cache()
    paths = [os.path.join(cache, folder) for folder in MAGI_CACHE_FOLDERS]
    existing_paths = [path for path in paths if os.path.isdir(path)]
    return StorageRow(
        name="Magi (full model)",
        description="Reads the text in the panels (for videos with a voice), and builds the panels-only model when running from source.",
        url=MAGI_PAGE_URL,
        paths=existing_paths,
        folder_to_open=existing_paths[0] if existing_paths else None,
        # Also when only part of it is there (e.g. a download that stopped half-way).
        can_delete=bool(existing_paths),
        status=DOWNLOADED
        if is_hugging_face_model_downloaded("ragavsachdeva/magiv2", MAGI_MODEL_REVISION)
        else NOT_DOWNLOADED,
        download_size=MAGI_DISK_BYTES,
        download=download_magi,
    )


def download_emotion_model():
    from EmotionAnalyzer import load_emotion_pipeline

    print(
        f"Downloading the emotion model ({format_size(EMOTION_DOWNLOAD_BYTES)}) from {EMOTION_PAGE_URL}..."
    )
    # Loading it downloads it the first time. The loaded model isn't kept.
    load_emotion_pipeline()


def get_emotion_row():
    # Only its own folder in the Hugging Face cache, which other apps share.
    folder = os.path.join(get_hugging_face_cache(), EMOTION_CACHE_FOLDER)
    # Also when only part of it is there (e.g. a download that stopped half-way).
    is_there = os.path.isdir(folder)
    return StorageRow(
        name="Emotion English DistilRoBERTa",
        description='Finds the emotion of each line, so Azure reads it in a matching voice style (Images To Video, with Azure\'s "Auto" voice style).',
        url=EMOTION_PAGE_URL,
        paths=[folder] if is_there else [],
        folder_to_open=folder if is_there else None,
        can_delete=is_there,
        status=DOWNLOADED
        if is_hugging_face_model_downloaded(EMOTION_MODEL_NAME, EMOTION_MODEL_REVISION)
        else NOT_DOWNLOADED,
        download_size=EMOTION_DOWNLOAD_BYTES,
        download=download_emotion_model,
    )


def get_panels_model_row():
    return StorageRow(
        name="Magi (panels only)",
        description="Finds the panels. The small part of the full Magi model that finds panels, included with Panelyze, so nothing needs to be downloaded for it.",
        url=MAGI_PAGE_URL,
        status=BUILT_IN if os.path.exists(PANELS_MODEL_FILE) else NOT_DOWNLOADED,
    )


def get_model_rows():
    """
    The models, by what they're for, in the order the tabs use them.
    """
    groups = [
        ("Panels and text", [get_panels_model_row(), get_magi_row()]),
        (
            "Upscaling",
            [
                get_waifu2x_row(),
                get_janai_row(
                    "MangaJaNai (7 models)",
                    'The "Best" upscale models for black and white manga, one for each common page height.',
                    "2x_MangaJaNai_",
                    janai.MANGA_MODEL_FILES.values(),
                    MANGA_MODELS_DOWNLOAD_BYTES,
                    download_manga_models,
                ),
                get_janai_row(
                    "IllustrationJaNai",
                    'The "Best" upscale model for color images.',
                    "2x_IllustrationJaNai_",
                    [janai.COLOR_MODEL_FILE],
                    COLOR_MODEL_DOWNLOAD_BYTES,
                    download_color_model,
                ),
            ],
        ),
        ("Voices", [get_emotion_row()]),
    ]
    rows = []
    for group, group_rows in groups:
        for row in group_rows:
            row.group = group
            rows.append(row)
    return rows
