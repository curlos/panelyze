import multiprocessing
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
from gui_classes.AppBar import AppBar
from gui_classes.MangaDexDownloaderView import MangaDexDownloaderView
from gui_classes.TerminalOutput import TerminalOutput
from gui_classes.MagiPanelByPanelView import MagiPanelByPanelView
from gui_classes.UpscaleImagesView import UpscaleImagesView
from gui_classes.ImagesToVideoView import ImagesToVideoView
from gui_classes.AppSettingsView import AppSettingsView
from gui_classes.PipelineView import PipelineView
from default_settings import DEFAULT_SETTINGS
from gui_classes.AppOutput import show_all_output_in_app
from utils import get_all_mangadex_languages


class GUI:
    def __init__(self, page: ft.Page):
        self.page = page

        self.page.theme_mode = "dark"
        self.page.theme = ft.Theme(color_scheme_seed="#5e81ac")
        self.page.dark_theme = ft.Theme(color_scheme_seed="#5e81ac")
        self.page.padding = 0

        self.page.title = "Panelyze"
        self.page.bgcolor = "#3b4252"

        self.set_client_storage_default_values()
        self.all_mangadex_languages = get_all_mangadex_languages()

        self.current_view = "Panel-By-Panel"
        self.is_job_running = False
        self.terminal_output = TerminalOutput(self.page)
        # From here on, everything printed (including errors and progress bars) also shows up in the app's terminal and the log file. This matters most when the app wasn't opened from a terminal.
        show_all_output_in_app(self.terminal_output.terminal_output_list_view)
        self.create_views()

        self.render_page_based_on_current_view()

    def create_views(self):
        self.MangaDexDownloaderView = MangaDexDownloaderView(self)
        self.MagiPanelByPanelView = MagiPanelByPanelView(self)
        self.UpscaleImagesView = UpscaleImagesView(self)
        self.ImagesToVideoView = ImagesToVideoView(self)
        self.PipelineView = PipelineView(self)
        self.AppSettingsView = AppSettingsView(self)

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

        self.create_views()

        self.render_page_based_on_current_view()
        self.page.update()

    def render_page_based_on_current_view(self):
        self.page.controls.clear()
        self.app_bar = AppBar(self)
        self.view_element = self.get_view_element()
        self.page.add(self.app_bar)

        view_element_with_terminal = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(content=self.view_element, expand=True),
                    ft.Container(
                        content=self.terminal_output,
                        alignment=ft.alignment.bottom_left,
                    ),
                ],
                expand=True,
            ),
            expand=True,
        )

        self.page.add(view_element_with_terminal)

    def get_view_element(self):
        if self.current_view == "Pipeline":
            # Settings may have changed in the other tabs since the review was last shown.
            self.PipelineView.refresh_review()

        return {
            "MangaDex Downloader": self.MangaDexDownloaderView,
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
            if not val and val != False:
                self.page.client_storage.set(setting_key, setting_value)


# Only open the window when this file is run directly (not when the tests import it).
if __name__ == "__main__":
    ft.app(target=GUI)
