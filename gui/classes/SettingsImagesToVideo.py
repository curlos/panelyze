import flet as ft
from classes.SettingsBase import SettingsBase


class SettingsImagesToVideo(
    SettingsBase,
):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.video_height_textfield = self.get_number_textfield(
            "Video Height (px)", "video_height"
        )

        self.image_displayed_duration_textfield = self.get_number_textfield(
            "Image Displayed Duration (seconds)", "image_displayed_duration"
        )

        self.reading_speed_wpm_textfield = self.get_number_textfield(
            "Reading Speed (WPM)", "reading_speed_wpm"
        )

        self.reading_speed_wpm_col = ft.Column(
            controls=[
                self.reading_speed_wpm_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_reading_speed_wpm")),
        )

        self.page_num_textfield_dict = {
            "video_height": self.video_height_textfield,
            "image_displayed_duration": self.image_displayed_duration_textfield,
            "reading_speed_wpm": self.reading_speed_wpm_textfield,
        }

        self.inner_content = [
            self.video_height_textfield,
            self.image_displayed_duration_textfield,
            ft.Checkbox(
                label="Use Reading Speed (WPM)",
                value=self.page.client_storage.get("use_reading_speed_wpm"),
                on_change=lambda e: self.toggle_setting_element_visibility(
                    e,
                    self.reading_speed_wpm_col,
                    "use_reading_speed_wpm",
                ),
            ),
            self.reading_speed_wpm_col,
        ]

        self.content = self.get_full_content()
