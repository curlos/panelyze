import flet as ft
from classes.SettingsBase import SettingsBase


class SettingsUpscaleImages(ft.NavigationDrawer, SettingsBase):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.bgcolor = "#3b4252"
        self.position = ft.NavigationDrawerPosition.END

        if not self.page.client_storage.get("upscale_ratio"):
            self.page.client_storage.set("upscale_ratio", 2)

        self.upscale_ratios = [1, 2, 4, 8, 16, 32]
        self.default_upscale_ratio = self.page.client_storage.get("upscale_ratio")

        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Text(
                                        "Settings - Upscale Images",
                                        size=14,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                ],
                            ),
                            expand=True,
                            padding=ft.padding.only(bottom=5),
                        ),
                        ft.Dropdown(
                            label="Upscale Ratio",
                            options=[
                                ft.dropdown.Option(upscale_ratio)
                                for upscale_ratio in self.upscale_ratios
                            ],
                            value=self.default_upscale_ratio,
                            text_style=ft.TextStyle(
                                color="white",  # Text color of the selected item
                                size=14,  # Font size
                            ),
                            fill_color="#3b4252",  # Background color of the dropdown
                            border_color="#5e81ac",
                            max_menu_height=300,
                            on_change=lambda e: self.change_setting(
                                "upscale_ratio", e.data
                            ),
                        ),
                    ],
                    expand=True,
                ),
                padding=15,
                expand=True,
            )
        ]
