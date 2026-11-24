"""Absolute Batman ch. 1, panels 30-49, upscaled to 4K with Fast, Better and Best through the app's Upscale tab. Run from the worktree with: pytest -p tests.fake_gui <this file> -s"""
import os, shutil, time
from PIL import Image
from tests.fake_gui import fake_event

BASE = os.path.expanduser(r"~/Documents/Panelyze/10-amd-gaming-pc")
PANELS = os.path.join(BASE, "Panel-By-Panel", "absolute batman", "Chapter_1_Absolute Batman, Vol. 1 The Zoo")
OUT = os.path.join(BASE, "benchmark-absolute-batman-ch1-upscale-4k")


def run_submit(view, input_directory, output_directory):
    directories = view.pick_input_output_directories_container
    directories.input_directory = str(input_directory)
    directories.output_directory = str(output_directory)
    directories.handle_submit(fake_event())


def test_upscale_4k(make_gui, monkeypatch):
    from gui_classes import JobView, PipelineView
    for module in (JobView, PipelineView):
        monkeypatch.setattr(module, "open_directory", lambda path: None)
    input_folder = os.path.join(OUT, "1-panels-30-to-49", "Chapter 1")
    os.makedirs(input_folder, exist_ok=True)
    for n in range(30, 50):
        shutil.copy2(os.path.join(PANELS, f"panel_{n}.png"), input_folder)

    gui = make_gui()
    storage = gui.page.client_storage
    storage.set("upscale_ratio", 32)
    storage.set("limit_upscale_to_4k", True)
    storage.set("image_format", "png")
    for model in ("fast", "better", "best"):
        storage.set("upscale_model", model)
        output = os.path.join(OUT, f"2-{model}")
        start = time.time()
        run_submit(gui.UpscaleImagesView, os.path.dirname(input_folder), output)
        seconds = time.time() - start
        images = [os.path.join(d, f) for d, _, names in os.walk(output) for f in names if f.endswith(".png")]
        sizes = sorted({max(Image.open(image).size) for image in images})
        print(f"\nUPSCALE {model}: {seconds:.1f} s for {len(images)} images ({seconds / max(len(images), 1):.1f} s each), longest sides: {sizes}", flush=True)
        assert len(images) == 20
