import flet as ft
from classes.SettingsBase import SettingsBase


class SettingsPanelByPanel(ft.NavigationDrawer, SettingsBase):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.bgcolor = "#3b4252"
        self.position = ft.NavigationDrawerPosition.END

        self.custom_panel_image_height_textfield = self.get_number_textfield(
            "Panel Height", "custom_panel_image_height"
        )
        self.custom_panel_image_height_col = ft.Column(
            controls=[
                self.custom_panel_image_height_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_custom_panel_image_height")),
        )

        self.page_num_textfield_dict = {
            "custom_panel_image_height": self.custom_panel_image_height_textfield,
        }

        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Text(
                                        "Settings - Panel-by-Panel",
                                        size=14,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                ],
                            ),
                            expand=True,
                            padding=ft.padding.only(bottom=5),
                        ),
                        ft.Checkbox(
                            label="Use Custom Panel Image Height",
                            value=self.page.client_storage.get(
                                "use_custom_panel_image_height"
                            ),
                            on_change=self.test,
                        ),
                        self.custom_panel_image_height_col,
                    ],
                    expand=True,
                ),
                padding=15,
                expand=True,
            )
        ]

    def test(self):
        print("e")
