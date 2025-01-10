import flet as ft
import pdb
from utils import construct_directory_structure, get_last_directory, is_image_file
import os
from pprint import pprint


class MagiPanelByPanelView(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.bgcolor = "#3b4252"

        self.parent_gui = parent_gui
        self.page = self.parent_gui.page
        self.pick_files_dialog = ft.FilePicker(on_result=self.pick_files_result)
        self.page.overlay.append(self.pick_files_dialog)
        self.expand = True

        self.pick_directory_container = ft.Container(
            content=ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.UPLOAD,
                            color="white",
                        ),
                        ft.Text("Pick Directory", color="white", size=14),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                bgcolor="#3b4252",
                border=ft.border.all(1, "#5e81ac"),
                border_radius=ft.border_radius.all(10),
                alignment=ft.alignment.center,
            ),
            bgcolor="#444c5e",
            on_click=self.open_file_picker_dialog,
            padding=5,
            border_radius=ft.border_radius.all(10),
            height=150,
            alignment=ft.alignment.center,
        )

        def handle_change(e: ft.ControlEvent):
            print(f"change on panel with index {e.data}")

        self.files_directory_panel_list = ft.ExpansionPanelList(
            expand_icon_color=ft.Colors.AMBER,
            elevation=2,
            expanded_header_padding=0,
            divider_color=ft.Colors.AMBER,
            on_change=handle_change,
            expand=True,
            controls=[
                # ft.ExpansionPanelList(
                #     expand_icon_color=ft.Colors.AMBER,
                #     elevation=2,
                #     expanded_header_padding=0,
                #     divider_color=ft.Colors.AMBER,
                #     on_change=handle_change,
                #     expand=True,
                #     controls=[
                #         self.get_expansion_panel(
                #             "Ch. 220 - A Faint Light", ["0.jpg", "1.jpg"]
                #         )
                #     ],
                # )
                self.get_expansion_panel("Ch. 220 - A Faint Light", ["0.jpg", "1.jpg"])
            ],
        )

        # terminal_output_list_view.controls.append(ft.Text(text, color=color))
        # terminal_output_list_view.update()  # Update the Flet UI

        self.files_list_container = ft.Container(
            content=ft.Container(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text("Files List", color="white", size=14),
                                    ft.IconButton(
                                        ft.Icons.CLOSE,
                                        icon_color="white",
                                        icon_size=16,
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

        self.content = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(controls=[self.pick_directory_container], expand=True),
                    ft.Column(controls=[self.files_list_container], expand=True),
                ],
                expand=True,
                spacing=5,
            ),
            margin=ft.margin.symmetric(horizontal=10),
        )

    def get_file_row(self, name, size):
        return ft.Container(
            content=ft.Row(
                controls=[ft.Text(name), ft.Text(size)],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor="#444c5e",
            padding=ft.padding.only(left=15, top=7, right=7, bottom=7),
        )

    def get_expansion_panel(self, directory_name, image_file_names):
        return ft.ExpansionPanel(
            bgcolor="#444c5e",
            expanded=False,
            header=ft.Container(
                content=ft.Text(directory_name),
                padding=4,
                alignment=ft.alignment.center_left,
            ),
            can_tap_header=True,
            content=ft.Container(
                content=ft.ListView(
                    controls=[
                        self.get_file_row(image_file_name, image_file_name)
                        for image_file_name in image_file_names  # Dynamically create the rows
                    ],
                    auto_scroll=False,
                ),
            ),
        )

    def open_file_picker_dialog(self, e):
        self.pick_files_dialog.get_directory_path()

    def pick_files_result(self, e):
        absolute_path = e.path
        relative_path = get_last_directory(e.path)

        directory_structure = construct_directory_structure(absolute_path)
        expansion_panels = self.build_expansion_panels(directory_structure)

        self.files_directory_panel_list.controls = expansion_panels
        self.files_directory_panel_list.update()

    def build_expansion_panels(self, structure):
        def create_panels(level):
            panels = []
            for key, value in level.items():
                if key == "__images__":
                    # Create a panel for images
                    image_controls = [ft.Text(img) for img in value]
                    panels.extend(image_controls)
                else:
                    # Create a nested panel for subdirectories
                    nested_panels = create_panels(value)
                    panels.append(
                        ft.ExpansionPanel(
                            header=ft.Text(key),
                            content=ft.Column(
                                nested_panels, scroll=ft.ScrollMode.ADAPTIVE
                            ),
                        )
                    )
            return panels

        return create_panels(structure)

    # def add_expansion_panels_for_directory(self, base_path, files_structure):
    #     # TODO: Recursively go through the files_structure object and add the elements to the UI and update the list.

    #     for key, val in files_structure.items():
    #         if key == "__images__":
    #             image_file_names = val

    #             expansion_panel = self.get_expansion_panel(base_path, image_file_names)
    #             self.files_directory_panel_list.controls.append(expansion_panel)
    #             self.files_directory_panel_list.update()
    #         else:
    #             expansion_panel = self.get_expansion_panel(key, [])
    #             self.files_directory_panel_list.controls.append(expansion_panel)
    #             self.files_directory_panel_list.update()

    #             self.add_expansion_panels_for_directory(key, val)
    #             print("Hello World")
