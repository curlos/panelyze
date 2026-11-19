import os
import flet as ft
from default_settings import PANELYZE_FOLDER, get_panelyze_folder_inside
from gui_classes.AppOutput import LOG_FILE_PATH
from utils import open_directory


class AppSettingsView(ft.Container):
    """
    App-wide settings (opened with the gear icon in the app bar). Each tab's own settings stay in that tab.
    """

    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui
        self.padding = 20
        # Takes the space above the terminal, so the page below can scroll when it doesn't all fit.
        self.expand = True

        self.panelyze_folder_text = ft.Text(
            self.parent_gui.page.client_storage.get("panelyze_folder"),
            color="white",
            selectable=True,
        )
        self.pick_panelyze_folder_dialog = ft.FilePicker(
            on_result=self.pick_panelyze_folder_result
        )
        self.parent_gui.page.overlay.append(self.pick_panelyze_folder_dialog)

        self.content = ft.Column(
            controls=[
                ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Everything Panelyze makes is saved in this folder, with a folder inside it for each tool. A tab can still save somewhere else if you pick a folder there.",
                    color="white",
                ),
                self.panelyze_folder_text,
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            text="Change Folder",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda e: self.pick_panelyze_folder_dialog.get_directory_path(),
                        ),
                        ft.ElevatedButton(
                            text="Use Default Folder",
                            icon=ft.Icons.RESTART_ALT,
                            on_click=lambda e: self.parent_gui.change_panelyze_folder(
                                PANELYZE_FOLDER
                            ),
                        ),
                    ]
                ),
                ft.Dropdown(
                    label="Also save each chapter as a comic file (.cbz)",
                    options=[
                        ft.dropdown.Option(key="", text="No"),
                        ft.dropdown.Option(key="small", text="Small: for phones and tablets (about 10x smaller)"),
                        ft.dropdown.Option(key="full", text="Full quality: the images as they are"),
                    ],
                    value=self.parent_gui.page.client_storage.get("save_as_cbz") or "",
                    on_change=lambda e: self.parent_gui.page.client_storage.set("save_as_cbz", e.data),
                ),
                ft.Text(
                    "Comic files are made for the panels (Panel-By-Panel) and upscaled images (Upscale). Open them in a comic reader app like Panels (iPhone and iPad) or Mihon (Android).",
                    color="white",
                ),
                ft.Text(
                    "Set every setting in every tab back to its default value. Your Azure key and region are kept.",
                    color="white",
                ),
                ft.ElevatedButton(
                    text="Reset All Settings",
                    icon=ft.Icons.RESTART_ALT,
                    bgcolor="#bf616a",
                    color="white",
                    on_click=lambda e: self.parent_gui.reset_settings_to_default(),
                ),
                ft.Text(
                    "Everything shown in the Terminal Output is also saved to a log file. It's useful to send along when something goes wrong.",
                    color="white",
                ),
                ft.ElevatedButton(
                    text="Open Log File",
                    icon=ft.Icons.DESCRIPTION,
                    on_click=lambda e: self.open_log_file(),
                ),
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
        )

    def pick_panelyze_folder_result(self, e):
        # The user cancelled the dialog.
        if not e.path:
            return

        self.parent_gui.change_panelyze_folder(get_panelyze_folder_inside(e.path))

    def open_log_file(self):
        if not os.path.exists(LOG_FILE_PATH):
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                f"ERROR: There's no log file yet ({LOG_FILE_PATH})."
            )
            return

        open_directory(LOG_FILE_PATH)
