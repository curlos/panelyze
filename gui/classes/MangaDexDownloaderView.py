import flet as ft
from utils import is_tool_installed, pip_install_or_uninstall_tool
from download_from_mangadex import download_from_mangadex


class MangaDexDownloaderView(ft.Container):
    def __init__(self, page):
        super().__init__()
        self.bgcolor = "#3b4252"

        self.install_mangadex_downloader()

        self.page = page
        self.pick_files_dialog = ft.FilePicker(on_result=self.pick_files_result)
        self.page.overlay.append(self.pick_files_dialog)

        self.mangadex_url_text_field = ft.TextField(
            label="Enter a MangaDex Page URL",
            expand=True,
            border_color="#5e81ac",
        )

        self.terminal_output_list_view = ft.ListView(expand=True, auto_scroll=True)
        self.terminal_arrow_icon = ft.IconButton(
            ft.Icons.KEYBOARD_ARROW_DOWN,
            on_click=self.toggle_terminal_visibility,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4), padding=1),
        )

        self.terminal_output_list_view_wrapper = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(value="Terminal Output", color="#8fbcbb"),
                            self.terminal_arrow_icon,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self.terminal_output_list_view,
                ],
            ),
            bgcolor="#3b4252",
            padding=10,
            height=200,
            border=ft.border.only(top=ft.border.BorderSide(1, "#5e81ac")),
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

        top_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(controls=[self.mangadex_url_text_field]),
                    self.download_button,
                    self.cancel_button,
                ],
            ),
            padding=15,
        )

        self.content = ft.Column(
            controls=[
                top_container,
                ft.Container(
                    content=self.terminal_output_list_view_wrapper,
                    expand=True,
                    alignment=ft.alignment.bottom_left,
                ),
            ],
            expand=True,
        )

    def install_mangadex_downloader(self):
        mangadex_downloader_module_name = "mangadex_downloader"

        if not is_tool_installed(mangadex_downloader_module_name):
            print(f"Error: {mangadex_downloader_module_name} is not installed.")
            pip_install_or_uninstall_tool(mangadex_downloader_module_name, "install")

    def open_file_picker_dialog(self, e):
        is_empty_url = not self.mangadex_url_text_field.value

        if is_empty_url:
            self.terminal_output_list_view.controls.append(
                ft.Text(
                    "ERROR: MangaDex Page URL must not be empty.", color=ft.Colors.RED
                )
            )
            self.terminal_output_list_view.update()
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
                self.terminal_output_list_view,
                self.page.client_storage,
                self.cancel_button,
            )
        finally:
            self.download_button.visible = True
            self.cancel_button.visible = False
            self.download_button.update()
            self.cancel_button.update()

    # Define a function to toggle visibility
    def toggle_terminal_visibility(self, e):
        self.terminal_output_list_view.visible = (
            not self.terminal_output_list_view.visible
        )

        # Check if height is currently fixed (200)
        if self.terminal_output_list_view_wrapper.height == 200:
            # Set to auto height by removing fixed height
            self.terminal_output_list_view_wrapper.height = 60
            self.terminal_arrow_icon.icon = ft.Icons.KEYBOARD_ARROW_UP
        else:
            # Reset to fixed height
            self.terminal_output_list_view_wrapper.height = 200
            self.terminal_arrow_icon.icon = ft.Icons.KEYBOARD_ARROW_DOWN

        self.page.update()  # Refresh the UI to reflect changes
