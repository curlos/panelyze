import flet as ft


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

        def get_file_row(i):
            return ft.Container(
                content=ft.Row(
                    controls=[ft.Text(f"{i}.jpg"), ft.Text("1.2 MB")],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                bgcolor="#444c5e",
                padding=ft.padding.only(left=15, top=7, right=7, bottom=7),
            )

        expansion_panel = ft.ExpansionPanel(
            bgcolor="#444c5e",
            expanded=False,
            header=ft.Container(
                content=ft.Text(
                    "Dragon Ball (Official Colored)/Vol. 19 Ch. 220 - A Faint Light"
                ),
                padding=4,
                alignment=ft.alignment.center_left,
            ),
            can_tap_header=True,
            content=ft.Container(
                height=300,  # Specify a fixed height for the scrollable area
                content=ft.ListView(
                    controls=[
                        get_file_row(i)
                        for i in range(24)  # Dynamically create the rows
                    ],
                    auto_scroll=False,
                ),
            ),
        )

        files_directory_panel_list = ft.ExpansionPanelList(
            expand_icon_color=ft.Colors.AMBER,
            elevation=2,
            expanded_header_padding=0,
            divider_color=ft.Colors.AMBER,
            on_change=handle_change,
            controls=[expansion_panel, expansion_panel, expansion_panel],
            expand=True,
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
                                    files_directory_panel_list,
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

    def open_file_picker_dialog(self, e):
        self.pick_files_dialog.get_directory_path()

    def pick_files_result(self, e):
        # mangadex_url_to_download_from = self.mangadex_url_text_field.value
        output_directory = e.path

        print(output_directory)

        # self.download_button.visible = False
        # self.cancel_button.visible = True
        # self.download_button.update()
        # self.cancel_button.update()

        # try:
        #     download_from_mangadex(
        #         mangadex_url_to_download_from,
        #         output_directory,
        #         self.parent_gui.terminal_output.terminal_output_list_view,
        #         self.page.client_storage,
        #         self.cancel_button,
        #     )
        # finally:
        #     self.download_button.visible = True
        #     self.cancel_button.visible = False
        #     self.download_button.update()
        #     self.cancel_button.update()
