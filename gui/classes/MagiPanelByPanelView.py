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
            margin=10,
            padding=5,
            border_radius=ft.border_radius.all(10),
            height=150,
            alignment=ft.alignment.center,
        )

        self.content = ft.Row(
            controls=[
                ft.Column(controls=[self.pick_directory_container], expand=True),
                ft.Column(controls=[self.pick_directory_container], expand=True),
            ],
            expand=True,
        )

    def open_file_picker_dialog(self, e):
        self.pick_files_dialog.get_directory_path()

    def pick_files_result(self, e):
        # mangadex_url_to_download_from = self.mangadex_url_text_field.value
        output_directory = e.path

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
