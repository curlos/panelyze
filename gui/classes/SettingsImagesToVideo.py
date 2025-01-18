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

        self.page_num_textfield_dict = {
            "video_height": self.video_height_textfield,
            "image_displayed_duration": self.image_displayed_duration_textfield,
        }

        self.inner_content = [
            self.video_height_textfield,
            self.image_displayed_duration_textfield,
        ]

        self.content = self.get_full_content()
