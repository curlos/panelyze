import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flet as ft
from classes.AppBar import AppBar
from classes.MangaDexDownloaderView import MangaDexDownloaderView


class GUI(ft.Page):
    def __init__(self, page: ft.Page):
        self.page = page

        self.page.theme_mode = "dark"
        self.page.theme = ft.Theme(color_scheme_seed="#5e81ac")
        self.page.dark_theme = ft.Theme(color_scheme_seed="#5e81ac")
        self.page.padding = 0

        self.page.title = "Manga Panel Splitter"
        self.page.bgcolor = "#3b4252"

        self.current_view = "MangaDex Downloader"
        self.render_page_based_on_current_view()

    def render_page_based_on_current_view(self):
        self.page.controls.clear()

        self.app_bar = AppBar(self)
        self.view_element = self.get_view_element()
        self.page.add(self.app_bar)
        self.page.add(self.view_element)

    def get_view_element(self):
        if self.current_view == "MangaDex Downloader":
            return MangaDexDownloaderView(self.page)
        elif self.current_view == "Panel-By-Panel":
            return ft.Text("Hello World! Panel-By-Panel.")


ft.app(target=GUI)
