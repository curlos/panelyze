import os
import azure.cognitiveservices.speech as speechsdk
from utils import utils_load_dotenv
from magi_panel_output import (
    frieren_ch_55_essential_text_matrix,
    one_piece_ch_595_panel_39_and_40,
)


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
