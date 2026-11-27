from types import SimpleNamespace
from typing import Any, cast

import flet as ft

from gui_classes import Nord
from gui_classes.AppBar import TAB_NAMES
from gui_classes.WrappingCheckbox import WrappingCheckbox
from tests.fake_gui import fake_event, get_all_controls

TABS = [
    "Download",
    "Panel-By-Panel",
    "Upscale Images",
    "Images To Video",
    "Pipeline",
    "Settings",
]


def test_clicking_the_label_toggles_the_checkbox_like_a_normal_one():
    changes = []
    checkbox = WrappingCheckbox(
        "A label that is much too long to fit",
        value=False,
        on_change=lambda e: changes.append(e.data),
    )
    label = cast(ft.Container, checkbox.controls[1])
    assert label.on_click is not None

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
        c
        for c in all_controls
        if isinstance(c, ft.Checkbox) and id(c) not in inner_checkboxes
    ]

    assert wrapping_checkboxes
    assert plain_checkboxes == []


def test_the_window_opens_big_and_cannot_be_made_smaller_than_the_minimum(make_gui):
    window = make_gui().page.window

    assert (window.width, window.height) == (1100, 750)
    assert (window.min_width, window.min_height) == (360, 600)


def test_on_a_mac_the_tabs_go_in_the_title_bar_and_drag_the_window(
    make_gui, monkeypatch
):
    from tests import fake_gui

    original_init = fake_gui.FakePage.__init__

    def init_on_a_mac(self):
        original_init(self)
        self.platform = ft.PagePlatform.MACOS

    monkeypatch.setattr(fake_gui.FakePage, "__init__", init_on_a_mac)
    gui = make_gui()

    assert gui.page.window.title_bar_hidden
    assert isinstance(gui.title_bar, ft.WindowDragArea)
    # Room for the red, yellow and green buttons.
    assert gui.app_bar.padding.left == 78

    # On a wider window, they're in the margin left of the content, so less room is needed.
    gui.page.width = 1440
    gui.handle_resized(None)
    assert gui.app_bar.padding.left == 58
    gui.page.width = 3440
    gui.handle_resized(None)
    assert gui.app_bar.padding.left == 0


def test_elsewhere_the_window_keeps_its_title_bar(make_gui):
    gui = make_gui()

    assert not gui.page.window.title_bar_hidden
    assert not isinstance(gui.title_bar, ft.WindowDragArea)


def test_the_tabs_wrap_onto_another_line_when_they_do_not_fit(make_gui):
    gui = make_gui()
    tab_row = gui.app_bar.content.controls[0]

    assert tab_row.wrap
    assert tab_row.expand
    assert len(tab_row.controls) == len(TABS) - 1


def test_a_narrow_window_puts_the_settings_under_the_tab_instead_of_on_its_right(
    make_gui,
):
    gui = make_gui()
    columns = gui.MagiPanelByPanelView.pick_input_output_directories_container.responsive_columns
    assert isinstance(columns.content, ft.Row)

    gui.page.width = 400
    gui.handle_resized(fake_event())

    assert gui.is_narrow
    assert isinstance(columns.content, ft.Column)
    assert isinstance(gui.MangaDexDownloaderView.responsive_columns.content, ft.Column)
    # Phone size: the Status view puts its timer and each step on lines of their own.
    assert gui.terminal_output.progress_panel.is_phone_size

    gui.page.width = 1400
    gui.handle_resized(fake_event())

    assert isinstance(columns.content, ft.Row)
    assert not gui.terminal_output.progress_panel.is_phone_size


def test_a_narrow_window_shows_only_the_tab_icons(make_gui):
    gui = make_gui()
    gui.page.width = 400
    gui.handle_resized(fake_event())

    tab_buttons = [tab.content for tab in gui.app_bar.content.controls[0].controls]

    assert len(tab_buttons) == len(TAB_NAMES)
    assert all(
        isinstance(button, ft.IconButton) and button.icon for button in tab_buttons
    )
    assert all(button.tooltip.message for button in tab_buttons)


def test_on_a_narrow_window_the_buttons_share_its_width_instead_of_going_past_it(
    make_gui,
):
    gui = make_gui()
    pickers = gui.MagiPanelByPanelView.pick_input_output_directories_container
    buttons = [pickers.clear_button, pickers.cancel_button, pickers.submit_button]
    assert all(button.width == 170 and not button.expand for button in buttons)

    gui.page.width = 360
    gui.handle_resized(None)
    assert all(not button.width and button.expand for button in buttons)


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

    assert make_gui().current_view == "Download"
    assert make_gui_with_start_tab("Panel-By-Panel").current_view == "Panel-By-Panel"
    # Not a tab (e.g. a tab that was renamed): the default, Download.
    assert make_gui_with_start_tab("Old Tab Name").current_view == "Download"
    # Picked before the Download tab was renamed.
    assert make_gui_with_start_tab("MangaDex Downloader").current_view == "Download"


def test_the_arrow_keys_move_between_the_tabs_while_a_tab_is_focused(
    make_gui, monkeypatch
):
    focused = []
    # A tab with its name shown has no tooltip; an icon-only one has the name in its tooltip.
    monkeypatch.setattr(ft.TextButton, "focus", lambda self: focused.append(self.text))
    monkeypatch.setattr(
        ft.IconButton, "focus", lambda self: focused.append(self.tooltip.message)
    )
    gui = make_gui()

    def press(key):
        gui.handle_keyboard_shortcut(
            SimpleNamespace(key=key, ctrl=False, meta=False, alt=False, shift=False)
        )
        return gui.current_view

    # Nothing happens while the focus is somewhere else (like in a text box).
    assert press("Arrow Right") == "Download"

    gui.focused_tab = "Download"
    assert press("Arrow Right") == "Panel-By-Panel"
    assert press("Arrow Right") == "Upscale Images"
    assert press("Home") == "Download"
    # Going around at the ends.
    assert press("Arrow Left") == "Settings"
    assert press("Arrow Right") == "Download"
    assert press("End") == "Settings"
    # The newly opened tab is the one that's focused.
    assert focused[-1].startswith("Settings")


def test_the_content_is_capped_and_centered_like_a_bootstrap_container():
    from gui import MAX_CONTENT_WIDTH, get_content_width

    assert MAX_CONTENT_WIDTH == 1400
    # A narrower window is filled completely, a wider one only gets more margin.
    assert [
        get_content_width(width) for width in (360, 760, 1100, 1400, 1920, 3440)
    ] == [360, 760, 1100, 1400, 1400, 1400]


def test_the_content_width_follows_the_window(make_gui):
    gui = make_gui()
    gui.page.width = 3440

    gui.handle_resized(None)
    assert gui.content_container.width == 1400

    gui.page.width = 1000
    gui.handle_resized(None)
    assert gui.content_container.width == 1000


def test_after_a_restart_the_content_fills_the_window_without_a_resize(
    make_gui, monkeypatch
):
    from tests import fake_gui

    original_init = fake_gui.FakePage.__init__

    def init_like_after_flet_run_r(self):
        original_init(self)
        # After "flet run -r" restarts the app, "page.width" is a stale 800, but the window is really 1300 wide.
        self.width = 800
        self.window.width = 1300

    monkeypatch.setattr(fake_gui.FakePage, "__init__", init_like_after_flet_run_r)
    gui = make_gui()

    assert gui.content_container.width == 1300


def test_in_a_browser_the_content_follows_the_page_width(make_gui, monkeypatch):
    from tests import fake_gui

    original_init = fake_gui.FakePage.__init__

    def init_in_a_browser(self):
        original_init(self)
        # A browser has no app window, so its window width means nothing.
        self.web = True
        self.width = 900
        self.window.width = 1300

    monkeypatch.setattr(fake_gui.FakePage, "__init__", init_in_a_browser)

    assert make_gui().content_container.width == 900


def test_the_terminal_spans_the_window_and_its_text_lines_up_with_the_content(
    make_gui,
):
    gui = make_gui()
    terminal = gui.terminal_output

    gui.page.width = 2000
    gui.handle_resized(None)
    assert terminal.border is None
    # 300 px of margin on each side of the 1400 px content, plus the terminal's own 10.
    assert terminal.output_container.padding.left == 310
    assert terminal.output_container.padding.right == 310

    gui.page.width = 1000
    gui.handle_resized(None)
    assert terminal.output_container.padding.left == 10


def test_the_tabs_settings_have_no_border_on_their_left(make_gui):
    gui = make_gui()

    # The Download tab used to be the only one with a border.
    assert gui.MangaDexDownloaderView.settings.border is None


def test_a_dropdown_with_descriptions_shows_the_one_of_the_selected_choice():
    import flet as ft
    from gui_classes.DropdownTextOptions import DropdownTextOptions

    changed = []
    dropdown = DropdownTextOptions(
        label="Upscale Model",
        options=[
            ft.dropdown.Option(key="fast", text="Fast"),
            ft.dropdown.Option(key="best", text="Best"),
        ],
        value="fast",
        on_change=lambda e: changed.append(e.data),
        descriptions={
            "fast": "About 30 seconds a chapter",
            "best": "Slower, bigger download",
        },
    )
    assert dropdown.helper_text == "About 30 seconds a chapter"

    dropdown.value = "best"
    assert dropdown.on_change is not None
    dropdown.on_change(fake_event(data="best"))

    assert dropdown.helper_text == "Slower, bigger download"
    assert changed == ["best"]


def test_both_reading_direction_dropdowns_show_the_same_choice(make_gui):
    gui = make_gui()
    dropdowns = [
        control
        for view in (gui.MagiPanelByPanelView, gui.ImagesToVideoView)
        for control in get_all_controls(view)
        if isinstance(control, ft.Dropdown) and control.label == "Reading Direction"
    ]
    assert len(dropdowns) == 2
    panel_by_panel_dropdown, video_dropdown = dropdowns

    panel_by_panel_dropdown.value = "4koma"
    assert panel_by_panel_dropdown.on_change is not None
    panel_by_panel_dropdown.on_change(fake_event(data="4koma"))

    assert gui.page.client_storage.get("reading_direction") == "4koma"
    assert video_dropdown.value == "4koma"
    assert (
        video_dropdown.helper_text
        == "Strips are read top to bottom, right strip first."
    )


def test_a_reading_direction_choice_only_changes_the_dropdowns_in_its_own_window(
    make_gui,
):
    # E.g. two browser tabs in web mode, each with its own saved settings.
    gui, other_gui = make_gui(), make_gui()
    assert gui.page is not other_gui.page

    def get_dropdown(view):
        return next(
            control
            for control in get_all_controls(view)
            if isinstance(control, ft.Dropdown) and control.label == "Reading Direction"
        )

    dropdown = get_dropdown(gui.MagiPanelByPanelView)
    assert dropdown.on_change is not None

    dropdown.on_change(fake_event(data="ltr"))

    assert get_dropdown(gui.ImagesToVideoView).value == "ltr"
    assert get_dropdown(other_gui.ImagesToVideoView).value == "auto"


def test_every_tabs_settings_can_be_scrolled_in_a_short_window(make_gui):
    gui = make_gui()

    for view in (
        gui.MagiPanelByPanelView,
        gui.UpscaleImagesView,
        gui.ImagesToVideoView,
    ):
        settings = (
            view.pick_input_output_directories_container.settings_container.content
        )
        # Stacked under the main part on a narrow window, the settings only get part of the height.
        assert (
            isinstance(settings, ft.Column) and settings.scroll and settings.expand
        ), type(view).__name__


def test_raw_output_only_follows_new_lines_while_scrolled_to_the_bottom(make_gui):
    list_view = make_gui().terminal_output.terminal_output_list_view
    assert list_view.auto_scroll and list_view.on_scroll is not None

    def scrolled(pixels):
        return list_view.on_scroll(
            cast(
                Any,
                SimpleNamespace(
                    event_type="end", pixels=pixels, max_scroll_extent=2000
                ),
            )
        )

    # Scrolled up to read: new lines don't pull it back down.
    scrolled(400)
    assert not list_view.auto_scroll
    # Back at the bottom (or nearly): new lines are followed again.
    scrolled(1990)
    assert list_view.auto_scroll


def test_the_terminals_resize_line_only_shows_while_the_mouse_is_over_it(make_gui):
    terminal = make_gui().terminal_output

    def line_color():
        return terminal.resize_line.border.top.color

    assert line_color() == ft.Colors.TRANSPARENT
    terminal.resize_handle.on_enter(fake_event())
    assert line_color() == Nord.BLUE
    terminal.resize_handle.on_exit(fake_event())
    assert line_color() == ft.Colors.TRANSPARENT


class FakeFletConnection:
    """
    Stands in for the Flet app at the other end, so a real Flet page can be used without a window: every control added gets an id, as the app would give it.
    """

    page_name = ""
    page_url = "http://localhost"
    pubsubhub = None

    def __init__(self):
        self.next_id = 0

    def send_commands(self, session_id, commands):
        results = []
        for command in commands:
            if command.name == "add":
                ids = []
                for _ in command.commands:
                    self.next_id += 1
                    ids.append(f"_{self.next_id}")
                results.append(" ".join(ids))
        return SimpleNamespace(results=results, error=None)

    def send_command(self, session_id, command):
        return SimpleNamespace(result="", error=None)


def test_a_tab_s_buttons_stay_on_the_page_when_the_window_becomes_narrow_or_wide(
    make_gui, monkeypatch, request
):
    # A real Flet page (not "FakePage"): the bug was in how Flet itself handles controls moved in one update.
    import asyncio

    from flet.core.page import Page

    import gui as gui_module
    from tests.fake_gui import FakeClientStorage

    loop = asyncio.new_event_loop()
    request.addfinalizer(loop.close)
    page = Page(cast(Any, FakeFletConnection()), "session", loop)
    page._set_attr("platform", "macos", dirty=False)
    page._set_attr("width", 1100, dirty=False)
    monkeypatch.setattr(Page, "client_storage", FakeClientStorage())
    gui = gui_module.GUI(page)
    gui.app_bar.change_view("Upscale Images")
    submit_button = (
        gui.UpscaleImagesView.pick_input_output_directories_container.submit_button
    )

    for width in (600, 1100):
        page._set_attr("width", width, dirty=False)
        gui.handle_resized(fake_event())

        # Off the page, its next update (when Upscale is clicked) failed and the app stayed locked.
        assert gui.is_narrow == (width == 600)
        assert submit_button.page is page
