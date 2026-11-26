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
