import flet as ft
from TextToSpeech import TextToSpeech
from classes.SettingsBase import SettingsBase
from classes.DropdownTextOptions import DropdownTextOptions


class TextToSpeechAzure(SettingsBase):
    def __init__(self, page, page_num_textfield_dict, radio_group_dict):
        super().__init__()
        self.page = page
        self.tts = TextToSpeech(self.page.client_storage)
        self.locale_voice_mapping = self.tts.locale_voice_mapping
        self.page_num_textfield_dict = page_num_textfield_dict
        self.radio_group_dict = radio_group_dict

        # Text-To-Speech (Azure)
        self.image_pre_tts_audio_delay_textfield = self.get_number_textfield(
            "Image Pre-TTS Audio Delay (seconds)",
            "image_pre_tts_audio_delay",
        )

        self.image_post_tts_audio_delay_textfield = self.get_number_textfield(
            "Image Post-TTS Audio Delay (seconds)",
            "image_post_tts_audio_delay",
        )

        self.page_num_textfield_dict["image_pre_tts_audio_delay"] = (
            self.image_pre_tts_audio_delay_textfield
        )
        self.page_num_textfield_dict["image_post_tts_audio_delay"] = (
            self.image_post_tts_audio_delay_textfield
        )

        self.radio_use_text_to_speech_azure = ft.Radio(
            label="Use Text-To-Speech (Azure)",
            value="use_text_to_speech_azure",
        )

        self.radio_group_dict["use_text_to_speech_azure"] = {
            "elem": self.radio_use_text_to_speech_azure,
            "toggle_elem": self,
            "setting_key": "use_text_to_speech_azure",
        }

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
                    ),
                    ft.Icon(
                        name=ft.Icons.INFO,
                        color="#5e81ac",
                        tooltip=ft.Tooltip(
                            message="Dynamic-Style (Emotion-By-Text): Instead of using one voice style throughout the whole video, this option will dynamically go through the text in an image and use the individual voice-style that fits each part of the text the most. For example, if one part of the text is 'angry', then the 'angry' voice style will be used. If another part is 'cheerful', then the 'cheerful' voice style will be used.",
                            text_style=ft.TextStyle(color="white"),
                            bgcolor="#3b4252",
                            border=ft.border.all(1, "#5e81ac"),
                            wait_duration=100,
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.VerticalAlignment.CENTER,
                spacing=5,
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

        self.content = ft.Column(
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
                ft.Checkbox(
                    label='Clean up TTS "audio-files" folder',
                    value=self.page.client_storage.get(
                        "clean_up_tts_audio_files_folder"
                    ),
                    on_change=lambda e: self.change_setting(
                        "clean_up_tts_audio_files_folder", e.data
                    ),
                ),
            ],
            visible=bool(self.page.client_storage.get("use_text_to_speech_azure")),
        )
        self.padding = ft.padding.only(left=30)

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
