import os
import threading
import shutil
import flet as ft
from gui_classes import Nord
from default_settings import can_pick_output_folders, get_output_directory
from utils import (
    COMIC_FILE_EXTENSIONS,
    IMAGE_EXTENSIONS,
    copy_picked_images_to_folder,
    extract_comic_files_to_folder,
    get_input_summary,
    get_last_directory,
    is_comic_file,
    reset_cancel_button,
    set_cancel_click,
)
from gui_classes.ResponsiveColumns import ResponsiveColumns


# Shown under the input buttons, so it's clear what a comic file is.
COMIC_FILES_HELP_TEXT = "Comic files: .cbz, .cbr, .zip, .epub or .pdf. Each file becomes a chapter."
NO_OUTPUT_FOLDER_TEXT = "No output folder picked"
# The Clear and main buttons don't stretch with the window. Two of them still fit side by side on a phone-size window.
ACTION_BUTTON_WIDTH = 170


def save_input_to_temporary_folder(comic_paths=(), image_paths=()):
    """
    The pages of picked comic files, or picked images, saved into a new temporary folder so they're processed exactly like a picked folder. Returns None when there's none of them (a folder was picked). Delete the returned folder's parent when done. (Links are downloaded in the Download tab instead.)
    """
    if comic_paths:
        print(f"Opening {len(comic_paths)} comic file(s)")
        return extract_comic_files_to_folder(comic_paths)
    if image_paths:
        return copy_picked_images_to_folder(image_paths)
    return None


class PickInputAndOutputDirectories(ft.Container):
    def __init__(
        self, on_submit, parent_gui, settings_container, output_setting_key=None, submit_text="Submit"
    ):
        super().__init__()

        self.input_directory = ""
        # Set when individual images were picked instead of a folder.
        self.input_image_paths = []
        # Set when comic files (.cbz, .pdf, ...) were picked instead of a folder.
        self.input_comic_paths = []
        # True when the input folder was filled in by the app (the result of the step before) instead of picked by the user.
        self.input_was_filled_in_by_app = False
        # The output folder is saved under this setting, and starts as its default folder. Without one, the user has to pick it.
        self.output_setting_key = output_setting_key
        self.on_submit = on_submit
        # Something the tab adds to the line under a picked folder (e.g. "2 already split (kept)"), or "" (see "refresh_input_summary").
        self.get_extra_input_summary = lambda input_directory, output_directory: ""

        self.parent_gui = parent_gui
        self.page = self.parent_gui.page
        self.output_directory = (
            get_output_directory(self.page.client_storage, output_setting_key)
            if output_setting_key
            else ""
        )
        self.pick_input_files_dialog = ft.FilePicker(
            on_result=self.pick_input_files_result
        )
        self.pick_output_files_dialog = ft.FilePicker(
            on_result=self.pick_output_files_result
        )
        self.pick_input_images_dialog = ft.FilePicker(
            on_result=self.pick_input_images_result
        )
        self.pick_input_comic_files_dialog = ft.FilePicker(
            on_result=self.pick_input_comic_files_result
        )
        self.page.overlay.append(self.pick_input_files_dialog)
        self.page.overlay.append(self.pick_input_comic_files_dialog)
        self.page.overlay.append(self.pick_input_images_dialog)
        self.page.overlay.append(self.pick_output_files_dialog)

        # The input can be a whole folder (with sub-folders), one or more images, or comic files. Everything is only as big as what's in it, with Submit right under it, so there's no big empty boxes.
        self.pick_input_directory_column = self.get_card(
            ft.Column(
                controls=[
                    # The buttons go onto more lines when the window is too narrow for them.
                    ft.Row(
                        controls=[
                            ft.TextButton(
                                text="Pick Input Folder",
                                icon=ft.Icons.FOLDER_OPEN,
                                style=ft.ButtonStyle(color=Nord.TEXT, shape=Nord.SQUARE, side=Nord.get_focus_border()),
                                on_click=self.open_input_files_picker_dialog,
                            ),
                            ft.Text("or", color=Nord.TEXT, size=14),
                            ft.TextButton(
                                text="Pick Input Image(s)",
                                icon=ft.Icons.IMAGE,
                                style=ft.ButtonStyle(color=Nord.TEXT, shape=Nord.SQUARE, side=Nord.get_focus_border()),
                                on_click=lambda e: self.pick_input_images_dialog.pick_files(
                                    allow_multiple=True,
                                    file_type=ft.FilePickerFileType.CUSTOM,
                                    allowed_extensions=[extension.lstrip(".") for extension in IMAGE_EXTENSIONS],
                                ),
                            ),
                            ft.TextButton(
                                text="Pick Comic File(s)",
                                icon=ft.Icons.MENU_BOOK,
                                style=ft.ButtonStyle(color=Nord.TEXT, shape=Nord.SQUARE, side=Nord.get_focus_border()),
                                on_click=lambda e: self.pick_input_comic_files_dialog.pick_files(
                                    allow_multiple=True,
                                    file_type=ft.FilePickerFileType.CUSTOM,
                                    allowed_extensions=[extension.lstrip(".") for extension in COMIC_FILE_EXTENSIONS],
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        wrap=True,
                    ),
                    ft.Text(COMIC_FILES_HELP_TEXT, color=Nord.TEXT_MUTED, size=12, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

        # What was picked, with a line under it saying what was found in it (see "get_input_summary").
        self.input_directory_row_text = ft.Text(
            self.input_directory, color=Nord.TEXT, size=14
        )
        self.input_summary_text = ft.Text("", color=Nord.TEXT_MUTED, size=12)
        self.selected_input_directory_row = self.get_card(
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FILE_OPEN, color=Nord.TEXT),
                    ft.Column(
                        controls=[self.input_directory_row_text, self.input_summary_text],
                        spacing=2,
                        expand=True,
                    ),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        icon_color=Nord.TEXT,
                        style=Nord.icon_button_style(),
                        tooltip=Nord.tooltip("Clear the input"),
                        on_click=self.handle_clear_input_directory,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )
        self.selected_input_directory_row.visible = False

        # Like the Download tab: one line with where the results are saved.
        self.output_directory_row_text = ft.Text(
            self.output_directory or NO_OUTPUT_FOLDER_TEXT,
            color=Nord.PATH if self.output_directory else Nord.TEXT,
            size=14,
            expand=True,
        )
        self.selected_output_directory_row = ft.Row(
            controls=[
                ft.Text("Save to:", color=Nord.TEXT),
                self.output_directory_row_text,
                ft.Row(
                    controls=[
                        ft.IconButton(
                            ft.Icons.FOLDER_OPEN,
                            icon_color=Nord.TEXT,
                            style=Nord.icon_button_style(),
                            tooltip=Nord.tooltip("Pick a different output folder"),
                            on_click=self.open_output_files_picker_dialog,
                        ),
                        ft.IconButton(
                            ft.Icons.RESTART_ALT,
                            icon_color=Nord.TEXT,
                            style=Nord.icon_button_style(),
                            tooltip=Nord.tooltip("Use the default output folder"),
                            on_click=self.handle_clear_output_directory,
                        ),
                    ],
                    spacing=0,
                    # Running from source, everything goes to the repo's own folder (see "can_pick_output_folders").
                    visible=can_pick_output_folders(),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.settings_container = settings_container
        self.submit_button = ft.FilledTonalButton(
            style=Nord.button_style("primary"),
            text=submit_text,
            width=ACTION_BUTTON_WIDTH,
            on_click=self.handle_submit,
        )

        # Shown instead of Clear while a job runs (see "handle_submit"). The job checks "cancel_event" as it goes, and "on_cancel" (set by the tab) can stop what's running right away.
        self.cancel_event = threading.Event()
        self.on_cancel = None
        # What the Status view says as soon as Cancel is clicked (e.g. "Cancelling after the chapter being split into panels...").
        self.get_cancel_message = lambda: "Cancelling..."
        self.cancel_button = ft.FilledTonalButton(
            style=Nord.button_style("danger"),
            text="Cancel",
            width=ACTION_BUTTON_WIDTH,
            visible=False,
        )
        set_cancel_click(self.cancel_button, self.handle_cancel, lambda: self.get_cancel_message())

        self.clear_button = ft.FilledTonalButton(
            style=Nord.button_style("secondary"),
            text="Clear",
            width=ACTION_BUTTON_WIDTH,
            on_click=self.handle_clear_all_directories,
        )

        self.responsive_columns = ResponsiveColumns(
            main=ft.Column(
                controls=[
                    self.pick_input_directory_column,
                    self.selected_input_directory_row,
                    self.selected_output_directory_row,
                    ft.Row(controls=[self.clear_button, self.cancel_button, self.submit_button]),
                ],
                spacing=14,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                # On a narrow window, what doesn't fit can be scrolled to.
                scroll=ft.ScrollMode.AUTO,
            ),
            settings=self.settings_container,
            # The main part is only as tall as what's in it, and the settings get the rest when stacked.
            main_fills_height=False,
        )
        self.content = self.responsive_columns


    def set_locked(self, locked):
        """
        While a job runs, nothing here can be changed: the input, the output folder, the settings and the buttons. What's on screen then says what the job is working on.
        """
        for control in (
            self.pick_input_directory_column,
            self.selected_input_directory_row,
            self.selected_output_directory_row,
            self.clear_button,
            self.settings_container,
            self.submit_button,
        ):
            control.disabled = locked
        # The button styles don't change for a disabled button, so it's faded like the other tabs.
        self.submit_button.opacity = 0.5 if locked else 1

        # This tab might not be on screen (a Pipeline runs this tab's job from its own tab).
        try:
            self.update()
        except Exception:
            pass

    def open_input_files_picker_dialog(self, e):
        self.pick_input_files_dialog.get_directory_path()

    def open_output_files_picker_dialog(self, e):
        self.pick_output_files_dialog.get_directory_path()

    def handle_cancel(self):
        self.cancel_event.set()
        if self.on_cancel:
            self.on_cancel()

    def handle_submit(self, e):
        # Flet runs click handlers in separate threads, so without this a double-click would start two runs that write the same files at the same time.
        if self.submit_button.disabled:
            return

        # Only one job (Magi, upscaling, video, download) can run at a time. Two jobs at once would fight over the GUI terminal output.
        if not self.parent_gui.try_to_start_job(self.submit_button.text):
            return
        self.cancel_event.clear()
        self.set_locked(True)
        self.submit_button.update()
        # Cancel takes Clear's place while the job runs (nothing can be cleared then, and three buttons don't fit side by side).
        self.clear_button.visible = False
        self.cancel_button.visible = True
        # In case a click came just after the last job ended.
        reset_cancel_button(self.cancel_button)
        self.clear_button.update()
        self.cancel_button.update()

        # What was picked when the main button was clicked.
        input_directory = self.input_directory
        input_comic_paths = list(self.input_comic_paths)
        input_image_paths = list(self.input_image_paths)
        output_directory = self.output_directory
        temporary_input_folder = None

        try:
            if not output_directory and input_comic_paths:
                # Checked before the comic files are opened.
                self.parent_gui.terminal_output.update_terminal_with_error_message(
                    "ERROR: Please enter a valid output directory."
                )
                return

            temporary_input_folder = save_input_to_temporary_folder(input_comic_paths, input_image_paths)
            if temporary_input_folder:
                input_directory = temporary_input_folder

            self.on_submit(input_directory, output_directory)
        except Exception as error:
            # e.g. a comic file that couldn't be opened.
            self.parent_gui.terminal_output.update_terminal_with_error_message(f"ERROR: {error}")
        finally:
            # Only ever delete the temporary folder made just above.
            if temporary_input_folder:
                shutil.rmtree(os.path.dirname(temporary_input_folder), ignore_errors=True)

            self.parent_gui.set_job_running(False)
            # So a Pipeline that runs this tab's job later doesn't find a Cancel left over.
            self.cancel_event.clear()
            self.set_locked(False)
            # What's already done has changed (e.g. "already split, nothing new to split").
            self.refresh_input_summary()

            # When a Pipeline ran this tab's job, this button isn't on the page and can't be updated. It shows as enabled when the tab is opened.
            self.cancel_button.visible = False
            reset_cancel_button(self.cancel_button)
            self.clear_button.visible = True
            if self.submit_button.page:
                self.submit_button.update()
                self.cancel_button.update()
                self.clear_button.update()

    def pick_input_files_result(self, e):
        # The user cancelled the dialog.
        if not e.path:
            return

        self.set_input_directory(e.path)

    def set_input_directory(self, input_directory, filled_in_by_app=False):
        self.clear_input()
        self.input_directory = input_directory
        self.input_was_filled_in_by_app = filled_in_by_app

        self.pick_input_directory_column.visible = False
        self.selected_input_directory_row.visible = True
        self.input_directory_row_text.value = get_last_directory(self.input_directory)
        self.refresh_input_summary(update=False)

        # This tab might not be on screen right now (the step before it can fill this in from another tab). It shows the new folder the next time it's opened.
        for control in (
            self.pick_input_directory_column,
            self.selected_input_directory_row,
            self.input_directory_row_text,
            self.input_summary_text,
        ):
            try:
                control.update()
            except Exception:
                pass

    def refresh_input_summary(self, update=True):
        """
        The line under a picked folder: what's in it, and what the tab adds (e.g. which chapters are already done).
        """
        if not self.input_directory or self.input_image_paths or self.input_comic_paths:
            return
        summary = get_input_summary(self.input_directory)
        extra = self.get_extra_input_summary(self.input_directory, self.output_directory)
        self.input_summary_text.value = f"{summary} · {extra}" if extra else summary
        if update:
            # This tab might not be on screen.
            try:
                self.input_summary_text.update()
            except Exception:
                pass

    def pick_input_images_result(self, e):
        # The user cancelled the dialog.
        if not e.files:
            return

        self.clear_input()
        self.input_image_paths = [file.path for file in e.files]
        # Shown in the app and checked against the output directory. The images themselves are copied to a temporary folder when Submit is clicked.
        self.input_directory = os.path.dirname(self.input_image_paths[0])

        if len(self.input_image_paths) == 1:
            label = os.path.basename(self.input_image_paths[0])
        else:
            label = f"{len(self.input_image_paths)} images from {get_last_directory(self.input_directory)}"

        self.show_input(label, get_input_summary(image_paths=self.input_image_paths))

    def pick_input_comic_files_result(self, e):
        # The user cancelled the dialog.
        if not e.files:
            return

        # The Mac file picker can let other files through, so check again.
        comic_paths = [file.path for file in e.files if is_comic_file(file.path)]
        if not comic_paths:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                f"ERROR: Please pick comic files ({', '.join(COMIC_FILE_EXTENSIONS)})."
            )
            return

        self.clear_input()
        self.input_comic_paths = comic_paths
        # The pages are saved to a temporary folder when the main button is clicked.
        self.input_directory = os.path.dirname(comic_paths[0])

        if len(comic_paths) == 1:
            label = os.path.basename(comic_paths[0])
        else:
            label = f"{len(comic_paths)} comic files from {get_last_directory(self.input_directory)}"

        self.show_input(label, get_input_summary(comic_paths=comic_paths))

    def clear_input(self):
        # Only one input is used at a time, so picking one clears the others.
        self.input_directory = ""
        self.input_image_paths = []
        self.input_comic_paths = []
        self.input_was_filled_in_by_app = False

    def show_input(self, label, summary=""):
        self.pick_input_directory_column.visible = False
        self.selected_input_directory_row.visible = True
        self.input_directory_row_text.value = label
        self.input_summary_text.value = summary

        self.pick_input_directory_column.update()
        self.selected_input_directory_row.update()
        self.input_directory_row_text.update()
        self.input_summary_text.update()

    def pick_output_files_result(self, e):
        # The user cancelled the dialog.
        if not e.path:
            return

        self.set_output_directory(e.path)

    def set_output_directory(self, output_directory):
        if self.output_setting_key:
            self.page.client_storage.set(self.output_setting_key, output_directory)

        self.show_output_directory(output_directory)

    def show_output_directory(self, output_directory):
        self.output_directory = output_directory
        self.output_directory_row_text.value = self.output_directory or NO_OUTPUT_FOLDER_TEXT
        self.output_directory_row_text.color = Nord.PATH if self.output_directory else Nord.TEXT
        self.output_directory_row_text.update()
        # What's already done can be different in another output folder.
        self.refresh_input_summary()

    def handle_clear_input_directory(self, e):
        self.clear_input()

        self.selected_input_directory_row.visible = False
        self.pick_input_directory_column.visible = True

        self.selected_input_directory_row.update()
        self.pick_input_directory_column.update()

    def handle_clear_output_directory(self, e):
        # With a default output folder, clearing goes back to it.
        if self.output_setting_key:
            self.page.client_storage.set(self.output_setting_key, "")
            self.show_output_directory(
                get_output_directory(self.page.client_storage, self.output_setting_key)
            )
            return

        self.show_output_directory("")

    def handle_clear_all_directories(self, e):
        self.handle_clear_input_directory(e)
        self.handle_clear_output_directory(e)

    def get_card(self, content):
        # A box that's only as big as what's in it.
        return ft.Container(
            content=content,
            bgcolor=Nord.SURFACE,
            border=ft.border.all(1, Nord.BLUE),
            padding=10,
        )
