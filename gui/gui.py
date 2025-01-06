import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flet as ft
from utils import is_tool_installed, pip_install_or_uninstall_tool
from download_from_mangadex import download_from_mangadex
from classes.AppBar import AppBar


class MangaDexDownloaderView(ft.Container):
    def __init__(self, page):
        super().__init__()
        self.bgcolor = "#3b4252"

        print("Calling install function now!")

        self.install_mangadex_downloader()

        self.page = page
        self.pick_files_dialog = ft.FilePicker(on_result=self.pick_files_result)
        self.page.overlay.append(self.pick_files_dialog)

        self.mangadex_url_text_field = ft.TextField(
            label="Enter a MangaDex Page URL",
            expand=True,
            border_color="#5e81ac",
        )

        self.output_list = ft.ListView(expand=True, auto_scroll=True)

        output_list_wrapper = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(value="Terminal Output", color="#8fbcbb"),
                    self.output_list,
                ]
            ),
            bgcolor="#3b4252",
            padding=10,
            height=200,
            border=ft.border.only(top=ft.border.BorderSide(1, "#5e81ac")),
        )

        self.expand = True

        top_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[self.mangadex_url_text_field]),
                    ft.FilledTonalButton(
                        text="Download",
                        color="white",
                        bgcolor="#5e81ac",
                        on_click=self.open_file_picker_dialog,
                    ),
                ],
            ),
            padding=15,
        )

        self.content = ft.Column(
            controls=[
                top_container,
                ft.Container(
                    content=output_list_wrapper,
                    expand=True,
                    alignment=ft.alignment.bottom_left,
                ),
            ],
            expand=True,
        )

    def install_mangadex_downloader(self):
        mangadex_downloader_module_name = "mangadex_downloader"

        print(
            f"Checking if installed: {is_tool_installed(mangadex_downloader_module_name)}"
        )

        if not is_tool_installed(mangadex_downloader_module_name):
            print(f"Error: {mangadex_downloader_module_name} is not installed.")
            pip_install_or_uninstall_tool(mangadex_downloader_module_name, "install")

    def open_file_picker_dialog(self, e):
        is_empty_url = not self.mangadex_url_text_field.value

        print(is_empty_url)

        if is_empty_url:
            self.output_list.controls.append(
                ft.Text(
                    "ERROR: MangaDex Page URL must not be empty.", color=ft.Colors.RED
                )
            )
            self.output_list.update()
        else:
            self.pick_files_dialog.get_directory_path()

    def pick_files_result(self, e):
        mangadex_url_to_download_from = self.mangadex_url_text_field.value
        output_directory = e.path

        download_from_mangadex(
            mangadex_url_to_download_from, output_directory, self.output_list
        )


def main(page: ft.Page):
    page.theme_mode = "dark"
    page.theme = ft.Theme(color_scheme_seed="#5e81ac")
    page.dark_theme = ft.Theme(color_scheme_seed="#5e81ac")
    page.padding = 0

    page.title = "Manga Panel Splitter"
    page.bgcolor = "#3b4252"

    # Define Navigation Drawer content
    page.navigation = ft.NavigationDrawer(
        controls=[
            ft.ListTile(
                title=ft.Text("Settings"),
                leading=ft.Icon(ft.icons.SETTINGS),
                on_click=lambda e: print("Settings clicked!"),
            ),
            ft.ListTile(
                title=ft.Text("About"),
                leading=ft.Icon(ft.icons.INFO),
                on_click=lambda e: print("About clicked!"),
            ),
        ]
    )

    app_bar = AppBar(page)
    mangadex_downloader_view = MangaDexDownloaderView(page)

    page.add(app_bar)
    page.add(mangadex_downloader_view)


ft.app(target=main)
