import flet as ft
from utils import is_tool_installed, pip_install_or_uninstall_tool


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
            border_color=ft.Colors.TEAL_500,
        )

        self.content = ft.Column(
            controls=[
                ft.Row(controls=[self.mangadex_url_text_field]),
                ft.FilledTonalButton(
                    text="Download",
                    color="white",
                    bgcolor=ft.Colors.TEAL_500,
                    on_click=self.open_file_picker_dialog,
                ),
            ]
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
        print("Going to start opening file picker dialog")
        self.pick_files_dialog.get_directory_path()

    def pick_files_result(self, e):
        print(f"Selected the folder: {e.path}")


def main(page: ft.Page):
    page.theme_mode = "dark"
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL_500)
    page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL_500)

    page.title = "Manga Panel Splitter"

    mangadex_downloader_view = MangaDexDownloaderView(page)

    page.add(mangadex_downloader_view)


ft.app(target=main)
