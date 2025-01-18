import flet as ft
from classes.SettingsBase import SettingsBase


class SettingsUpscaleImages(SettingsBase):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.upscale_ratios = [1, 2, 4, 8, 16, 32]
        self.default_upscale_ratio = self.page.client_storage.get("upscale_ratio")

        self.noise_levels = [-1, 0, 1, 2, 3]
        self.default_noise_level = self.page.client_storage.get("noise_level")

        self.image_formats = ["jpg", "png", "webp"]
        self.default_image_format = self.page.client_storage.get("image_format")

        self.custom_panel_image_height_textfield = self.get_number_textfield(
            "Image Height (px)", "custom_panel_image_height"
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

        self.inner_content = [
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
                on_change=lambda e: self.change_setting("upscale_ratio", e.data),
            ),
            ft.Dropdown(
                label="Noise Level",
                options=[
                    ft.dropdown.Option(noise_level) for noise_level in self.noise_levels
                ],
                value=self.default_noise_level,
                text_style=ft.TextStyle(
                    color="white",  # Text color of the selected item
                    size=14,  # Font size
                ),
                fill_color="#3b4252",  # Background color of the dropdown
                border_color="#5e81ac",
                max_menu_height=300,
                on_change=lambda e: self.change_setting("noise_level", e.data),
            ),
            ft.Dropdown(
                label="Image Format",
                options=[
                    ft.dropdown.Option(image_format)
                    for image_format in self.image_formats
                ],
                value=self.default_image_format,
                text_style=ft.TextStyle(
                    color="white",  # Text color of the selected item
                    size=14,  # Font size
                ),
                fill_color="#3b4252",  # Background color of the dropdown
                border_color="#5e81ac",
                max_menu_height=300,
                on_change=lambda e: self.change_setting("image_format", e.data),
            ),
            ft.Checkbox(
                label="Use Custom Panel Image Height",
                value=self.page.client_storage.get("use_custom_panel_image_height"),
                on_change=lambda e: self.toggle_setting_element_visibility(
                    e,
                    self.custom_panel_image_height_col,
                    "use_custom_panel_image_height",
                ),
            ),
            self.custom_panel_image_height_col,
        ]

        self.content = self.get_full_content()
