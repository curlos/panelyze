"""
Every Images To Video setting, checked by making real (small) videos. Offline: Magi and the voice are faked, everything else (moviepy, ffmpeg, drawing the boxes) is real.
"""
import os
import sys

import numpy
import pytest
from moviepy import AudioClip, AudioFileClip, VideoFileClip
from PIL import Image

from default_settings import DEFAULT_SETTINGS
from SpeechTextParser import SpeechTextParser
from VideoCreatorFromImages import VideoCreatorFromImages

# What "Magi" reads on the two test panels: 5 words, then 10 words (at 150 words a minute, 2 s and 4 s).
PANEL_TEXT = ["One two three four five.", "One two three four five six seven eight nine ten."]


def make_settings(**overrides):
    """
    The app's default settings with some changed, like the saved settings the Images To Video tab passes in.
    """
    # Small videos are quick to make.
    # Timed by reading speed, with no voice and no pause, unless a test changes them (the voice is the default), so each test only measures its own setting.
    return {
        **DEFAULT_SETTINGS,
        "video_height": 360,
        "reading_direction": "ltr",
        "use_reading_speed_wpm": True,
        "use_text_to_speech_azure": False,
        "image_post_tts_audio_delay": 0,
        **overrides,
    }


def make_panels(tmp_path):
    folder = tmp_path / "Ch 1"
    folder.mkdir()
    for number in (1, 2):
        Image.new("RGB", (300, 400), "white").save(folder / f"panel_{number}.png")
    return folder


def fake_magi(monkeypatch):
    results = [
        {"texts": [[20, 20 + 30 * index, 280, 50 + 30 * index]], "ocr": [text], "is_essential_text": [True]}
        for index, text in enumerate(PANEL_TEXT)
    ]

    class FakeMagi:
        def get_data_from_images(self, input_directory, reading_direction="rtl"):
            return results

    monkeypatch.setattr(SpeechTextParser, "magi", property(lambda self: FakeMagi()))


def fake_voice(video_creator, seconds_per_word=0.4):
    """
    A "voice" that says each word in 0.4 s (a quiet tone: pure silence comes back from an mp3 as almost no time).
    """
    def generate_audio(text_list, output_file):
        words = len(" ".join(text_list).split())
        # Like the real voice: nothing to say, no file.
        if not words:
            return
        AudioClip(lambda t: 0.1 * numpy.sin(2 * numpy.pi * 440 * t), duration=words * seconds_per_word, fps=22050).write_audiofile(
            output_file, logger=None
        )

    video_creator.tts.generate_audio = generate_audio


def make_video(tmp_path, monkeypatch, extension="mp4", voice=False, **settings):
    fake_magi(monkeypatch)
    panels = make_panels(tmp_path)
    video_creator = VideoCreatorFromImages(make_settings(**settings))
    if voice:
        fake_voice(video_creator)
    output_directory = tmp_path / "Videos" / "Ch 1"
    output_file = f"{output_directory}.{extension}"
    video_creator.create_video_from_images(str(panels), output_file, str(output_directory))
    with VideoFileClip(output_file) as video:
        info = {"duration": video.duration, "size": tuple(video.size), "has_audio": video.audio is not None}
    return info, output_directory


# "Image displayed duration": neither the reading speed nor the voice sets the time.
FIXED_TIME = dict(use_reading_speed_wpm=False, use_text_to_speech_azure=False, use_minimum_image_duration=False)


@pytest.mark.parametrize("extension", ["mp4", "mov"])
def test_the_video_format(tmp_path, monkeypatch, extension):
    info, _ = make_video(tmp_path, monkeypatch, extension, image_displayed_duration=2, **FIXED_TIME)

    assert info["duration"] == pytest.approx(4, abs=0.2)


@pytest.mark.parametrize(
    "aspect_ratio, height, size",
    [("16:9", 360, (640, 360)), ("9:16", 360, (360, 640)), ("1:1", 360, (360, 360)), ("16:9", 720, (1280, 720))],
)
def test_the_video_shape_and_resolution(tmp_path, monkeypatch, aspect_ratio, height, size):
    info, _ = make_video(
        tmp_path, monkeypatch, video_aspect_ratio=aspect_ratio, image_displayed_duration=1, **{**FIXED_TIME, "video_height": height}
    )

    assert info["size"] == size


def test_each_image_shows_for_the_set_time(tmp_path, monkeypatch):
    info, _ = make_video(tmp_path, monkeypatch, image_displayed_duration=3, **FIXED_TIME)

    assert info["duration"] == pytest.approx(6, abs=0.2)
    assert not info["has_audio"]


@pytest.mark.parametrize(
    "words_a_minute, minimum, expected",
    [
        # 5 and 10 words: 2 s + 4 s at 150 words a minute, half that at 300.
        (150, None, 6),
        (300, None, 3),
        # A higher speed only makes the video shorter down to the minimum time per image.
        (300, 3, 6),
        (600, 3, 6),
    ],
)
def test_reading_speed_and_the_minimum_time(tmp_path, monkeypatch, words_a_minute, minimum, expected):
    info, _ = make_video(
        tmp_path,
        monkeypatch,
        use_reading_speed_wpm=True,
        reading_speed_wpm=words_a_minute,
        use_minimum_image_duration=minimum is not None,
        minimum_image_duration=minimum or 0,
    )

    assert info["duration"] == pytest.approx(expected, abs=0.6)


@pytest.mark.parametrize("words_a_minute", [0, -50, "", "fast"])
def test_a_reading_speed_that_isnt_a_positive_number_uses_150(words_a_minute):
    # 0 used to divide by zero and stop the video.
    assert VideoCreatorFromImages(make_settings(reading_speed_wpm=words_a_minute)).reading_speed_wpm == 150


@pytest.mark.parametrize("clean_up", [True, False])
def test_the_voice_over_sets_each_image_s_time_and_its_folder_is_cleaned_up(tmp_path, monkeypatch, clean_up):
    info, output_directory = make_video(
        tmp_path,
        monkeypatch,
        voice=True,
        use_reading_speed_wpm=False,
        use_text_to_speech_azure=True,
        use_minimum_image_duration=False,
        image_pre_tts_audio_delay=0.5,
        image_post_tts_audio_delay=0.5,
        clean_up_tts_audio_files_folder=clean_up,
    )

    # 5 and 10 words at 0.4 s a word (2 s and 4 s), plus 1 s of pauses around each.
    assert info["duration"] == pytest.approx(8, abs=0.3)
    assert info["has_audio"]
    assert (output_directory / "audio-files").exists() == (not clean_up)
    assert (output_directory / "transcript.txt").read_text(encoding="utf-8").count("One two three") == 2


@pytest.mark.parametrize("clean_up", [True, False])
def test_highlighting_the_text_boxes(tmp_path, monkeypatch, clean_up):
    info, output_directory = make_video(
        tmp_path,
        monkeypatch,
        voice=True,
        use_reading_speed_wpm=False,
        use_text_to_speech_azure=True,
        use_minimum_image_duration=False,
        highlight_text_boxes_in_images=True,
        clean_up_images_with_highlighted_text_boxes_folder=clean_up,
    )

    # One highlighted image per line, as long as its voice: 2 s + 4 s.
    assert info["duration"] == pytest.approx(6, abs=0.6)
    highlighted_folder = output_directory / "images-with-highlighted-text-boxes"
    if clean_up:
        assert not highlighted_folder.exists()
    else:
        assert sorted(path.stem for path in highlighted_folder.iterdir()) == ["panel_1-1", "panel_2-1"]


@pytest.mark.parametrize(
    "settings, expected",
    [
        # Reading speed, no voice: each line's image for its words (5 and 10 words at 150 a minute).
        ({"use_reading_speed_wpm": True, "reading_speed_wpm": 150}, 6),
        # A fixed time, no voice: each line's image for that time.
        ({"use_reading_speed_wpm": False, "image_displayed_duration": 2}, 4),
    ],
)
def test_highlighting_without_a_voice(tmp_path, monkeypatch, settings, expected):
    info, output_directory = make_video(
        tmp_path,
        monkeypatch,
        use_text_to_speech_azure=False,
        use_minimum_image_duration=False,
        highlight_text_boxes_in_images=True,
        clean_up_images_with_highlighted_text_boxes_folder=False,
        **settings,
    )

    assert info["duration"] == pytest.approx(expected, abs=0.6)
    assert not info["has_audio"]
    assert sorted(path.stem for path in (output_directory / "images-with-highlighted-text-boxes").iterdir()) == ["panel_1-1", "panel_2-1"]


@pytest.mark.parametrize(
    "settings, expected",
    [
        # 0 or less for the time per image uses the default, 5 s (it used to stop the video).
        ({**FIXED_TIME, "image_displayed_duration": 0}, 10),
        ({**FIXED_TIME, "image_displayed_duration": -2}, 10),
        # A negative pause counts as none, so the voice is never cut off (2 s + 4 s of voice).
        ({"use_reading_speed_wpm": False, "use_text_to_speech_azure": True, "use_minimum_image_duration": False, "image_pre_tts_audio_delay": -1, "image_post_tts_audio_delay": -1}, 6),
    ],
)
def test_time_settings_below_zero(tmp_path, monkeypatch, settings, expected):
    info, _ = make_video(tmp_path, monkeypatch, voice=settings.get("use_text_to_speech_azure", False), **settings)

    assert info["duration"] == pytest.approx(expected, abs=0.3)


def test_a_panel_without_text_shows_for_the_minimum_time(tmp_path, monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "PANEL_TEXT", ["One two three four five.", ""])
    info, _ = make_video(
        tmp_path,
        monkeypatch,
        voice=True,
        use_reading_speed_wpm=False,
        use_text_to_speech_azure=True,
        use_minimum_image_duration=True,
        minimum_image_duration=3,
    )

    # 5 words of voice (2 s, under the minimum: 3 s), then the panel without text: 3 s.
    assert info["duration"] == pytest.approx(6, abs=0.3)


def test_the_text_box_look(tmp_path):
    from DrawBoxCoords import DrawBoxCoords

    image_path = tmp_path / "panel_1.png"
    Image.new("RGB", (400, 400), "white").save(image_path)
    settings = make_settings(
        images_to_video_text_box_border_color="#0000ff",
        images_to_video_text_box_border_color_opacity=1,
        images_to_video_text_box_border_width=6,
        images_to_video_text_box_padding=20,
        images_to_video_text_box_background_color="#00ff00",
        images_to_video_text_box_background_color_opacity=0.5,
        images_to_video_text_box_border_style="solid",
    )

    DrawBoxCoords(settings).draw_box_coords_box_list([[100, 100, 300, 300]], str(image_path), str(tmp_path / "out"))

    image = Image.open(next((tmp_path / "out").iterdir())).convert("RGB")
    # The border is 20 px outside the text box (the padding), in blue.
    border = [image.getpixel((x, 200)) for x in range(70, 90)]
    assert any(blue > 200 and red < 80 and green < 80 for red, green, blue in border)
    # Inside, white is half covered by green.
    red, green, blue = image.getpixel((200, 200))
    assert green > 200 and 100 < red < 160 and 100 < blue < 160
    # Outside, the image is untouched.
    assert image.getpixel((20, 200)) == (255, 255, 255)


@pytest.mark.parametrize("border_style", ["solid", "dotted", "dashed", "dashdot"])
def test_every_border_style_draws_a_border(tmp_path, border_style):
    from DrawBoxCoords import DrawBoxCoords

    image_path = tmp_path / "panel_1.png"
    Image.new("RGB", (400, 400), "white").save(image_path)
    settings = make_settings(
        images_to_video_text_box_border_color="#0000ff",
        images_to_video_text_box_border_width=4,
        images_to_video_text_box_padding=0,
        images_to_video_text_box_background_color_opacity=0,
        images_to_video_text_box_border_style=border_style,
    )

    DrawBoxCoords(settings).draw_box_coords_box_list([[100, 100, 300, 300]], str(image_path), str(tmp_path / "out"))

    image = Image.open(next((tmp_path / "out").iterdir())).convert("RGB")
    # Along the top edge: how much of it is blue. Solid all of it, the others leave gaps.
    top_edge = [max((image.getpixel((x, y)) for y in range(96, 105)), key=lambda pixel: pixel[2] - pixel[0]) for x in range(110, 290)]
    blue_share = sum(blue > 150 and red < 120 for red, green, blue in top_edge) / len(top_edge)
    if border_style == "solid":
        assert blue_share > 0.95
    else:
        assert 0.1 < blue_share < 0.95


def test_the_settings_are_read_from_the_saved_settings():
    video_creator = VideoCreatorFromImages(
        make_settings(
            video_height="720",
            video_aspect_ratio="9:16",
            image_displayed_duration="4",
            reading_speed_wpm="200",
            minimum_image_duration="2",
            image_pre_tts_audio_delay="0.5",
            image_post_tts_audio_delay="1",
            reading_direction="rtl",
        )
    )

    assert video_creator.get_video_frame_size() == (720, 1280)
    assert (video_creator.image_displayed_duration, video_creator.reading_speed_wpm, video_creator.minimum_image_duration) == (4, 200, 2)
    assert (video_creator.image_pre_tts_audio_delay, video_creator.image_post_tts_audio_delay) == (0.5, 1)
    assert video_creator.speech_text_parser.reading_direction == "rtl"


def test_a_pause_between_the_lines_of_a_panel(tmp_path, monkeypatch):
    # "Pause between lines" (azure_break_time_between_text): silence between each line, for Edge too.
    from TextToSpeech import TextToSpeech

    tts = TextToSpeech({"azure_break_time_between_text": "1"})

    def say(text, output_file):
        AudioClip(lambda t: 0.1 * numpy.sin(2 * numpy.pi * 440 * t), duration=1, fps=22050).write_audiofile(output_file, logger=None)

    monkeypatch.setattr(tts, "generate_audio_for_text", say)
    output_file = str(tmp_path / "panel_1.mp3")

    tts.generate_audio(["First line.", "Second line."], output_file)

    with AudioFileClip(output_file) as audio:
        # 1 s + 1 s of pause + 1 s.
        assert audio.duration == pytest.approx(3, abs=0.2)
    # The pieces are deleted.
    assert os.listdir(tmp_path) == ["panel_1.mp3"]
