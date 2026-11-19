import threading
import flet as ft
from TextToSpeech import (
    AZURE_VOICE_STYLE_OPTIONS,
    DEFAULT_VOICE_LOCALE,
    DEFAULT_VOICE_NAME,
    TTS_ENGINE_OPTIONS,
    VOICE_PITCH_OPTIONS,
    VOICE_RATE_OPTIONS,
    VOICE_VOLUME_OPTIONS,
    TextToSpeech,
)
from gui_classes.SettingsBase import SettingsBase
from gui_classes.DropdownTextOptions import DropdownTextOptions


# Note: The default engine is the free "edge-tts". The paid Azure Speech service is still available for anyone with their own key. The settings keys still start with "azure_" (from when this only used Azure) so existing saved settings keep working; the voice settings apply to both engines.
class TextToSpeechAzure(SettingsBase):
    def __init__(self, page, radio_group_dict):
        super().__init__()
        self.page = page
        self.tts = TextToSpeech(self.page.client_storage)
        # Until the full voice list has loaded (in the background, so it never slows down opening the app), only the saved voice is shown.
        saved_locale = self.get_setting_value("azure_voice_locale")
        saved_voice_name = self.get_setting_value("azure_voice_name")
        self.locale_voice_mapping = {saved_locale: {saved_voice_name: {}}}
        self.radio_group_dict = radio_group_dict

        self.image_pre_tts_audio_delay_textfield = self.get_number_textfield(
            "Image Pre-TTS Audio Delay (seconds)",
            "image_pre_tts_audio_delay",
        )

        self.image_post_tts_audio_delay_textfield = self.get_number_textfield(
            "Image Post-TTS Audio Delay (seconds)",
            "image_post_tts_audio_delay",
        )


        self.radio_use_text_to_speech_azure = ft.Radio(
            label="Use Text-To-Speech (needs internet)",
            value="use_text_to_speech_azure",
        )

        default_locale = self.get_setting_value("azure_voice_locale")
        if default_locale not in self.locale_voice_mapping:
            default_locale = DEFAULT_VOICE_LOCALE

        default_voice_names = self.get_voice_names(default_locale)
        default_voice_name = self.page.client_storage.get("azure_voice_name")
        if default_voice_name not in default_voice_names:
            default_voice_name = default_voice_names[0]

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
            options=[ft.dropdown.Option(name) for name in default_voice_names],
            value=default_voice_name,
            on_change=lambda e: self.change_setting("azure_voice_name", e.data),
        )

        self.voice_volume_options_dropdown = self.get_named_options_dropdown(
            "Voice Volume", VOICE_VOLUME_OPTIONS, "azure_voice_volume", "x-loud"
        )
        self.voice_rate_options_dropdown = self.get_named_options_dropdown(
            "Voice Rate", VOICE_RATE_OPTIONS, "azure_voice_rate", "medium"
        )
        self.voice_pitch_options_dropdown = self.get_named_options_dropdown(
            "Voice Pitch", VOICE_PITCH_OPTIONS, "azure_voice_pitch", "medium"
        )

        # Engine: Edge (free, default) or Azure (your own key). The key and region fields only show for Azure.
        self.azure_key_and_region_col = ft.Column(
            controls=[
                self.get_text_setting_textfield(
                    "Azure Subscription Key", "azure_subscription_key", password=True
                ),
                self.get_text_setting_textfield(
                    "Azure Region (e.g. eastus)", "azure_region"
                ),
                DropdownTextOptions(
                    label="Voice Style (only some voices have styles)",
                    options=[
                        ft.dropdown.Option(key=style, text=label)
                        for style, label in AZURE_VOICE_STYLE_OPTIONS.items()
                    ],
                    value=self.get_setting_value("azure_voice_style"),
                    on_change=lambda e: self.change_setting("azure_voice_style", e.data),
                ),
                ft.Text(
                    'Auto reads each line in a style that fits its emotion. The emotion model (about 330 MB) downloads automatically the first time it\'s used.',
                    size=12,
                    color="white",
                ),
                ft.Text("Voice Style Strength:"),
                ft.Slider(
                    value=float(self.get_setting_value("azure_voice_style_degree")),
                    min=0.5,
                    max=2,
                    divisions=6,
                    label="{value}",
                    round=2,
                    on_change_end=lambda e: self.change_setting("azure_voice_style_degree", e.data),
                    height=20,
                ),
            ],
            visible=self.get_setting_value("tts_engine") == "azure",
        )

        self.tts_engine_dropdown = DropdownTextOptions(
            label="Text-To-Speech Engine",
            options=[
                ft.dropdown.Option(key=engine, text=engine_label)
                for engine, engine_label in TTS_ENGINE_OPTIONS.items()
            ],
            value=self.get_setting_value("tts_engine"),
            on_change=self.handle_tts_engine_change,
        )

        default_azure_break_time_between_text = float(
            self.get_setting_value("azure_break_time_between_text")
        )

        self.text_to_speech_azure_col = ft.Column(
            controls=[
                self.tts_engine_dropdown,
                self.azure_key_and_region_col,
                self.voice_locale_dropdown,
                self.voice_names_dropdown,
                self.voice_volume_options_dropdown,
                self.voice_rate_options_dropdown,
                self.voice_pitch_options_dropdown,
                ft.Text("Break Time Between Text (seconds):"),
                ft.Container(
                    content=ft.Slider(
                        value=default_azure_break_time_between_text,
                        min=0,
                        max=5,
                        divisions=20,
                        label="{value}s",
                        round=2,
                        on_change_end=lambda e: self.change_setting(
                            "azure_break_time_between_text", e.data
                        ),
                        height=20,
                    ),
                    padding=ft.padding.only(bottom=10),
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

        self.content = self.text_to_speech_azure_col

        threading.Thread(target=self.load_voice_list, daemon=True).start()

        self.radio_group_dict["use_text_to_speech_azure"] = {
            "elem": self.radio_use_text_to_speech_azure,
            "toggle_elem": self.text_to_speech_azure_col,
            "setting_key": "use_text_to_speech_azure",
        }

    def load_voice_list(self):
        self.locale_voice_mapping = self.get_locale_voice_mapping()

        locale = self.voice_locale_dropdown.value
        if locale not in self.locale_voice_mapping:
            locale = DEFAULT_VOICE_LOCALE
        voice_names = self.get_voice_names(locale)
        voice_name = self.voice_names_dropdown.value
        if voice_name not in voice_names:
            voice_name = voice_names[0]

        self.voice_locale_dropdown.options = [
            ft.dropdown.Option(option) for option in sorted(self.locale_voice_mapping)
        ]
        self.voice_locale_dropdown.value = locale
        self.voice_names_dropdown.options = [
            ft.dropdown.Option(name) for name in voice_names
        ]
        self.voice_names_dropdown.value = voice_name

        # Only redraw if the dropdowns are on screen right now. Otherwise they'll show the new options the next time they are.
        for dropdown in (self.voice_locale_dropdown, self.voice_names_dropdown):
            if dropdown.page:
                dropdown.update()

    def get_locale_voice_mapping(self):
        try:
            return self.tts.locale_voice_mapping
        except Exception as error:
            # Offline (or the voice list couldn't be fetched). Still show the default voice so the app opens.
            print(f"Could not fetch the Text-To-Speech voice list: {error}")
            return {DEFAULT_VOICE_LOCALE: {DEFAULT_VOICE_NAME: {}}}

    def get_voice_names(self, locale):
        return sorted(self.locale_voice_mapping.get(locale, {}).keys()) or [
            DEFAULT_VOICE_NAME
        ]

    def get_named_options_dropdown(self, label, options, setting_key, default_value):
        value = self.get_setting_value(setting_key)

        # A value saved from the old Azure settings (like "silent") might not be an option anymore.
        if value not in options:
            value = default_value
            self.change_setting(setting_key, value)

        return DropdownTextOptions(
            label=label,
            options=[ft.dropdown.Option(option) for option in options],
            value=value,
            on_change=lambda e: self.change_setting(setting_key, e.data),
        )

    def get_text_setting_textfield(self, label, setting_key, password=False):
        return ft.TextField(
            label=label,
            border_color="#5e81ac",
            value=self.page.client_storage.get(setting_key) or "",
            password=password,
            can_reveal_password=password,
            on_change=lambda e: self.change_setting(setting_key, e.data.strip()),
        )

    def handle_tts_engine_change(self, e):
        self.change_setting("tts_engine", e.data)
        self.azure_key_and_region_col.visible = e.data == "azure"
        self.azure_key_and_region_col.update()

    def handle_voice_locale_change(self, e):
        self.change_setting("azure_voice_locale", e.data)

        voice_names = self.get_voice_names(e.data)

        self.voice_names_dropdown.options = [
            ft.dropdown.Option(name) for name in voice_names
        ]
        self.voice_names_dropdown.value = voice_names[0]
        self.change_setting("azure_voice_name", voice_names[0])
        self.voice_names_dropdown.update()
