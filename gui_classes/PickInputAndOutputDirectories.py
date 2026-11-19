import os
import shutil
import flet as ft
from utils import (
    IMAGE_EXTENSIONS,
    copy_picked_images_to_folder,
    get_last_directory,
)


class PickInputAndOutputDirectories(ft.Container):
    def __init__(self, on_submit, parent_gui, settings_container):
        super().__init__()

        self.input_directory = ""
        # Set when individual images were picked instead of a folder.
        self.input_image_paths = []
        self.output_directory = ""
        self.on_submit = on_submit

        self.parent_gui = parent_gui
        self.page = self.parent_gui.page
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
                    style=ft.ButtonStyle(color="white"),
                    on_click=self.open_input_files_picker_dialog,
                ),
                ft.Text("or", color="white", size=14),
                ft.TextButton(
                    text="Pick Input Image(s)",
                    icon=ft.Icons.IMAGE,
                    style=ft.ButtonStyle(color="white"),
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
                    color="white",
                ),
                ft.Text(
                    "Pick Output Directory",
                    color="white",
                    size=14,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True,
        )

        self.output_directory_row_text = ft.Text(
            self.output_directory,
            color="white",
            size=14,
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
                                                color="white",
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
                                            ft.IconButton(
                                                ft.Icons.CLOSE,
                                                icon_color="white",
                                                on_click=self.handle_clear_output_directory,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                ]
                            ),
                            alignment=ft.alignment.top_left,
                        ),
                        bgcolor="#3b4252",
                        border=ft.border.all(1, "#5e81ac"),
                        border_radius=ft.border_radius.all(10),
                        alignment=ft.alignment.center,
                        padding=10,
                    ),
                    bgcolor="#444c5e",
                    padding=5,
                    border_radius=ft.border_radius.all(10),
                    expand=True,
                    alignment=ft.alignment.top_left,
                )
            ],
            expand=True,
            visible=False,
        )

        self.pick_output_directory_column = self.get_pick_directory_container(
            [
                self.pick_output_directory_row,
            ],
            self.open_output_files_picker_dialog,
        )

        self.input_directory_row_text = ft.Text(
            self.input_directory,
            color="white",
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
                                                color="white",
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
                                                icon_color="white",
                                                on_click=self.handle_clear_input_directory,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                ]
                            ),
                            alignment=ft.alignment.top_left,
                        ),
                        bgcolor="#3b4252",
                        border=ft.border.all(1, "#5e81ac"),
                        border_radius=ft.border_radius.all(10),
                        alignment=ft.alignment.center,
                        padding=10,
                    ),
                    bgcolor="#444c5e",
                    padding=5,
                    border_radius=ft.border_radius.all(10),
                    expand=True,
                    alignment=ft.alignment.top_left,
                )
            ],
            expand=True,
            visible=False,
        )

        self.settings_container = settings_container
        self.submit_button = ft.FilledTonalButton(
            text="Submit",
            color="white",
            bgcolor="#5e81ac",
            expand=True,
            on_click=self.handle_submit,
        )

        self.content = ft.Row(
            controls=[
                ft.Column(
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
                                    text="Clear",
                                    color="white",
                                    bgcolor="#444c5e",
                                    expand=True,
                                    on_click=self.handle_clear_all_directories,
                                ),
                                self.submit_button,
                            ]
                        ),
                    ],
                    expand=True,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Column(controls=[self.settings_container]),
            ],
            expand=True,
            spacing=5,
        )

        self.margin = ft.margin.symmetric(horizontal=10)

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

        absolute_path = e.path
        self.input_directory = absolute_path
        self.input_image_paths = []

        self.pick_input_directory_column.visible = False
        self.selected_input_directory_row.visible = True
        self.input_directory_row_text.value = get_last_directory(self.input_directory)

        self.pick_input_directory_column.update()
        self.selected_input_directory_row.update()
        self.input_directory_row_text.update()

    def pick_input_images_result(self, e):
        # The user cancelled the dialog.
        if not e.files:
            return

        self.input_image_paths = [file.path for file in e.files]
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

        self.output_directory = e.path

        self.pick_output_directory_column.visible = False
        self.selected_output_directory_row.visible = True
        self.output_directory_row_text.value = get_last_directory(self.output_directory)

        self.pick_output_directory_column.update()
        self.selected_output_directory_row.update()
        self.output_directory_row_text.update()

    def handle_clear_input_directory(self, e):
        self.input_directory = ""
        self.input_image_paths = []

        self.selected_input_directory_row.visible = False
        self.pick_input_directory_column.visible = True

        self.selected_input_directory_row.update()
        self.pick_input_directory_column.update()

    def handle_clear_output_directory(self, e):
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
                content=ft.Row(
                    controls=controls,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                bgcolor="#3b4252",
                border=ft.border.all(1, "#5e81ac"),
                border_radius=ft.border_radius.all(10),
                alignment=ft.alignment.center,
                expand=True,
                padding=10,
            ),
            bgcolor="#444c5e",
            on_click=on_click,
            padding=5,
            border_radius=ft.border_radius.all(10),
            alignment=ft.alignment.center,
            expand=True,
        )
