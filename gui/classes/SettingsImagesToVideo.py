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
            "Image Displayed Duration (sec.)", "image_displayed_duration"
        )

        self.image_displayed_duration_col = ft.Column(
            controls=[
                self.image_displayed_duration_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_image_displayed_duration")),
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

        self.radio_use_reading_speed_wpm = ft.Radio(
            label="Use Reading Speed (WPM)",
            value="use_reading_speed_wpm",
        )

        self.radio_use_image_displayed_duration = ft.Radio(
            label="Use Image Displayed Duration (sec.)",
            value="use_image_displayed_duration",
        )

        self.radio_group_dict = {
            "use_reading_speed_wpm": {
                "elem": self.radio_use_reading_speed_wpm,
                "toggle_elem": self.reading_speed_wpm_col,
                "setting_key": "use_reading_speed_wpm",
            },
            "use_image_displayed_duration": {
                "elem": self.radio_use_image_displayed_duration,
                "toggle_elem": self.image_displayed_duration_col,
                "setting_key": "use_image_displayed_duration",
            },
        }

        self.inner_content = [
            self.video_height_textfield,
            self.image_displayed_duration_textfield,
            ft.RadioGroup(
                content=ft.Column(
                    controls=[val["elem"] for val in self.radio_group_dict.values()]
                ),
                on_change=lambda e: self.handle_radio_group_change(
                    e, self.radio_group_dict
                ),
                value=self.get_radio_group_init_value(
                    radio_group_dict=self.radio_group_dict
                ),
            ),
            self.reading_speed_wpm_col,
            self.image_displayed_duration_col,
        ]

        self.content = self.get_full_content()
