import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flet as ft
from classes.AppBar import AppBar
from classes.MangaDexDownloaderView import MangaDexDownloaderView


def main(page: ft.Page):
    page.theme_mode = "dark"
    page.theme = ft.Theme(color_scheme_seed="#5e81ac")
    page.dark_theme = ft.Theme(color_scheme_seed="#5e81ac")
    page.padding = 0

    page.title = "Manga Panel Splitter"
    page.bgcolor = "#3b4252"

    app_bar = AppBar(page)
    mangadex_downloader_view = MangaDexDownloaderView(page)

    page.add(app_bar)
    page.add(mangadex_downloader_view)


ft.app(target=main)
