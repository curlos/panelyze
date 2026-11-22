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
def never_open_finder_windows(monkeypatch):
    """
    The app opens a job's output folder in Finder when it finishes. Tests must never do that (it would open a window every time one runs), whichever part of the app starts the job.
    """
    import utils
    from gui_classes import AppSettingsView, JobView, MangaDexDownloaderView, PipelineView

    for module in (utils, AppSettingsView, JobView, MangaDexDownloaderView, PipelineView):
        monkeypatch.setattr(module, "open_directory", lambda path: None)
