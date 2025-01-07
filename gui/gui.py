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

        app_bar = AppBar(page)
        mangadex_downloader_view = MangaDexDownloaderView(page)

        self.page.add(app_bar)
        self.page.add(mangadex_downloader_view)


ft.app(target=GUI)
