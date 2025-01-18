import flet as ft
from classes.SettingsBase import SettingsBase


class SettingsPanelByPanel(SettingsBase):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.custom_panel_image_height_textfield = self.get_number_textfield(
            "Panel Height (px)", "custom_panel_image_height"
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
