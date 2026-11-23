"""
A fake Flet page so the real GUI and its views can be built and driven in tests without opening a window. Click and change handlers are called directly, the same way a click would call them.
"""
from types import SimpleNamespace

import flet as ft
import pytest


class FakeClientStorage:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)

    def contains_key(self, key):
        return key in self.values


def get_all_controls(control):
    """
    The control and every control inside it.
    """
    all_controls = [control]
    for child in control._get_children():
        all_controls.extend(get_all_controls(child))
    return all_controls


class FakePageControls(list):
    def clear(self):
        # Like a real Flet page: controls taken off the screen lose their link to the page ("control.page" becomes None).
        for control in self:
            for removed_control in get_all_controls(control):
                removed_control.page = None
        super().clear()


class FakePage:
    def __init__(self):
        self.client_storage = FakeClientStorage()
        self.overlay = []
        self.controls = FakePageControls()
        self.window = SimpleNamespace(height=900, width=1400)
        self.height = 900
        self.width = 1400
        self.web = False
        # Like a real Flet page: the space between what's added to it.
        self.spacing = 10

    def add(self, *controls):
        # Like a real Flet page: controls put on the screen get linked to the page.
        for control in controls:
            for added_control in get_all_controls(control):
                added_control.page = self
        self.controls.extend(controls)

    def update(self, *args):
        pass

    # Like a real Flet page: a dialog is opened and closed on the page.
    def open(self, control):
        self.dialog = control

    def close(self, control):
        self.dialog = None

    def run_thread(self, handler, *args):
        handler(*args)


def fake_event(data=None, path=None, control=None, files=None):
    return SimpleNamespace(data=data, path=path, control=control, files=files)


@pytest.fixture
def make_gui(monkeypatch):
    """
    Returns a function that builds the real GUI on a fake page. Slow or network setup (MangaDex languages, pip checks, TTS voice list) is replaced with small fake values.
    """
    # Controls that aren't on a real page can't be updated. In tests, updating is a no-op.
    monkeypatch.setattr(ft.Control, "update", lambda self, *args, **kwargs: None)
    # Leave pytest's own output capturing alone ("AppOutput" has its own tests).
    monkeypatch.setattr(
        "gui.show_all_output_in_app", lambda terminal_output_list_view: None
    )

    import gui
    from gui_classes import TextToSpeechAzure

    monkeypatch.setattr(
        TextToSpeechAzure.TextToSpeechAzure,
        "get_locale_voice_mapping",
        lambda self: {"en-US": {"en-US-AriaNeural": {}, "en-US-GuyNeural": {}}},
    )

    def build():
        page = FakePage()
        return gui.GUI(page)

    return build
