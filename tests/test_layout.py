from types import SimpleNamespace

import flet as ft

from gui_classes.WrappingCheckbox import WrappingCheckbox
from tests.fake_gui import fake_event, get_all_controls

TABS = [
    "MangaDex Downloader",
    "Panel-By-Panel",
    "Upscale Images",
    "Images To Video",
    "Pipeline",
    "Settings",
]


def test_clicking_the_label_toggles_the_checkbox_like_a_normal_one():
    changes = []
    checkbox = WrappingCheckbox("A label that is much too long to fit", value=False, on_change=lambda e: changes.append(e.data))
    label = checkbox.controls[1]

    label.on_click(fake_event())
    label.on_click(fake_event())

    assert changes == ["true", "false"]
    assert checkbox.value is False


def test_the_value_can_be_read_and_set_like_a_normal_checkbox():
    checkbox = WrappingCheckbox("Label")

    checkbox.value = True

    assert checkbox.value is True
    assert checkbox.checkbox.value is True


def test_every_checkbox_in_the_app_wraps_its_label(make_gui):
    gui = make_gui()
    # Open every tab, since only the open one is on the page.
    all_controls = []
    for tab in TABS:
        gui.app_bar.change_view(tab)
        all_controls += get_all_controls(gui.view_element)

    wrapping_checkboxes = [c for c in all_controls if isinstance(c, WrappingCheckbox)]
    inner_checkboxes = {id(c.checkbox) for c in wrapping_checkboxes}
    plain_checkboxes = [
        c for c in all_controls if isinstance(c, ft.Checkbox) and id(c) not in inner_checkboxes
    ]

    assert wrapping_checkboxes
    assert plain_checkboxes == []


def test_the_window_opens_big_and_cannot_be_made_smaller_than_the_minimum(make_gui):
    window = make_gui().page.window

    assert (window.width, window.height) == (1100, 750)
    assert (window.min_width, window.min_height) == (360, 600)


def test_the_tabs_wrap_onto_another_line_when_they_do_not_fit(make_gui):
    gui = make_gui()
    tab_row = gui.app_bar.content.controls[0]

    assert tab_row.wrap
    assert tab_row.expand
    assert len(tab_row.controls) == len(TABS) - 1


def test_a_narrow_window_puts_the_settings_under_the_tab_instead_of_on_its_right(make_gui):
    gui = make_gui()
    columns = gui.MagiPanelByPanelView.pick_input_output_directories_container.responsive_columns
    assert isinstance(columns.content, ft.Row)

    gui.page.width = 400
    gui.handle_resized(fake_event())

    assert gui.is_narrow
    assert isinstance(columns.content, ft.Column)
    assert isinstance(gui.MangaDexDownloaderView.responsive_columns.content, ft.Column)

    gui.page.width = 1400
    gui.handle_resized(fake_event())

    assert isinstance(columns.content, ft.Row)


def test_a_narrow_window_shows_only_the_tab_icons(make_gui):
    gui = make_gui()
    gui.page.width = 400
    gui.handle_resized(fake_event())

    tab_buttons = [tab.content for tab in gui.app_bar.content.controls[0].controls]

    assert all(isinstance(button, ft.IconButton) and button.icon for button in tab_buttons)
    assert all(button.tooltip for button in tab_buttons)


def test_ctrl_or_cmd_and_a_number_opens_that_tab(make_gui):
    gui = make_gui()

    gui.handle_keyboard_shortcut(SimpleNamespace(key="5", ctrl=True, meta=False))
    assert gui.current_view == "Pipeline"

    gui.handle_keyboard_shortcut(SimpleNamespace(key=",", ctrl=False, meta=True))
    assert gui.current_view == "Settings"

    # Without Ctrl or Cmd, typing a number does nothing.
    gui.handle_keyboard_shortcut(SimpleNamespace(key="1", ctrl=False, meta=False))
    assert gui.current_view == "Settings"


def test_the_app_opens_on_the_tab_picked_in_settings(make_gui, monkeypatch):
    from tests import fake_gui

    # Every new fake page starts with "start_tab" saved as below (like a setting saved in an earlier session).
    def make_gui_with_start_tab(start_tab):
        original_init = fake_gui.FakePage.__init__

        def init_with_start_tab(self):
            original_init(self)
            self.client_storage.set("start_tab", start_tab)

        monkeypatch.setattr(fake_gui.FakePage, "__init__", init_with_start_tab)
        return make_gui()

    assert make_gui().current_view == "Panel-By-Panel"
    assert make_gui_with_start_tab("MangaDex Downloader").current_view == "MangaDex Downloader"
    # Not a tab (e.g. a tab that was renamed): Panel-By-Panel.
    assert make_gui_with_start_tab("Old Tab Name").current_view == "Panel-By-Panel"


def test_the_arrow_keys_move_between_the_tabs_while_a_tab_is_focused(make_gui, monkeypatch):
    focused = []
    monkeypatch.setattr(ft.TextButton, "focus", lambda self: focused.append(self.tooltip))
    monkeypatch.setattr(ft.IconButton, "focus", lambda self: focused.append(self.tooltip))
    gui = make_gui()

    def press(key):
        gui.handle_keyboard_shortcut(SimpleNamespace(key=key, ctrl=False, meta=False, alt=False, shift=False))
        return gui.current_view

    # Nothing happens while the focus is somewhere else (like in a text box).
    assert press("Arrow Right") == "Panel-By-Panel"

    gui.focused_tab = "Panel-By-Panel"
    assert press("Arrow Right") == "Upscale Images"
    assert press("Home") == "MangaDex Downloader"
    # Going around at the ends.
    assert press("Arrow Left") == "Settings"
    assert press("Arrow Right") == "MangaDex Downloader"
    assert press("End") == "Settings"
    # The newly opened tab is the one that's focused.
    assert focused[-1].startswith("Settings")
