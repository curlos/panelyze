import flet as ft
from classes.SettingsBase import SettingsBase
from TextToSpeech import TextToSpeech


class SettingsImagesToVideo(
    SettingsBase,
):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.tts = TextToSpeech(self.page.client_storage)
        self.locale_voice_mapping = self.tts.locale_voice_mapping

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

        # Text-To-Speech (Azure)
        self.image_pre_tts_audio_delay_textfield = self.get_number_textfield(
            "Image Pre-TTS Audio Delay (seconds)",
            "image_pre_tts_audio_delay",
        )

        self.image_post_tts_audio_delay_textfield = self.get_number_textfield(
            "Image Post-TTS Audio Delay (seconds)",
            "image_post_tts_audio_delay",
        )

        self.azure_subscription_key_textfield = ft.TextField(
            label="Azure Subscription Key",
            border_color="#5e81ac",
            password=True,
            can_reveal_password=True,
            value=self.page.client_storage.get("azure_subscription_key"),
            on_change=lambda e: self.change_setting("azure_subscription_key", e.data),
        )

        self.azure_region_textfield = ft.TextField(
            label="Azure Region",
            border_color="#5e81ac",
            value=self.page.client_storage.get("azure_region"),
            on_change=lambda e: self.change_setting("azure_region", e.data),
        )

        default_locale = self.get_setting_value("azure_voice_locale", "en-US")

        default_voice_dict = self.locale_voice_mapping[default_locale]
        default_voice_short_names = default_voice_dict.keys()
        default_voice_short_names_list = list(default_voice_dict.keys())
        default_voice_name = (
            self.page.client_storage.get("azure_voice_name")
            or default_voice_short_names_list[0]
        )

        default_azure_voice_volume = self.get_setting_value(
            "azure_voice_volume", "x-loud"
        )
        default_azure_voice_rate = self.get_setting_value("azure_voice_rate", "medium")
        default_azure_voice_pitch = self.get_setting_value(
            "azure_voice_pitch", "medium"
        )
        default_azure_break_time_between_text = float(
            self.get_setting_value("azure_break_time_between_text", 0.00)
        )
        default_azure_voice_style_degree = float(
            self.get_setting_value("azure_voice_style_degree", 2.00)
        )

        self.azure_voice_pitch_options = ["x-low", "low", "medium", "high", "x-high"]
        self.azure_voice_rate_options = ["x-slow", "slow", "medium", "fast", "x-fast"]
        self.azure_voice_volume_options = [
            "silent",
            "x-soft",
            "soft",
            "medium",
            "loud",
            "x-loud",
        ]

        default_voice = default_voice_dict[default_voice_name]
        default_voice_style_list = default_voice.style_list
        default_azure_voice_style = self.get_setting_value(
            "azure_voice_style", "No Style"
        )

        self.dynamic_style_dropdown_option = ft.dropdown.Option(
            key="Dynamic-Style (Emotion-By-Text)",
            content=ft.Row(
                controls=[
                    ft.Text(
                        value="Dynamic-Style (Emotion-By-Text)",
                        tooltip=ft.Tooltip(
                            message="Dynamic-Style (Emotion-By-Text): Instead of using one voice style throughout the whole video, this option will dynamically go through the text in an image and use the individual voice-style that fits each part of the text the most. For example, if one part of the text is 'angry', then the 'angry' voice style will be used. If another part is 'cheerful', then the 'cheerful' voice style will be used.",
                            text_style=ft.TextStyle(color="white"),
                            bgcolor="#3b4252",
                            border=ft.border.all(1, "#5e81ac"),
                            wait_duration=500,
                        ),
                    ),
                ]
            ),
        )

        default_voice_style_list_options = [
            ft.dropdown.Option("No Style"),
            self.dynamic_style_dropdown_option,
        ]
        default_voice_style_list_options.extend(
            [ft.dropdown.Option(style) for style in default_voice_style_list if style]
        )

        self.voice_locale_dropdown = DropdownTextOptions(
            label="Voice Locale",
            options=[
                ft.dropdown.Option(locale)
                for locale in sorted(self.locale_voice_mapping.keys())
            ],
            value=default_locale,
            on_change=self.handle_voice_locale_change,
        )

        self.voice_names_dropdown = DropdownTextOptions(
            label="Voice Names",
            options=[
                ft.dropdown.Option(voice_short_name)
                for voice_short_name in default_voice_short_names
            ],
            value=default_voice_name,
            on_change=self.handle_voice_name_change,
        )

        self.voice_volume_options_dropdown = DropdownTextOptions(
            label="Voice Volume",
            options=[
                ft.dropdown.Option(volume) for volume in self.azure_voice_volume_options
            ],
            value=default_azure_voice_volume,
            on_change=lambda e: self.change_setting("azure_voice_volume", e.data),
        )

        self.voice_rate_options_dropdown = DropdownTextOptions(
            label="Voice Rate",
            options=[
                ft.dropdown.Option(rate) for rate in self.azure_voice_rate_options
            ],
            value=default_azure_voice_rate,
            on_change=lambda e: self.change_setting("azure_voice_rate", e.data),
        )

        self.voice_pitch_options_dropdown = DropdownTextOptions(
            label="Voice Pitch",
            options=[
                ft.dropdown.Option(pitch) for pitch in self.azure_voice_pitch_options
            ],
            value=default_azure_voice_pitch,
            on_change=lambda e: self.change_setting("azure_voice_pitch", e.data),
        )

        self.voice_style_options_dropdown = DropdownTextOptions(
            label="Voice Style",
            options=default_voice_style_list_options,
            value=default_azure_voice_style,
            on_change=lambda e: self.change_setting("azure_voice_style", e.data),
        )

        self.text_to_speech_azure_col = ft.Column(
            controls=[
                self.azure_subscription_key_textfield,
                self.azure_region_textfield,
                self.voice_locale_dropdown,
                self.voice_names_dropdown,
                self.voice_style_options_dropdown,
                ft.Text("Voice Style Degree (Intensity):"),
                ft.Slider(
                    value=default_azure_voice_style_degree,
                    min=0,
                    max=2,
                    divisions=20,
                    label="{value}",
                    round=2,
                    on_change_end=lambda e: self.change_setting(
                        "azure_voice_style_degree", e.data
                    ),
                ),
                self.voice_volume_options_dropdown,
                self.voice_rate_options_dropdown,
                self.voice_pitch_options_dropdown,
                ft.Text("Break Time Between Text (seconds):"),
                ft.Slider(
                    value=default_azure_break_time_between_text,
                    min=0,
                    max=5,
                    divisions=20,
                    label="{value}s",
                    round=2,
                    on_change_end=lambda e: self.change_setting(
                        "azure_break_time_between_text", e.data
                    ),
                ),
                self.image_pre_tts_audio_delay_textfield,
                self.image_post_tts_audio_delay_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_text_to_speech_azure")),
        )

        self.radio_use_text_to_speech_azure = ft.Radio(
            label="Use Text-To-Speech (Azure)",
            value="use_text_to_speech_azure",
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
            "use_text_to_speech_azure": {
                "elem": self.radio_use_text_to_speech_azure,
                "toggle_elem": self.text_to_speech_azure_col,
                "setting_key": "use_text_to_speech_azure",
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

        # Highlight Text In Images
        self.highlight_text_boxes_in_images_textfield = self.get_number_textfield(
            "Text Box Color", "text_box_color"
        )

        self.highlight_text_boxes_in_images_col = ft.Column(
            controls=[
                self.highlight_text_boxes_in_images_textfield,
            ],
            visible=bool(
                self.page.client_storage.get("highlight_text_boxes_in_images")
            ),
        )

        self.page_num_textfield_dict = {
            "video_height": self.video_height_textfield,
            "reading_speed_wpm": self.reading_speed_wpm_textfield,
            "image_displayed_duration": self.image_displayed_duration_textfield,
            "minimum_image_duration": self.minimum_image_duration_textfield,
            "image_pre_tts_audio_delay": self.image_pre_tts_audio_delay_textfield,
            "image_post_tts_audio_delay": self.image_post_tts_audio_delay_textfield,
        }

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
            ft.Checkbox(
                label="Highlight Text Boxes In Images",
                value=self.page.client_storage.get("highlight_text_boxes_in_images"),
                on_change=lambda e: self.toggle_setting_element_visibility(
                    e,
                    self.highlight_text_boxes_in_images_col,
                    "highlight_text_boxes_in_images",
                ),
            ),
            self.highlight_text_boxes_in_images_col,
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

    def handle_voice_locale_change(self, e):
        self.change_setting("azure_voice_locale", e.data)

        current_locale = self.get_setting_value("azure_voice_locale", "en-US")

        current_voice_dict = self.locale_voice_mapping[current_locale]
        current_voice_short_names = current_voice_dict.keys()
        current_voice_short_names_list = list(current_voice_dict.keys())
        current_voice_name = current_voice_short_names_list[0]

        self.voice_names_dropdown.options = [
            ft.dropdown.Option(voice_short_name)
            for voice_short_name in current_voice_short_names
        ]
        self.voice_names_dropdown.value = current_voice_name
        self.change_setting("azure_voice_name", current_voice_name)
        self.voice_names_dropdown.update()

        current_voice = current_voice_dict[current_voice_name]
        current_voice_style_list = current_voice.style_list

        self.voice_style_options_dropdown.options = [
            ft.dropdown.Option("No Style"),
            self.dynamic_style_dropdown_option,
        ]

        self.voice_style_options_dropdown.options.extend(
            [ft.dropdown.Option(style) for style in current_voice_style_list if style]
        )
        self.voice_style_options_dropdown.value = "No Style"
        self.change_setting("azure_voice_style", "No Style")
        self.voice_style_options_dropdown.update()

    def handle_voice_name_change(self, e):
        self.change_setting("azure_voice_name", e.data)

        current_locale = self.get_setting_value("azure_voice_locale", "en-US")
        current_voice_dict = self.locale_voice_mapping[current_locale]
        current_voice_name = e.data

        current_voice = current_voice_dict[current_voice_name]
        current_voice_style_list = current_voice.style_list

        self.voice_style_options_dropdown.options = [
            ft.dropdown.Option("No Style"),
            self.dynamic_style_dropdown_option,
        ]

        self.voice_style_options_dropdown.options.extend(
            [ft.dropdown.Option(style) for style in current_voice_style_list if style]
        )
        self.voice_style_options_dropdown.value = "No Style"
        self.change_setting("azure_voice_style", "No Style")
        self.voice_style_options_dropdown.update()


class DropdownTextOptions(ft.Dropdown):
    def __init__(self, label, options, value, on_change):
        super().__init__()
        self.label = label
        self.options = options
        self.value = value
        self.on_change = on_change

        self.text_style = ft.TextStyle(
            color="white",  # Text color of the selected item
            size=14,  # Font size
        )
        self.fill_color = "#3b4252"  # Background color of the dropdown
        self.border_color = "#5e81ac"
        self.max_menu_height = 300
