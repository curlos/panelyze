import flet as ft
from default_settings import get_output_directory
from download_from_mangadex import download_from_mangadex
from gui_classes.SettingsMangaDexDownloader import SettingsMangaDexDownloader
from utils import get_newest_subfolder


class MangaDexDownloaderView(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.bgcolor = "#3b4252"

        self.parent_gui = parent_gui
        self.page = self.parent_gui.page
        self.pick_files_dialog = ft.FilePicker(on_result=self.pick_output_directory_result)
        self.page.overlay.append(self.pick_files_dialog)

        # Downloads go to the saved output folder (the default one unless it was changed).
        self.output_directory_text = ft.Text(
            get_output_directory(self.page.client_storage, "output_directory_mangadex"),
            color="white",
            expand=True,
        )

        self.mangadex_url_text_field = ft.TextField(
            label="Enter a MangaDex Page URL",
            border_color="#5e81ac",
        )

        self.expand = True

        self.download_button = ft.FilledTonalButton(
            text="Download",
            color="white",
            bgcolor="#5e81ac",
            on_click=self.handle_download,
        )

        # The Cancel button gets its click handler when a download starts (see "download_from_mangadex").
        self.cancel_button = ft.FilledTonalButton(
            text="Cancel",
            color="white",
            bgcolor="red",
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
                                ft.Row(
                                    controls=[
                                        ft.Text("Save to:", color="white"),
                                        self.output_directory_text,
                                        ft.IconButton(
                                            ft.Icons.FOLDER_OPEN,
                                            icon_color="white",
                                            tooltip="Pick a different output folder",
                                            on_click=lambda e: self.pick_files_dialog.get_directory_path(),
                                        ),
                                        ft.IconButton(
                                            ft.Icons.RESTART_ALT,
                                            icon_color="white",
                                            tooltip="Use the default output folder",
                                            on_click=lambda e: self.set_output_directory(""),
                                        ),
                                    ]
                                ),
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

    def set_output_directory(self, output_directory):
        # An empty one means the default folder.
        self.page.client_storage.set("output_directory_mangadex", output_directory)
        self.output_directory_text.value = get_output_directory(
            self.page.client_storage, "output_directory_mangadex"
        )
        self.output_directory_text.update()

    def fill_in_panel_by_panel_input(self, output_directory):
        """
        Panel-By-Panel is the next step, so it starts with the manga that was just downloaded (the newest folder in the output folder), unless the user picked a folder there themselves.
        """
        downloaded_manga_directory = get_newest_subfolder(output_directory)
        picker = self.parent_gui.MagiPanelByPanelView.pick_input_output_directories_container

        if downloaded_manga_directory and (
            not picker.input_directory or picker.input_was_filled_in_by_app
        ):
            picker.set_input_directory(downloaded_manga_directory, filled_in_by_app=True)

    def pick_output_directory_result(self, e):
        # The user cancelled the dialog.
        if not e.path:
            return

        self.set_output_directory(e.path)

    def handle_download(self, e):
        if not self.mangadex_url_text_field.value:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: MangaDex Page URL must not be empty."
            )
            return

        # Only one job can run at a time (see "PickInputAndOutputDirectories.handle_submit").
        if self.parent_gui.is_job_running:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: Another job is still running. Please wait for it to finish."
            )
            return

        mangadex_url_to_download_from = self.mangadex_url_text_field.value
        output_directory = get_output_directory(
            self.page.client_storage, "output_directory_mangadex"
        )

        self.parent_gui.is_job_running = True
        self.download_button.visible = False
        self.cancel_button.visible = True
        self.download_button.update()
        self.cancel_button.update()

        terminal_output = self.parent_gui.terminal_output
        terminal_output.show_loading_text("Downloading from MangaDex...")

        try:
            download_from_mangadex(
                mangadex_url_to_download_from,
                output_directory,
                terminal_output.terminal_output_list_view,
                self.parent_gui.page.client_storage,
                self.cancel_button,
            )
            terminal_output.hide_loading_text("MangaDex download ended.")
            self.fill_in_panel_by_panel_input(output_directory)
        except Exception:
            terminal_output.hide_loading_text("MangaDex download failed.", success=False)
            raise
        finally:
            self.parent_gui.is_job_running = False
            self.download_button.visible = True
            self.cancel_button.visible = False
            self.download_button.update()
            self.cancel_button.update()
