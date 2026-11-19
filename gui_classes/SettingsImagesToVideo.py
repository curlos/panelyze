import flet as ft
from gui_classes.SettingsBase import SettingsBase
from gui_classes.TextToSpeechAzure import TextToSpeechAzure
from gui_classes.HighlightTextBoxesInImages import HighlightTextBoxesInImages
from gui_classes.DropdownTextOptions import DropdownTextOptions
from gui_classes.ReadingDirectionSetting import get_reading_direction_dropdown


class SettingsImagesToVideo(
    SettingsBase,
):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.video_extensions = ["mp4", "mov"]
        default_video_extension = self.get_setting_value("video_extension")

        # Saved as "video_height" (its old name), but it's the resolution: the shorter side of the video.
        self.video_height_textfield = self.get_number_textfield(
            "Video Resolution (px, e.g. 1080 = 1080p)", "video_height"
        )

        self.video_aspect_ratio_dropdown = DropdownTextOptions(
            label="Video Shape",
            options=[
                ft.dropdown.Option(key="16:9", text="16:9 Landscape (YouTube)"),
                ft.dropdown.Option(
                    key="9:16", text="9:16 Vertical (TikTok, Shorts, Reels)"
                ),
                ft.dropdown.Option(key="1:1", text="1:1 Square"),
            ],
            value=self.get_setting_value("video_aspect_ratio"),
            on_change=lambda e: self.change_setting("video_aspect_ratio", e.data),
        )

        self.video_extensions_dropdown = DropdownTextOptions(
            label="Video Format",
            options=[
                ft.dropdown.Option(video_extension)
                for video_extension in self.video_extensions
            ],
            value=default_video_extension,
            on_change=lambda e: self.change_setting("video_extension", e.data),
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

        self.minimum_image_duration_col = ft.Container(
            content=ft.Column(
                controls=[
                    self.minimum_image_duration_textfield,
                ],
                visible=bool(
                    self.page.client_storage.get("use_minimum_image_duration")
                ),
            ),
            padding=ft.padding.only(left=30),
        )


        self.text_to_speech_azure_col = TextToSpeechAzure(
            page, self.radio_group_dict
        )

        self.inner_content = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.RadioGroup(
                            content=ft.Column(
                                controls=[
                                    val["elem"]
                                    for val in self.radio_group_dict.values()
                                ]
                            ),
                            on_change=lambda e: self.handle_radio_group_change(
                                e, self.radio_group_dict
                            ),
                            value=self.get_radio_group_init_value(
                                radio_group_dict=self.radio_group_dict
                            ),
                        ),
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    self.reading_speed_wpm_col,
                                    self.image_displayed_duration_col,
                                    self.text_to_speech_azure_col,
                                ]
                            ),
                            padding=ft.padding.only(left=30),
                        ),
                    ],
                ),
                padding=ft.padding.only(bottom=10),
                margin=ft.margin.only(bottom=10),
                border=ft.border.only(bottom=ft.border.BorderSide(2, "#5e81ac")),
            ),
            get_reading_direction_dropdown(self.page),
            self.video_aspect_ratio_dropdown,
            self.video_height_textfield,
            self.video_extensions_dropdown,
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
        ]

        self.content = self.get_full_content()
