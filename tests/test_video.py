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

    # A direction saved next to the images (used by "Automatic") changes too.
    (images / "reading-direction.txt").write_text("4koma")
    video_creator.get_essential_text_and_magi_data(str(images), str(output), image_count=2)
    assert len(runs) == 4


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
        get_durations(video_creator, images, tmp_path, [[f"line {number}"] for number in range(40)])

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


def test_writing_the_video_shows_how_many_frames_are_written(monkeypatch):
    import VideoCreatorFromImages as video_module

    reported = []
    monkeypatch.setattr(video_module, "report_progress", lambda **fields: reported.append(fields))
    logger = video_module.VideoWritingProgress()

    # What MoviePy does while it writes the frames.
    for _ in logger.iter_bar(frame_index=range(3)):
        pass

    # Counting up from 0, never shown full before the frames are written.
    assert [fields["pages_done"] for fields in reported] == [0, 1, 2, 3]
    assert reported[-1] == {"pages_done": 3, "pages_total": 3, "unit": "frames", "detail": "Writing the video file"}


def test_a_bubble_in_two_panels_is_only_said_once():
    from VideoCreatorFromImages import remove_lines_said_in_the_image_before

    text = [
        ["Stop the print!", "A call will go through to you."],
        # The same bubble, kept whole in the next panel too.
        ["A call will go  through to you.", "Got it!"],
        # Short lines are often really said again, by someone else.
        ["Got it!", "We made it just in time, huh?"],
        ["We made it just in time, huh?"],
        # Not right after it, so it's said again.
        ["A call will go through to you."],
    ]

    assert remove_lines_said_in_the_image_before(text) == [
        ["Stop the print!", "A call will go through to you."],
        ["Got it!"],
        ["Got it!", "We made it just in time, huh?"],
        [],
        ["A call will go through to you."],
    ]


def test_a_bubble_in_two_panels_is_only_in_the_transcript_once(tmp_path):
    from VideoCreatorFromImages import VideoCreatorFromImages

    late = "Your report is late!"
    nonsense = "Don't give me that early morning nonsense!"
    VideoCreatorFromImages.save_essential_text_to_transcript(None, [[late, nonsense], [nonsense, "No!"], ["No!"]], str(tmp_path))

    # Shachou ch. 3, page 1: Magi's boxes for two panels overlap, so both have the same bubbles. A short line is kept: it's often really said again.
    assert (tmp_path / "transcript.txt").read_text().split("\n") == [
        late, nonsense, "------ new image ------",
        "No!", "------ new image ------",
        "No!", "------ new image ------",
        "",
    ]


def test_with_highlighting_a_repeated_bubble_gets_no_frame_and_no_audio():
    from VideoCreatorFromImages import mark_repeated_lines_as_not_dialogue

    late = "Your report is late!"
    nonsense = "Don't give me that early morning nonsense!"
    magi_data = [
        {"texts": [[0, 0, 1, 1]] * 3, "ocr": [late, nonsense, "CHUN"], "is_essential_text": [True, True, False]},
        # The next panel has the same two bubbles, a short line, and its own line.
        {"texts": [[0, 0, 1, 1]] * 4, "ocr": [late, nonsense, "No!", "It's been half a year"], "is_essential_text": [True, True, True, True]},
    ]

    marked = mark_repeated_lines_as_not_dialogue(magi_data)

    # Marked as not dialogue, like a sound effect: no highlighted frame and no audio for them.
    assert marked[0]["is_essential_text"] == [True, True, False]
    assert marked[1]["is_essential_text"] == [False, False, True, True]
    # Magi's saved results aren't changed.
    assert magi_data[1]["is_essential_text"] == [True, True, True, True]


def test_a_bubble_cut_off_by_a_panel_s_edge_is_only_read_where_it_s_whole():
    from VideoCreatorFromImages import mark_repeated_lines_as_not_dialogue

    # Shachou to Sake to Hoshi ch. 8, panels 17 and 18 (Magi's real boxes and reading, after a 2x upscale).
    magi_data = [
        {"texts": [[3, 90, 147, 325], [200, 900, 260, 980]], "ocr": ["me to think it...", "Hah..."], "is_essential_text": [True, True]},
        {"texts": [[1370, 85, 1599, 314]], "ocr": ["come to think of it..."], "is_essential_text": [True]},
    ]
    sizes = [(434, 1108), (1614, 1116)]

    marked = mark_repeated_lines_as_not_dialogue(magi_data, sizes)

    assert marked[0]["is_essential_text"] == [False, True]
    assert marked[1]["is_essential_text"] == [True]

    # Cut off, but not whole in a panel next to it: kept, so it's still read once.
    alone = mark_repeated_lines_as_not_dialogue([magi_data[0]], [sizes[0]])
    assert alone[0]["is_essential_text"] == [True, True]

    # Read exactly, even though it's cut off: the whole copy next door is still read (not taken for a repeat).
    exact = [
        {"texts": [[100, 900, 300, 1108]], "ocr": ["Come to think of it, where is he?"], "is_essential_text": [True]},
        {"texts": [[100, 100, 300, 300]], "ocr": ["Come to think of it, where is he?"], "is_essential_text": [True]},
    ]
    assert [image["is_essential_text"] for image in mark_repeated_lines_as_not_dialogue(exact, [(434, 1108), (434, 1108)])] == [[False], [True]]
    # The other way around: whole first, cut off in the next image.
    assert [image["is_essential_text"] for image in mark_repeated_lines_as_not_dialogue(exact[::-1], [(434, 1108), (434, 1108)])] == [[True], [False]]
    # Not alike enough, or too short: kept.
    different = [dict(exact[0], ocr=["Where did everyone go today?"]), exact[1]]
    assert [image["is_essential_text"] for image in mark_repeated_lines_as_not_dialogue(different, [(434, 1108), (434, 1108)])] == [[True], [True]]
    short = [dict(exact[0], ocr=["No way!"]), dict(exact[1], ocr=["No way..."])]
    assert [image["is_essential_text"] for image in mark_repeated_lines_as_not_dialogue(short, [(434, 1108), (434, 1108)])] == [[True], [True]]
