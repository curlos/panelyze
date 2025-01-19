import os
import azure.cognitiveservices.speech as speechsdk

subscription_key = os.getenv("AZURE_SUBSCRIPTION_KEY")
region = os.getenv("AZURE_REGION")


def test_ssml(subscription_key, region):
    """
    Test basic SSML functionality with Azure TTS.
    """
    # Set up Azure Speech configuration
    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)

    ssml_text = """
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="en-US-AvaMultilingualNeural">
            <prosody rate='100%'>This is a simple test.</prosody>
        </voice>
    </speak>
    """

    # Initialize the synthesizer without specifying audio_config
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

    # Synthesize SSML
    result = synthesizer.speak_ssml_async(ssml_text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("SSML test succeeded.")
    else:
        print(f"SSML test failed: {result.reason}")


# Example usage
test_ssml(subscription_key=subscription_key, region=region)
