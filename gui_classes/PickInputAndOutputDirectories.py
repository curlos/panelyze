import os
import shutil
import flet as ft
from gui_classes import Nord
from default_settings import can_pick_output_folders, get_output_directory
from utils import (
    IMAGE_EXTENSIONS,
    copy_picked_images_to_folder,
    get_last_directory,
)
from gui_classes.ResponsiveColumns import ResponsiveColumns


class PickInputAndOutputDirectories(ft.Container):
    def __init__(
        self, on_submit, parent_gui, settings_container, output_setting_key=None
    ):
        super().__init__()

        self.input_directory = ""
        # Set when individual images were picked instead of a folder.
        self.input_image_paths = []
        # True when the input folder was filled in by the app (the result of the step before) instead of picked by the user.
        self.input_was_filled_in_by_app = False
        # The output folder is saved under this setting, and starts as its default folder. Without one, the user has to pick it.
        self.output_setting_key = output_setting_key
        self.on_submit = on_submit

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
        self.page.overlay.append(self.pick_input_files_dialog)
        self.page.overlay.append(self.pick_input_images_dialog)
        self.page.overlay.append(self.pick_output_files_dialog)

        # The input can be a whole folder (with sub-folders) or one or more images.
        self.pick_input_directory_column = self.get_pick_directory_container(
            [
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
            ],
            None,
        )

        self.pick_output_directory_row = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.UPLOAD,
                    color=Nord.TEXT,
                ),
                ft.Text(
                    "Pick Output Directory",
                    color=Nord.TEXT,
                    size=14,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )

        self.output_directory_row_text = ft.Text(
            self.output_directory,
            color=Nord.TEXT,
            size=14,
            expand=True,
        )

        self.selected_output_directory_row = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Container(
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(
                                                ft.Icons.FILE_OPEN,
                                                color=Nord.TEXT,
                                            ),
                                            ft.Text(
                                                "Output Directory",
                                                weight=ft.FontWeight.W_700,
                                            ),
                                        ]
                                    ),
                                    ft.Row(
                                        controls=[
                                            self.output_directory_row_text,
                                            ft.Row(
                                                controls=[
                                                    ft.IconButton(
                                                        ft.Icons.FOLDER_OPEN,
                                                        icon_color=Nord.TEXT,
                                                        style=Nord.icon_button_style(),
                                                        tooltip="Pick a different output folder",
                                                        on_click=self.open_output_files_picker_dialog,
                                                    ),
                                                    ft.IconButton(
                                                        ft.Icons.RESTART_ALT,
                                                        icon_color=Nord.TEXT,
                                                        style=Nord.icon_button_style(),
                                                        tooltip="Use the default output folder",
                                                        on_click=self.handle_clear_output_directory,
                                                    ),
                                                ],
                                                spacing=0,
                                                # Running from source, everything goes to the repo's own folder (see "can_pick_output_folders").
                                                visible=can_pick_output_folders(),
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                ]
                            ),
                            alignment=ft.alignment.top_left,
                        ),
                        bgcolor=Nord.SURFACE,
                        border=ft.border.all(1, Nord.BLUE),
                        alignment=ft.alignment.center,
                        padding=10,
                    ),
                    expand=True,
                    alignment=ft.alignment.top_left,
                )
            ],
            expand=True,
            visible=bool(self.output_directory),
        )

        self.pick_output_directory_column = self.get_pick_directory_container(
            [
                self.pick_output_directory_row,
            ],
            self.open_output_files_picker_dialog,
        )
        self.pick_output_directory_column.visible = not self.output_directory

        self.input_directory_row_text = ft.Text(
            self.input_directory,
            color=Nord.TEXT,
            size=14,
        )

        self.selected_input_directory_row = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Container(
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Icon(
                                                ft.Icons.FILE_OPEN,
                                                color=Nord.TEXT,
                                            ),
                                            ft.Text(
                                                "Input Directory",
                                                weight=ft.FontWeight.W_700,
                                            ),
                                        ]
                                    ),
                                    ft.Row(
                                        controls=[
                                            self.input_directory_row_text,
                                            ft.IconButton(
                                                ft.Icons.CLOSE,
                                                icon_color=Nord.TEXT,
                                                style=Nord.icon_button_style(),
                                                tooltip="Clear the input",
                                                on_click=self.handle_clear_input_directory,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                ]
                            ),
                            alignment=ft.alignment.top_left,
                        ),
                        bgcolor=Nord.SURFACE,
                        border=ft.border.all(1, Nord.BLUE),
                        alignment=ft.alignment.center,
                        padding=10,
                    ),
                    expand=True,
                    alignment=ft.alignment.top_left,
                )
            ],
            expand=True,
            visible=False,
        )

        self.settings_container = settings_container
        self.submit_button = ft.FilledTonalButton(
            style=Nord.button_style("primary"),
            text="Submit",
            expand=True,
            on_click=self.handle_submit,
        )

        self.responsive_columns = ResponsiveColumns(
            main=ft.Column(
                controls=[
                    ft.Column(
                        controls=[
                            self.pick_input_directory_column,
                            self.selected_input_directory_row,
                            self.pick_output_directory_column,
                            self.selected_output_directory_row,
                        ],
                        expand=True,
                    ),
                    ft.Row(
                        controls=[
                            ft.FilledTonalButton(
                                style=Nord.button_style("secondary"),
                                text="Clear",
                                expand=True,
                                on_click=self.handle_clear_all_directories,
                            ),
                            self.submit_button,
                        ]
                    ),
                ],
                spacing=10,
                alignment=ft.MainAxisAlignment.START,
            ),
            settings=self.settings_container,
        )
        self.content = self.responsive_columns


    def open_input_files_picker_dialog(self, e):
        self.pick_input_files_dialog.get_directory_path()

    def open_output_files_picker_dialog(self, e):
        self.pick_output_files_dialog.get_directory_path()

    def handle_submit(self, e):
        # Flet runs click handlers in separate threads, so without this a double-click would start two runs that write the same files at the same time.
        if self.submit_button.disabled:
            return

        # Only one job (Magi, upscaling, video, download) can run at a time. Two jobs at once would fight over the GUI terminal output.
        if self.parent_gui.is_job_running:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: Another job is still running. Please wait for it to finish."
            )
            return

        self.parent_gui.is_job_running = True
        self.submit_button.disabled = True
        self.submit_button.opacity = 0.5
        self.submit_button.update()

        # What was picked when Submit was clicked. (The pickers can still be used while the job runs, so these are read only once.)
        input_directory = self.input_directory
        input_image_paths = list(self.input_image_paths)
        output_directory = self.output_directory
        picked_images_folder = None

        try:
            # Picked images are copied into their own temporary folder, so they're processed exactly like a picked folder.
            if input_image_paths:
                picked_images_folder = copy_picked_images_to_folder(input_image_paths)
                input_directory = picked_images_folder

            self.on_submit(input_directory, output_directory)
        finally:
            # Only ever delete the temporary folder made just above.
            if picked_images_folder:
                shutil.rmtree(os.path.dirname(picked_images_folder), ignore_errors=True)

            self.parent_gui.is_job_running = False
            self.submit_button.disabled = False
            self.submit_button.opacity = 1

            # If the user switched to another tab while the job was running, this button isn't on the page right now and can't be updated. It'll still show as enabled when they switch back.
            if self.submit_button.page:
                self.submit_button.update()

    def pick_input_files_result(self, e):
        # The user cancelled the dialog.
        if not e.path:
            return

        self.set_input_directory(e.path)

    def set_input_directory(self, input_directory, filled_in_by_app=False):
        self.input_directory = input_directory
        self.input_image_paths = []
        self.input_was_filled_in_by_app = filled_in_by_app

        self.pick_input_directory_column.visible = False
        self.selected_input_directory_row.visible = True
        self.input_directory_row_text.value = get_last_directory(self.input_directory)

        # This tab might not be on screen right now (the step before it can fill this in from another tab). It shows the new folder the next time it's opened.
        for control in (
            self.pick_input_directory_column,
            self.selected_input_directory_row,
            self.input_directory_row_text,
        ):
            try:
                control.update()
            except Exception:
                pass

    def pick_input_images_result(self, e):
        # The user cancelled the dialog.
        if not e.files:
            return

        self.input_image_paths = [file.path for file in e.files]
        self.input_was_filled_in_by_app = False
        # Shown in the app and checked against the output directory. The images themselves are copied to a temporary folder when Submit is clicked.
        self.input_directory = os.path.dirname(self.input_image_paths[0])

        if len(self.input_image_paths) == 1:
            label = os.path.basename(self.input_image_paths[0])
        else:
            label = f"{len(self.input_image_paths)} images from {get_last_directory(self.input_directory)}"

        self.pick_input_directory_column.visible = False
        self.selected_input_directory_row.visible = True
        self.input_directory_row_text.value = label

        self.pick_input_directory_column.update()
        self.selected_input_directory_row.update()
        self.input_directory_row_text.update()

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

        self.pick_output_directory_column.visible = False
        self.selected_output_directory_row.visible = True
        self.output_directory_row_text.value = self.output_directory

        self.pick_output_directory_column.update()
        self.selected_output_directory_row.update()
        self.output_directory_row_text.update()

    def handle_clear_input_directory(self, e):
        self.input_directory = ""
        self.input_image_paths = []
        self.input_was_filled_in_by_app = False

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

        self.output_directory = ""

        self.pick_output_directory_column.visible = True
        self.selected_output_directory_row.visible = False
        self.output_directory_row_text.value = ""

        self.pick_output_directory_column.update()
        self.selected_output_directory_row.update()
        self.output_directory_row_text.update()

    def handle_clear_all_directories(self, e):
        self.handle_clear_input_directory(e)
        self.handle_clear_output_directory(e)

    def get_pick_directory_container(self, controls, on_click):
        return ft.Container(
            content=ft.Container(
                # The buttons go onto more lines when the window is too narrow for them.
                content=ft.Row(
                    controls=controls,
                    alignment=ft.MainAxisAlignment.CENTER,
                    wrap=True,
                ),
                bgcolor=Nord.SURFACE,
                border=ft.border.all(1, Nord.BLUE),
                alignment=ft.alignment.center,
                expand=True,
                padding=10,
            ),
            on_click=on_click,
            # Lets a clickable box be picked with the keyboard too (Tab to it, then Enter).
            ink=on_click is not None,
            alignment=ft.alignment.center,
            expand=True,
        )
