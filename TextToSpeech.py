import os
import azure.cognitiveservices.speech as speechsdk
from utils import utils_load_dotenv
from magi_panel_output import frieren_ch_55_essential_text_matrix


class TextToSpeech:
    def __init__(self):
        utils_load_dotenv()

        self.subscription_key = os.getenv("AZURE_SUBSCRIPTION_KEY")
        self.region = os.getenv("AZURE_REGION")

    def generate_azure_audio(self, text, output_file):
        """
        Generate TTS audio with Azure and save it to a file.
        """
        # Set up Azure Speech configuration
        speech_config = speechsdk.SpeechConfig(
            subscription=self.subscription_key, region=self.region
        )
        audio_config = speechsdk.AudioConfig(filename=output_file)

        # Create SSML text with the working voice and prosody for rate control
        ssml_text = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang='en-US'>
            <voice name='en-US-AriaNeural'>
                <mstts:express-as style='formal' styledegree='2'>
                    {text}
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

    # os.makedirs("tts-test-output", exist_ok=True)

    # for index, panel_text_arr in enumerate(frieren_ch_55_essential_text_matrix[:6]):
    #     all_panel_text_str = " ".join(panel_text_arr)
    #     output_file = f"tts-test-output/panel_{index + 1}.wav"

    #     if all_panel_text_str:
    #         print(all_panel_text_str)
    #         tts.generate_azure_audio(all_panel_text_str, output_file)

    tts.generate_azure_audio("Hello John", "output-azure-sentiment.wav")
