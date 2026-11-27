import os
from types import SimpleNamespace

import pytest
from PIL import Image

import default_settings
import gui_classes.UpscaleImagesView as upscale_module
from utils import replace_extension


@pytest.fixture(autouse=True)
def png_by_default(monkeypatch):
    # These tests were written for PNG output (the default is WebP, see "test_upscaled_images_are_webp_by_default_and_stop_at_4k" in test_gui.py).
    monkeypatch.setitem(default_settings.DEFAULT_SETTINGS, "image_format", "png")


def make_fake_waifu2x(monkeypatch, runs, fail_on=()):
    """
    A fake waifu2x that "upscales" a whole folder: it saves each image at the given ratio, in the output format, and prints a "done" line for each, like the real one.
    """

    def fake_upscale(
        input_image, output_image, upscale_ratio, image_format, model, on_line, **kwargs
    ):
        file_names = sorted(os.listdir(input_image))
        runs.append({"ratio": upscale_ratio, "model": model, "files": file_names})

        for file_name in file_names:
            if file_name in fail_on:
                continue
            with Image.open(os.path.join(input_image, file_name)) as image:
                image.resize(
                    (image.width * upscale_ratio, image.height * upscale_ratio)
                ).save(
                    os.path.join(
                        output_image, replace_extension(file_name, image_format)
                    )
                )
            on_line(f"{file_name} -> out done\n")

    monkeypatch.setattr(upscale_module, "upscale_with_waifu2x", fake_upscale)
    monkeypatch.setattr(upscale_module, "ProcessManager", lambda: SimpleNamespace())


def run_upscale(gui, tmp_path, sizes):
    chapter = tmp_path / "panels" / "Ch 1"
    chapter.mkdir(parents=True, exist_ok=True)
    for number, size in enumerate(sizes, start=1):
        Image.new("RGB", size, "white").save(chapter / f"panel_{number}.png")

    gui.UpscaleImagesView.process_image_folder(
        str(chapter),
        [{"name": f"panel_{number}.png"} for number in range(1, len(sizes) + 1)],
        str(tmp_path / "panels"),
        str(tmp_path / "upscaled"),
    )
    return tmp_path / "upscaled" / "panels" / "Ch 1"


def test_custom_panel_height_resizes_every_image_to_that_height(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("use_custom_panel_image_height", True)
    gui.page.client_storage.set("custom_panel_image_height", "300")

    # 2x: 200x160 and 120x160, then made 300 px tall, keeping their shape.
    output = run_upscale(gui, tmp_path, [(100, 80), (60, 80)])

    assert Image.open(output / "panel_1.png").size == (375, 300)
    assert Image.open(output / "panel_2.png").size == (225, 300)


def test_best_with_the_4k_limit_a_custom_height_and_a_max_width_all_apply_in_order(
    make_gui, tmp_path, monkeypatch
):
    import janai

    runs, janai_ratios = [], []
    make_fake_waifu2x(monkeypatch, runs)

    def fake_janai(input_image, output_image, upscale_ratio):
        janai_ratios.append(upscale_ratio)
        with Image.open(input_image) as image:
            image.resize(
                (image.width * upscale_ratio, image.height * upscale_ratio)
            ).save(output_image)

    monkeypatch.setattr(janai, "upscale_image_with_janai", fake_janai)
    gui = make_gui()
    storage = gui.page.client_storage
    storage.set("upscale_model", "best")
    storage.set("upscale_ratio", 32)
    storage.set("limit_upscale_to_4k", True)
    storage.set("use_custom_panel_image_height", True)
    storage.set("custom_panel_image_height", "1000")
    storage.set("use_max_image_width", True)
    storage.set("max_image_width", "600")

    output = run_upscale(gui, tmp_path, [(350, 429)])

    # "Best" 8x because of the 4K limit (2800x3432, left under 4K), then 1000 px tall (815x1000), then at most 600 px wide.
    assert janai_ratios == [8]
    assert Image.open(output / "panel_1.png").size == (600, 736)


def test_a_folder_saved_as_png_because_of_webp_s_size_limit_still_gets_the_custom_height(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    storage = gui.page.client_storage
    storage.set("image_format", "webp")
    storage.set("use_custom_panel_image_height", True)
    storage.set("custom_panel_image_height", "300")

    # A long webtoon strip, too tall for WebP: the folder is saved as PNG, then made 300 px tall.
    output = run_upscale(gui, tmp_path, [(1000, 17000)])

    assert sorted(os.listdir(output)) == ["panel_1.png"]
    assert Image.open(output / "panel_1.png").size == (17, 300)


@pytest.mark.parametrize("height", ["", "0", "abc"])
def test_a_custom_height_or_max_width_that_isnt_a_number_above_0_resizes_nothing(
    make_gui, tmp_path, monkeypatch, height
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("use_custom_panel_image_height", True)
    gui.page.client_storage.set("custom_panel_image_height", height)
    gui.page.client_storage.set("use_max_image_width", True)
    gui.page.client_storage.set("max_image_width", height)

    output = run_upscale(gui, tmp_path, [(100, 80)])

    assert Image.open(output / "panel_1.png").size == (200, 160)


def test_max_image_width_only_shrinks_images_that_are_wider(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("use_max_image_width", True)
    gui.page.client_storage.set("max_image_width", "150")

    # 2x: 200x160 is wider than 150 (made 150x120); 100x160 isn't (kept).
    output = run_upscale(gui, tmp_path, [(100, 80), (50, 80)])

    assert Image.open(output / "panel_1.png").size == (150, 120)
    assert Image.open(output / "panel_2.png").size == (100, 160)


@pytest.mark.parametrize("noise_level", ["-1", "0", "3"])
def test_the_noise_level_is_given_to_waifu2x(
    make_gui, tmp_path, monkeypatch, noise_level
):
    noise_levels = []
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    fake_upscale = upscale_module.upscale_with_waifu2x

    def record_noise_level(*args, noise_level, **kwargs):
        noise_levels.append(noise_level)
        return fake_upscale(*args, **kwargs)

    monkeypatch.setattr(upscale_module, "upscale_with_waifu2x", record_noise_level)
    gui = make_gui()
    gui.page.client_storage.set("noise_level", noise_level)

    run_upscale(gui, tmp_path, [(100, 80)])

    assert noise_levels == [noise_level]


def test_waifu2x_is_run_with_the_ratio_noise_level_format_and_model(
    monkeypatch, tmp_path
):
    import waifu2x

    commands = []
    monkeypatch.setattr(
        waifu2x, "get_waifu2x_path", lambda: str(tmp_path / "waifu2x-ncnn-vulkan.exe")
    )
    monkeypatch.setattr(
        waifu2x.subprocess, "run", lambda command, check: commands.append(command)
    )

    waifu2x.upscale_with_waifu2x(
        "in", "out", upscale_ratio=4, noise_level=2, image_format="webp", model="fast"
    )

    command = commands[0]
    assert command[command.index("-s") + 1] == "4"
    assert command[command.index("-n") + 1] == "2"
    assert command[command.index("-f") + 1] == "webp"
    assert command[command.index("-m") + 1].endswith(waifu2x.WAIFU2X_MODELS["fast"])


def test_a_folder_with_an_image_too_big_for_webp_is_saved_as_png(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("image_format", "webp")

    # A long webtoon strip: already past 4K, so it's only cleaned up, but 17000 px is more than WebP allows (16383).
    output = run_upscale(gui, tmp_path, [(100, 17000), (100, 80)])

    assert sorted(os.listdir(output)) == ["panel_1.png", "panel_2.png"]


def test_webp_images_left_from_an_earlier_run_are_removed_when_the_folder_is_saved_as_png(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("image_format", "webp")
    # An earlier run of this folder saved WebP images.
    output = tmp_path / "upscaled" / "panels" / "Ch 1"
    output.mkdir(parents=True)
    (output / "panel_1.webp").write_bytes(b"old")

    run_upscale(gui, tmp_path, [(100, 17000)])

    assert sorted(os.listdir(output)) == ["panel_1.png"]


def test_a_big_upscale_without_the_4k_limit_is_saved_as_png_when_too_big_for_webp(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("image_format", "webp")
    gui.page.client_storage.set("limit_upscale_to_4k", False)
    # The dropdown saves the ratio as text.
    gui.page.client_storage.set("upscale_ratio", "32")

    # 640 px x 32 = 20480 px, more than WebP allows (16383).
    output = run_upscale(gui, tmp_path, [(640, 10)])

    assert runs[0]["ratio"] == 32
    assert sorted(os.listdir(output)) == ["panel_1.png"]


def test_images_finished_before_a_cancel_still_keep_the_4k_limit(
    make_gui, tmp_path, monkeypatch
):
    from utils import DownloadCancelled

    gui = make_gui()
    view = gui.UpscaleImagesView
    gui.page.client_storage.set("upscale_ratio", 4)
    gui.page.client_storage.set("limit_upscale_to_4k", True)

    def fake_upscale(
        input_image, output_image, upscale_ratio, image_format, model, on_line, **kwargs
    ):
        # panel_1 is done (2x of 2100x3170 = 4200x6340, past 4K), panel_2 is cut off by the cancel, panel_3 never starts.
        with Image.open(os.path.join(input_image, "panel_1.png")) as image:
            image.resize(
                (image.width * upscale_ratio, image.height * upscale_ratio)
            ).save(os.path.join(output_image, "panel_1.png"))
        with open(os.path.join(output_image, "panel_2.png"), "wb") as file:
            file.write(b"\x89PNG\r\n\x1a\n half written")
        view.cancel_event.set()

    monkeypatch.setattr(upscale_module, "upscale_with_waifu2x", fake_upscale)
    monkeypatch.setattr(upscale_module, "ProcessManager", lambda: SimpleNamespace())
    errors = []
    monkeypatch.setattr(
        gui.terminal_output, "update_terminal_with_error_message", errors.append
    )

    # The text Panel-By-Panel read is only copied along when the whole folder is done.
    from utils import PANEL_TEXT_FILE_NAME

    (tmp_path / "panels" / "Ch 1").mkdir(parents=True)
    (tmp_path / "panels" / "Ch 1" / PANEL_TEXT_FILE_NAME).write_text("[]")

    with pytest.raises(DownloadCancelled):
        run_upscale(gui, tmp_path, [(2100, 3170), (2100, 3170), (2100, 3170)])

    output = tmp_path / "upscaled" / "panels" / "Ch 1"
    assert sorted(os.listdir(output)) == ["panel_1.png"]
    assert max(Image.open(output / "panel_1.png").size) == 3840
    assert errors == []


def test_images_finished_before_a_cancel_also_get_the_custom_height(
    make_gui, tmp_path, monkeypatch
):
    from utils import DownloadCancelled

    gui = make_gui()
    view = gui.UpscaleImagesView
    storage = gui.page.client_storage
    storage.set("upscale_ratio", 2)
    storage.set("use_custom_panel_image_height", True)
    storage.set("custom_panel_image_height", "500")

    def fake_upscale(
        input_image, output_image, upscale_ratio, image_format, model, on_line, **kwargs
    ):
        # panel_1 is done, then the cancel.
        with Image.open(os.path.join(input_image, "panel_1.png")) as image:
            image.resize(
                (image.width * upscale_ratio, image.height * upscale_ratio)
            ).save(os.path.join(output_image, "panel_1.png"))
        view.cancel_event.set()

    monkeypatch.setattr(upscale_module, "upscale_with_waifu2x", fake_upscale)
    monkeypatch.setattr(upscale_module, "ProcessManager", lambda: SimpleNamespace())

    with pytest.raises(DownloadCancelled):
        run_upscale(gui, tmp_path, [(300, 400), (300, 400)])

    assert Image.open(
        tmp_path / "upscaled" / "panels" / "Ch 1" / "panel_1.png"
    ).size == (375, 500)


def test_all_images_are_upscaled_in_one_run_with_the_fast_model(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("image_format", "webp")

    output = run_upscale(gui, tmp_path, [(100, 80), (60, 90), (50, 50)])

    assert runs == [
        {
            "ratio": 2,
            "model": "fast",
            "files": ["panel_1.png", "panel_2.png", "panel_3.png"],
        }
    ]
    assert sorted(os.listdir(output)) == [
        "panel_1.webp",
        "panel_2.webp",
        "panel_3.webp",
    ]
    assert Image.open(output / "panel_1.webp").size == (200, 160)


def test_the_better_waifu2x_model_can_be_picked(make_gui, tmp_path, monkeypatch):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("upscale_model", "better")

    run_upscale(gui, tmp_path, [(100, 80)])

    assert runs[0]["model"] == "better"


def test_the_best_model_upscales_each_image_with_janai_except_ones_already_4k(
    make_gui, tmp_path, monkeypatch
):
    import janai

    runs, janai_runs = [], []
    make_fake_waifu2x(monkeypatch, runs)

    def fake_janai(input_image, output_image, upscale_ratio):
        janai_runs.append(
            (
                os.path.basename(input_image),
                os.path.basename(output_image),
                upscale_ratio,
            )
        )
        with Image.open(input_image) as image:
            image.resize(
                (image.width * upscale_ratio, image.height * upscale_ratio)
            ).save(output_image)

    monkeypatch.setattr(janai, "upscale_image_with_janai", fake_janai)
    gui = make_gui()
    gui.page.client_storage.set("upscale_model", "best")
    gui.page.client_storage.set("image_format", "webp")

    output = run_upscale(gui, tmp_path, [(100, 80), (4000, 200), (60, 90)])

    assert janai_runs == [
        ("panel_1.png", "panel_1.webp", 2),
        ("panel_3.png", "panel_3.webp", 2),
    ]
    # The image that's already 4K is only cleaned up, by waifu2x.
    assert runs == [{"ratio": 1, "model": "better", "files": ["panel_2.png"]}]
    assert sorted(os.listdir(output)) == [
        "panel_1.webp",
        "panel_2.webp",
        "panel_3.webp",
    ]


@pytest.mark.parametrize("model", ["fast", "better"])
def test_fast_and_better_download_waifu2x_at_the_start_of_the_job(
    make_gui, monkeypatch, model
):
    from gui_classes import UpscaleImagesView

    downloads = []
    monkeypatch.setattr(
        UpscaleImagesView, "download_waifu2x", lambda: downloads.append("waifu2x")
    )
    gui = make_gui()
    gui.page.client_storage.set("upscale_model", model)

    gui.UpscaleImagesView.before_job()

    assert downloads == ["waifu2x"]


@pytest.mark.parametrize(
    "sizes, downloads_waifu2x",
    [([(100, 80), (60, 90)], False), ([(100, 80), (4000, 200)], True)],
)
def test_best_only_downloads_waifu2x_for_an_image_already_4k(
    make_gui, tmp_path, monkeypatch, sizes, downloads_waifu2x
):
    import janai
    from gui_classes import UpscaleImagesView

    downloads = []
    monkeypatch.setattr(
        UpscaleImagesView, "download_waifu2x", lambda: downloads.append("waifu2x")
    )
    make_fake_waifu2x(monkeypatch, [])

    def fake_janai(input_image, output_image, upscale_ratio):
        with Image.open(input_image) as image:
            image.resize(
                (image.width * upscale_ratio, image.height * upscale_ratio)
            ).save(output_image)

    monkeypatch.setattr(janai, "upscale_image_with_janai", fake_janai)
    gui = make_gui()
    gui.page.client_storage.set("upscale_model", "best")

    # Not at the start of the job (this was the bug: it was downloaded for every job)...
    gui.UpscaleImagesView.before_job()
    assert downloads == []
    # ...only when an image needs it.
    run_upscale(gui, tmp_path, sizes)

    # "Best" upscales with MangaJaNai or IllustrationJaNai. waifu2x is only for an image that's already 4K (it's only cleaned up).
    assert downloads == (["waifu2x"] if downloads_waifu2x else [])


def test_images_the_4k_limit_upscales_less_get_their_own_run(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()

    # The second image is already wider than 4K, so it isn't made bigger (only cleaned up, which only the best model can do).
    output = run_upscale(gui, tmp_path, [(100, 80), (4000, 200)])

    assert runs == [
        {"ratio": 1, "model": "better", "files": ["panel_2.png"]},
        {"ratio": 2, "model": "fast", "files": ["panel_1.png"]},
    ]
    assert Image.open(output / "panel_2.png").size == (4000, 200)
    # The temporary folders for each run are gone.
    assert sorted(os.listdir(output)) == ["panel_1.png", "panel_2.png"]


def test_progress_counts_each_finished_image_and_a_failed_one_is_reported(
    make_gui, tmp_path, monkeypatch
):
    import gui_classes.UpscaleImagesView as view_module

    runs = []
    make_fake_waifu2x(monkeypatch, runs, fail_on=("panel_2.png",))
    reports = []
    monkeypatch.setattr(
        view_module, "report_progress", lambda **fields: reports.append(fields)
    )
    gui = make_gui()
    errors = []
    gui.terminal_output.update_terminal_with_error_message = errors.append

    output = run_upscale(gui, tmp_path, [(100, 80), (60, 90), (50, 50)])

    assert reports == [
        {"pages_done": 0, "pages_total": 3, "unit": "images"},
        {"pages_done": 1},
        {"pages_done": 2},
    ]
    assert sorted(os.listdir(output)) == ["panel_1.png", "panel_3.png"]
    assert len(errors) == 1 and "panel_2.png" in errors[0]


def test_the_upscaled_chapter_is_also_saved_as_a_comic_file_when_turned_on(
    make_gui, tmp_path, monkeypatch
):
    import zipfile

    make_fake_waifu2x(monkeypatch, [])
    gui = make_gui()
    assert gui.page.client_storage.get("save_as_cbz") == ""
    gui.page.client_storage.set("save_as_cbz", "full")

    output = run_upscale(gui, tmp_path, [(100, 80), (60, 90)])

    with zipfile.ZipFile(f"{output}.cbz") as cbz:
        assert cbz.namelist() == ["0001.png", "0002.png", "ComicInfo.xml"]
        # They're panels, so they're shown one at a time like Panel-By-Panel's comic files.
        assert cbz.read("ComicInfo.xml").decode().count('DoublePage="true"') == 2


def test_upscaled_pages_are_not_marked_as_one_image_at_a_time(
    make_gui, tmp_path, monkeypatch
):
    import zipfile

    make_fake_waifu2x(monkeypatch, [])
    gui = make_gui()
    gui.page.client_storage.set("save_as_cbz", "full")
    chapter = tmp_path / "pages" / "Ch 1"
    chapter.mkdir(parents=True)
    Image.new("RGB", (60, 90), "white").save(chapter / "001.png")

    gui.UpscaleImagesView.process_image_folder(
        str(chapter),
        [{"name": "001.png"}],
        str(tmp_path / "pages"),
        str(tmp_path / "upscaled"),
    )

    with zipfile.ZipFile(tmp_path / "upscaled" / "pages" / "Ch 1.cbz") as cbz:
        # Pages can still be shown two at a time, like a book. Nothing else to say, so no ComicInfo.xml.
        assert cbz.namelist() == ["0001.png"]


def test_an_image_is_copied_when_a_hard_link_cant_be_made(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    source.write_bytes(b"image")

    def fail_to_link(source_path, destination_path):
        raise OSError("cross-device link")

    monkeypatch.setattr(os, "link", fail_to_link)

    upscale_module.link_or_copy_file(str(source), str(tmp_path / "copy.png"))

    assert (tmp_path / "copy.png").read_bytes() == b"image"


def test_best_stops_short_of_4k_without_stretching_when_the_last_pass_would_go_far_past_it(
    make_gui, tmp_path, monkeypatch
):
    import janai

    runs, janai_runs = [], []
    make_fake_waifu2x(monkeypatch, runs)

    def fake_janai(input_image, output_image, upscale_ratio):
        janai_runs.append((os.path.basename(input_image), upscale_ratio))
        with Image.open(input_image) as image:
            image.resize(
                (image.width * upscale_ratio, image.height * upscale_ratio)
            ).save(output_image)

    monkeypatch.setattr(janai, "upscale_image_with_janai", fake_janai)
    gui = make_gui()
    gui.page.client_storage.set("upscale_model", "best")
    gui.page.client_storage.set("upscale_ratio", 32)
    gui.page.client_storage.set("limit_upscale_to_4k", True)

    # A 350x429 panel (Absolute Batman): 16x would be 6864px, so "Best" does 8x and it stays at 3432px (not stretched to 4K). A 500x1000 panel: 4x would be 4000px, only a bit past 4K, so "Best" does all of it.
    output = run_upscale(gui, tmp_path, [(350, 429), (500, 1000)])

    assert janai_runs == [("panel_1.png", 8), ("panel_2.png", 4)]
    assert Image.open(output / "panel_1.png").size == (2800, 3432)
    assert Image.open(output / "panel_2.png").size == (1920, 3840)


def test_the_best_model_at_1x_only_cleans_up_with_waifu2x_also_without_the_4k_limit(
    make_gui, tmp_path, monkeypatch
):
    import janai

    runs, janai_runs = [], []
    make_fake_waifu2x(monkeypatch, runs)
    monkeypatch.setattr(
        janai, "upscale_image_with_janai", lambda *args: janai_runs.append(args)
    )
    gui = make_gui()
    gui.page.client_storage.set("upscale_model", "best")
    gui.page.client_storage.set("limit_upscale_to_4k", False)
    # What the Upscale Ratio dropdown saves.
    gui.page.client_storage.set("upscale_ratio", "1")

    run_upscale(gui, tmp_path, [(100, 80)])

    assert janai_runs == []
    assert runs == [{"ratio": 1, "model": "better", "files": ["panel_1.png"]}]


def test_an_upscaled_image_left_from_an_earlier_run_is_not_taken_for_a_new_one(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    # waifu2x exits with 0 even when it couldn't upscale an image.
    make_fake_waifu2x(monkeypatch, runs, fail_on=("panel_1.png",))
    gui = make_gui()
    errors = []
    gui.terminal_output.update_terminal_with_error_message = errors.append
    earlier_output = tmp_path / "upscaled" / "panels" / "Ch 1"
    earlier_output.mkdir(parents=True)
    Image.new("RGB", (10, 10), "black").save(earlier_output / "panel_1.png")

    output = run_upscale(gui, tmp_path, [(100, 80)])

    assert os.listdir(output) == []
    assert len(errors) == 1 and "panel_1.png" in errors[0]


def test_the_saved_upscale_ratio_and_noise_level_are_shown_when_the_app_opens_again(
    make_gui,
):
    from tests.fake_gui import fake_event, get_all_controls
    import flet as ft

    gui = make_gui()
    dropdowns = {
        control.label: control
        for control in get_all_controls(gui.UpscaleImagesView)
        if isinstance(control, ft.Dropdown)
    }
    # What the dropdowns save when a choice is picked.
    for label, value in (("Upscale Ratio", "4"), ("Noise Level", "-1")):
        on_change = dropdowns[label].on_change
        assert on_change is not None
        on_change(fake_event(data=value, control=dropdowns[label]))

    # The app opened again with the same settings.
    gui_again = type(gui)(gui.page)
    dropdowns = {
        control.label: control
        for control in get_all_controls(gui_again.UpscaleImagesView)
        if isinstance(control, ft.Dropdown)
    }

    for label, value in (("Upscale Ratio", "4"), ("Noise Level", "-1")):
        assert dropdowns[label].value == value
        assert value in [option.key for option in dropdowns[label].options]


def test_an_upscale_too_big_to_fit_in_memory_is_refused_before_anything_is_upscaled(
    make_gui, tmp_path, monkeypatch
):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("limit_upscale_to_4k", False)
    gui.page.client_storage.set("upscale_ratio", "32")

    # 1000 x 1000 px at 32x is 32,000 x 32,000 px (1,024 megapixels, about 3 GB just to hold it).
    with pytest.raises(ValueError, match="too big to upscale"):
        run_upscale(gui, tmp_path, [(100, 100), (1000, 1000)])

    assert runs == []


def test_an_upscale_is_refused_when_the_results_might_not_fit_on_the_disk(
    make_gui, tmp_path, monkeypatch
):
    import utils

    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("upscale_ratio", "2")
    # Only 1 MB free.
    monkeypatch.setattr(
        utils.shutil, "disk_usage", lambda path: SimpleNamespace(free=1_000_000)
    )

    # Two 1000 x 1000 px images at 2x: up to 24 MB.
    with pytest.raises(utils.NotEnoughSpace, match="Not enough space"):
        run_upscale(gui, tmp_path, [(1000, 1000), (1000, 1000)])

    assert runs == []
