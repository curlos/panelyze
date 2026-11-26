"""
How long each image stays on screen in Images To Video: a fixed time, the reading speed (words per minute), or the voice-over's length, with a minimum time and pauses before and after the voice. All offline: no Magi, no voice service.
"""

import os

import numpy
import pytest
from moviepy import AudioClip, AudioFileClip
from PIL import Image

from SpeechTextParser import SpeechTextParser
from VideoCreatorFromImages import VideoCreatorFromImages


def test_reading_speed_gives_each_image_time_for_its_words():
    # 150 words a minute is 2.5 words a second.
    durations = SpeechTextParser().get_images_duration_based_on_wpm(
        None,
        150,
        essential_text_in_images_matrix=[["one two three"], [], ["a b", "c d e f g"]],
    )

    assert durations == pytest.approx([1.2, 0, 2.8])


def test_reading_speed_line_by_line_gives_each_line_its_own_time():
    # With highlighting, each line gets its own image; an image without text still shows for a second.
    durations = SpeechTextParser().get_images_duration_based_on_wpm(
        None,
        150,
        one_text_str_at_a_time=True,
        essential_text_in_images_matrix=[["one two three", "four five"], []],
    )

    assert durations == pytest.approx([1.2, 0.8, 1])


def make_video_creator(**settings):
    video_creator = VideoCreatorFromImages({})
    video_creator.use_text_to_speech_azure = False
    video_creator.use_reading_speed_wpm = False
    video_creator.image_displayed_duration = 5
    video_creator.use_minimum_image_duration = False
    video_creator.minimum_image_duration = 3
    for name, value in settings.items():
        setattr(video_creator, name, value)
    return video_creator


@pytest.mark.parametrize(
    "settings, expected",
    [
        # A fixed time for every image.
        ({}, 5),
        # The reading speed's time, or the voice-over's length ("use_text_to_speech_azure" means text-to-speech with either engine).
        ({"use_reading_speed_wpm": True}, 1.2),
        ({"use_text_to_speech_azure": True}, 4.5),
        # The voice-over wins over the reading speed.
        ({"use_text_to_speech_azure": True, "use_reading_speed_wpm": True}, 4.5),
        # The minimum time: for short or empty images, never for longer ones.
        ({"use_reading_speed_wpm": True, "use_minimum_image_duration": True}, 3),
        ({"use_text_to_speech_azure": True, "use_minimum_image_duration": True}, 4.5),
        ({"use_minimum_image_duration": True, "image_displayed_duration": 1}, 3),
    ],
)
def test_how_long_an_image_is_shown(settings, expected):
    video_creator = make_video_creator(**settings)

    assert video_creator.get_img_duration([1.2], [4.5], 0) == pytest.approx(expected)


def save_images(folder, names):
    os.makedirs(folder, exist_ok=True)
    paths = []
    for name in names:
        path = os.path.join(folder, f"{name}.png")
        Image.new("RGB", (40, 60), "white").save(path)
        paths.append(path)
    return paths


def save_voice_over(output_directory, name, seconds):
    """
    A quiet tone in an mp3, standing in for a voice-over line (pure silence comes back from the mp3 as 0.05 s long). Returns its real length (mp3s are a little longer than asked).
    """
    path = os.path.join(output_directory, "audio-files", f"{name}.mp3")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    AudioClip(
        lambda t: 0.1 * numpy.sin(2 * numpy.pi * 440 * t), duration=seconds, fps=44100
    ).write_audiofile(path, logger=None)
    with AudioFileClip(path) as clip:
        return clip.duration


def get_clip_durations(
    video_creator, images, highlighted_folder, durations_by_tts, output_directory
):
    try:
        clips = video_creator.get_clips(
            images, highlighted_folder, [], durations_by_tts, output_directory
        )
        return [clip.duration for clip in clips], [
            clip.audio is not None for clip in clips
        ]
    finally:
        video_creator.close_audio_clips()


def test_the_pauses_before_and_after_the_voice_are_added_to_its_image(tmp_path):
    output_directory = str(tmp_path / "video")
    images = save_images(str(tmp_path / "panels"), ["panel_1", "panel_2"])
    voice_length = save_voice_over(output_directory, "panel_1", 4)
    video_creator = make_video_creator(
        use_text_to_speech_azure=True,
        use_minimum_image_duration=True,
        image_pre_tts_audio_delay=0.5,
        image_post_tts_audio_delay=1,
    )

    durations, has_audio = get_clip_durations(
        video_creator, images, None, [voice_length, 0], output_directory
    )

    # panel_1: its voice-over, plus 0.5 s before and 1 s after. panel_2 has no text: the minimum time, no voice.
    assert durations == pytest.approx([voice_length + 1.5, 3])
    assert has_audio == [True, False]


def test_an_image_is_never_cut_shorter_than_its_voice_over(tmp_path):
    output_directory = str(tmp_path / "video")
    images = save_images(str(tmp_path / "panels"), ["panel_1"])
    voice_length = save_voice_over(output_directory, "panel_1", 2)
    # The voice-over is 2 s, the minimum time 3 s: the image stays 3 s.
    video_creator = make_video_creator(
        use_text_to_speech_azure=True, use_minimum_image_duration=True
    )

    durations, _ = get_clip_durations(
        video_creator, images, None, [voice_length], output_directory
    )

    assert durations == pytest.approx([3])


def test_with_highlighting_the_pauses_go_around_each_panel_not_each_line(tmp_path):
    # Each line gets its own highlighted image ("panel_1-1", "panel_1-2", ...) that lasts as long as its line.
    output_directory = str(tmp_path / "video")
    highlighted_folder = str(tmp_path / "highlighted")
    names = ["panel_1-1", "panel_1-2", "panel_2-1"]
    save_images(highlighted_folder, names)
    lengths = [save_voice_over(output_directory, name, 1) for name in names]
    video_creator = make_video_creator(
        use_text_to_speech_azure=True,
        highlight_text_boxes_in_images=True,
        image_pre_tts_audio_delay=0.5,
        image_post_tts_audio_delay=1,
    )

    durations, _ = get_clip_durations(
        video_creator, [], highlighted_folder, lengths, output_directory
    )

    # The pause before only on a panel's first line, the pause after only on its last line.
    assert durations == pytest.approx(
        [lengths[0] + 0.5, lengths[1] + 1, lengths[2] + 0.5 + 1]
    )
