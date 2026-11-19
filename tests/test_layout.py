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
    assert (window.min_width, window.min_height) == (800, 600)


def test_the_tabs_wrap_onto_another_line_when_they_do_not_fit(make_gui):
    gui = make_gui()
    tab_row = gui.app_bar.content.controls[0]

    assert tab_row.wrap
    assert tab_row.expand
    assert len(tab_row.controls) == len(TABS) - 1
