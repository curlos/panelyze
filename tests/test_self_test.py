import pytest

import janai
import self_test


@pytest.mark.skipif(
    not janai.can_use_coreml(), reason="Core ML is only used on Apple Silicon Macs"
)
def test_the_best_upscaler_check_runs_core_ml_on_this_computer(tmp_path):
    assert (
        self_test.check_best_upscaler_libraries(str(tmp_path))
        == "spandrel loads, and Core ML converts and runs a model"
    )


def test_the_best_upscaler_check_works_without_core_ml(tmp_path, monkeypatch):
    monkeypatch.setattr(janai, "can_use_coreml", lambda: False)

    assert (
        self_test.check_best_upscaler_libraries(str(tmp_path))
        == "spandrel loads (Core ML isn't used on this computer)"
    )


def test_the_best_upscaler_check_is_part_of_the_self_test():
    assert self_test.check_best_upscaler_libraries in self_test.CHECKS


def test_the_video_check_fails_when_ffmpeg_is_not_the_one_that_comes_with_the_app(
    monkeypatch, tmp_path
):
    import moviepy.config

    # Like imageio-ffmpeg 0.5.1 on an Apple Silicon Mac: no ffmpeg of its own, so MoviePy ran the computer's ("ffmpeg" on the PATH, e.g. Homebrew's), which users don't have.
    monkeypatch.setattr(moviepy.config, "FFMPEG_BINARY", "ffmpeg")

    with pytest.raises(
        AssertionError, match="isn't the one that comes with imageio-ffmpeg"
    ):
        self_test.check_video(str(tmp_path))


def test_the_best_upscaler_check_fails_on_an_apple_silicon_mac_where_core_ml_does_not_load(
    monkeypatch, tmp_path
):
    import platform
    import sys

    # Loaded before pretending to be a Mac below (on Windows, torch only loads its DLLs when it sees "win32").
    import numpy  # noqa: F401
    import spandrel  # noqa: F401
    import torch  # noqa: F401

    # Like coremltools 8.1 on Python 3.12 without setuptools: it doesn't load, so the app would quietly use the slower PyTorch.
    monkeypatch.setattr(janai, "can_use_coreml", lambda: False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setitem(sys.modules, "coremltools", None)

    with pytest.raises(ImportError):
        self_test.check_best_upscaler_libraries(str(tmp_path))


def test_the_window_app_check_only_runs_in_the_packaged_mac_app(tmp_path):
    assert (
        self_test.check_mac_window_app(str(tmp_path))
        == "only checked in the packaged Mac app"
    )
    assert self_test.check_mac_window_app in self_test.CHECKS


def test_the_window_app_check_fails_when_the_window_app_is_still_named_flet(
    monkeypatch, tmp_path
):
    import plistlib
    import sys

    import utils

    # Like "flet pack" in Flet 0.25.2, which skipped renaming Flet's window app, so the Dock showed a second "Flet" icon.
    resources = tmp_path / "Panelyze.app" / "Contents" / "Resources"
    resources.mkdir(parents=True)
    (resources / "AppIcon.icns").write_bytes(b"icon")
    info = {"CFBundleName": "Panelyze", "CFBundleIconFile": "AppIcon.icns"}
    monkeypatch.setattr(utils, "is_running_as_packaged_app", lambda: True)
    monkeypatch.setattr(utils, "get_mac_window_app_folder", lambda: str(tmp_path))
    monkeypatch.setattr(sys, "platform", "darwin")

    with open(resources.parent / "Info.plist", "wb") as plist_file:
        plistlib.dump(info, plist_file)
    assert (
        self_test.check_mac_window_app(str(tmp_path))
        == "the window app is named Panelyze, with the Panelyze icon"
    )

    with open(resources.parent / "Info.plist", "wb") as plist_file:
        plistlib.dump({**info, "CFBundleName": "Flet"}, plist_file)
    with pytest.raises(AssertionError, match="the window app is Flet"):
        self_test.check_mac_window_app(str(tmp_path))


def test_the_matplotlib_cache_check_only_runs_in_the_packaged_app(tmp_path):
    assert (
        self_test.check_matplotlib_cache(str(tmp_path))
        == "only checked in the packaged app"
    )
    assert self_test.check_matplotlib_cache in self_test.CHECKS


def test_the_matplotlib_cache_check_fails_when_the_cache_is_a_new_folder_each_time(
    monkeypatch, tmp_path
):
    import matplotlib

    import utils

    # Like PyInstaller's own setting: a new, empty folder each time the app opens.
    monkeypatch.setattr(utils, "is_running_as_packaged_app", lambda: True)
    monkeypatch.setattr(matplotlib, "get_cachedir", lambda: str(tmp_path))

    with pytest.raises(AssertionError, match="matplotlib's cache is in"):
        self_test.check_matplotlib_cache(str(tmp_path))
