import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from xml.sax.saxutils import escape

import edge_tts
from moviepy import AudioClip, AudioFileClip, concatenate_audioclips
from utils import utils_load_dotenv

DEFAULT_VOICE_LOCALE = "en-US"
DEFAULT_VOICE_NAME = "en-US-AriaNeural"

# "edge" is free (no key). "azure" is the paid Azure Speech service and needs your own key.
TTS_ENGINE_OPTIONS = {
    "edge": "Edge (Free, no key needed)",
    "azure": "Azure (Your own subscription key)",
}

# The dropdowns in the GUI use readable names. edge-tts and Azure both want percentages (rate, volume) and Hz (pitch).
VOICE_RATE_OPTIONS = {
    "x-slow": "-50%",
    "slow": "-25%",
    "medium": "+0%",
    "fast": "+25%",
    "x-fast": "+50%",
}
VOICE_PITCH_OPTIONS = {
    "x-low": "-20Hz",
    "low": "-10Hz",
    "medium": "+0Hz",
    "high": "+10Hz",
    "x-high": "+20Hz",
}
VOICE_VOLUME_OPTIONS = {
    "x-soft": "-50%",
    "soft": "-25%",
    "medium": "+0%",
    "loud": "+25%",
    "x-loud": "+50%",
}


# Azure only: the speaking style of the voice (e.g. "cheerful" or "sad"). "auto" picks a style for each line from its emotion (see "EmotionAnalyzer.py"). Only some Azure voices have styles; other voices just ignore it.
AZURE_VOICE_STYLE_OPTIONS = {
    "none": "None",
    "auto": "Auto (emotion of each line)",
    "cheerful": "Cheerful",
    "excited": "Excited",
    "friendly": "Friendly",
    "hopeful": "Hopeful",
    "sad": "Sad",
    "angry": "Angry",
    "shouting": "Shouting",
    "terrified": "Terrified",
    "whispering": "Whispering",
    "serious": "Serious",
    "calm": "Calm",
}

# The styles each Azure voice has, fetched from Azure once per app run.
_cached_azure_voice_styles = {}

# The voice list only changes when Microsoft adds voices, so it's fetched once per app run and shared (instead of again for every new "TextToSpeech" or after "Reset All Settings").
_cached_locale_voice_mapping = None


def run_async(coroutine):
    """
    edge-tts is async. Run the coroutine in its own thread so this works whether or not an event loop is already running (Flet may have one running).
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coroutine).result()


class TextToSpeech:
    """
    Text-To-Speech with one of two engines (the "tts_engine" setting):
    - "edge" (default): Free. Uses Microsoft Edge's online neural voices through the "edge-tts" package. No API key or account needed.
    - "azure": The paid Azure Speech service, for anyone with their own subscription key. Its package is only imported when it's used.
    Both use the same voice names (Edge's voices are Azure voices) and need an internet connection.
    """

    def __init__(self, flet_page_client_storage=None):
        self.flet_page_client_storage = flet_page_client_storage

    @property
    def locale_voice_mapping(self):
        # Fetched the first time it's needed instead of when this class is created, so that creating it never makes a network request.
        global _cached_locale_voice_mapping

        if _cached_locale_voice_mapping is None:
            _cached_locale_voice_mapping = self.get_locale_voice_mapping()

        return _cached_locale_voice_mapping

    def get_locale_voice_mapping(self):
        """
        Returns a dict like { "en-US": { "en-US-AriaNeural": {...voice info...}, ... }, ... }
        """
        all_voices = run_async(edge_tts.list_voices())

        locale_voice_mapping = {}
        for voice in all_voices:
            locale_voice_mapping.setdefault(voice["Locale"], {})[
                voice["ShortName"]
            ] = voice

        return locale_voice_mapping

    def get_setting(self, setting_key, default_value):
        if not self.flet_page_client_storage:
            return default_value

        return self.flet_page_client_storage.get(setting_key) or default_value

    def generate_audio(self, text_list, output_file):
        """
        Generate TTS audio (mp3) for a list of text and save it to "output_file". If a break time is set, each piece of text is generated separately with silence in between.
        """
        if isinstance(text_list, str):
            text_list = [text_list]

        # A line with no letters or digits (like "!" or "...") can't be spoken. The voice service fails on it ("No audio was received"), so it's left out.
        text_list = [
            text.strip()
            for text in text_list
            if text and any(character.isalnum() for character in text)
        ]

        if not text_list:
            return

        break_time_between_text = float(
            self.get_setting("azure_break_time_between_text", 0)
        )

        # With Azure's "Auto" style, each line is read on its own so it can get its own style.
        reads_each_line_separately = (
            self.get_setting("tts_engine", "edge") == "azure"
            and self.get_setting("azure_voice_style", "none") == "auto"
        )

        if (break_time_between_text <= 0 and not reads_each_line_separately) or len(text_list) == 1:
            self.generate_audio_for_text(" ".join(text_list), output_file)
        else:
            self.generate_audio_with_breaks(
                text_list, output_file, break_time_between_text
            )

        print(f"Audio saved to {output_file}")

    def generate_audio_with_breaks(
        self, text_list, output_file, break_time_between_text
    ):
        part_files = []
        audio_clips = []

        try:
            for index, text in enumerate(text_list):
                part_file = f"{output_file}.part-{index + 1}.mp3"
                self.generate_audio_for_text(text, part_file)
                part_files.append(part_file)

                audio_clips.append(AudioFileClip(part_file))

                is_last_text = index == len(text_list) - 1

                if not is_last_text and break_time_between_text > 0:
                    audio_clips.append(
                        AudioClip(lambda t: 0, duration=break_time_between_text, fps=44100)
                    )

            concatenate_audioclips(audio_clips).write_audiofile(
                output_file, logger=None
            )
        finally:
            for audio_clip in audio_clips:
                audio_clip.close()

            for part_file in part_files:
                if os.path.exists(part_file):
                    os.remove(part_file)

    def generate_audio_for_text(self, text, output_file, max_attempts=3):
        if self.get_setting("tts_engine", "edge") == "azure":
            self.generate_azure_audio_for_text(text, output_file)
            return

        voice_name = self.get_voice_name()
        rate = VOICE_RATE_OPTIONS.get(self.get_setting("azure_voice_rate", "medium"))
        pitch = VOICE_PITCH_OPTIONS.get(
            self.get_setting("azure_voice_pitch", "medium")
        )
        volume = VOICE_VOLUME_OPTIONS.get(
            self.get_setting("azure_voice_volume", "medium")
        )

        # The service can occasionally fail or rate limit, so wait a bit and try again before giving up.
        for attempt in range(1, max_attempts + 1):
            try:
                # A new "Communicate" is needed for each attempt. edge-tts can only use each one once.
                communicate = edge_tts.Communicate(
                    text,
                    voice_name,
                    rate=rate or "+0%",
                    pitch=pitch or "+0Hz",
                    volume=volume or "+0%",
                )
                run_async(communicate.save(output_file))
                return
            except Exception as error:
                if attempt == max_attempts:
                    raise RuntimeError(
                        f"Text-To-Speech failed after {max_attempts} attempts (check your internet connection): {error}"
                    ) from error

                print(f"Text-To-Speech failed ({error}). Retrying in {attempt * 2}s...")
                time.sleep(attempt * 2)

    def generate_azure_audio_for_text(self, text, output_file):
        """
        Same as the Edge version but with the paid Azure Speech service. The key and region come from the settings, or from "AZURE_SUBSCRIPTION_KEY" and "AZURE_REGION" in a ".env" file.
        """
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as error:
            raise RuntimeError(
                'Azure Text-To-Speech needs its package. Install it with: pip install azure-cognitiveservices-speech'
            ) from error

        utils_load_dotenv()
        subscription_key = self.get_setting(
            "azure_subscription_key", os.getenv("AZURE_SUBSCRIPTION_KEY")
        )
        region = self.get_setting("azure_region", os.getenv("AZURE_REGION"))

        if not subscription_key or not region:
            raise RuntimeError(
                "Azure Text-To-Speech needs a subscription key and a region. Add them in the Text-To-Speech settings."
            )

        speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key, region=region
        )
        voice_styles = []
        if self.get_setting("azure_voice_style", "none") != "none":
            voice_styles = self.get_azure_voice_styles(speechsdk, speech_config)

        # mp3, the same as edge-tts, so the rest of the video code doesn't need to know which engine made the audio.
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3
        )
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_config
        )

        result = synthesizer.speak_ssml_async(self.get_azure_ssml(text, voice_styles)).get()

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            error_details = getattr(result, "cancellation_details", None)
            raise RuntimeError(
                f"Azure Text-To-Speech failed: {getattr(error_details, 'error_details', result.reason)}"
            )

    def get_azure_voice_styles(self, speechsdk, speech_config):
        """
        The speaking styles the chosen Azure voice has (e.g. ["angry", "cheerful", ...]). Many voices have none.
        """
        voice_name = self.get_setting("azure_voice_name", DEFAULT_VOICE_NAME)

        if voice_name not in _cached_azure_voice_styles:
            locale = "-".join(voice_name.split("-")[:2])
            voices = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = voices.get_voices_async(locale).get()

            # Don't remember a failed lookup (wrong key, no internet, etc.) as "this voice has no styles". Try again next time.
            if result.reason != speechsdk.ResultReason.VoicesListRetrieved:
                print(f"Couldn't get the voice styles from Azure ({result.reason}). Using the normal voice style.")
                return []

            _cached_azure_voice_styles[voice_name] = next(
                (
                    [style for style in voice.style_list if style]
                    for voice in result.voices
                    if voice.short_name == voice_name
                ),
                [],
            )

        return _cached_azure_voice_styles[voice_name]

    def get_azure_voice_style(self, text, voice_styles):
        """
        The style to read "text" in, or "" for the voice's normal style.
        """
        style = self.get_setting("azure_voice_style", "none")

        # A voice without styles can't use one, so don't even load the emotion model.
        if style == "none" or not voice_styles:
            return ""

        if style == "auto":
            from EmotionAnalyzer import get_emotion_analyzer

            return get_emotion_analyzer().get_voice_style(text, voice_styles)

        # A fixed style the voice doesn't have would just be ignored by Azure.
        return style if style in voice_styles else ""

    def get_azure_ssml(self, text, voice_styles=()):
        # Use the saved voice as is. Checking it against Edge's voice list would make Azure depend on Edge's online service, and Azure has voices that Edge doesn't.
        voice_name = self.get_setting("azure_voice_name", DEFAULT_VOICE_NAME)
        rate = VOICE_RATE_OPTIONS.get(self.get_setting("azure_voice_rate", "medium"))
        pitch = VOICE_PITCH_OPTIONS.get(
            self.get_setting("azure_voice_pitch", "medium")
        )
        volume = VOICE_VOLUME_OPTIONS.get(
            self.get_setting("azure_voice_volume", "medium")
        )
        locale = "-".join(voice_name.split("-")[:2])
        spoken_text = f"""<prosody rate='{rate or "+0%"}' pitch='{pitch or "+0Hz"}' volume='{volume or "+0%"}'>{escape(text)}</prosody>"""

        style = self.get_azure_voice_style(text, voice_styles)
        if style:
            # How strong the style is, from 0.01 (barely) to 2 (twice as strong).
            style_degree = self.get_setting("azure_voice_style_degree", 1)
            spoken_text = f"<mstts:express-as style='{style}' styledegree='{style_degree}'>{spoken_text}</mstts:express-as>"

        return f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='{locale}'>
    <voice name='{voice_name}'>
        {spoken_text}
    </voice>
</speak>"""

    def get_voice_name(self):
        voice_name = self.get_setting("azure_voice_name", DEFAULT_VOICE_NAME)

        # A voice saved from the old Azure settings might not exist in edge-tts. Fall back to the default voice instead of failing.
        voice_exists = any(
            voice_name in voices for voices in self.locale_voice_mapping.values()
        )
        if not voice_exists:
            print(f'Voice "{voice_name}" is not available. Using "{DEFAULT_VOICE_NAME}".')
            return DEFAULT_VOICE_NAME

        return voice_name
