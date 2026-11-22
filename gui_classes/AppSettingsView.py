import os
import flet as ft
from gui_classes import Nord
from gui_classes.AppBar import TAB_NAMES
from gui_classes.DropdownTextOptions import DropdownTextOptions
import default_settings
from default_settings import PANELYZE_FOLDER, get_panelyze_folder_inside
from gui_classes.AppOutput import LOG_FILE_PATH
from utils import open_directory

# "No" is saved as "" (no comic file), but a dropdown choice with an empty key shows nothing in the box, so it's "no" there.
CBZ_DESCRIPTIONS = {
    "no": "",
    "small": "For phones and tablets, about 10x smaller.",
    "full": "The images as they are.",
}


def get_help_text(text):
    return ft.Text(text, color=Nord.TEXT)


def get_section(title, controls):
    """
    One group of settings, in a box of its own with a title, so the settings page reads as separate parts.
    """
    return ft.Container(
        content=ft.Column(
            controls=[ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=Nord.TEXT_BRIGHT), *controls],
            spacing=12,
        ),
        # The page's own color, so the dropdowns inside look like the ones in the other tabs. (Without a color, Flutter paints a dropdown's hover over the grey line under it too.)
        bgcolor=Nord.BACKGROUND,
        border=ft.border.all(1, Nord.SURFACE_HIGH),
        padding=16,
    )


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

        dev_output_folder = default_settings.DEV_OUTPUT_FOLDER
        self.panelyze_folder_text = ft.Text(
            dev_output_folder or self.parent_gui.page.client_storage.get("panelyze_folder"),
            color=Nord.PATH,
            selectable=True,
        )
        self.pick_panelyze_folder_dialog = ft.FilePicker(
            on_result=self.pick_panelyze_folder_result
        )
        self.parent_gui.page.overlay.append(self.pick_panelyze_folder_dialog)

        start_tab_section = get_section(
            "Starting up",
            [
                DropdownTextOptions(
                    label="Tab to open when Panelyze starts",
                    options=[ft.dropdown.Option(tab_name) for tab_name in TAB_NAMES],
                    value=self.parent_gui.get_start_tab(),
                    on_change=lambda e: self.parent_gui.page.client_storage.set("start_tab", e.data),
                ),
            ],
        )
        folder_section = get_section(
            "Where everything is saved",
            [
                get_help_text(
                    "Everything Panelyze makes is saved in this folder, with a folder inside it for each tool. A tab can still save somewhere else if you pick a folder there."
                ),
                self.panelyze_folder_text,
                ft.Text(
                    "Running from source (development), so everything is saved in this repo's own folder (this can't be changed here).",
                    size=12,
                    color=Nord.TEXT_MUTED,
                    visible=bool(dev_output_folder),
                ),
                ft.Row(
                    # Changing the folder does nothing when running from source (see "get_dev_output_folder").
                    visible=not dev_output_folder,
                    wrap=True,
                    controls=[
                        ft.ElevatedButton(
                            style=Nord.button_style("secondary"),
                            text="Change Folder",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda e: self.pick_panelyze_folder_dialog.get_directory_path(),
                        ),
                        ft.ElevatedButton(
                            style=Nord.button_style("secondary"),
                            text="Use Default Folder",
                            icon=ft.Icons.RESTART_ALT,
                            on_click=lambda e: self.parent_gui.change_panelyze_folder(
                                PANELYZE_FOLDER
                            ),
                        ),
                    ]
                ),
            ],
        )
        comic_file_section = get_section(
            ".cbz files",
            [
                get_help_text(
                    ".cbz files are made for downloaded chapters (the Download tab, not a Pipeline's Download step), panels (Panel-By-Panel) and upscaled images (Upscale). Open them in a comic reader app like Panels (iPhone and iPad) or Mihon (Android)."
                ),
                DropdownTextOptions(
                    label="Also save each chapter as a .cbz file",
                    options=[
                        ft.dropdown.Option(key="no", text="No"),
                        ft.dropdown.Option(key="small", text="Small"),
                        ft.dropdown.Option(key="full", text="Full quality"),
                    ],
                    value=self.parent_gui.page.client_storage.get("save_as_cbz") or "no",
                    on_change=lambda e: self.parent_gui.page.client_storage.set(
                        "save_as_cbz", "" if e.data == "no" else e.data
                    ),
                    descriptions=CBZ_DESCRIPTIONS,
                ),
            ],
        )
        log_file_section = get_section(
            "Log file",
            [
                get_help_text(
                    "Everything shown in the Terminal Output is also saved to a log file. It's useful to send along when something goes wrong."
                ),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            style=Nord.button_style("secondary"),
                            text="Open Log File",
                            icon=ft.Icons.DESCRIPTION,
                            on_click=lambda e: self.open_log_file(),
                        ),
                    ]
                ),
            ],
        )
        reset_section = get_section(
            "Reset",
            [
                get_help_text(
                    "Set every setting in every tab back to its default value. Your Azure key and region are kept."
                ),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            style=Nord.button_style("danger"),
                            text="Reset All Settings",
                            icon=ft.Icons.RESTART_ALT,
                            on_click=lambda e: self.parent_gui.reset_settings_to_default(),
                        ),
                    ]
                ),
            ],
        )

        self.content = ft.Column(
            controls=[
                ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
                start_tab_section,
                folder_section,
                comic_file_section,
                log_file_section,
                # Last, since it can't be undone.
                reset_section,
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        # The scrollbar is always shown, so it's clear there's more below when the window is short. It's drawn over the right edge of what scrolls, so the settings leave room for it on the right.
        self.content = ft.Column(
            controls=[ft.Container(content=self.content, padding=ft.padding.only(right=20))],
            scroll=ft.ScrollMode.ALWAYS,
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
