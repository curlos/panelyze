import os
import threading
import flet as ft
from gui_classes import Nord
from gui_classes.AppBar import TAB_NAMES
from gui_classes.DropdownTextOptions import DropdownTextOptions
import default_settings
from default_settings import APP_VERSION, PANELYZE_FOLDER, get_panelyze_folder_inside
from gui_classes.AppOutput import LOG_FILE_PATH, LOG_FOLDER
from gui_classes.StorageSection import StorageSection
from utils import open_directory

# "No" is saved as "" (no comic file), but a dropdown choice with an empty key shows nothing in the box, so it's "no" there.
CBZ_DESCRIPTIONS = {
    "no": "",
    "small": "For phones and tablets, about 10x smaller.",
    "full": "The images as they are.",
}
REPO_URL = "https://github.com/curlos/panelyze"
# Straight to a new issue (with the "Something went wrong" template).
ISSUES_URL = "https://github.com/curlos/panelyze/issues/new/choose"
RESET_MESSAGE = "All settings in every tab are back to their defaults."
# How long "All settings ... are back to their defaults." stays next to (or above) the button.
RESET_MESSAGE_SECONDS = 3


def get_device_sentence():
    """
    Where the AI models run, as a sentence ("The AI models run on the AMD Radeon RX 6700 XT. ..."; see "magi.get_device_choice"), and the names of the devices in it. Magi is imported only here, since that loads PyTorch (slow).
    """
    from magi import get_device_choice

    _, sentence, device_names = get_device_choice()
    return sentence, device_names


def get_help_text(text):
    return ft.Text(text, color=Nord.TEXT)


def get_section(title, controls, title_button=None):
    """
    One group of settings, in a box of its own with a title, so the settings page reads as separate parts. "title_button" (e.g. Storage's Refresh) goes right after the title.
    """
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            title,
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=Nord.TEXT_BRIGHT,
                        ),
                        *([title_button] if title_button else []),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                *controls,
            ],
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
            dev_output_folder
            or self.parent_gui.page.client_storage.get("panelyze_folder"),
            color=Nord.PATH,
            selectable=True,
        )
        self.pick_panelyze_folder_dialog = ft.FilePicker(
            on_result=self.pick_panelyze_folder_result
        )
        self.parent_gui.page.overlay.append(self.pick_panelyze_folder_dialog)

        self.start_tab_dropdown = DropdownTextOptions(
            label="Tab to open when Panelyze starts",
            options=[ft.dropdown.Option(tab_name) for tab_name in TAB_NAMES],
            value=self.parent_gui.get_start_tab(),
            on_change=lambda e: self.parent_gui.page.client_storage.set(
                "start_tab", e.data
            ),
        )
        start_tab_section = get_section("Starting up", [self.start_tab_dropdown])
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
                            on_click=lambda e: (
                                self.pick_panelyze_folder_dialog.get_directory_path()
                            ),
                        ),
                        ft.ElevatedButton(
                            style=Nord.button_style("secondary"),
                            text="Use Default Folder",
                            icon=ft.Icons.RESTART_ALT,
                            on_click=lambda e: self.parent_gui.change_panelyze_folder(
                                PANELYZE_FOLDER
                            ),
                        ),
                    ],
                ),
            ],
        )
        # Filled in each time this page is opened (see "get_view_element" in gui.py).
        self.storage_section = StorageSection(self.parent_gui)
        storage_section = get_section(
            "Storage",
            [
                get_help_text(
                    "What Panelyze keeps on this computer, and how much space it takes. A deleted model is downloaded again the next time it's needed."
                ),
                self.storage_section,
            ],
            title_button=self.storage_section.refresh_button,
        )
        self.cbz_dropdown = DropdownTextOptions(
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
        )
        comic_file_section = get_section(
            ".cbz files",
            [
                get_help_text(
                    ".cbz files are made for downloaded chapters (the Download tab, not a Pipeline's Download step), panels (Panel-By-Panel) and upscaled images (Upscale). Open them in a comic reader app like Panels (iPhone and iPad) or Mihon (Android)."
                ),
                self.cbz_dropdown,
            ],
        )
        # Filled in the first time this page is opened (see "show_device").
        self.device_text = ft.Text(
            "Checking...", color=Nord.TEXT_BRIGHT, selectable=True
        )
        self.device_check_started = False
        device_section = get_section(
            "GPU",
            [
                get_help_text(
                    'The AI models (Magi, and the "Best" upscaler) run on your computer\'s GPU when they can, which is much faster than the CPU. With more than one GPU, Panelyze uses the most powerful one they can run on.'
                ),
                self.device_text,
                ft.Text(
                    '"Fast" and "Better" upscales use waifu2x, which picks a GPU itself.',
                    size=12,
                    color=Nord.TEXT_MUTED,
                ),
            ],
        )
        log_file_section = get_section(
            "Log file",
            [
                get_help_text(
                    "Everything shown in Activity's Log is also saved to a log file. The current log has everything since you opened Panelyze. The logs folder also keeps the last 9 times you used it (panelyze.1.log is the last time), e.g. to see why the app crashed."
                ),
                ft.Row(
                    wrap=True,
                    controls=[
                        ft.ElevatedButton(
                            style=Nord.button_style("secondary"),
                            text="Open Current Log",
                            icon=ft.Icons.DESCRIPTION,
                            on_click=lambda e: self.open_log_file(),
                        ),
                        ft.ElevatedButton(
                            style=Nord.button_style("secondary"),
                            text="Open Logs Folder",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda e: self.open_log_file(LOG_FOLDER),
                        ),
                        self.storage_section.log_size_text,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Reporting is a separate step (doing something with a log), so it gets some space above it.
                ft.Container(
                    padding=ft.padding.only(top=12),
                    content=get_help_text(
                        "Something went wrong? Report it on Panelyze's GitHub: say what you did and what happened, and attach a log. Reports are public, so check the log first for anything you don't want others to see (it has your folder paths and chapter links)."
                    ),
                ),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            style=Nord.button_style("secondary"),
                            text="Report a Problem",
                            icon=ft.Icons.BUG_REPORT,
                            # Opens the page in the browser.
                            url=ISSUES_URL,
                        ),
                    ]
                ),
            ],
        )
        about_section = get_section(
            "About",
            [
                ft.Text(
                    f"Panelyze {APP_VERSION}",
                    weight=ft.FontWeight.BOLD,
                    color=Nord.TEXT_BRIGHT,
                ),
                get_help_text(
                    "Panelyze turns manga and comic pages into one image per panel, in reading order, so you can read them one at a time on a phone or tablet instead of zooming around a whole page. It finds the panels with an AI model (Magi) that runs on your own computer (it's downloaded the first time)."
                ),
                get_help_text(
                    "It can also download chapters (MangaDex, comix.to, the Internet Archive or any web page), upscale images, and make videos from the panels, with a voice reading the text if you like. The Pipeline runs these steps in a row."
                ),
                get_help_text(
                    "Panelyze is free and open source. The code, new versions and what's being worked on are on GitHub."
                ),
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            style=Nord.button_style("secondary"),
                            text="View on GitHub",
                            icon=ft.Icons.OPEN_IN_NEW,
                            # Opens the page in the browser.
                            url=REPO_URL,
                        ),
                    ]
                ),
            ],
        )
        # Shown for a few seconds after a reset: next to the button, or above it in a narrow window (where next to it doesn't fit, and under it is out of view, since Reset is the last part of the page).
        self.reset_message_beside = ft.Text(
            RESET_MESSAGE, color=Nord.GREEN, visible=False
        )
        self.reset_message_above = ft.Text(
            RESET_MESSAGE, color=Nord.GREEN, visible=False
        )
        self.hide_reset_message_timer = None
        reset_section = get_section(
            "Reset",
            [
                get_help_text(
                    "Set every setting in every tab back to its default value. Your Azure key and region are kept."
                ),
                self.reset_message_above,
                ft.Row(
                    # Only if the window is made narrow while the message is shown: it moves under the button instead of being cut off.
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.ElevatedButton(
                            style=Nord.button_style("danger"),
                            text="Reset All Settings",
                            icon=ft.Icons.RESTART_ALT,
                            on_click=lambda e: (
                                self.parent_gui.reset_settings_to_default()
                            ),
                        ),
                        self.reset_message_beside,
                    ],
                ),
            ],
        )

        self.content = ft.Column(
            controls=[
                ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
                start_tab_section,
                folder_section,
                storage_section,
                comic_file_section,
                device_section,
                log_file_section,
                about_section,
                # Last, since it can't be undone.
                reset_section,
            ],
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        # The scrollbar is always shown, so it's clear there's more below when the window is short. It's drawn over the right edge of what scrolls, so the settings leave room for it on the right.
        self.content = ft.Column(
            controls=[
                ft.Container(content=self.content, padding=ft.padding.only(right=20))
            ],
            scroll=ft.ScrollMode.ALWAYS,
        )

    def show_reset_settings(self):
        """
        After "Reset All Settings": shows this page's settings as they are now (the other tabs are made again instead, but this page is kept so it doesn't scroll back to the top), then the message next to the button (above it in a narrow window) for a few seconds.
        """
        storage = self.parent_gui.page.client_storage
        self.start_tab_dropdown.value = self.parent_gui.get_start_tab()
        self.cbz_dropdown.value = storage.get("save_as_cbz") or "no"
        self.cbz_dropdown.helper_text = CBZ_DESCRIPTIONS.get(
            self.cbz_dropdown.value, ""
        )
        self.panelyze_folder_text.value = (
            default_settings.DEV_OUTPUT_FOLDER or storage.get("panelyze_folder")
        )

        # Narrow is the same width at which the other tabs move their settings under the preview (wide enough for the message next to the button).
        is_narrow = self.parent_gui.is_narrow
        self.reset_message_above.visible = is_narrow
        self.reset_message_beside.visible = not is_narrow
        # Clicking again starts the few seconds over.
        if self.hide_reset_message_timer:
            self.hide_reset_message_timer.cancel()
        self.hide_reset_message_timer = threading.Timer(
            RESET_MESSAGE_SECONDS, self.hide_reset_message
        )
        self.hide_reset_message_timer.daemon = True
        self.hide_reset_message_timer.start()

    def show_device(self):
        """
        Finds where the AI models run, the first time this page is opened (so when Panelyze starts only if Settings is the start tab). It loads PyTorch and tries each GPU (a few seconds), so it's done in the background. Trying a GPU takes some of its memory until Panelyze closes, as a job using the AI models would.
        """
        if self.device_check_started:
            return
        self.device_check_started = True
        threading.Thread(target=self.check_device, daemon=True).start()

    def check_device(self):
        try:
            sentence, device_names = get_device_sentence()
            self.device_text.value = None
            self.device_text.spans = Nord.get_highlighted_spans(
                sentence, device_names, Nord.DEVICE
            )
        except Exception as error:
            self.device_text.value = f"Couldn't check the GPU ({error})."
        if self.device_text.page:
            self.device_text.update()

    def hide_reset_message(self):
        for message in [self.reset_message_above, self.reset_message_beside]:
            message.visible = False
            if message.page:
                message.update()

    def pick_panelyze_folder_result(self, e):
        # The user cancelled the dialog.
        if not e.path:
            return

        self.parent_gui.change_panelyze_folder(get_panelyze_folder_inside(e.path))

    def open_log_file(self, path=None):
        # The log file, or the folder with every kept log in it.
        path = path or LOG_FILE_PATH
        if not os.path.exists(path):
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                f"ERROR: There's no log file yet ({path})."
            )
            return

        open_directory(path)
