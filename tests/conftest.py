import os
import sys

import pytest

# Make the repo's root-level modules (utils.py, magi.py, etc.) importable from the tests.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.fake_gui import make_gui  # noqa: E402,F401 (makes the "make_gui" fixture available to every test)


@pytest.fixture(autouse=True)
def act_like_the_packaged_app(monkeypatch):
    """
    The tests run the same wherever they're run from (from source, the app saves to the repo's own folder, see "get_dev_output_folder").
    """
    import default_settings

    monkeypatch.setattr(default_settings, "DEV_OUTPUT_FOLDER", None)


@pytest.fixture(autouse=True)
def never_check_the_gpu_in_settings(monkeypatch):
    """
    The Settings page finds the GPU when it's opened, which loads PyTorch and sets up every GPU. Tests use a fixed answer instead, so they don't depend on this computer's GPUs.
    """
    from gui_classes import AppSettingsView

    monkeypatch.setattr(
        AppSettingsView,
        "get_device_sentence",
        lambda: (
            "The AI models run on the Test GPU. Not used: the Old GPU (PyTorch can't run on it).",
            ["Test GPU", "Old GPU"],
        ),
    )


@pytest.fixture(autouse=True)
def start_without_a_status_view(monkeypatch):
    """
    Each test starts without the Status view a test before it made (making one makes it the one that's reported to), so what one test reported never shows up in another.
    """
    from gui_classes import ProgressPanel

    monkeypatch.setattr(ProgressPanel, "current_progress_panel", None)


@pytest.fixture(autouse=True)
def never_download_waifu2x(monkeypatch):
    """
    The Upscale tab downloads waifu2x when it isn't installed. Tests must never download it, and shouldn't depend on whether it's installed (the tests that run waifu2x fake it).
    """
    from gui_classes import UpscaleImagesView

    monkeypatch.setattr(UpscaleImagesView, "download_waifu2x", lambda: "/fake/waifu2x")


@pytest.fixture(autouse=True)
def never_open_finder_windows(monkeypatch):
    """
    The app opens a job's output folder in Finder when it finishes. Tests must never do that (it would open a window every time one runs), whichever part of the app starts the job.
    """
    import utils
    from gui_classes import (
        AppSettingsView,
        JobView,
        MangaDexDownloaderView,
        PipelineView,
    )

    for module in (
        utils,
        AppSettingsView,
        JobView,
        MangaDexDownloaderView,
        PipelineView,
    ):
        monkeypatch.setattr(module, "open_directory", lambda path: None)


@pytest.fixture(autouse=True)
def keep_storage_in_tmp_path(monkeypatch, tmp_path):
    """
    Settings → Storage adds up the size of the app's folders whenever Settings is opened. Tests point it at empty folders in "tmp_path" instead, so they never read (or delete) the real downloads, models or Hugging Face cache.
    """
    import janai
    import storage
    from default_settings import OUTPUT_SUBFOLDERS
    import utils
    from gui_classes import StorageSection

    panelyze_folder = tmp_path / "Documents" / "Panelyze"
    monkeypatch.setattr(
        storage, "get_panelyze_folder", lambda client_storage: str(panelyze_folder)
    )
    monkeypatch.setattr(
        storage,
        "get_output_directory",
        lambda client_storage, key: str(panelyze_folder / OUTPUT_SUBFOLDERS[key]),
    )
    app_support = tmp_path / "Application Support" / "Panelyze"
    monkeypatch.setattr(
        utils, "DOWNLOADED_WAIFU2X_FOLDER", str(app_support / "waifu2x")
    )
    monkeypatch.setattr(janai, "MODELS_FOLDER", str(app_support / "upscale-models"))

    # No test downloads a model straight out of its zip on GitHub: a test's fake "download_file" gets the whole zip instead (a test can give its own "open_remote_zip").
    def whole_files_only(url):
        raise utils.PartialDownloadNotSupported(url)

    import waifu2x

    # waifu2x.py has its own copy of the folder (imported from utils.py), which it deletes before a download.
    monkeypatch.setattr(
        waifu2x, "DOWNLOADED_WAIFU2X_FOLDER", str(app_support / "waifu2x")
    )
    monkeypatch.setattr(janai, "open_remote_zip", whole_files_only)
    monkeypatch.setattr(waifu2x, "open_remote_zip", whole_files_only)
    monkeypatch.setattr(
        storage, "get_hugging_face_cache", lambda: str(tmp_path / "huggingface")
    )
    monkeypatch.setattr(
        storage, "PANELS_MODEL_FILE", str(tmp_path / "panels.safetensors")
    )
    monkeypatch.setattr(
        StorageSection, "LOG_FILE_PATH", str(tmp_path / "Logs" / "panelyze.log")
    )
    monkeypatch.setattr(StorageSection, "LOG_FOLDER", str(tmp_path / "Logs"))
    monkeypatch.setattr(StorageSection, "open_directory", lambda path: None)
