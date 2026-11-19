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

    text_matrix, _ = video_creator.get_essential_text_and_magi_data(
        "unused", str(tmp_path), image_count=3
    )

    assert text_matrix == [["from magi"], [], []]
