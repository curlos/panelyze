"""
A quick check that everything Panelyze needs works, with no window: "python gui.py --self-test" (or "Panelyze.app/Contents/MacOS/Panelyze --self-test").

"build_mac_app.sh" runs it on the freshly built app, so a broken bundle (e.g. a missing library, Magi files or waifu2x) is caught before it's zipped and shared. Nothing here needs the internet.
"""

import os
import subprocess
import sys
import tempfile
import traceback

from PIL import Image, ImageDraw

from default_settings import LOG_FOLDER


def make_test_page(path):
    """
    A simple drawn manga page with 3 panels (no real manga page can be shipped with the app).
    """
    page = Image.new("RGB", (800, 1200), "white")
    draw = ImageDraw.Draw(page)

    for x1, y1, x2, y2 in [
        (30, 30, 390, 580),
        (410, 30, 770, 580),
        (30, 600, 770, 1170),
    ]:
        draw.rectangle((x1, y1, x2, y2), outline="black", width=8)
        for i in range(6):
            draw.line(
                (x1 + 40 + i * 40, y1 + 60, x1 + 120 + i * 30, y2 - 60),
                fill="black",
                width=4,
            )
        draw.ellipse((x1 + 60, y1 + 80, x1 + 220, y1 + 200), outline="black", width=4)

    page.save(path)


def check_magi_panels(work_directory):
    import numpy
    from magi import Magi

    page_path = os.path.join(work_directory, "page_1.png")
    make_test_page(page_path)
    panels = Magi().predict_panels([numpy.array(Image.open(page_path))])[0]["panels"]

    assert len(panels) == 3, f"expected 3 panels, found {len(panels)}"
    return "3 panels found"


def check_waifu2x(work_directory):
    from utils import ProcessManager, get_waifu2x_path, is_running_as_packaged_app
    from waifu2x import download_waifu2x, upscale_with_waifu2x

    if is_running_as_packaged_app():
        # The packaged app must use its own copy, not one found on the PATH or downloaded: that's what this check is for when the app is built.
        assert (get_waifu2x_path() or "").startswith(sys._MEIPASS), (  # pyright: ignore[reportAttributeAccessIssue]
            "waifu2x isn't bundled in the app"
        )
    else:
        # Downloaded the first time when running from source, like the Upscale tab does.
        download_waifu2x()

    input_image = os.path.join(work_directory, "small.png")
    output_image = os.path.join(work_directory, "small_2x.png")
    Image.new("RGB", (40, 30), "white").save(input_image)
    upscale_with_waifu2x(
        input_image,
        output_image,
        upscale_ratio=2,
        noise_level=0,
        process_manager=ProcessManager(),
    )

    assert Image.open(output_image).size == (80, 60), "wrong upscaled size"
    return "upscaled 40x30 to 80x60"


def check_video(work_directory):
    from VideoCreatorFromImages import VideoCreatorFromImages

    images_folder = os.path.join(work_directory, "panels")
    os.makedirs(images_folder)
    Image.new("RGB", (300, 400), "white").save(
        os.path.join(images_folder, "panel_1.png")
    )
    Image.new("RGB", (400, 300), "gray").save(
        os.path.join(images_folder, "panel_2.png")
    )

    settings = {
        "use_reading_speed_wpm": False,
        "use_image_displayed_duration": True,
        "image_displayed_duration": "1",
        "use_minimum_image_duration": False,
        "video_height": "240",
    }
    video_creator = VideoCreatorFromImages(settings)
    video_creator.initialize_flet_client_storage_values(settings)
    video_file = os.path.join(work_directory, "video.mp4")
    video_creator.create_video_from_images(
        images_folder,
        video_file,
        full_output_directory=os.path.join(work_directory, "video"),
    )

    assert os.path.getsize(video_file) > 0, "empty video"
    return "made a 2-panel video"


def check_mangadex_downloader(work_directory):
    from download_from_mangadex import get_mangadex_downloader_command

    result = subprocess.run(
        get_mangadex_downloader_command() + ["--list-language"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert "English" in result.stdout, (
        f"no language list: {result.stdout[-300:]}{result.stderr[-300:]}"
    )
    return "mangadex-downloader runs"


def check_text_to_speech_libraries(work_directory):
    import azure.cognitiveservices.speech as speechsdk
    import edge_tts

    assert edge_tts.Communicate

    # Creating a config loads Azure's native library (without contacting Azure).
    speechsdk.SpeechConfig(subscription="self-test", region="eastus")
    return "edge-tts and Azure Speech load"


def check_comic_files(work_directory):
    import shutil
    import zipfile
    from utils import extract_comic_files_to_folder

    pdf_path = os.path.join(work_directory, "comic.pdf")
    make_test_page(os.path.join(work_directory, "page.png"))
    Image.open(os.path.join(work_directory, "page.png")).save(pdf_path)
    cbz_path = os.path.join(work_directory, "comic.cbz")
    with zipfile.ZipFile(cbz_path, "w") as cbz:
        cbz.write(os.path.join(work_directory, "page.png"), "page.png")

    # Rendering the PDF loads pypdfium2's native library.
    folder = extract_comic_files_to_folder([pdf_path, cbz_path])
    try:
        pages = sorted(os.listdir(os.path.join(folder, "comic")))
    finally:
        shutil.rmtree(os.path.dirname(folder))

    assert pages == ["001.png"], pages
    return ".pdf and .cbz files open"


def check_comix_downloader(work_directory):
    # Only loads the code (comix.to itself isn't contacted).
    from download_from_comix import parse_comix_url
    from src.api.comix import ComixAPI
    from src.core.downloader import MangaDownloader
    from src.utils.nodriver_compat import load_nodriver

    assert ComixAPI and MangaDownloader
    assert load_nodriver().start
    assert parse_comix_url("https://comix.to/title/w25zn-slam-dunk") == ("w25zn", None)
    return "comix.to downloader and nodriver load"


def check_best_upscaler_libraries(work_directory):
    import numpy
    import spandrel
    import torch
    from janai import can_use_coreml

    assert spandrel.ModelLoader
    if not can_use_coreml():
        return "spandrel loads (Core ML isn't used on this computer)"

    # The same steps as for a real "Best" model (see "get_coreml_upscale_function"), on a tiny one: the real ones are a 592 MB download.
    import coremltools as ct

    layer = torch.nn.Conv2d(3, 3, 3, padding=1).eval()
    traced_layer = torch.jit.trace(layer, torch.rand(1, 3, 16, 16))
    model = ct.convert(
        traced_layer,
        inputs=[ct.TensorType(name="image", shape=(1, 3, 16, 16))],
        outputs=[ct.TensorType(name="upscaled")],
        minimum_deployment_target=ct.target.macOS13,
        convert_to="mlprogram",
    )
    model_path = os.path.join(work_directory, "tiny.mlpackage")
    model.save(model_path)  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
    output = ct.models.MLModel(model_path).predict(
        {"image": numpy.zeros((1, 3, 16, 16), numpy.float32)}
    )["upscaled"]

    assert output.shape == (1, 3, 16, 16), f"wrong output shape {output.shape}"
    return "spandrel loads, and Core ML converts and runs a model"


CHECKS = [
    check_magi_panels,
    check_waifu2x,
    check_video,
    check_mangadex_downloader,
    check_text_to_speech_libraries,
    check_comic_files,
    check_comix_downloader,
    check_best_upscaler_libraries,
]


# A packaged app may have nowhere to print to, so the results are also saved here.
REPORT_FILE_PATH = os.path.join(LOG_FOLDER, "self-test.log")


def run_self_test():
    """
    Run every check and print the results. Returns the exit code: 0 if everything passed, 1 otherwise.
    """
    report_lines = []
    failed_checks = 0

    for check in CHECKS:
        with tempfile.TemporaryDirectory(
            prefix="panelyze-self-test-"
        ) as work_directory:
            try:
                report_lines.append(f"PASS {check.__name__}: {check(work_directory)}")
            except Exception:
                failed_checks += 1
                report_lines.append(f"FAIL {check.__name__}:\n{traceback.format_exc()}")
        print(report_lines[-1], flush=True)

    report_lines.append(
        "SELF-TEST PASSED"
        if failed_checks == 0
        else f"SELF-TEST FAILED ({failed_checks} failed)"
    )
    print(report_lines[-1], flush=True)

    os.makedirs(os.path.dirname(REPORT_FILE_PATH), exist_ok=True)
    with open(REPORT_FILE_PATH, "w") as report_file:
        report_file.write("\n".join(report_lines) + "\n")

    return 0 if failed_checks == 0 else 1


if __name__ == "__main__":
    sys.exit(run_self_test())
