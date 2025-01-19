import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flet as ft
from classes.AppBar import AppBar
from classes.MangaDexDownloaderView import MangaDexDownloaderView
from classes.TerminalOutput import TerminalOutput
from classes.MagiPanelByPanelView import MagiPanelByPanelView
from classes.UpscaleImagesView import UpscaleImagesView
from classes.ImagesToVideoView import ImagesToVideoView
from utils import get_all_mangadex_languages


class GUI(ft.Page):
    def __init__(self, page: ft.Page):
        self.page = page

        self.page.theme_mode = "dark"
        self.page.theme = ft.Theme(color_scheme_seed="#5e81ac")
        self.page.dark_theme = ft.Theme(color_scheme_seed="#5e81ac")
        self.page.padding = 0

        self.page.title = "Manga Panel Splitter"
        self.page.bgcolor = "#3b4252"

        self.set_client_storage_default_values()
        self.all_mangadex_languages = get_all_mangadex_languages()

        self.current_view = "Images To Video"
        self.terminal_output = TerminalOutput(self.page)
        self.MangaDexDownloaderView = MangaDexDownloaderView(self)
        self.MagiPanelByPanelView = MagiPanelByPanelView(self)
        self.UpscaleImagesView = UpscaleImagesView(self)
        self.ImagesToVideoView = ImagesToVideoView(self)

        self.render_page_based_on_current_view()

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
        if self.current_view == "MangaDex Downloader":
            return self.MangaDexDownloaderView
        elif self.current_view == "Panel-By-Panel":
            return self.MagiPanelByPanelView
        elif self.current_view == "Upscale Images":
            return self.UpscaleImagesView
        elif self.current_view == "Images To Video":
            return self.ImagesToVideoView

    def get_client_storage_default_values(self):
        client_storage_default_values = {
            # MangaDex Downloader
            "language": {"name": "English", "code": "en"},
            "use_start_and_end_pages": False,
            "use_start_and_end_chapters": False,
            "use_chapter_title": False,
            "no_group_name": False,
            "replace_existing_manga": False,
            "no_oneshot_chapters": False,
            "use_chapter_cover": False,
            "use_volume_cover": False,
            "start_page": "",
            "end_page": "",
            "start_chapter": "",
            "end_chapter": "",
            # Upscale Images
            "upscale_ratio": 2,
            "noise_level": 0,
            "image_format": "png",
            # Images To Video
            "video_height": 1080,
            "use_reading_speed_wpm": True,
            "reading_speed_wpm": 150,
            "use_image_displayed_duration": False,
            "image_displayed_duration": 5,
            "use_minimum_image_duration": True,
            "minimum_image_duration": 5,
        }

        return client_storage_default_values

    def set_client_storage_default_values(self):
        client_storage_default_values = self.get_client_storage_default_values()

        for setting_key, setting_value in client_storage_default_values.items():
            val = self.page.client_storage.get(setting_key)
            if not val and val != False:
                self.page.client_storage.set(setting_key, setting_value)


ft.app(target=GUI)
