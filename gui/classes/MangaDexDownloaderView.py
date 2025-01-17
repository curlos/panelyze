import flet as ft
from utils import is_tool_installed, pip_install_or_uninstall_tool
from download_from_mangadex import download_from_mangadex
from classes.SettingsMangaDexDownloader import SettingsMangaDexDownloader


class MangaDexDownloaderView(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.bgcolor = "#3b4252"

        self.install_mangadex_downloader()

        self.parent_gui = parent_gui
        self.page = self.parent_gui.page
        self.pick_files_dialog = ft.FilePicker(on_result=self.pick_files_result)
        self.page.overlay.append(self.pick_files_dialog)

        self.mangadex_url_text_field = ft.TextField(
            label="Enter a MangaDex Page URL",
            # expand=True,
            border_color="#5e81ac",
        )

        self.expand = True

        self.download_button = ft.FilledTonalButton(
            text="Download",
            color="white",
            bgcolor="#5e81ac",
            on_click=self.open_file_picker_dialog,
        )

        self.cancel_button = ft.FilledTonalButton(
            text="Cancel",
            color="white",
            bgcolor="red",
            on_click=self.open_file_picker_dialog,
            visible=False,
        )

        self.settings = SettingsMangaDexDownloader(
            self.page, self.parent_gui.all_mangadex_languages
        )

        top_container = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                self.mangadex_url_text_field,
                                self.download_button,
                                self.cancel_button,
                            ],
                            expand=True,
                        ),
                        padding=15,
                        expand=True,
                    ),
                    ft.Container(content=ft.Column(controls=[self.settings])),
                ]
            ),
        )

        self.content = top_container

    def install_mangadex_downloader(self):
        mangadex_downloader_module_name = "mangadex_downloader"

        if not is_tool_installed(mangadex_downloader_module_name):
            print(f"Error: {mangadex_downloader_module_name} is not installed.")
            pip_install_or_uninstall_tool(mangadex_downloader_module_name, "install")

    def open_file_picker_dialog(self, e):
        is_empty_url = not self.mangadex_url_text_field.value

        if is_empty_url:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: MangaDex Page URL must not be empty."
            )
        else:
            self.pick_files_dialog.get_directory_path()

    def pick_files_result(self, e):
        mangadex_url_to_download_from = self.mangadex_url_text_field.value
        output_directory = e.path

        self.download_button.visible = False
        self.cancel_button.visible = True
        self.download_button.update()
        self.cancel_button.update()

        try:
            download_from_mangadex(
                mangadex_url_to_download_from,
                output_directory,
                self.parent_gui.terminal_output.terminal_output_list_view,
                self.page.client_storage,
                self.cancel_button,
            )
        finally:
            self.download_button.visible = True
            self.cancel_button.visible = False
            self.download_button.update()
            self.cancel_button.update()
