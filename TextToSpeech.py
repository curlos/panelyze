import os
import azure.cognitiveservices.speech as speechsdk
from utils import utils_load_dotenv


class TextToSpeech:
    def __init__(self, flet_page_client_storage=None):
        utils_load_dotenv()
        self.subscription_key = os.getenv("AZURE_SUBSCRIPTION_KEY")
        self.region = os.getenv("AZURE_REGION")

        self.flet_page_client_storage = flet_page_client_storage

    def get_locale_voice_mapping(self):
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

        # Create a dictionary with locale as key and another dictionary as value
        locale_voice_mapping = {}
        for voice in results.voices:
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

        azure_voice_locale = "en-US"
        azure_voice_name = "en-US-AriaNeural"

        azure_voice_volume = "x-loud"
        azure_voice_rate = "medium"
        azure_voice_pitch = "medium"
        azure_break_time_between_text = 0.00

        if self.flet_page_client_storage:
            azure_voice_locale = self.flet_page_client_storage.get("azure_voice_locale")
            azure_voice_name = self.flet_page_client_storage.get("azure_voice_name")

            azure_voice_volume = self.flet_page_client_storage.get("azure_voice_volume")
            azure_voice_rate = self.flet_page_client_storage.get("azure_voice_rate")
            azure_voice_pitch = self.flet_page_client_storage.get("azure_voice_pitch")
            azure_break_time_between_text = float(
                self.flet_page_client_storage.get("azure_break_time_between_text")
            )

        ssml_text = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='{azure_voice_locale}'>
            <voice name='{azure_voice_name}'>
                <mstts:express-as style='formal' styledegree='2'>
                    <prosody pitch="{azure_voice_pitch}" rate="{azure_voice_rate}" volume="{azure_voice_volume}">
        """

        # Add text from the array with pauses
        for line in text_list:
            ssml_text += f"{line}<break time='{azure_break_time_between_text}s'/>"  # Add a 1-second pause after each line

        # Close SSML tags
        ssml_text += """
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """

        # Generate audio
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )

        result = synthesizer.speak_ssml_async(ssml_text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            print(f"Audio saved to {output_file}")
        else:
            print(f"Azure TTS failed: {result.reason}")


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
