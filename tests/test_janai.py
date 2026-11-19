import os
import zipfile

import numpy
import pytest
from PIL import Image

import janai


def upscale_tile_like_nearest(tile):
    """
    A fake model: makes the tile 2x bigger by repeating each pixel, so the right result is easy to know.
    """
    return tile.repeat(2, axis=1).repeat(2, axis=2)


@pytest.mark.parametrize("fixed_tile_size", [True, False])
def test_tiles_are_put_back_together_without_seams(fixed_tile_size):
    image = numpy.random.default_rng(0).random((3, 70, 101), dtype=numpy.float32)

    result = janai.upscale_in_tiles(upscale_tile_like_nearest, image, 2, 48, fixed_tile_size)

    assert numpy.array_equal(result, upscale_tile_like_nearest(image))


def test_the_neural_engine_always_gets_the_same_tile_size():
    sizes = set()

    def upscale_tile(tile):
        sizes.add(tile.shape)
        return upscale_tile_like_nearest(tile)

    # Smaller than one tile in one direction and bigger in the other.
    janai.upscale_in_tiles(upscale_tile, numpy.zeros((3, 20, 130), dtype=numpy.float32), 2, 48, True)

    assert sizes == {(3, 48, 48)}


def test_color_is_told_apart_from_black_and_white_with_a_slight_tint():
    tinted_gray = Image.new("RGB", (50, 50), (120, 118, 125))
    colorful = Image.new("RGB", (50, 50), (40, 140, 230))

    assert not janai.is_color_image(tinted_gray)
    assert not janai.is_color_image(Image.new("L", (50, 50), 128))
    assert janai.is_color_image(colorful)


def test_the_manga_model_is_picked_by_the_page_height_saved_in_the_panel(tmp_path):
    panel = tmp_path / "panel_1.png"
    Image.new("RGB", (300, 200)).save(panel, pnginfo=janai.get_page_height_info(1600))
    page = tmp_path / "page.png"
    Image.new("RGB", (900, 1250)).save(page)

    assert janai.get_page_height(Image.open(panel)) == 1600
    # A whole page (or a panel from an older version) uses its own height.
    assert janai.get_page_height(Image.open(page)) == 1250
    assert janai.get_manga_model_height(1250) == 1200
    assert janai.get_manga_model_height(1600) == 1600
    assert janai.get_manga_model_height(5000) == 2048


def test_panel_by_panel_saves_the_page_height_in_each_panel(tmp_path):
    from magi import Magi

    page = numpy.zeros((1600, 1000, 3), dtype=numpy.uint8)
    Magi().save_cropped_panels(page, {"panels": [[0, 0, 500, 400]]}, str(tmp_path))

    assert janai.get_page_height(Image.open(tmp_path / "panel_1.png")) == 1600


def use_fake_models(monkeypatch):
    used = []
    monkeypatch.setattr(janai, "download_model_file", lambda file_name, zip_url, report=print: file_name)

    def fake_get_upscaler(model_path, use_neural_engine, report=print):
        used.append((model_path, use_neural_engine))
        return upscale_tile_like_nearest

    monkeypatch.setattr(janai, "get_upscaler", fake_get_upscaler)
    return used


def test_black_and_white_uses_mangajanai_on_the_neural_engine_and_stays_grayscale(tmp_path, monkeypatch):
    used = use_fake_models(monkeypatch)
    panel = tmp_path / "panel_1.png"
    Image.new("RGB", (30, 20), (90, 90, 92)).save(panel, pnginfo=janai.get_page_height_info(1600))

    janai.upscale_image_with_janai(str(panel), str(tmp_path / "out.png"), 2)

    assert used == [(janai.MANGA_MODEL_FILES[1600], True)]
    output = Image.open(tmp_path / "out.png")
    assert output.size == (60, 40) and output.mode == "L"


def test_color_uses_illustrationjanai_and_4x_is_two_passes(tmp_path, monkeypatch):
    used = use_fake_models(monkeypatch)
    panel = tmp_path / "panel_1.png"
    Image.new("RGB", (30, 20), (40, 140, 230)).save(panel)

    janai.upscale_image_with_janai(str(panel), str(tmp_path / "out.webp"), 4)

    assert used == [(janai.COLOR_MODEL_FILE, False)] * 2
    output = Image.open(tmp_path / "out.webp")
    assert output.size == (120, 80) and output.mode == "RGB"


def test_a_4x_black_and_white_upscale_uses_the_model_for_the_bigger_page_the_second_time(tmp_path, monkeypatch):
    used = use_fake_models(monkeypatch)
    panel = tmp_path / "panel_1.png"
    Image.new("L", (30, 20), 128).save(panel, pnginfo=janai.get_page_height_info(1200))

    janai.upscale_image_with_janai(str(panel), str(tmp_path / "out.png"), 4)

    assert [model for model, _ in used] == [janai.MANGA_MODEL_FILES[1200], janai.MANGA_MODEL_FILES[2048]]


def test_models_are_downloaded_once_keeping_only_the_2x_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(janai, "MODELS_FOLDER", str(tmp_path / "models"))
    zip_path = tmp_path / "models.zip"
    with zipfile.ZipFile(zip_path, "w") as models_zip:
        models_zip.writestr("folder/2x_Model_A.pth", b"a")
        models_zip.writestr("folder/2x_Model_B.safetensors", b"b")
        models_zip.writestr("folder/4x_Model_C.pth", b"c")
    downloads = []
    original_urlretrieve = janai.urllib.request.urlretrieve
    monkeypatch.setattr(
        janai.urllib.request,
        "urlretrieve",
        lambda url, path: downloads.append(url) or original_urlretrieve(zip_path.as_uri(), path),
    )

    path = janai.download_model_file("2x_Model_A.pth", "https://example.com/models.zip", report=lambda text: None)
    janai.download_model_file("2x_Model_B.safetensors", "https://example.com/models.zip", report=lambda text: None)

    assert open(path, "rb").read() == b"a"
    assert sorted(os.listdir(tmp_path / "models")) == ["2x_Model_A.pth", "2x_Model_B.safetensors"]
    assert downloads == ["https://example.com/models.zip"]
