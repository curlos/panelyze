import sys
import os

# Add the root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import flet as ft
from utils import is_tool_installed, pip_install_or_uninstall_tool
from download_from_mangadex import download_from_mangadex


class MangaDexDownloaderView(ft.Container):
    def __init__(self, page):
        super().__init__()

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
                controls=[ft.Text(value="Terminal", color="#8fbcbb"), self.output_list]
            ),
            bgcolor="#3b4252",
            padding=10,
            height=200,
            border=ft.border.only(top=ft.border.BorderSide(1, "white")),
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


class AppBarButton(ft.TextButton):
    def __init__(self, text, current_view, change_view):
        super().__init__()
        self.text = text
        self.on_click = lambda e: change_view(text)
        self.set_button_style_by_view(current_view)

    def set_button_style_by_view(self, current_view):
        self.style = ft.ButtonStyle(
            bgcolor=(
                "#5e81ac" if current_view == self.text else ft.Colors.BLUE_GREY_800
            ),
            color="white",
            shape={
                ft.ControlState.HOVERED: ft.RoundedRectangleBorder(radius=0),
                ft.ControlState.DEFAULT: ft.RoundedRectangleBorder(radius=0),
            },
        )


class AppBar(ft.Container):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.current_view = "MangaDex Downloader"

        # Define the buttons
        self.mangadex_button = AppBarButton(
            text="MangaDex Downloader",
            current_view=self.current_view,
            change_view=self.change_view,
        )

        self.panel_button = AppBarButton(
            text="Panel-By-Panel",
            current_view=self.current_view,
            change_view=self.change_view,
        )

        self.bgcolor = ft.Colors.BLUE_GREY_800
        self.content = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        self.mangadex_button,
                        self.panel_button,
                    ]
                ),
                ft.IconButton(ft.icons.MENU, on_click=lambda e: page.navigation.open()),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=True,
        )

    # Function to change the view and update the button styles
    def change_view(self, view_name):
        self.current_view = view_name

        # Update button styles dynamically
        self.mangadex_button.style = ft.ButtonStyle(
            bgcolor=(
                "#5e81ac"
                if self.current_view == "MangaDex Downloader"
                else ft.Colors.BLUE_GREY_800
            ),
            color="white",
        )

        self.panel_button.style = ft.ButtonStyle(
            bgcolor=(
                "#5e81ac"
                if self.current_view == "Panel-By-Panel"
                else ft.Colors.BLUE_GREY_800
            ),
            color="white",
        )

        self.page.update()  # Refresh the UI


def main(page: ft.Page):
    page.theme_mode = "dark"
    page.theme = ft.Theme(color_scheme_seed="#5e81ac")
    page.dark_theme = ft.Theme(color_scheme_seed="#5e81ac")
    page.padding = 0

    page.title = "Manga Panel Splitter"

    app_bar = AppBar(page)

    page.add(app_bar)

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

    mangadex_downloader_view = MangaDexDownloaderView(page)

    page.add(mangadex_downloader_view)


ft.app(target=main)
