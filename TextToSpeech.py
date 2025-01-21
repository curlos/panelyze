import os
import azure.cognitiveservices.speech as speechsdk
from utils import utils_load_dotenv
from EmotionAnalyzer import EmotionAnalyzer


class TextToSpeech:
    def __init__(self, flet_page_client_storage=None):
        utils_load_dotenv()
        self.subscription_key = os.getenv("AZURE_SUBSCRIPTION_KEY")
        self.region = os.getenv("AZURE_REGION")

        self.flet_page_client_storage = flet_page_client_storage
        self.locale_voice_mapping = self.get_locale_voice_mapping()
        self.emotion_analyzer = EmotionAnalyzer()

    def get_all_voices(self):
        subscription_key = (
            self.flet_page_client_storage.get("azure_subscription_key")
            or self.subscription_key
        )
        region = self.flet_page_client_storage.get("azure_region") or self.region

        # Configure the Azure Speech SDK
        speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key, region=region
        )

        # Create the speech synthesizer
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

        # Fetch all available voices
        results = synthesizer.get_voices_async().get()

        return results

    def get_all_voice_styles(self):
        all_voices = self.get_all_voices()
        all_voice_styles = {}

        for voice in all_voices.voices:
            for voice_style in voice.style_list:
                if voice_style:
                    all_voice_styles[voice_style] = True

        return list(all_voice_styles.keys())

    def get_locale_voice_mapping(self):
        all_voices = self.get_all_voices()

        # Create a dictionary with locale as key and another dictionary as value
        locale_voice_mapping = {}
        for voice in all_voices.voices:
            if voice.locale not in locale_voice_mapping:
                locale_voice_mapping[voice.locale] = {}
            locale_voice_mapping[voice.locale][voice.short_name] = voice

        return locale_voice_mapping

    def generate_azure_audio(self, text_list, output_file):
        """
        Generate TTS audio with Azure and save it to a file.
        """
        subscription_key = (
            self.flet_page_client_storage.get("azure_subscription_key")
            or self.subscription_key
        )
        region = self.flet_page_client_storage.get("azure_region") or self.region

        # Set up Azure Speech configuration
        speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key, region=region
        )
        audio_config = speechsdk.AudioConfig(filename=output_file)

        ssml_text = self.get_ssml_text(text_list)

        # Generate audio
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )

        result = synthesizer.speak_ssml_async(ssml_text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"Audio saved to {output_file}")
        else:
            print(f"Azure TTS failed: {result.reason}")

    def get_ssml_text(self, text_list):
        azure_voice_locale = "en-US"
        azure_voice_name = "en-US-AriaNeural"

        azure_voice_volume = "x-loud"
        azure_voice_rate = "medium"
        azure_voice_pitch = "medium"
        azure_break_time_between_text = 0.00
        azure_voice_style = ""

        if self.flet_page_client_storage:
            azure_voice_locale = self.flet_page_client_storage.get("azure_voice_locale")
            azure_voice_name = self.flet_page_client_storage.get("azure_voice_name")

            azure_voice_volume = self.flet_page_client_storage.get("azure_voice_volume")
            azure_voice_rate = self.flet_page_client_storage.get("azure_voice_rate")
            azure_voice_pitch = self.flet_page_client_storage.get("azure_voice_pitch")
            azure_break_time_between_text = float(
                self.flet_page_client_storage.get("azure_break_time_between_text")
            )

            temp_azure_voice_style = self.flet_page_client_storage.get(
                "azure_voice_style"
            )

            if temp_azure_voice_style and temp_azure_voice_style != "No Style":
                azure_voice_style = temp_azure_voice_style

        azure_voice = self.locale_voice_mapping[azure_voice_locale][azure_voice_name]
        has_voice_styles = len(azure_voice.style_list) > 0

        if azure_voice_style == "Dynamic-Style (Emotion-By-Text)" and has_voice_styles:
            azure_voice_style_list_dict = {}

            for voice_style in azure_voice.style_list:
                azure_voice_style_list_dict[voice_style] = True

            # Dynamic style applied to each text individually
            ssml_text = f"""
            <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='{azure_voice_locale}'>
                <voice name='{azure_voice_name}'>
                    <prosody pitch="{azure_voice_pitch}" rate="{azure_voice_rate}" volume="{azure_voice_volume}">
            """

            # Add text from the array with individual styles
            for line in text_list:
                emotion, _ = self.emotion_analyzer.get_emotion(line)
                emotion_voice_styles = self.emotion_analyzer.azure_emotion_dict[emotion]
                voice_style_to_use_for_line = ""

                for voice_style in emotion_voice_styles:
                    current_voice_has_voice_style = (
                        voice_style in azure_voice_style_list_dict
                    )

                    if current_voice_has_voice_style:
                        voice_style_to_use_for_line = voice_style
                        break

                ssml_text += f"""
                        <mstts:express-as style='{voice_style_to_use_for_line}' styledegree='2'>
                            {line}
                        </mstts:express-as>
                        <break time='{azure_break_time_between_text}s'/>
                """

            # Close SSML tags
            ssml_text += """
                    </prosody>
                </voice>
            </speak>
            """
        else:
            # Single style applied around all text
            ssml_text = f"""
            <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='{azure_voice_locale}'>
                <voice name='{azure_voice_name}'>
                    <mstts:express-as style='{azure_voice_style}' styledegree='2'>
                        <prosody pitch="{azure_voice_pitch}" rate="{azure_voice_rate}" volume="{azure_voice_volume}">
            """

            # Add all text together with pauses
            for line in text_list:
                ssml_text += f"""
                            {line}
                            <break time='{azure_break_time_between_text}s'/>
                """

            # Close SSML tags
            ssml_text += """
                        </prosody>
                    </mstts:express-as>
                </voice>
            </speak>
            """

        return ssml_text


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    tts = TextToSpeech()

    os.makedirs("tts-test-output", exist_ok=True)

    one_piece_ch_595_panel_39_and_40_essential_text_matrix = [
        [
            "Red Line: Holy Land of Mariejoa",
            "vanished...?",
            "Yeah. That's what happened.",
            "I don't mean just like a figure of speech, either. He literally vanished into thin air!!",
            "Fuffuffu... it sure took me by surprise, I'll tell you that. Does the Kage Kage no mi have that kind of power?",
            "This is no joking matter!!!",
        ],
        [
            "Ahh, don't worry... He was half-dead already. There was no saving him, no matter where he went.",
            "Well... unless he managed to resurrect himself as a zombie, of course... Fuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffu! Hey, it serves him right.",
            "And you call this doing your job, do you...?!!!",
        ],
    ]

    for index, panel_text_arr in enumerate(
        one_piece_ch_595_panel_39_and_40_essential_text_matrix
    ):
        all_panel_text_str = " ".join(panel_text_arr)
        output_file = f"z-tts-test-output/panel_{index + 1}.wav"

        if all_panel_text_str:
            print(all_panel_text_str)
            tts.generate_azure_audio(all_panel_text_str, output_file)
