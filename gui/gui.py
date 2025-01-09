import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flet as ft
from classes.AppBar import AppBar
from classes.MangaDexDownloaderView import MangaDexDownloaderView
from classes.TerminalOutput import TerminalOutput
from classes.MagiPanelByPanelView import MagiPanelByPanelView


class GUI(ft.Page):
    def __init__(self, page: ft.Page):
        self.page = page

        self.page.theme_mode = "dark"
        self.page.theme = ft.Theme(color_scheme_seed="#5e81ac")
        self.page.dark_theme = ft.Theme(color_scheme_seed="#5e81ac")
        self.page.padding = 0

        self.page.title = "Manga Panel Splitter"
        self.page.bgcolor = "#3b4252"

        self.current_view = "Panel-By-Panel"
        self.terminal_output = TerminalOutput(self.page)
        self.MangaDexDownloaderView = MangaDexDownloaderView(self)
        self.MagiPanelByPanelView = MagiPanelByPanelView(self)

        self.render_page_based_on_current_view()

    def render_page_based_on_current_view(self):
        self.page.controls.clear()
        self.app_bar = AppBar(self)
        self.view_element = self.get_view_element()
        self.page.add(self.app_bar)

        view_element_with_terminal = ft.Column(
            controls=[
                self.view_element,
                ft.Container(
                    content=self.terminal_output,
                    expand=True,
                    alignment=ft.alignment.bottom_left,
                ),
            ],
            expand=True,
        )

        self.page.add(view_element_with_terminal)

    def get_view_element(self):
        if self.current_view == "MangaDex Downloader":
            return self.MangaDexDownloaderView
        elif self.current_view == "Panel-By-Panel":
            return self.MagiPanelByPanelView


ft.app(target=GUI)
