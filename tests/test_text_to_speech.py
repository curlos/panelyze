import pytest

import TextToSpeech as text_to_speech_module
from TextToSpeech import TextToSpeech


def test_azure_without_a_key_gives_a_clear_error(monkeypatch, tmp_path):
    # Don't read the real ".env" file.
    monkeypatch.setattr(text_to_speech_module, "utils_load_dotenv", lambda: None)
    monkeypatch.delenv("AZURE_SUBSCRIPTION_KEY", raising=False)
    monkeypatch.delenv("AZURE_REGION", raising=False)

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
    monkeypatch.setattr(text_to_speech_module, "run_async", lambda coroutine: coroutine.close())
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


def test_azure_ssml_does_not_need_the_edge_voice_list(monkeypatch):
    tts = TextToSpeech({"azure_voice_name": "en-US-AvaMultilingualNeural"})
    monkeypatch.setattr(
        tts, "get_voice_name", lambda: (_ for _ in ()).throw(AssertionError("no Edge lookup"))
    )

    assert "name='en-US-AvaMultilingualNeural'" in tts.get_azure_ssml("Hi")


def make_azure_tts(**settings):
    return TextToSpeech({"tts_engine": "azure", "azure_voice_name": "en-US-AriaNeural", **settings})


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
    monkeypatch.setattr(tts, "generate_audio_for_text", lambda text, output_file: spoken.append(text))
    monkeypatch.setattr(text_to_speech_module, "AudioFileClip", lambda path: FakeClip())
    monkeypatch.setattr(text_to_speech_module, "concatenate_audioclips", lambda clips: FakeClip())

    tts.generate_audio(["First line.", "Second line."], str(tmp_path / "out.mp3"))

    assert spoken == ["First line.", "Second line."]


def test_voice_without_styles_never_loads_the_emotion_model(monkeypatch):
    import EmotionAnalyzer

    loaded = []
    monkeypatch.setattr(
        EmotionAnalyzer.EmotionAnalyzer, "emotion_pipeline", property(lambda self: loaded.append(1))
    )

    ssml = make_azure_tts(azure_voice_style="auto").get_azure_ssml("Hello", [])

    assert "express-as" not in ssml
    assert loaded == []


def test_a_failed_style_lookup_is_not_remembered(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(text_to_speech_module, "_cached_azure_voice_styles", {})
    failure = SimpleNamespace(reason="Canceled", voices=[])
    success_voice = SimpleNamespace(short_name="en-US-AriaNeural", style_list=["cheerful", ""])
    results = [failure, SimpleNamespace(reason="VoicesListRetrieved", voices=[success_voice])]

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


def test_lines_with_nothing_to_say_are_left_out_of_the_voice_over(tmp_path, monkeypatch):
    spoken = []
    text_to_speech = TextToSpeech({})
    monkeypatch.setattr(
        text_to_speech, "generate_audio_for_text", lambda text, output_file, *args: spoken.append(text)
    )

    # A lone "!" or "..." can't be spoken, and the voice service fails on it.
    text_to_speech.generate_audio(["Hello there.", "!", "...!", "Why?!"], str(tmp_path / "a.mp3"))
    text_to_speech.generate_audio(["!", "?", "..."], str(tmp_path / "b.mp3"))

    assert spoken == ["Hello there. Why?!"]


def test_words_split_across_lines_of_a_speech_bubble_are_read_as_one_word():
    from TextToSpeech import join_words_split_across_lines

    # As Magi reads them from the bubbles of a real chapter (Shachou to Sake to Hoshi ch. 8).
    assert join_words_split_across_lines("The Presi- dential Office") == "The Presidential Office"
    assert join_words_split_across_lines("So embar-\nrassing!") == "So embarrassing!"
    # With a capital, only when it makes a real word (as Magi read them in that chapter).
    assert join_words_split_across_lines("Well, Presi- Dent?") == "Well, President?"
    assert join_words_split_across_lines("Communica- Tions from the client") == "Communications from the client"
    assert join_words_split_across_lines("PRESI- DENT") == "PRESIDENT"
    # Someone cut off, real hyphens (no space after them) and stutters stay.
    assert join_words_split_across_lines("Wait- Stop! HEY- YOU") == "Wait- Stop! HEY- YOU"
    assert join_words_split_across_lines("Wait- what?! I want- you to go") == "Wait- what?! I want- you to go"
    assert join_words_split_across_lines("hard-working chit-chats") == "hard-working chit-chats"
    assert join_words_split_across_lines("Wh- what? N-NO!") == "Wh- what? N-NO!"


def test_the_voice_reads_split_words_as_one_word(monkeypatch, tmp_path):
    from TextToSpeech import TextToSpeech

    tts = TextToSpeech({})
    said = []
    monkeypatch.setattr(tts, "generate_audio_for_text", lambda text, output_file: said.append(text))

    tts.generate_audio(["It's impos- sible!"], str(tmp_path / "line.mp3"))

    assert said == ["It's impossible!"]
