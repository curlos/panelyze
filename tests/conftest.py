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


@pytest.fixture(autouse=True)
def never_ask_for_the_translators_model_lists(monkeypatch):
    """
    Translate's settings list the models Ollama has installed, or the ones an API key can use. Tests never ask Ollama or the internet for that (tests of "list_models" itself fake the answers).
    """
    import translate
    from gui_classes import SettingsTranslate, TranslateView

    monkeypatch.setattr(SettingsTranslate, "list_models", lambda engine, api_key="": [])
    monkeypatch.setattr(SettingsTranslate, "list_installed_ollama_models", lambda: {})
    # The default Ollama model depends on what's downloaded and the free disk space: none, and plenty.
    monkeypatch.setattr(translate, "list_installed_ollama_models", lambda: {})
    # Translate's own check before a job: Ollama not running, so it never downloads a model in a test.
    monkeypatch.setattr(TranslateView, "list_installed_ollama_models", lambda: None)
    monkeypatch.setattr(translate, "get_free_disk_gb", lambda: 100)
