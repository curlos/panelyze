import flet as ft
from classes.SettingsBase import SettingsBase


class SettingsImagesToVideo(
    ft.NavigationDrawer,
    SettingsBase,
):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.bgcolor = "#3b4252"
        self.position = ft.NavigationDrawerPosition.END

        self.video_height_textfield = self.get_number_textfield(
            "Video Height (px)", "video_height"
        )

        self.image_displayed_duration_textfield = self.get_number_textfield(
            "Image Displayed Duration (seconds)", "image_displayed_duration"
        )

        self.page_num_textfield_dict = {
            "video_height": self.video_height_textfield,
            "image_displayed_duration": self.image_displayed_duration_textfield,
        }

        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Text(
                                        "Settings - Images To Video",
                                        size=14,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                ],
                            ),
                            expand=True,
                            padding=ft.padding.only(bottom=5),
                        ),
                        self.video_height_textfield,
                        self.image_displayed_duration_textfield,
                    ],
                    expand=True,
                ),
                padding=15,
                expand=True,
            )
        ]
