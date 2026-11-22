import os
from types import SimpleNamespace

from PIL import Image

import gui_classes.UpscaleImagesView as upscale_module
from utils import replace_extension


def make_fake_waifu2x(monkeypatch, runs, fail_on=()):
    """
    A fake waifu2x that "upscales" a whole folder: it saves each image at the given ratio, in the output format, and prints a "done" line for each, like the real one.
    """

    def fake_upscale(input_image, output_image, upscale_ratio, image_format, model, on_line, **kwargs):
        file_names = sorted(os.listdir(input_image))
        runs.append({"ratio": upscale_ratio, "model": model, "files": file_names})

        for file_name in file_names:
            if file_name in fail_on:
                continue
            with Image.open(os.path.join(input_image, file_name)) as image:
                image.resize((image.width * upscale_ratio, image.height * upscale_ratio)).save(
                    os.path.join(output_image, replace_extension(file_name, image_format))
                )
            on_line(f"{file_name} -> out done\n")

    monkeypatch.setattr(upscale_module, "upscale_with_waifu2x", fake_upscale)
    monkeypatch.setattr(upscale_module, "ProcessManager", lambda: SimpleNamespace())


def run_upscale(gui, tmp_path, sizes):
    chapter = tmp_path / "panels" / "Ch 1"
    chapter.mkdir(parents=True)
    for number, size in enumerate(sizes, start=1):
        Image.new("RGB", size, "white").save(chapter / f"panel_{number}.png")

    gui.UpscaleImagesView.process_image_folder(
        str(chapter),
        [{"name": f"panel_{number}.png"} for number in range(1, len(sizes) + 1)],
        str(tmp_path / "panels"),
        str(tmp_path / "upscaled"),
    )
    return tmp_path / "upscaled" / "panels" / "Ch 1"


def test_all_images_are_upscaled_in_one_run_with_the_fast_model(make_gui, tmp_path, monkeypatch):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("image_format", "webp")

    output = run_upscale(gui, tmp_path, [(100, 80), (60, 90), (50, 50)])

    assert runs == [{"ratio": 2, "model": "fast", "files": ["panel_1.png", "panel_2.png", "panel_3.png"]}]
    assert sorted(os.listdir(output)) == ["panel_1.webp", "panel_2.webp", "panel_3.webp"]
    assert Image.open(output / "panel_1.webp").size == (200, 160)


def test_the_better_waifu2x_model_can_be_picked(make_gui, tmp_path, monkeypatch):
    runs = []
    make_fake_waifu2x(monkeypatch, runs)
    gui = make_gui()
    gui.page.client_storage.set("upscale_model", "better")

    run_upscale(gui, tmp_path, [(100, 80)])

    assert runs[0]["model"] == "better"


def test_the_best_model_upscales_each_image_with_janai_except_ones_already_4k(make_gui, tmp_path, monkeypatch):
    import janai

    runs, janai_runs = [], []
    make_fake_waifu2x(monkeypatch, runs)

    def fake_janai(input_image, output_image, upscale_ratio):
        janai_runs.append((os.path.basename(input_image), os.path.basename(output_image), upscale_ratio))
        with Image.open(input_image) as image:
            image.resize((image.width * upscale_ratio, image.height * upscale_ratio)).save(output_image)

    monkeypatch.setattr(janai, "upscale_image_with_janai", fake_janai)
    gui = make_gui()
    gui.page.client_storage.set("upscale_model", "best")
    gui.page.client_storage.set("image_format", "webp")

    output = run_upscale(gui, tmp_path, [(100, 80), (4000, 200), (60, 90)])

    assert janai_runs == [("panel_1.png", "panel_1.webp", 2), ("panel_3.png", "panel_3.webp", 2)]
    # The image that's already 4K is only cleaned up, by waifu2x.
    assert runs == [{"ratio": 1, "model": "better", "files": ["panel_2.png"]}]
    assert sorted(os.listdir(output)) == ["panel_1.webp", "panel_2.webp", "panel_3.webp"]


def test_images_the_4k_limit_upscales_less_get_their_own_run(make_gui, tmp_path, monkeypatch):
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


def test_progress_counts_each_finished_image_and_a_failed_one_is_reported(make_gui, tmp_path, monkeypatch):
    import gui_classes.UpscaleImagesView as view_module

    runs = []
    make_fake_waifu2x(monkeypatch, runs, fail_on=("panel_2.png",))
    reports = []
    monkeypatch.setattr(view_module, "report_progress", lambda **fields: reports.append(fields))
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


def test_the_upscaled_chapter_is_also_saved_as_a_comic_file_when_turned_on(make_gui, tmp_path, monkeypatch):
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


def test_upscaled_pages_are_not_marked_as_one_image_at_a_time(make_gui, tmp_path, monkeypatch):
    import zipfile

    make_fake_waifu2x(monkeypatch, [])
    gui = make_gui()
    gui.page.client_storage.set("save_as_cbz", "full")
    chapter = tmp_path / "pages" / "Ch 1"
    chapter.mkdir(parents=True)
    Image.new("RGB", (60, 90), "white").save(chapter / "001.png")

    gui.UpscaleImagesView.process_image_folder(str(chapter), [{"name": "001.png"}], str(tmp_path / "pages"), str(tmp_path / "upscaled"))

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
