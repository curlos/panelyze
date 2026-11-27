import os
import plistlib
import shutil
import subprocess
import sys

import pytest

from default_settings import CODE_FOLDER


@pytest.mark.skipif(sys.platform != "darwin", reason="Only made on a Mac")
def test_the_dev_window_app_is_named_panelyze_with_the_panelyze_icon(tmp_path):
    def make():
        return subprocess.run(
            [os.path.join(CODE_FOLDER, "make_dev_window_app.sh")],
            env={**os.environ, "PANELYZE_DEV_WINDOW_DIR": str(tmp_path)},
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    window_folder = make()

    # Flet looks for the ".app" in this folder (FLET_VIEW_PATH).
    assert os.listdir(window_folder) == ["Panelyze.app"]
    contents = os.path.join(window_folder, "Panelyze.app", "Contents")
    with open(os.path.join(contents, "Info.plist"), "rb") as plist_file:
        info = plistlib.load(plist_file)
    assert info["CFBundleName"] == "Panelyze"
    assert info["CFBundleIconFile"] == "AppIcon"
    assert "CFBundleIconName" not in info
    assert os.path.exists(os.path.join(contents, "Resources", "AppIcon.icns"))
    # Flet's bundle ID, so the saved settings stay the same.
    assert info["CFBundleIdentifier"] == "com.appveyor.flet"

    # Made once: later runs just print the folder.
    made_at = os.path.getmtime(contents)
    assert make() == window_folder
    assert os.path.getmtime(contents) == made_at

    # A broken signature would stop the window from opening.
    subprocess.run(
        ["codesign", "--verify", os.path.join(window_folder, "Panelyze.app")],
        check=True,
    )
    # Nothing is left next to it, and the 120 MB copy isn't kept with the test's files.
    assert os.listdir(tmp_path) == [os.path.basename(window_folder)]
    shutil.rmtree(window_folder)
