import sys
import types
from types import SimpleNamespace
from typing import Any, cast

import pytest

import TextToSpeech as text_to_speech_module
from TextToSpeech import TextToSpeech


def test_azure_without_a_key_gives_a_clear_error(tmp_path):
    tts = TextToSpeech({"tts_engine": "azure"})

    with pytest.raises(RuntimeError, match="subscription key and a region"):
        tts.generate_audio_for_text("Hello", str(tmp_path / "out.mp3"))


def test_azure_ssml_escapes_text_and_uses_voice_settings(monkeypatch):
    tts = TextToSpeech(
        {"azure_voice_name": "en-GB-SoniaNeural", "azure_voice_rate": "fast"}
    )
    monkeypatch.setattr(tts, "get_voice_name", lambda: "en-GB-SoniaNeural")

    ssml = tts.get_azure_ssml("Tom & Jerry <3")

    assert "Tom &amp; Jerry &lt;3" in ssml
    assert "name='en-GB-SoniaNeural'" in ssml
    assert "xml:lang='en-GB'" in ssml
    assert "rate='+25%'" in ssml


def test_edge_is_the_default_engine(monkeypatch, tmp_path):
    tts = TextToSpeech({})

    def fail(*args, **kwargs):
        raise AssertionError("Azure should not be used by default")

    monkeypatch.setattr(tts, "generate_azure_audio_for_text", fail)
    monkeypatch.setattr(
        text_to_speech_module, "run_async", lambda coroutine: coroutine.close()
    )
    monkeypatch.setattr(tts, "get_voice_name", lambda: "en-US-AriaNeural")

    tts.generate_audio_for_text("Hello", str(tmp_path / "out.mp3"))


def test_edge_retry_uses_a_new_communicate_each_attempt(monkeypatch, tmp_path):
    created = []

    class FakeCommunicate:
        def __init__(self, *args, **kwargs):
            created.append(self)

        async def save(self, output_file):
            if len(created) == 1:
                raise ConnectionError("network blip")

    monkeypatch.setattr(text_to_speech_module.edge_tts, "Communicate", FakeCommunicate)
    monkeypatch.setattr(text_to_speech_module.time, "sleep", lambda seconds: None)
    tts = TextToSpeech({})
    monkeypatch.setattr(tts, "get_voice_name", lambda: "en-US-AriaNeural")

    tts.generate_audio_for_text("Hello", str(tmp_path / "out.mp3"))

    assert len(created) == 2


def test_edge_gets_the_voice_speed_pitch_and_volume_from_the_settings(
    monkeypatch, tmp_path
):
    sent = []

    class FakeCommunicate:
        def __init__(self, text, voice, rate, pitch, volume):
            sent.append((text, voice, rate, pitch, volume))

        async def save(self, output_file):
            pass

    monkeypatch.setattr(text_to_speech_module.edge_tts, "Communicate", FakeCommunicate)
    tts = TextToSpeech(
        {
            "azure_voice_name": "en-GB-SoniaNeural",
            "azure_voice_rate": "fast",
            "azure_voice_pitch": "low",
            "azure_voice_volume": "x-loud",
        }
    )
    # The voice exists in Edge's list (no internet needed).
    monkeypatch.setattr(
        TextToSpeech,
        "locale_voice_mapping",
        property(lambda self: {"en-GB": {"en-GB-SoniaNeural": {}}}),
    )

    tts.generate_audio_for_text("Hello", str(tmp_path / "out.mp3"))

    assert sent == [("Hello", "en-GB-SoniaNeural", "+25%", "-10Hz", "+50%")]


def test_azure_ssml_does_not_need_the_edge_voice_list(monkeypatch):
    tts = TextToSpeech({"azure_voice_name": "en-US-AvaMultilingualNeural"})
    monkeypatch.setattr(
        tts,
        "get_voice_name",
        lambda: (_ for _ in ()).throw(AssertionError("no Edge lookup")),
    )

    assert "name='en-US-AvaMultilingualNeural'" in tts.get_azure_ssml("Hi")


def make_azure_tts(**settings):
    return TextToSpeech(
        {"tts_engine": "azure", "azure_voice_name": "en-US-AriaNeural", **settings}
    )


def test_azure_without_a_voice_style_has_no_style_markup():
    ssml = make_azure_tts().get_azure_ssml("Hello", ["cheerful"])

    assert "express-as" not in ssml


def test_azure_fixed_voice_style_is_used_when_the_voice_has_it():
    tts = make_azure_tts(azure_voice_style="cheerful", azure_voice_style_degree=1.5)

    ssml = tts.get_azure_ssml("Hello", ["cheerful", "sad"])

    assert "<mstts:express-as style='cheerful' styledegree='1.5'>" in ssml
    assert "xmlns:mstts=" in ssml


def test_azure_fixed_voice_style_the_voice_lacks_is_skipped():
    tts = make_azure_tts(azure_voice_style="angry")

    assert "express-as" not in tts.get_azure_ssml("Hello", ["cheerful"])
    assert "express-as" not in tts.get_azure_ssml("Hello", [])


def test_auto_voice_style_uses_the_emotion_of_each_line(monkeypatch):
    import EmotionAnalyzer

    emotions = {"I'm so happy!": "joy", "Leave me alone.": "anger"}
    analyzer = EmotionAnalyzer.EmotionAnalyzer()
    monkeypatch.setattr(analyzer, "get_emotion", lambda text: (emotions[text], 0.9))
    monkeypatch.setattr(EmotionAnalyzer, "_shared_emotion_analyzer", analyzer)
    tts = make_azure_tts(azure_voice_style="auto")
    voice_styles = ["cheerful", "angry"]

    assert "style='cheerful'" in tts.get_azure_ssml("I'm so happy!", voice_styles)
    assert "style='angry'" in tts.get_azure_ssml("Leave me alone.", voice_styles)
    # A voice without styles just speaks normally.
    assert "express-as" not in tts.get_azure_ssml("I'm so happy!", [])


@pytest.mark.parametrize(
    "magi_device, expected_device",
    [("cuda:1", "cuda:1"), ("cuda:0", "cuda:0"), ("mps", "cpu"), ("cpu", "cpu")],
)
def test_the_emotion_model_runs_on_the_gpu_magi_picked(magi_device, expected_device):
    # On the Windows PC, transformers' own pick ("cuda:0") was the built-in graphics, where it fails with "invalid kernel file". Magi picks "cuda:1", the RX 6700 XT.
    from EmotionAnalyzer import get_emotion_model_device

    assert get_emotion_model_device(magi_device) == expected_device


def test_the_emotion_model_is_loaded_once_when_several_lines_need_it_at_the_same_time(
    monkeypatch,
):
    # A video makes 4 voice-over lines at once; loading the model 4 times at once broke it ("Cannot copy out of meta tensor").
    import threading
    import time

    import EmotionAnalyzer

    loads = []

    def slow_load():
        loads.append(1)
        time.sleep(0.05)
        return "pipeline"

    monkeypatch.setattr(EmotionAnalyzer, "load_emotion_pipeline", slow_load)
    analyzer = EmotionAnalyzer.EmotionAnalyzer()
    results = []
    threads = [
        threading.Thread(target=lambda: results.append(analyzer.emotion_pipeline))
        for _ in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert loads == [1]
    assert results == ["pipeline"] * 4


def test_the_emotion_model_is_loaded_on_the_gpu_magi_picked(monkeypatch):
    import EmotionAnalyzer
    import magi

    monkeypatch.setattr(magi, "get_device", lambda: "cuda:1")
    used = []
    import transformers.pipelines

    def fake_pipeline(task, model, device):
        return used.append(device) or "pipeline"

    # Both places "from transformers import pipeline" can find it: transformers 4.57 looks it up in "transformers.pipelines" each time, older versions keep it on "transformers".
    monkeypatch.setattr(transformers.pipelines, "pipeline", fake_pipeline)
    monkeypatch.setattr(transformers, "pipeline", fake_pipeline)

    assert EmotionAnalyzer.load_emotion_pipeline() == "pipeline"
    assert used == ["cuda:1"]


def test_auto_voice_style_ignores_unsure_emotions(monkeypatch):
    import EmotionAnalyzer

    analyzer = EmotionAnalyzer.EmotionAnalyzer()
    monkeypatch.setattr(analyzer, "get_emotion", lambda text: ("fear", 0.43))

    assert analyzer.get_voice_style("The meeting starts at noon.", ["terrified"]) == ""


def test_the_emotion_model_is_not_loaded_unless_auto_is_used(monkeypatch):
    import EmotionAnalyzer

    loaded = []
    monkeypatch.setattr(
        EmotionAnalyzer.EmotionAnalyzer,
        "emotion_pipeline",
        property(lambda self: loaded.append(1)),
    )

    for style in ("none", "cheerful"):
        make_azure_tts(azure_voice_style=style).get_azure_ssml("Hello", ["cheerful"])

    assert loaded == []


def test_auto_style_reads_each_line_separately(monkeypatch, tmp_path):
    class FakeClip:
        def close(self):
            pass

        def write_audiofile(self, *args, **kwargs):
            pass

    tts = make_azure_tts(azure_voice_style="auto")
    spoken = []
    monkeypatch.setattr(
        tts, "generate_audio_for_text", lambda text, output_file: spoken.append(text)
    )
    monkeypatch.setattr(text_to_speech_module, "AudioFileClip", lambda path: FakeClip())
    monkeypatch.setattr(
        text_to_speech_module, "concatenate_audioclips", lambda clips: FakeClip()
    )

    tts.generate_audio(["First line.", "Second line."], str(tmp_path / "out.mp3"))

    assert spoken == ["First line.", "Second line."]


def test_voice_without_styles_never_loads_the_emotion_model(monkeypatch):
    import EmotionAnalyzer

    loaded = []
    monkeypatch.setattr(
        EmotionAnalyzer.EmotionAnalyzer,
        "emotion_pipeline",
        property(lambda self: loaded.append(1)),
    )

    ssml = make_azure_tts(azure_voice_style="auto").get_azure_ssml("Hello", [])

    assert "express-as" not in ssml
    assert loaded == []


def test_a_failed_style_lookup_is_not_remembered(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(text_to_speech_module, "_cached_azure_voice_styles", {})
    failure = SimpleNamespace(reason="Canceled", voices=[])
    success_voice = SimpleNamespace(
        short_name="en-US-AriaNeural", style_list=["cheerful", ""]
    )
    results = [
        failure,
        SimpleNamespace(reason="VoicesListRetrieved", voices=[success_voice]),
    ]

    class FakeSynthesizer:
        def __init__(self, **kwargs):
            pass

        def get_voices_async(self, locale):
            return SimpleNamespace(get=lambda: results.pop(0))

    speechsdk = SimpleNamespace(
        SpeechSynthesizer=FakeSynthesizer,
        ResultReason=SimpleNamespace(VoicesListRetrieved="VoicesListRetrieved"),
    )
    tts = make_azure_tts(azure_voice_style="cheerful")

    assert tts.get_azure_voice_styles(speechsdk, None) == []
    assert tts.get_azure_voice_styles(speechsdk, None) == ["cheerful"]


@pytest.mark.parametrize("succeeds", [True, False])
def test_azure_never_holds_the_audio_file_open(tmp_path, monkeypatch, succeeds):
    # Written by Azure itself, the file stayed open for a while afterwards, and Windows couldn't delete it ("file in use": a line read in parts was skipped). Now Azure gives the audio back and the app saves it.
    output_file = tmp_path / "out.mp3"
    audio_configs = []

    class FakeSynthesizer:
        def __init__(self, speech_config, audio_config):
            audio_configs.append(audio_config)

        def speak_ssml_async(self, ssml):
            if succeeds:
                result = SimpleNamespace(
                    reason="SynthesizingAudioCompleted", audio_data=b"mp3 audio"
                )
            else:
                result = SimpleNamespace(
                    reason="Canceled",
                    cancellation_details=SimpleNamespace(
                        error_details="Authentication error (401)."
                    ),
                )
            return SimpleNamespace(get=lambda: result)

    speech = cast(Any, types.ModuleType("azure.cognitiveservices.speech"))
    speech.SpeechConfig = lambda subscription, region: SimpleNamespace(
        set_speech_synthesis_output_format=lambda output_format: None
    )
    speech.SpeechSynthesisOutputFormat = SimpleNamespace(
        Audio24Khz48KBitRateMonoMp3="mp3"
    )
    speech.SpeechSynthesizer = FakeSynthesizer
    speech.ResultReason = SimpleNamespace(
        SynthesizingAudioCompleted="SynthesizingAudioCompleted"
    )
    # "import azure.cognitiveservices.speech" finds the real package first, so the fake replaces it there too (no network in tests).
    pytest.importorskip("azure.cognitiveservices.speech")
    monkeypatch.setitem(sys.modules, "azure.cognitiveservices.speech", speech)
    monkeypatch.setattr(sys.modules["azure.cognitiveservices"], "speech", speech)
    tts = make_azure_tts(azure_subscription_key="not-a-real-key", azure_region="eastus")

    if succeeds:
        tts.generate_azure_audio_for_text("Hello", str(output_file))
        assert output_file.read_bytes() == b"mp3 audio"
    else:
        with pytest.raises(RuntimeError, match="Authentication error"):
            tts.generate_azure_audio_for_text("Hello", str(output_file))
        assert not output_file.exists()

    # Azure never gets the file, so it can't keep it open.
    assert audio_configs == [None]


def test_lines_with_nothing_to_say_are_left_out_of_the_voice_over(
    tmp_path, monkeypatch
):
    spoken = []
    text_to_speech = TextToSpeech({})
    monkeypatch.setattr(
        text_to_speech,
        "generate_audio_for_text",
        lambda text, output_file, *args: spoken.append(text),
    )

    # A lone "!" or "..." can't be spoken, and the voice service fails on it.
    text_to_speech.generate_audio(
        ["Hello there.", "!", "...!", "Why?!"], str(tmp_path / "a.mp3")
    )
    text_to_speech.generate_audio(["!", "?", "..."], str(tmp_path / "b.mp3"))

    assert spoken == ["Hello there. Why?!"]


def test_words_split_across_lines_of_a_speech_bubble_are_read_as_one_word():
    from TextToSpeech import join_words_split_across_lines

    # As Magi reads them from the bubbles of a real chapter (Shachou to Sake to Hoshi ch. 8).
    assert (
        join_words_split_across_lines("The Presi- dential Office")
        == "The Presidential Office"
    )
    assert join_words_split_across_lines("So embar-\nrassing!") == "So embarrassing!"
    # With a capital, only when it makes a real word (as Magi read them in that chapter).
    assert join_words_split_across_lines("Well, Presi- Dent?") == "Well, President?"
    assert (
        join_words_split_across_lines("Communica- Tions from the client")
        == "Communications from the client"
    )
    assert join_words_split_across_lines("PRESI- DENT") == "PRESIDENT"
    # Someone cut off, real hyphens (no space after them) and stutters stay.
    assert (
        join_words_split_across_lines("Wait- Stop! HEY- YOU") == "Wait- Stop! HEY- YOU"
    )
    assert (
        join_words_split_across_lines("Wait- what?! I want- you to go")
        == "Wait- what?! I want- you to go"
    )
    assert (
        join_words_split_across_lines("hard-working chit-chats")
        == "hard-working chit-chats"
    )
    assert join_words_split_across_lines("Wh- what? N-NO!") == "Wh- what? N-NO!"


def test_the_voice_reads_split_words_as_one_word(monkeypatch, tmp_path):
    from TextToSpeech import TextToSpeech

    tts = TextToSpeech({})
    said = []
    monkeypatch.setattr(
        tts, "generate_audio_for_text", lambda text, output_file: said.append(text)
    )

    tts.generate_audio(["It's impos- sible!"], str(tmp_path / "line.mp3"))

    assert said == ["It's impossible!"]
