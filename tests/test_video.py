import os
import edge_tts
from PIL import Image

from DrawBoxCoords import DrawBoxCoords
from TextToSpeech import TextToSpeech
from VideoCreatorFromImages import VideoCreatorFromImages


def test_creating_the_video_creator_makes_no_network_calls(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Should not fetch voices when the class is created")

    monkeypatch.setattr(edge_tts, "list_voices", fail)

    TextToSpeech({})
    VideoCreatorFromImages({})


def test_every_panel_fits_in_the_same_16_9_frame(tmp_path):
    video_creator = VideoCreatorFromImages({"video_height": "720"})
    video_creator.initialize_flet_client_storage_values({"video_height": "720"})

    wide_image = tmp_path / "wide.png"
    tall_image = tmp_path / "tall.png"
    Image.new("RGB", (4000, 500), "white").save(wide_image)
    Image.new("RGB", (300, 2000), "white").save(tall_image)

    for image_path in [wide_image, tall_image]:
        clip = video_creator.get_image_clip_fit_to_video_frame(str(image_path))
        assert tuple(clip.size) == (1280, 720)
        assert clip.with_duration(1).get_frame(0).shape == (720, 1280, 3)


import pytest


@pytest.mark.parametrize(
    "aspect_ratio, expected_size",
    [("16:9", (1920, 1080)), ("9:16", (1080, 1920)), ("1:1", (1080, 1080))],
)
def test_video_shape_uses_resolution_as_the_shorter_side(aspect_ratio, expected_size):
    settings = {"video_height": "1080", "video_aspect_ratio": aspect_ratio}
    video_creator = VideoCreatorFromImages(settings)

    assert video_creator.get_video_frame_size() == expected_size


def test_draw_box_coords_works_without_saved_settings_and_keeps_resolution(tmp_path):
    # Empty settings used to crash with float(None).
    draw_box_coords = DrawBoxCoords({})

    image_path = tmp_path / "panel_1.png"
    Image.new("RGB", (1234, 2000), "white").save(image_path)

    output_folder = tmp_path / "highlighted"
    draw_box_coords.draw_box_coords_box_list(
        [[100, 100, 400, 300]], str(image_path), str(output_folder)
    )

    output_images = list(output_folder.iterdir())
    assert len(output_images) == 1
    assert Image.open(output_images[0]).size == (1234, 2000)


def write_transcript(directory, text):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "transcript.txt").write_text(text)


def test_transcript_skips_blank_lines(tmp_path):
    write_transcript(tmp_path, "Hello\n\n   \n------ new image ------\n------ new image ------\n")

    video_creator = VideoCreatorFromImages({})

    assert video_creator.get_essential_text_from_transcript(str(tmp_path)) == [
        ["Hello"],
        [],
    ]


def test_transcript_that_does_not_match_the_images_is_not_used(tmp_path, monkeypatch):
    # The transcript has 2 images worth of text but the chapter now has 3 images.
    write_transcript(tmp_path, "A\n------ new image ------\nB\n------ new image ------\n")

    video_creator = VideoCreatorFromImages({})
    monkeypatch.setattr(
        video_creator.speech_text_parser,
        "get_essential_text_list_in_images",
        lambda image_folder: [["from magi"], [], []],
    )

    images = tmp_path / "images"
    images.mkdir()

    text_matrix, _ = video_creator.get_essential_text_and_magi_data(
        str(images), str(tmp_path), image_count=3
    )

    assert text_matrix == [["from magi"], [], []]


def get_video_creator_with_fake_magi(monkeypatch, highlight=True):
    """
    A video creator whose "Magi" gives fixed results for 2 images and counts how many times it's asked to run.
    """
    from SpeechTextParser import SpeechTextParser

    runs = []
    magi_results = [
        {"texts": [[0, 0, 5, 5]], "ocr": ["Hello there."], "is_essential_text": [True]},
        {"texts": [[1, 1, 6, 6], [2, 2, 7, 7]], "ocr": ["BOOM", "Hi!"], "is_essential_text": [False, True]},
    ]

    class FakeMagi:
        def get_data_from_images(self, input_directory, reading_direction="rtl"):
            runs.append(reading_direction)
            return magi_results

    monkeypatch.setattr(SpeechTextParser, "magi", property(lambda self: FakeMagi()))
    video_creator = VideoCreatorFromImages({})
    video_creator.highlight_text_boxes_in_images = highlight
    return video_creator, runs


def make_images(tmp_path, sizes=(10, 20)):
    images = tmp_path / "images"
    images.mkdir(exist_ok=True)
    for number, size in enumerate(sizes, start=1):
        (images / f"panel_{number}.png").write_bytes(b"x" * size)
    return images


def test_magi_only_runs_once_for_the_same_images_even_when_highlighting(tmp_path, monkeypatch):
    video_creator, runs = get_video_creator_with_fake_magi(monkeypatch)
    images = make_images(tmp_path)
    output = tmp_path / "out"

    first_text, first_data = video_creator.get_essential_text_and_magi_data(str(images), str(output), image_count=2)
    # A transcript now exists, which highlighting doesn't use. The saved Magi results are used instead.
    second_text, second_data = video_creator.get_essential_text_and_magi_data(str(images), str(output), image_count=2)

    assert len(runs) == 1
    assert first_text == second_text == [["Hello there."], ["Hi!"]]
    assert first_data == second_data
    assert (output / "magi-data.json").exists()


def test_magi_runs_again_when_the_images_or_reading_direction_change(tmp_path, monkeypatch):
    video_creator, runs = get_video_creator_with_fake_magi(monkeypatch)
    images = make_images(tmp_path)
    output = tmp_path / "out"
    video_creator.get_essential_text_and_magi_data(str(images), str(output), image_count=2)

    make_images(tmp_path, sizes=(10, 21))
    video_creator.get_essential_text_and_magi_data(str(images), str(output), image_count=2)
    assert len(runs) == 2

    video_creator.speech_text_parser.reading_direction = "ltr"
    video_creator.get_essential_text_and_magi_data(str(images), str(output), image_count=2)
    assert runs == ["rtl", "rtl", "ltr"]


def test_a_broken_saved_file_is_ignored(tmp_path, monkeypatch):
    video_creator, runs = get_video_creator_with_fake_magi(monkeypatch)
    images = make_images(tmp_path)
    output = tmp_path / "out"
    output.mkdir()
    (output / "magi-data.json").write_text("{not json")

    video_creator.get_essential_text_and_magi_data(str(images), str(output), image_count=2)

    assert len(runs) == 1
    assert not (output / "magi-data.json.tmp").exists()


def test_without_highlighting_the_saved_results_also_save_reading_the_text(tmp_path, monkeypatch):
    video_creator, runs = get_video_creator_with_fake_magi(monkeypatch, highlight=False)
    video_creator.use_reading_speed_wpm = True
    images = make_images(tmp_path)
    output = tmp_path / "out"

    video_creator.get_essential_text_and_magi_data(str(images), str(output), image_count=2)
    (output / "transcript.txt").unlink()
    text, _ = video_creator.get_essential_text_and_magi_data(str(images), str(output), image_count=2)

    assert len(runs) == 1
    assert text == [["Hello there."], ["Hi!"]]


def test_numpy_numbers_can_be_saved(tmp_path):
    import numpy

    from VideoCreatorFromImages import get_json_value

    assert get_json_value(numpy.int64(3)) == 3
    assert get_json_value(numpy.array([1.5, 2.5])) == [1.5, 2.5]


def test_one_voice_over_line_failing_is_skipped_but_several_in_a_row_stop_the_video(tmp_path):
    video_creator = VideoCreatorFromImages({})
    attempts = []

    def fake_generate_audio(text_list, output_file):
        attempts.append(text_list)
        if text_list != ["fine"]:
            raise RuntimeError("No audio was received.")

    video_creator.tts.generate_audio = fake_generate_audio

    video_creator.generate_voice_over(["bad"], str(tmp_path / "a.mp3"))
    video_creator.generate_voice_over(["fine"], str(tmp_path / "b.mp3"))
    # A success in between starts the count again.
    video_creator.generate_voice_over(["bad"], str(tmp_path / "c.mp3"))
    video_creator.generate_voice_over(["bad"], str(tmp_path / "d.mp3"))

    try:
        video_creator.generate_voice_over(["bad"], str(tmp_path / "e.mp3"))
        raise AssertionError("the third failure in a row should stop the video")
    except RuntimeError as error:
        assert "No audio was received" in str(error)


def make_voice_over_video_creator(tmp_path, monkeypatch, highlight=False, fail=lambda text_list: False):
    """
    A video creator whose voice-over "says" each line by writing a file, and whose audio length is the number of words.
    """
    import time

    import VideoCreatorFromImages as module

    video_creator = VideoCreatorFromImages({})
    video_creator.highlight_text_boxes_in_images = highlight
    spoken = []

    def fake_generate_audio(text_list, output_file):
        # The first line is the slowest, so the lines finish out of order.
        time.sleep(0.05 if text_list == ["one two"] else 0)
        spoken.append(text_list)
        if fail(text_list):
            raise RuntimeError("No audio was received.")
        with open(output_file, "w") as file:
            file.write(" ".join(text_list))

    video_creator.tts.generate_audio = fake_generate_audio
    monkeypatch.setattr(module, "get_audio_duration", lambda path: len(open(path).read().split()))
    images = [str(tmp_path / f"panel_{number}.png") for number in (1, 2, 3)]
    return video_creator, images, spoken


def get_durations(video_creator, images, tmp_path, text_matrix):
    return video_creator.get_images_duration_based_on_tts(
        images, str(tmp_path / "highlighted"), str(tmp_path / "audio"), text_matrix, None
    )


def test_voice_over_lines_are_made_at_the_same_time_but_the_durations_stay_in_order(tmp_path, monkeypatch):
    video_creator, images, spoken = make_voice_over_video_creator(tmp_path, monkeypatch)

    durations = get_durations(video_creator, images, tmp_path, [["one two"], [], ["three"]])

    # The image without text is shown for 1 second.
    assert durations == [2, 1, 1]
    assert sorted(spoken) == [["one two"], ["three"]]


def test_with_highlighting_each_line_gets_its_own_voice_over_in_order(tmp_path, monkeypatch):
    video_creator, images, _ = make_voice_over_video_creator(tmp_path, monkeypatch, highlight=True)
    # Drawing the highlighted boxes isn't what's tested here.
    video_creator.draw_boxes_with_text_and_magi_data = lambda *args, **kwargs: None

    durations = get_durations(video_creator, images, tmp_path, [["one two", "a b c"], [], ["x"]])

    assert durations == [2, 3, 1, 1]
    assert sorted(os.listdir(tmp_path / "audio")) == ["panel_1-1.mp3", "panel_1-2.mp3", "panel_3-1.mp3"]


def test_a_line_that_fails_gets_no_voice_but_the_video_goes_on(tmp_path, monkeypatch):
    video_creator, images, _ = make_voice_over_video_creator(
        tmp_path, monkeypatch, fail=lambda text_list: text_list == ["bad"]
    )

    assert get_durations(video_creator, images, tmp_path, [["one two"], ["bad"], ["three"]]) == [2, 1, 1]


def test_when_the_voice_over_stops_the_waiting_lines_are_not_tried(tmp_path, monkeypatch):
    video_creator, _, spoken = make_voice_over_video_creator(tmp_path, monkeypatch, fail=lambda text_list: True)
    images = [str(tmp_path / f"panel_{number}.png") for number in range(1, 41)]

    with pytest.raises(RuntimeError, match="No audio was received"):
        get_durations(video_creator, images, tmp_path, [["line"]] * 40)

    assert len(spoken) < 40


def write_panel_text(images, lines):
    import json

    (images / "panel-text.json").write_text(json.dumps(lines))


def test_the_text_panel_by_panel_read_is_used_instead_of_running_magi(tmp_path, monkeypatch):
    video_creator, runs = get_video_creator_with_fake_magi(monkeypatch, highlight=False)
    images = make_images(tmp_path)
    write_panel_text(images, [["From the page."], []])

    text, _ = video_creator.get_essential_text_and_magi_data(str(images), str(tmp_path / "out"), image_count=2)

    assert runs == []
    assert text == [["From the page."], []]


def test_text_for_a_different_number_of_images_is_not_used(tmp_path, monkeypatch):
    video_creator, runs = get_video_creator_with_fake_magi(monkeypatch, highlight=False)
    images = make_images(tmp_path)
    # E.g. an image failed to upscale.
    write_panel_text(images, [["One."], ["Two."], ["Three."]])

    text, _ = video_creator.get_essential_text_and_magi_data(str(images), str(tmp_path / "out"), image_count=2)

    assert len(runs) == 1
    assert text == [["Hello there."], ["Hi!"]]


def test_highlighting_still_reads_the_panels_because_it_needs_where_the_text_is(tmp_path, monkeypatch):
    video_creator, runs = get_video_creator_with_fake_magi(monkeypatch, highlight=True)
    images = make_images(tmp_path)
    write_panel_text(images, [["From the page."], []])

    video_creator.get_essential_text_and_magi_data(str(images), str(tmp_path / "out"), image_count=2)

    assert len(runs) == 1
