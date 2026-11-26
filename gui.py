import multiprocessing
import threading
import sys

# In the packaged app, Python libraries (e.g. torch) sometimes start helper processes by running the app itself with special arguments. This makes the app recognize those and act as the helper, instead of opening another window.
multiprocessing.freeze_support()

# The packaged app starts a second copy of itself with "--run-mangadex" to run the MangaDex Downloader (a packaged app has no separate Python to run it with). That copy only runs the downloader, never the window.
if len(sys.argv) > 1 and sys.argv[1] == "--run-mangadex":
    from mangadex_downloader.cli import main

    main(sys.argv[2:])
    sys.exit(0)

# Checks that everything the app needs works, with no window (see "self_test.py").
if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
    from self_test import run_self_test

    sys.exit(run_self_test())

import flet as ft
from gui_classes.AppBar import AppBar, SHORTCUT_KEYS, TAB_LIST_KEYS, TAB_NAMES
from gui_classes import Nord
from gui_classes.MangaDexDownloaderView import MangaDexDownloaderView
from gui_classes.TerminalOutput import TerminalOutput
from gui_classes.MagiPanelByPanelView import MagiPanelByPanelView
from gui_classes.UpscaleImagesView import UpscaleImagesView
from gui_classes.ImagesToVideoView import ImagesToVideoView
from gui_classes.AppSettingsView import AppSettingsView
from gui_classes.PipelineView import PipelineView
from default_settings import DEFAULT_SETTINGS
from gui_classes.AppOutput import show_all_output_in_app
from utils import add_line_to_terminal_output_list_view, get_all_mangadex_languages


# The window opens at the default size. It can't be made smaller than the minimum size (about a phone's width), because the views don't fit in less space.
DEFAULT_WINDOW_WIDTH = 1100
DEFAULT_WINDOW_HEIGHT = 750
MIN_WINDOW_WIDTH = 360
MIN_WINDOW_HEIGHT = 600
# When the window is narrower than this, each tab's settings go under it instead of on its right, and the tabs at the top only show their icons.
NARROW_WINDOW_WIDTH = 760
# Everything (the tabs at the top, the tab's content and the terminal) is no wider than this (a bit wider than Bootstrap's largest container, 1320, and narrower than Tailwind's, 1536). A wider window only gets more margin on its sides, so on an ultra-wide screen the margins keep growing. A narrower window is filled completely.
MAX_CONTENT_WIDTH = 1400


def get_content_width(window_width):
    return min(window_width, MAX_CONTENT_WIDTH)


class GUI:
    def __init__(self, page: ft.Page):
        self.page = page
        # After "flet run -r" restarts the app, "page.width" is a stale 800 until the window is resized, but the window's own width is right. In a browser, there's no window.
        self.window_width = page.width if page.web else page.window.width or page.width
        self.set_window_size()

        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.theme = self.page.dark_theme = Nord.get_theme()
        self.page.padding = 0

        self.page.title = "Panelyze"
        # On a Mac, the tabs go up in the title bar next to the red, yellow and green buttons, like in Safari or Notes. Windows keeps its title bar (hiding it would also hide its minimize, maximize and close buttons).
        self.tabs_in_title_bar = (
            getattr(page, "platform", None) == ft.PagePlatform.MACOS and not page.web
        )
        self.page.window.title_bar_hidden = self.tabs_in_title_bar
        self.page.bgcolor = Nord.BACKGROUND
        self.page.on_resized = self.handle_resized
        self.page.on_keyboard_event = self.handle_keyboard_shortcut

        self.set_client_storage_default_values()
        self.all_mangadex_languages = get_all_mangadex_languages()

        self.current_view = self.get_start_tab()
        self.is_job_running = False
        # Flet runs click handlers in separate threads, so two clicks could both find no job running (see "try_to_start_job").
        self.job_lock = threading.Lock()
        self.running_job_name = ""
        self.is_narrow = self.get_is_narrow()
        # The tab in the app bar that's focused with the keyboard (None when the focus is somewhere else).
        self.focused_tab = None
        self.app_bar_slot = None
        self.title_bar = None
        self.view_slot = None
        # Holds everything on the page, at "get_content_width" (see "update_content_width").
        self.content_container = None
        self.terminal_output = TerminalOutput(self.page)
        # From here on, everything printed (including errors and progress bars) also shows up in the app's terminal and the log file. This matters most when the app wasn't opened from a terminal.
        show_all_output_in_app(self.terminal_output.terminal_output_list_view)
        self.create_views()

        self.render_page_based_on_current_view()

    def set_window_size(self):
        window = self.page.window
        window.width = DEFAULT_WINDOW_WIDTH
        window.height = DEFAULT_WINDOW_HEIGHT
        window.min_width = MIN_WINDOW_WIDTH
        window.min_height = MIN_WINDOW_HEIGHT

    def create_views(self, keep_settings_view=False):
        self.MangaDexDownloaderView = MangaDexDownloaderView(self)
        self.MagiPanelByPanelView = MagiPanelByPanelView(self)
        self.UpscaleImagesView = UpscaleImagesView(self)
        self.ImagesToVideoView = ImagesToVideoView(self)
        self.PipelineView = PipelineView(self)
        # Kept when resetting from the Settings page, so it stays scrolled where it was.
        if not keep_settings_view:
            self.AppSettingsView = AppSettingsView(self)
        self.set_views_narrow()

    def get_start_tab(self):
        # The tab picked in Settings. The default tab if it isn't one of the tabs (e.g. a tab that was renamed).
        start_tab = self.page.client_storage.get("start_tab")
        # The Download tab's old name, saved before it was renamed.
        if start_tab == "MangaDex Downloader":
            return "Download"
        return start_tab if start_tab in TAB_NAMES else DEFAULT_SETTINGS["start_tab"]

    def get_is_narrow(self):
        return (self.window_width or DEFAULT_WINDOW_WIDTH) < NARROW_WINDOW_WIDTH

    def set_views_narrow(self):
        # The tabs with settings on their right. (Pipeline and Settings are one column, so they already fit.)
        for view in [
            self.MangaDexDownloaderView,
            self.MagiPanelByPanelView,
            self.UpscaleImagesView,
            self.ImagesToVideoView,
        ]:
            view.set_narrow(self.is_narrow)

    def update_content_width(self):
        if not (self.content_container and self.app_bar_slot):
            return

        window_width = self.window_width or DEFAULT_WINDOW_WIDTH
        content_width = get_content_width(window_width)
        if self.content_container.width != content_width:
            self.content_container.width = content_width
            self.app_bar_slot.width = content_width
            self.content_container.update()
            self.app_bar_slot.update()

        # The terminal's text lines up with the content.
        self.terminal_output.set_side_margin(self.get_side_margin())

        if self.tabs_in_title_bar:
            self.app_bar.set_room_for_title_bar_buttons()
            self.app_bar.update()

    def get_side_margin(self):
        """
        The empty space on each side of the content, on a window wider than "MAX_CONTENT_WIDTH".
        """
        window_width = self.window_width or DEFAULT_WINDOW_WIDTH
        return (window_width - get_content_width(window_width)) / 2

    def try_to_start_job(self, job_name):
        """
        Start "job_name" if no other job is running (only one runs at a time), and say so if one is. Checked and claimed in one go, so a double-click (or a click and Enter) can't start two. Returns whether it started.
        """
        with self.job_lock:
            if self.is_job_running:
                already_running = True
            else:
                already_running = False
                self.is_job_running = True
        if already_running:
            # Only in the Raw Output: the Status view keeps showing the job that's running (an error there would mark it as failed).
            add_line_to_terminal_output_list_view(
                self.terminal_output.terminal_output_list_view,
                "ERROR: Another job is still running. Please wait for it to finish.",
                color=Nord.RED_TEXT,
            )
            return False
        self.set_job_running(True, job_name)
        return True

    def set_job_running(self, running, job_name=""):
        """
        Only one job runs at a time. While one runs, the other tabs are faded and can't be opened (with a hint saying which job they're waiting for), so nothing can start another job or change a setting the job is using.
        """
        self.is_job_running = running
        self.running_job_name = job_name
        # The new tabs aren't focused (the old ones are gone without telling).
        self.focused_tab = None
        # A new app bar, with the other tabs faded or back to normal.
        self.app_bar = AppBar(self)
        assert self.app_bar_slot, "A job started before the app bar was shown."
        self.app_bar_slot.content = self.app_bar
        try:
            self.app_bar_slot.update()
        except Exception:
            # E.g. the page has closed.
            pass

    def handle_resized(self, e):
        self.window_width = self.page.width
        self.update_content_width()

        is_narrow = self.get_is_narrow()
        if is_narrow == self.is_narrow:
            return

        self.is_narrow = is_narrow
        self.set_views_narrow()
        # Re-rendering also builds a new app bar, with or without the tab names.
        self.render_page_based_on_current_view()
        self.page.update()

    def handle_keyboard_shortcut(self, e):
        # While a tab is focused, the arrow keys (and Home and End) open the tabs around it.
        if (
            self.focused_tab
            and e.key in TAB_LIST_KEYS
            and not (e.ctrl or e.meta or e.alt or e.shift)
        ):
            self.app_bar.move_to_tab(e.key)
            return

        # Ctrl or ⌘ + a tab's key (see "SHORTCUT_KEYS") opens that tab.
        if not (e.ctrl or e.meta):
            return

        for view_name, key in SHORTCUT_KEYS.items():
            if e.key == key:
                self.app_bar.change_view(view_name)
                return

    def reset_settings_to_default(self):
        """
        Set every setting back to its default value. The views read their settings when they're created, so they're re-created afterwards to show the default values.
        """
        # Re-creating the views while a job is running would break that job.
        if self.is_job_running:
            self.terminal_output.update_terminal_with_error_message(
                "ERROR: Can't reset settings while a job is running. Please wait for it to finish."
            )
            return

        for setting_key in DEFAULT_SETTINGS:
            self.page.client_storage.remove(setting_key)

        self.set_client_storage_default_values()

        self.create_views(keep_settings_view=True)
        self.AppSettingsView.show_reset_settings()

        self.render_page_based_on_current_view()
        self.page.update()

    def change_panelyze_folder(self, panelyze_folder):
        """
        Save everything in "panelyze_folder" from now on (except for tools that have their own output folder picked). The views read their output folder when they're created, so they're re-created afterwards to show the new folders.
        """
        # Re-creating the views while a job is running would break that job.
        if self.is_job_running:
            self.terminal_output.update_terminal_with_error_message(
                "ERROR: Can't change the folder while a job is running. Please wait for it to finish."
            )
            return

        self.page.client_storage.set("panelyze_folder", panelyze_folder)

        self.create_views()

        self.render_page_based_on_current_view()
        self.page.update()

    def render_page_based_on_current_view(self):
        self.app_bar = AppBar(self)
        self.view_element = self.get_view_element()

        # The terminal is added to the page only once and stays on it when switching tabs. Taking it off the page would reset its scroll position. After the first time, only the app bar and the tab's content are swapped.
        if self.app_bar_slot and self.view_slot:
            self.app_bar_slot.content = self.app_bar
            self.view_slot.content = self.view_element
            return

        content_width = get_content_width(self.window_width or DEFAULT_WINDOW_WIDTH)
        self.app_bar_slot = ft.Container(content=self.app_bar, width=content_width)
        self.view_slot = ft.Container(content=self.view_element, expand=True)

        # The tab bar's color spans the whole window, like a title bar, and its tabs line up with the content under it.
        self.title_bar = ft.Container(
            content=ft.Row(
                controls=[self.app_bar_slot], alignment=ft.MainAxisAlignment.CENTER
            ),
            bgcolor=Nord.SURFACE,
        )
        if self.tabs_in_title_bar:
            # Dragging it moves the window. Double-clicking it doesn't zoom the window: listening for a double-click would make every click on a tab wait about 0.3 seconds, to see if a second click comes.
            self.title_bar = ft.WindowDragArea(self.title_bar, maximizable=False)

        self.content_container = ft.Container(
            content=self.view_slot, width=content_width
        )
        # The content is centered between the tab bar and the terminal, which span the whole window.
        self.page.add(
            ft.Column(
                controls=[
                    self.title_bar,
                    ft.Row(
                        controls=[self.content_container],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                        expand=True,
                    ),
                    self.terminal_output,
                ],
                spacing=self.page.spacing,
                expand=True,
            )
        )
        self.update_content_width()

    def get_view_element(self):
        if self.current_view == "Pipeline":
            # Settings may have changed in the other tabs since the review was last shown.
            self.PipelineView.refresh_review()
        if self.current_view == "Settings":
            self.AppSettingsView.show_device()

        return {
            "Download": self.MangaDexDownloaderView,
            "Panel-By-Panel": self.MagiPanelByPanelView,
            "Upscale Images": self.UpscaleImagesView,
            "Images To Video": self.ImagesToVideoView,
            "Pipeline": self.PipelineView,
            "Settings": self.AppSettingsView,
        }[self.current_view]

    def get_client_storage_default_values(self):
        return dict(DEFAULT_SETTINGS)

    def set_client_storage_default_values(self):
        client_storage_default_values = self.get_client_storage_default_values()

        for setting_key, setting_value in client_storage_default_values.items():
            val = self.page.client_storage.get(setting_key)
            # False and 0 are saved choices, so only a missing value gets the default.
            if not val and val != False:  # noqa: E712
                self.page.client_storage.set(setting_key, setting_value)


# Only open the window when this file is run directly (not when the tests import it).
if __name__ == "__main__":
    ft.app(target=GUI)
