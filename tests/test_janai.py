import os
import shutil
import urllib.error
import zipfile

import numpy
import pytest
from PIL import Image

from gui_classes.ProgressPanel import get_download_detail
import janai


def upscale_tile_like_nearest(tile):
    """
    A fake model: makes the tile 2x bigger by repeating each pixel, so the right result is easy to know.
    """
    return tile.repeat(2, axis=1).repeat(2, axis=2)


@pytest.mark.parametrize(
    "hip_version, expected_fixed_tile_size", [("10.3.0", True), (None, False)]
)
def test_pytorch_tiles_are_all_the_same_size_only_with_amd_s_pytorch(
    monkeypatch, hip_version, expected_fixed_tile_size
):
    import torch.version

    # AMD's PyTorch (ROCm) works out each new tile size the first time it sees it, so there it's always 512x512.
    monkeypatch.setattr(torch.version, "hip", hip_version)
    monkeypatch.setattr(janai, "can_use_coreml", lambda: False)
    monkeypatch.setattr(
        janai,
        "get_pytorch_upscale_function",
        lambda model_path: (lambda tile: tile, "cpu"),
    )
    monkeypatch.setattr(janai, "_loaded_upscalers", {})
    calls = []
    monkeypatch.setattr(
        janai,
        "upscale_in_tiles",
        lambda upscale_tile, image, scale, tile_size, fixed_tile_size: calls.append(
            (tile_size, fixed_tile_size)
        ),
    )

    janai.get_upscaler("model.pth", use_neural_engine=False)(numpy.zeros((3, 10, 10)))

    assert calls == [(512, expected_fixed_tile_size)]


def test_the_status_view_shows_where_best_runs(monkeypatch):
    from gui_classes import ProgressPanel

    reported = []
    monkeypatch.setattr(
        ProgressPanel, "report_progress", lambda **fields: reported.append(fields)
    )
    monkeypatch.setattr(janai, "can_use_coreml", lambda: False)
    monkeypatch.setattr(
        janai,
        "get_pytorch_upscale_function",
        lambda model_path: (lambda tile: tile, "cpu"),
    )
    monkeypatch.setattr(janai, "_loaded_upscalers", {})
    monkeypatch.setattr(
        ProgressPanel, "current_progress_panel", ProgressPanel.ProgressPanel()
    )

    # Each time, also once the model is loaded.
    janai.get_upscaler("model.pth", use_neural_engine=False)
    janai.get_upscaler("model.pth", use_neural_engine=False)

    assert [fields for fields in reported if "device" in fields] == [
        {"device": "CPU"},
        {"device": "CPU"},
    ]
    # Loading the model is a step of its own in the Status view, only the first time.
    assert [fields["stage"] for fields in reported if "stages" in fields] == [
        "Loading MangaJaNai into PyTorch"
    ]


def test_on_a_mac_converting_for_core_ml_is_a_step_only_the_first_time(
    monkeypatch, tmp_path
):
    import sys
    import types

    from gui_classes import ProgressPanel

    # A fake Core ML, so this also runs on a computer without it.
    class FakeMLModel:
        def __init__(self, path, compute_units):
            pass

        def predict(self, inputs):
            return {"upscaled": inputs["image"]}

    fake_coremltools = types.SimpleNamespace(
        ComputeUnit=types.SimpleNamespace(ALL="all", CPU_AND_GPU="cpu and gpu"),
        models=types.SimpleNamespace(MLModel=FakeMLModel),
    )
    monkeypatch.setitem(sys.modules, "coremltools", fake_coremltools)
    monkeypatch.setattr(
        janai,
        "convert_to_coreml",
        lambda model_path, coreml_path, report: os.makedirs(coreml_path),
    )
    panel = ProgressPanel.ProgressPanel()
    monkeypatch.setattr(ProgressPanel, "current_progress_panel", panel)
    model_path = str(tmp_path / janai.COLOR_MODEL_FILE)
    details = []
    original_render = panel.render
    monkeypatch.setattr(
        panel, "render", lambda: (details.append(panel.detail), original_render())
    )

    for _ in range(2):
        panel.start("Upscaling images...")
        janai.get_coreml_upscale_function(model_path, False, "IllustrationJaNai")

    # The second time is like opening the app again: the Core ML copy is already saved, so it's only loaded.
    assert panel.stages == (
        "Loading IllustrationJaNai into Core ML",
        "Upscaling images...",
    )
    assert os.path.isdir(
        str(
            tmp_path
            / "2x_IllustrationJaNai_V2standard_FDAT_M_unshuffle_40k-256.mlpackage"
        )
    )
    # What each step does is said under it, and taken away afterwards.
    assert janai.COREML_CONVERT_DETAIL in details
    assert details.count(janai.COREML_LOAD_DETAIL) >= 2
    assert panel.detail is None


def test_when_core_ml_fails_pytorch_is_used_and_the_status_view_goes_on(
    monkeypatch, tmp_path
):
    from gui_classes import ProgressPanel

    def fail(*args):
        raise RuntimeError("Core ML broke")

    monkeypatch.setattr(janai, "can_use_coreml", lambda: True)
    monkeypatch.setattr(janai, "get_coreml_upscale_function", fail)
    monkeypatch.setattr(
        janai,
        "get_pytorch_upscale_function",
        lambda model_path: (upscale_tile_like_nearest, "cpu"),
    )
    monkeypatch.setattr(janai, "_loaded_upscalers", {})
    panel = ProgressPanel.ProgressPanel()
    monkeypatch.setattr(ProgressPanel, "current_progress_panel", panel)
    panel.start("Upscaling images...")
    reported = []

    upscale = janai.get_upscaler(
        str(tmp_path / janai.COLOR_MODEL_FILE), False, report=reported.append
    )

    assert upscale(numpy.zeros((3, 4, 4), numpy.float32)).shape == (3, 8, 8)
    assert "Core ML broke" in reported[0]
    assert panel.stages == (
        "Loading IllustrationJaNai into PyTorch",
        "Upscaling images...",
    )
    assert panel.stage == "Upscaling images..." and panel.detail is None


@pytest.mark.parametrize(
    "width, tiles_across", [(1000, 2), (512, 1), (300, 1), (1100, 3)]
)
def test_no_same_size_tile_is_upscaled_twice(width, tiles_across):
    # 512 px tiles overlapping by 8 px: a 1000 px image is two tiles (0-512 and 488-1000). The second reaches the edge, so it keeps everything to it, and the same tile isn't upscaled again for the last 8 px.
    tiles = []

    def record(tile):
        tiles.append(tile.shape)
        return upscale_tile_like_nearest(tile)

    image = numpy.random.default_rng(0).random((3, width, width), dtype=numpy.float32)
    result = janai.upscale_in_tiles(record, image, 2, 512, fixed_tile_size=True)

    assert len(tiles) == tiles_across**2
    assert set(tiles) == {(3, 512, 512)}
    # Still the whole image, without seams.
    assert numpy.array_equal(result, upscale_tile_like_nearest(image))


@pytest.mark.parametrize("fixed_tile_size", [True, False])
def test_tiles_are_put_back_together_without_seams(fixed_tile_size):
    image = numpy.random.default_rng(0).random((3, 70, 101), dtype=numpy.float32)

    result = janai.upscale_in_tiles(
        upscale_tile_like_nearest, image, 2, 48, fixed_tile_size
    )

    assert numpy.array_equal(result, upscale_tile_like_nearest(image))


def test_the_neural_engine_always_gets_the_same_tile_size():
    sizes = set()

    def upscale_tile(tile):
        sizes.add(tile.shape)
        return upscale_tile_like_nearest(tile)

    # Smaller than one tile in one direction and bigger in the other.
    janai.upscale_in_tiles(
        upscale_tile, numpy.zeros((3, 20, 130), dtype=numpy.float32), 2, 48, True
    )

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
    monkeypatch.setattr(
        janai, "download_model_file", lambda file_name, zip_url, report=print: file_name
    )

    def fake_get_upscaler(model_path, use_neural_engine, report=print):
        used.append((model_path, use_neural_engine))
        return upscale_tile_like_nearest

    monkeypatch.setattr(janai, "get_upscaler", fake_get_upscaler)
    return used


def test_black_and_white_uses_mangajanai_on_the_neural_engine_and_stays_grayscale(
    tmp_path, monkeypatch
):
    used = use_fake_models(monkeypatch)
    panel = tmp_path / "panel_1.png"
    Image.new("RGB", (30, 20), (90, 90, 92)).save(
        panel, pnginfo=janai.get_page_height_info(1600)
    )

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


def test_a_4x_black_and_white_upscale_uses_the_model_for_the_bigger_page_the_second_time(
    tmp_path, monkeypatch
):
    used = use_fake_models(monkeypatch)
    panel = tmp_path / "panel_1.png"
    Image.new("L", (30, 20), 128).save(panel, pnginfo=janai.get_page_height_info(1200))

    janai.upscale_image_with_janai(str(panel), str(tmp_path / "out.png"), 4)

    assert [model for model, _ in used] == [
        janai.MANGA_MODEL_FILES[1200],
        janai.MANGA_MODEL_FILES[2048],
    ]


def test_models_are_downloaded_once_keeping_only_the_2x_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(janai, "MODELS_FOLDER", str(tmp_path / "models"))
    zip_path = tmp_path / "models.zip"
    with zipfile.ZipFile(zip_path, "w") as models_zip:
        models_zip.writestr("folder/2x_Model_A.pth", b"a")
        models_zip.writestr("folder/2x_Model_B.safetensors", b"b")
        models_zip.writestr("folder/4x_Model_C.pth", b"c")
    downloads = []
    monkeypatch.setattr(
        janai,
        "download_file",
        lambda url, path, name=None: (
            downloads.append(url) or shutil.copyfile(zip_path, path)
        ),
    )

    path = janai.download_model_file(
        "2x_Model_A.pth", "https://example.com/models.zip", report=lambda text: None
    )
    janai.download_model_file(
        "2x_Model_B.safetensors",
        "https://example.com/models.zip",
        report=lambda text: None,
    )

    assert open(path, "rb").read() == b"a"
    assert sorted(os.listdir(tmp_path / "models")) == [
        "2x_Model_A.pth",
        "2x_Model_B.safetensors",
    ]
    assert downloads == ["https://example.com/models.zip"]


@pytest.mark.parametrize("zip_files", [None, {"folder/2x_Other_Model.pth": b"x"}])
def test_a_broken_model_download_stops_the_job_instead_of_trying_each_image(
    tmp_path, monkeypatch, zip_files
):
    monkeypatch.setattr(janai, "MODELS_FOLDER", str(tmp_path / "models"))

    def fake_download(url, path, name=None):
        # An error page saved instead of the zip, or a zip without the model.
        if zip_files is None:
            open(path, "wb").write(b"<html>Not found</html>")
            return
        with zipfile.ZipFile(path, "w") as models_zip:
            for name, data in zip_files.items():
                models_zip.writestr(name, data)

    monkeypatch.setattr(janai, "download_file", fake_download)

    # Upscale Images stops the job on an "OSError", like for a missing internet connection.
    with pytest.raises(OSError):
        janai.download_model_file(
            "2x_Model_A.pth", "https://example.com/models.zip", report=lambda text: None
        )


def test_a_16_bit_grayscale_scan_keeps_its_grays(tmp_path, monkeypatch):
    use_fake_models(monkeypatch)
    panel = tmp_path / "panel_1.png"
    # Dark gray, saved as a 16-bit PNG.
    Image.fromarray(numpy.full((20, 30), 16384, dtype=numpy.uint16)).save(panel)

    janai.upscale_image_with_janai(str(panel), str(tmp_path / "out.png"), 2)

    output = numpy.asarray(Image.open(tmp_path / "out.png"))
    assert abs(float(output.mean()) - 64) < 2


def test_transparent_parts_become_white_like_a_page(tmp_path, monkeypatch):
    use_fake_models(monkeypatch)
    panel = tmp_path / "panel_1.png"
    image = Image.new("RGBA", (30, 20), (0, 0, 0, 0))
    image.paste((0, 0, 0, 255), (0, 0, 10, 20))
    image.save(panel)

    janai.upscale_image_with_janai(str(panel), str(tmp_path / "out.png"), 2)

    output = Image.open(tmp_path / "out.png").convert("L")
    assert output.getpixel((5, 5)) == 0 and output.getpixel((50, 30)) == 255


def test_a_32_bit_image_with_8_bit_values_keeps_its_grays():
    image = Image.fromarray(numpy.full((4, 4), 128, dtype=numpy.int32), mode="I")

    assert janai.get_8_bit_rgb_image(image).getpixel((0, 0)) == (128, 128, 128)


def test_a_model_download_says_where_the_model_comes_from(tmp_path, monkeypatch):
    monkeypatch.setattr(janai, "MODELS_FOLDER", str(tmp_path / "models"))
    reported = []

    def no_internet(url, path, name=None):
        raise urllib.error.URLError("nodename nor servname provided")

    monkeypatch.setattr(janai, "download_file", no_internet)

    with pytest.raises(OSError, match="check your internet connection") as error:
        janai.download_model_file(
            "2x_Model_A.pth", "https://example.com/models.zip", report=reported.append
        )

    assert janai.MODELS_PAGE_URL in reported[0]
    assert janai.MODELS_PAGE_URL in str(error.value)


def test_only_the_2x_models_are_downloaded_out_of_the_zip(tmp_path, monkeypatch):
    from gui_classes import ProgressPanel

    monkeypatch.setattr(janai, "MODELS_FOLDER", str(tmp_path / "models"))
    zip_path = tmp_path / "models.zip"
    with zipfile.ZipFile(zip_path, "w") as models_zip:
        models_zip.writestr("folder/2x_Model_A.pth", b"a" * 1000)
        models_zip.writestr("folder/4x_Model_C.pth", b"c" * 5000)
    # The zip on the server, opened without downloading it.
    monkeypatch.setattr(janai, "open_remote_zip", lambda url: zipfile.ZipFile(zip_path))
    monkeypatch.setattr(
        janai, "download_file", lambda *args, **kwargs: pytest.fail("not the whole zip")
    )
    reported = []
    monkeypatch.setattr(
        ProgressPanel, "report_progress", lambda **fields: reported.append(fields)
    )

    path = janai.download_model_file(
        "2x_Model_A.pth", janai.MANGA_MODELS_ZIP_URL, report=lambda text: None
    )

    assert open(path, "rb").read() == b"a" * 1000
    assert os.listdir(tmp_path / "models") == ["2x_Model_A.pth"]
    # Only the 2x model counts toward what's downloaded.
    details = [fields for fields in reported if "detail" in fields]
    assert details == [
        {
            "detail": get_download_detail("Downloading MangaJaNai: 1.0 KB of 1.0 KB"),
            "fraction_done": 1.0,
        },
        {"detail": None, "fraction_done": None},
    ]


def test_a_download_that_stops_half_way_leaves_no_broken_model(tmp_path, monkeypatch):
    monkeypatch.setattr(janai, "MODELS_FOLDER", str(tmp_path / "models"))
    zip_path = tmp_path / "models.zip"
    with zipfile.ZipFile(zip_path, "w") as models_zip:
        models_zip.writestr("2x_Model_A.pth", b"a" * 1000)

    class ConnectionLost(zipfile.ZipFile):
        def open(self, *args, **kwargs):
            raise OSError("Connection reset")

    monkeypatch.setattr(janai, "open_remote_zip", lambda url: ConnectionLost(zip_path))

    with pytest.raises(OSError, match="check your internet connection"):
        janai.download_model_file(
            "2x_Model_A.pth", janai.MANGA_MODELS_ZIP_URL, report=lambda text: None
        )
    assert os.listdir(tmp_path / "models") == []


def test_a_model_is_not_downloaded_without_enough_space(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import utils

    monkeypatch.setattr(
        utils.shutil, "disk_usage", lambda path: SimpleNamespace(free=1_000_000)
    )
    monkeypatch.setattr(
        janai, "download_file", lambda *args, **kwargs: pytest.fail("downloaded")
    )

    with pytest.raises(utils.NotEnoughSpace, match="MangaJaNai: it needs 236 MB"):
        janai.download_model_file(
            janai.MANGA_MODEL_FILES[1200],
            janai.MANGA_MODELS_ZIP_URL,
            report=lambda text: None,
        )


@pytest.mark.parametrize(
    "on_a_mac, files, loaded, expected",
    [
        # The first time ever.
        (
            True,
            [],
            False,
            [
                "Downloading MangaJaNai (one time only)",
                "Converting MangaJaNai 1600p for Core ML (one time only)",
                "Loading MangaJaNai 1600p into Core ML",
            ],
        ),
        # Downloaded early (Settings → Storage → Download): not converted yet.
        (
            True,
            ["2x_MangaJaNai_1600p_V1_ESRGAN_90k.pth"],
            False,
            [
                "Converting MangaJaNai 1600p for Core ML (one time only)",
                "Loading MangaJaNai 1600p into Core ML",
            ],
        ),
        # Each time the app is opened.
        (
            True,
            [
                "2x_MangaJaNai_1600p_V1_ESRGAN_90k.pth",
                "2x_MangaJaNai_1600p_V1_ESRGAN_90k-256.mlpackage",
            ],
            False,
            ["Loading MangaJaNai 1600p into Core ML"],
        ),
        # Already loaded.
        (True, ["2x_MangaJaNai_1600p_V1_ESRGAN_90k.pth"], True, []),
        # Windows (and Intel Macs): no Core ML.
        (
            False,
            [],
            False,
            [
                "Downloading MangaJaNai (one time only)",
                "Loading MangaJaNai 1600p into PyTorch",
            ],
        ),
    ],
)
def test_the_steps_a_model_still_needs(
    monkeypatch, tmp_path, on_a_mac, files, loaded, expected
):
    monkeypatch.setattr(janai, "MODELS_FOLDER", str(tmp_path))
    monkeypatch.setattr(janai, "can_use_coreml", lambda: on_a_mac)
    for file_name in files:
        (tmp_path / file_name).mkdir()
    model_path = str(tmp_path / "2x_MangaJaNai_1600p_V1_ESRGAN_90k.pth")
    monkeypatch.setattr(
        janai, "_loaded_upscalers", {(model_path, True): "loaded"} if loaded else {}
    )

    assert (
        janai.get_steps_to_get_ready(model_path, janai.MANGA_MODELS_ZIP_URL, True)
        == expected
    )


def test_a_4x_upscale_lists_both_manga_models_steps_before_the_first_one_starts(
    monkeypatch, tmp_path
):
    from gui_classes import ProgressPanel

    monkeypatch.setattr(janai, "MODELS_FOLDER", str(tmp_path))
    monkeypatch.setattr(janai, "can_use_coreml", lambda: True)
    monkeypatch.setattr(janai, "_loaded_upscalers", {})
    panel = ProgressPanel.ProgressPanel()
    monkeypatch.setattr(ProgressPanel, "current_progress_panel", panel)
    panel.start("Upscaling images...")
    listed_at_the_first_download = []

    def fake_download(file_name, zip_url, report=print):
        if not listed_at_the_first_download:
            listed_at_the_first_download.extend(panel.stages)
        return os.path.join(janai.MODELS_FOLDER, file_name)

    monkeypatch.setattr(janai, "download_model_file", fake_download)
    monkeypatch.setattr(
        janai,
        "get_upscaler",
        lambda model_path, use_neural_engine, report=print: upscale_tile_like_nearest,
    )
    # A black-and-white page 1,600 px tall: 1600p for the first pass, then 2048p (it's 3,200 px tall by then).
    Image.new("L", (1000, 1600), 255).save(tmp_path / "page.png")

    janai.upscale_image_with_janai(
        str(tmp_path / "page.png"), str(tmp_path / "out.png"), 4
    )

    assert listed_at_the_first_download == [
        "Downloading MangaJaNai (one time only)",
        "Converting MangaJaNai 1600p for Core ML (one time only)",
        "Loading MangaJaNai 1600p into Core ML",
        "Converting MangaJaNai 2048p for Core ML (one time only)",
        "Loading MangaJaNai 2048p into Core ML",
        "Upscaling images...",
    ]
