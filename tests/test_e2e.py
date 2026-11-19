"""
End-to-end tests: the real tools (Magi, waifu2x, edge-tts, MangaDex, MoviePy) driven through the app's own Submit buttons, on a fake page with no window.

Slow (about 30 seconds) and some need the internet, so they only run with: pytest -m e2e
"""
import os
import shutil
import socket

import pytest
from PIL import Image

from tests.fake_gui import fake_event

pytestmark = pytest.mark.e2e

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_PAGE = os.path.join(
    REPO_DIR, "testing-output", "One Piece (Official Colored)", "0003_Chapter.3", "01.png"
)
# A short public English chapter. Only its first page is downloaded.
MANGADEX_CHAPTER_URL = os.environ.get(
    "PANELYZE_TEST_MANGADEX_URL",
    "https://mangadex.org/chapter/0aaf8b27-0013-4ae0-8935-91a089466874",
)


def has_internet():
    try:
        socket.create_connection(("api.mangadex.org", 443), timeout=5).close()
        return True
    except OSError:
        return False


needs_internet = pytest.mark.skipif(not has_internet(), reason="No internet connection")
needs_waifu2x = pytest.mark.skipif(
    not shutil.which("waifu2x-ncnn-vulkan"), reason="waifu2x-ncnn-vulkan isn't installed"
)
needs_sample_page = pytest.mark.skipif(
    not os.path.exists(SAMPLE_PAGE), reason=f"Sample page not found: {SAMPLE_PAGE}"
)


@pytest.fixture
def gui(make_gui, monkeypatch):
    # Don't open Finder windows during tests.
    from gui_classes import JobView, PipelineView

    for module in (JobView, PipelineView):
        monkeypatch.setattr(module, "open_directory", lambda path: None)

    return make_gui()


def run_submit(view, input_directory, output_directory):
    directories = view.pick_input_output_directories_container
    directories.input_directory = str(input_directory)
    directories.output_directory = str(output_directory)
    directories.handle_submit(fake_event())


def image_files(directory):
    return sorted(
        file_name
        for _, _, file_names in os.walk(directory)
        for file_name in file_names
        if file_name.endswith((".png", ".jpg", ".jpeg", ".webp"))
    )


@needs_sample_page
def test_panel_by_panel_splits_a_real_page(gui, tmp_path):
    chapter = tmp_path / "Test Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    shutil.copy(SAMPLE_PAGE, chapter / "page_1.png")

    run_submit(gui.MagiPanelByPanelView, tmp_path / "Test Manga", tmp_path / "out")

    panels_folder = tmp_path / "out" / "panel-by-panel" / "not-grouped" / "Test Manga" / "Ch 1"
    # The full Magi model also finds exactly 4 panels on this page.
    assert sorted(os.listdir(panels_folder)) == [f"panel_{n}.png" for n in range(1, 5)]


@needs_waifu2x
def test_upscale_doubles_a_real_image(gui, tmp_path):
    chapter = tmp_path / "Test Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    Image.new("RGB", (200, 300), "white").save(chapter / "panel_1.png")
    gui.page.client_storage.set("upscale_ratio", 2)

    run_submit(gui.UpscaleImagesView, tmp_path / "Test Manga", tmp_path / "out")

    output_image = tmp_path / "out" / "Test Manga" / "Ch 1" / "panel_1.png"
    assert Image.open(output_image).size == (400, 600)


@needs_waifu2x
def test_upscale_never_goes_past_4k(gui, tmp_path):
    chapter = tmp_path / "Test Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    Image.new("RGB", (1000, 600), "white").save(chapter / "wide.png")
    Image.new("RGB", (4000, 100), "white").save(chapter / "already_4k.png")
    gui.page.client_storage.set("upscale_ratio", 16)

    run_submit(gui.UpscaleImagesView, tmp_path / "Test Manga", tmp_path / "out")

    output = tmp_path / "out" / "Test Manga" / "Ch 1"
    # 1000px x 4 = 4000px, shrunk to 3840px (instead of 16x = 16000px).
    assert Image.open(output / "wide.png").size == (3840, 2304)
    # Already bigger than 4K: denoised only, not upscaled.
    assert Image.open(output / "already_4k.png").size == (4000, 100)


@needs_internet
def test_text_to_speech_makes_real_audio(tmp_path):
    from TextToSpeech import TextToSpeech
    from VideoCreatorFromImages import get_audio_duration

    output_file = str(tmp_path / "speech.mp3")
    TextToSpeech({}).generate_audio(["Hello there.", "This is a test."], output_file)

    assert get_audio_duration(output_file) > 1


def test_images_to_video_makes_a_real_video(gui, tmp_path):
    from moviepy import VideoFileClip

    chapter = tmp_path / "Test Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    Image.new("RGB", (400, 600), "white").save(chapter / "panel_1.png")
    Image.new("RGB", (900, 300), "gray").save(chapter / "panel_2.png")
    storage = gui.page.client_storage
    storage.set("use_reading_speed_wpm", False)
    storage.set("use_image_displayed_duration", True)
    storage.set("image_displayed_duration", "1")
    storage.set("use_minimum_image_duration", False)
    storage.set("video_height", "360")
    storage.set("video_aspect_ratio", "9:16")

    run_submit(gui.ImagesToVideoView, tmp_path / "Test Manga", tmp_path / "out")

    video = VideoFileClip(str(tmp_path / "out" / "Test Manga" / "Ch 1.mp4"))
    assert tuple(video.size) == (360, 640)
    assert video.duration == pytest.approx(2, abs=0.2)
    video.close()


def download_first_page(gui, output_directory):
    from download_from_mangadex import download_from_mangadex

    storage = gui.page.client_storage
    storage.set("use_start_and_end_pages", True)
    storage.set("start_page", "1")
    storage.set("end_page", "1")

    download_from_mangadex(MANGADEX_CHAPTER_URL, str(output_directory), None, storage)


@needs_internet
def test_mangadex_downloads_a_real_page(gui, tmp_path):
    download_first_page(gui, tmp_path / "download")

    assert len(image_files(tmp_path / "download")) == 1


@needs_internet
def test_pipeline_runs_every_step_on_a_real_page(gui, tmp_path):
    if not shutil.which("waifu2x-ncnn-vulkan"):
        pytest.skip("waifu2x-ncnn-vulkan isn't installed")

    storage = gui.page.client_storage
    storage.set("use_start_and_end_pages", True)
    storage.set("start_page", "1")
    storage.set("end_page", "1")
    storage.set("upscale_ratio", 2)
    storage.set("use_reading_speed_wpm", False)
    storage.set("use_image_displayed_duration", True)
    storage.set("image_displayed_duration", "1")
    storage.set("use_minimum_image_duration", False)
    storage.set("video_height", "360")

    pipeline = gui.PipelineView
    for step in pipeline.step_checkboxes.values():
        step.value = True
    pipeline.mangadex_url_text_field.value = MANGADEX_CHAPTER_URL
    pipeline.output_directory = str(tmp_path / "out")

    pipeline.handle_run_pipeline(fake_event())

    terminal_lines = [
        control.value for control in gui.terminal_output.terminal_output_list_view.controls
    ]
    assert any("Pipeline finished" in line for line in terminal_lines), terminal_lines[-5:]
    assert image_files(tmp_path / "out" / "3-upscale-images")
    videos = [
        file_name
        for _, _, file_names in os.walk(tmp_path / "out" / "4-images-to-video")
        for file_name in file_names
        if file_name.endswith(".mp4")
    ]
    assert videos


@needs_internet
def test_azure_reads_each_line_in_the_style_of_its_emotion(tmp_path):
    """
    Needs a real Azure key in ".env" (AZURE_SUBSCRIPTION_KEY and AZURE_REGION). Also downloads the emotion model (about 330 MB) the first time.
    """
    from dotenv import load_dotenv

    load_dotenv(os.path.join(REPO_DIR, ".env"))
    if not (os.getenv("AZURE_SUBSCRIPTION_KEY") and os.getenv("AZURE_REGION")):
        pytest.skip("No Azure key in .env")

    from EmotionAnalyzer import get_emotion_analyzer
    from TextToSpeech import TextToSpeech
    from VideoCreatorFromImages import get_audio_duration

    # Aria has many styles. The emotion model should pick different ones for these lines.
    tts = TextToSpeech(
        {"tts_engine": "azure", "azure_voice_name": "en-US-AriaNeural", "azure_voice_style": "auto"}
    )
    analyzer = get_emotion_analyzer()
    happy_emotion, _ = analyzer.get_emotion("I'm so happy to see you!")
    angry_emotion, _ = analyzer.get_emotion("Get out of my sight right now!")
    assert happy_emotion == "joy"
    assert angry_emotion == "anger"

    output_file = str(tmp_path / "styled.mp3")
    tts.generate_audio(["I'm so happy to see you!", "Get out of my sight right now!"], output_file)

    assert get_audio_duration(output_file) > 2
