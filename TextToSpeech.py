import os
import azure.cognitiveservices.speech as speechsdk

from utils import utils_load_dotenv


class TextToSpeech:
    def __init__(self):
        utils_load_dotenv()

        self.subscription_key = os.getenv("AZURE_SUBSCRIPTION_KEY")
        self.region = os.getenv("AZURE_REGION")

    def calculate_azure_rate(self, wpm, base_wpm=150):
        """
        Map WPM to Azure's percentage-based rate with bounds (-100% to +400%).
        """
        rate_percentage = (wpm / base_wpm) * 100

        # Cap the rate to Azure's limits
        return max(50, min(rate_percentage, 400))

    def generate_azure_audio_with_wpm(self, text, output_file, wpm=150):
        """
        Generate TTS audio with Azure, save it to a file, and control the WPM rate.
        """
        # Set up Azure Speech configuration
        speech_config = speechsdk.SpeechConfig(
            subscription=self.subscription_key, region=self.region
        )
        audio_config = speechsdk.AudioConfig(filename=output_file)

        # Calculate Azure speech rate and cap it
        rate_percentage = self.calculate_azure_rate(wpm)

        # Create SSML text with the working voice and prosody for rate control
        ssml_text = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
            <voice name='en-US-AvaMultilingualNeural'>
                <prosody rate='{rate_percentage}%'>
                    {text}
                </prosody>
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

    # Example Usage
    text = "This is a test of Azure TTS with a custom speaking rate."
    output_file = "output_azure.wav"
    wpm = 1  # Desired words per minute
    tts.generate_azure_audio_with_wpm(text, output_file, wpm)
