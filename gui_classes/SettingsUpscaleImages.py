import flet as ft
from gui_classes.DropdownTextOptions import DropdownTextOptions
from gui_classes import Nord
from gui_classes.WrappingCheckbox import WrappingCheckbox
from gui_classes.SettingsBase import SettingsBase


# The upscalers to pick from, as (setting value, what's shown). Measured on a 97-panel chapter on an M1 MacBook.
UPSCALE_MODELS = {"fast": "Fast", "better": "Better", "best": "Best"}
UPSCALE_MODEL_DESCRIPTIONS = {
    "fast": "waifu2x, about 30 seconds a chapter",
    "better": "waifu2x cunet: cleaner gray shading, about 2x slower",
    "best": "MangaJaNai, or IllustrationJaNai for color. Best for manga, slower; downloads about 600 MB the first time.",
}


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

        self.max_image_width_textfield = self.get_number_textfield(
            "Max Image Width (px)", "max_image_width"
        )
        self.max_image_width_col = ft.Column(
            controls=[
                self.max_image_width_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_max_image_width")),
        )


        self.inner_content = [
            DropdownTextOptions(
                label="Upscale Model",
                options=[
                    ft.dropdown.Option(key=model, text=text)
                    for model, text in UPSCALE_MODELS.items()
                ],
                value=self.page.client_storage.get("upscale_model"),
                on_change=lambda e: self.change_setting("upscale_model", e.data),
                descriptions=UPSCALE_MODEL_DESCRIPTIONS,
            ),
            ft.Dropdown(
                border_radius=0,
                label="Upscale Ratio",
                options=[
                    ft.dropdown.Option(upscale_ratio)
                    for upscale_ratio in self.upscale_ratios
                ],
                value=self.default_upscale_ratio,
                text_style=ft.TextStyle(
                    color=Nord.TEXT,  # Text color of the selected item
                    size=14,  # Font size
                ),
                fill_color=Nord.SURFACE,  # Background color of the dropdown
                border_color=Nord.BLUE,
                max_menu_height=300,
                on_change=lambda e: self.change_setting("upscale_ratio", e.data),
            ),
            ft.Dropdown(
                border_radius=0,
                label="Noise Level",
                options=[
                    ft.dropdown.Option(noise_level) for noise_level in self.noise_levels
                ],
                value=self.default_noise_level,
                text_style=ft.TextStyle(
                    color=Nord.TEXT,  # Text color of the selected item
                    size=14,  # Font size
                ),
                fill_color=Nord.SURFACE,  # Background color of the dropdown
                border_color=Nord.BLUE,
                max_menu_height=300,
                on_change=lambda e: self.change_setting("noise_level", e.data),
            ),
            ft.Dropdown(
                border_radius=0,
                label="Image Format",
                options=[
                    ft.dropdown.Option(image_format)
                    for image_format in self.image_formats
                ],
                value=self.default_image_format,
                text_style=ft.TextStyle(
                    color=Nord.TEXT,  # Text color of the selected item
                    size=14,  # Font size
                ),
                fill_color=Nord.SURFACE,  # Background color of the dropdown
                border_color=Nord.BLUE,
                max_menu_height=300,
                on_change=lambda e: self.change_setting("image_format", e.data),
            ),
            # Upscaling an already big image (e.g. 8000px at 16x) would take forever for no visible gain.
            WrappingCheckbox(
                label="Don't upscale past 4K (3840px on the longest side)",
                value=self.page.client_storage.get("limit_upscale_to_4k"),
                on_change=lambda e: self.change_setting("limit_upscale_to_4k", e.data),
            ),
            WrappingCheckbox(
                label="Use Custom Image Height",
                value=self.page.client_storage.get("use_custom_panel_image_height"),
                on_change=lambda e: self.toggle_setting_element_visibility(
                    e,
                    self.custom_panel_image_height_col,
                    "use_custom_panel_image_height",
                ),
            ),
            self.custom_panel_image_height_col,
            # Big images like colorspreads can balloon to 100+ MB after a 4x upscale, so this caps how wide they can get.
            WrappingCheckbox(
                label="Use Max Image Width",
                value=self.page.client_storage.get("use_max_image_width"),
                on_change=lambda e: self.toggle_setting_element_visibility(
                    e,
                    self.max_image_width_col,
                    "use_max_image_width",
                ),
            ),
            self.max_image_width_col,
        ]

        self.content = self.get_full_content()
