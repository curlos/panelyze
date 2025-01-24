import flet as ft
from classes.SettingsBase import SettingsBase
from classes.TextToSpeechAzure import TextToSpeechAzure
from classes.HighlightTextBoxesInImages import HighlightTextBoxesInImages


class SettingsImagesToVideo(
    SettingsBase,
):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.video_height_textfield = self.get_number_textfield(
            "Video Height (px)", "video_height"
        )

        # Reading Speed
        self.reading_speed_wpm_textfield = self.get_number_textfield(
            "Reading Speed (WPM)", "reading_speed_wpm"
        )

        self.reading_speed_wpm_col = ft.Column(
            controls=[
                self.reading_speed_wpm_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_reading_speed_wpm")),
        )

        self.radio_use_reading_speed_wpm = ft.Radio(
            label="Use Reading Speed (WPM)",
            value="use_reading_speed_wpm",
        )

        # Image Displayed Duration
        self.image_displayed_duration_textfield = self.get_number_textfield(
            "Image Displayed Duration (sec.)", "image_displayed_duration"
        )

        self.image_displayed_duration_col = ft.Column(
            controls=[
                self.image_displayed_duration_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_image_displayed_duration")),
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

        # Use Minimum Image Duration
        self.minimum_image_duration_textfield = self.get_number_textfield(
            "Minimum Image Duration (seconds)", "minimum_image_duration"
        )

        self.minimum_image_duration_col = ft.Column(
            controls=[
                self.minimum_image_duration_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_minimum_image_duration")),
        )

        self.page_num_textfield_dict = {
            "video_height": self.video_height_textfield,
            "reading_speed_wpm": self.reading_speed_wpm_textfield,
            "image_displayed_duration": self.image_displayed_duration_textfield,
            "minimum_image_duration": self.minimum_image_duration_textfield,
        }

        self.text_to_speech_azure_col = TextToSpeechAzure(
            page, self.page_num_textfield_dict, self.radio_group_dict
        )

        self.inner_content = [
            self.video_height_textfield,
            ft.Checkbox(
                label="Use Minimum Image Duration (sec.)",
                value=self.page.client_storage.get("use_minimum_image_duration"),
                on_change=lambda e: self.toggle_setting_element_visibility(
                    e,
                    self.minimum_image_duration_col,
                    "use_minimum_image_duration",
                ),
            ),
            self.minimum_image_duration_col,
            HighlightTextBoxesInImages(self.page),
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
            self.text_to_speech_azure_col,
        ]

        self.content = self.get_full_content()
