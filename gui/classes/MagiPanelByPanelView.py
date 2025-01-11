import flet as ft
import pdb
from utils import (
    construct_directory_structure,
    format_size,
    get_last_directory,
    open_directory,
    remove_last_directory,
)
import os
from pprint import pprint
from magi import Magi


class MagiPanelByPanelView(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.bgcolor = "#3b4252"

        self.parent_gui = parent_gui
        self.page = self.parent_gui.page
        self.pick_input_files_dialog = ft.FilePicker(
            on_result=self.pick_input_files_result
        )
        self.pick_output_files_dialog = ft.FilePicker(
            on_result=self.pick_output_files_result
        )
        self.page.overlay.append(self.pick_input_files_dialog)
        self.page.overlay.append(self.pick_output_files_dialog)
        self.expand = True

        self.input_directory = ""
        self.output_directory = ""
        self.magi = None

        self.pick_input_directory_column = self.get_pick_directory_container(
            [
                ft.Icon(
                    ft.Icons.UPLOAD,
                    color="white",
                ),
                ft.Text("Pick Input Directory", color="white", size=14),
            ],
            self.open_input_files_picker_dialog,
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

        self.selected_output_directory_row = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.FILE_OPEN,
                            color="white",
                        ),
                        ft.Text("Output Directory", weight=ft.FontWeight.W_700),
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
            ],
            alignment=ft.MainAxisAlignment.START,
            expand=True,
            visible=False,
            wrap=True,
        )

        self.pick_output_directory_column = self.get_pick_directory_container(
            [
                self.pick_output_directory_row,
                self.selected_output_directory_row,
            ],
            self.open_output_files_picker_dialog,
        )

        self.files_directory_panel_list = ft.Column(controls=[])

        self.files_list_column = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Container(
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row(
                                        controls=[
                                            ft.Text(
                                                "Files List",
                                                color="white",
                                                size=14,
                                                weight=ft.FontWeight.W_700,
                                            ),
                                            ft.IconButton(
                                                ft.Icons.CLOSE,
                                                icon_color="white",
                                                icon_size=16,
                                                on_click=self.handle_clear_input_directory,
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                    ft.ListView(
                                        controls=[
                                            self.files_directory_panel_list,
                                        ],
                                        expand=True,
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

        self.content = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    self.pick_input_directory_column,
                                    self.files_list_column,
                                    self.pick_output_directory_column,
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
                                    ft.FilledTonalButton(
                                        text="Submit",
                                        color="white",
                                        bgcolor="#5e81ac",
                                        expand=True,
                                        on_click=self.handle_convert_to_panel_by_panel,
                                    ),
                                ]
                            ),
                        ],
                        expand=True,
                        spacing=10,
                        alignment=ft.MainAxisAlignment.START,
                    ),
                ],
                expand=True,
                spacing=5,
            ),
            margin=ft.margin.symmetric(horizontal=10),
        )

    def open_input_files_picker_dialog(self, e):
        self.pick_input_files_dialog.get_directory_path()

    def open_output_files_picker_dialog(self, e):
        self.pick_output_files_dialog.get_directory_path()

    def pick_input_files_result(self, e):
        absolute_path = e.path
        self.input_directory = absolute_path

        self.files_directory_structure = construct_directory_structure(absolute_path)
        expansion_tiles = self.build_expansion_tiles(self.files_directory_structure)

        self.files_directory_panel_list.controls = expansion_tiles
        self.files_list_column.visible = True
        self.pick_input_directory_column.visible = False

        self.files_list_column.update()
        self.files_directory_panel_list.update()
        self.pick_input_directory_column.update()

    def pick_output_files_result(self, e):
        self.output_directory = e.path

        self.pick_output_directory_row.visible = False
        self.selected_output_directory_row.visible = True
        self.output_directory_row_text.value = get_last_directory(self.output_directory)

        self.pick_output_directory_row.update()
        self.selected_output_directory_row.update()
        self.output_directory_row_text.update()

    def build_expansion_tiles(self, structure):
        def create_tiles(level, i):
            tiles = []
            for key, value in level.items():
                if key == "__images__":
                    # Create ListTiles for images
                    tiles.extend(
                        [
                            ft.ListTile(
                                title=ft.Row(
                                    controls=[
                                        ft.Text(img["name"], size=14),
                                        ft.Text(format_size(img["size"]), size=14),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                dense=True,
                                content_padding=ft.padding.only(
                                    left=i * 10, top=0, right=10, bottom=0
                                ),
                                bgcolor="#444c5e",
                            )
                            for img in value
                        ]
                    )
                else:
                    # Recursively create nested tiles for directories
                    nested_tiles = create_tiles(value, i + 1)
                    tiles.append(
                        ft.ExpansionTile(
                            title=ft.Text(key),
                            maintain_state=True,
                            text_color="white",
                            controls=nested_tiles,  # Add children here
                            tile_padding=ft.padding.only(
                                left=i * 10, top=0, right=0, bottom=0
                            ),
                        )
                    )
            return tiles

        return create_tiles(structure, 1)

    def handle_clear_input_directory(self, e):
        self.input_directory = ""

        self.files_list_column.visible = False
        self.pick_input_directory_column.visible = True

        self.files_list_column.update()
        self.pick_input_directory_column.update()

    def handle_clear_output_directory(self, e):
        self.output_directory = ""

        self.pick_output_directory_row.visible = True
        self.selected_output_directory_row.visible = False
        self.output_directory_row_text.value = ""

        self.pick_output_directory_row.update()
        self.selected_output_directory_row.update()
        self.output_directory_row_text.update()

    def handle_clear_all_directories(self, e):
        self.handle_clear_input_directory(e)
        self.handle_clear_output_directory(e)

    def handle_convert_to_panel_by_panel(self, e):
        print(f"Input Directory: {self.input_directory}")
        print(f"Output Directory: {self.output_directory}")

        if not self.input_directory and not self.output_directory:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: Please enter valid input and output directories."
            )
            return
        elif not self.input_directory:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: Please enter a valid input directory."
            )
            return
        elif not self.output_directory:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: Please enter a valid output directory."
            )
            return

        # TODO: Bring back in a moment.
        if not self.magi:
            self.magi = Magi()

        self.process_images_in_structure(
            self.files_directory_structure, remove_last_directory(self.input_directory)
        )
        open_directory(self.output_directory)

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

    def process_images_in_structure(self, structure, base_path=""):
        def traverse_and_process(level, current_path):
            for key, value in level.items():
                if key == "__images__":
                    print("\n")
                    print(self.input_directory)
                    # Current path is a directory containing images
                    input_directory = os.path.join(base_path, current_path)
                    print(f"Processing: {input_directory} -> {self.output_directory}")
                    print("\n")

                    # Call the processing function
                    self.magi.get_panels_for_chapter(
                        input_directory, self.output_directory
                    )
                else:
                    # Traverse nested directories
                    next_path = os.path.join(current_path, key) if current_path else key
                    traverse_and_process(value, next_path)

        # Start the traversal from the root of the structure
        traverse_and_process(structure, base_path)
