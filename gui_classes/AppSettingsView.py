import os
import flet as ft
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

        self.content = ft.Column(
            controls=[
                ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
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
        )

    def open_log_file(self):
        if not os.path.exists(LOG_FILE_PATH):
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                f"ERROR: There's no log file yet ({LOG_FILE_PATH})."
            )
            return

        open_directory(LOG_FILE_PATH)
