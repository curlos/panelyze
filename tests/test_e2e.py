"""
End-to-end tests: the real tools (Magi, waifu2x, edge-tts, MangaDex, MoviePy) driven through the app's own Submit buttons, on a fake page with no window.

Slow (a few minutes) and some need the internet, so they only run with: pytest -m e2e
"""
import os
import shutil
import socket

import pytest
from PIL import Image

from tests.fake_gui import fake_event

pytestmark = pytest.mark.e2e

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Where the test chapter is saved after the first download, so later runs don't download it again. It only ever holds the Dragon Ball chapter, and it's in ".gitignore".
TEST_CHAPTER_CACHE_DIR = os.path.join(REPO_DIR, "test-chapter-cache", "dragon-ball-ch-93")
TEST_CHAPTER_PAGE_COUNT = 3
# The chapter every test download uses: Dragon Ball, chapter 93. Only its first 3 pages are downloaded. The downloader numbers the files from 00, so "00" is the cover (page 1), "01" is page 2 and "02" is page 3.
MANGADEX_CHAPTER_URL = os.environ.get(
    "PANELYZE_TEST_MANGADEX_URL",
    "https://mangadex.org/chapter/ac33cc50-a1b2-49b0-a388-0d0ee4ebce18/14",
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


def image_paths(directory):
    return sorted(
        os.path.join(folder, file_name)
        for folder, _, file_names in os.walk(directory)
        for file_name in file_names
        if file_name.endswith((".png", ".jpg", ".jpeg", ".webp"))
    )


def image_files(directory):
    return sorted(
        file_name
        for _, _, file_names in os.walk(directory)
        for file_name in file_names
        if file_name.endswith((".png", ".jpg", ".jpeg", ".webp"))
    )


def download_test_chapter(output_directory):
    """
    Download the first 3 pages of the test chapter: the cover and 2 story pages with panels and text.
    """
    from default_settings import DEFAULT_SETTINGS
    from download_from_mangadex import download_from_mangadex
    from tests.fake_gui import FakeClientStorage

    storage = FakeClientStorage()
    storage.values.update(DEFAULT_SETTINGS)
    storage.set("use_start_and_end_pages", True)
    storage.set("start_page", "1")
    storage.set("end_page", "3")

    download_from_mangadex(MANGADEX_CHAPTER_URL, str(output_directory), None, storage)


@pytest.fixture(scope="session")
def test_chapter():
    """
    The folder with the test chapter's pages (Dragon Ball, chapter 93). It's downloaded the first time and reused after that.
    """
    if len(image_files(TEST_CHAPTER_CACHE_DIR)) != TEST_CHAPTER_PAGE_COUNT:
        if not has_internet():
            pytest.skip("The test chapter isn't saved yet and there's no internet connection")

        # Start over so a download that stopped halfway can't leave a partial chapter behind.
        shutil.rmtree(TEST_CHAPTER_CACHE_DIR, ignore_errors=True)
        download_test_chapter(TEST_CHAPTER_CACHE_DIR)

    pages = image_files(TEST_CHAPTER_CACHE_DIR)
    assert len(pages) == TEST_CHAPTER_PAGE_COUNT, f"Couldn't download the test chapter: {pages}"
    return TEST_CHAPTER_CACHE_DIR


def test_panel_by_panel_splits_real_pages(gui, tmp_path, test_chapter):
    run_submit(gui.MagiPanelByPanelView, test_chapter, tmp_path / "out")

    # The cover has no panels, but pages 2 and 3 are story pages.
    assert image_files(tmp_path / "out" / "panel-by-panel" / "not-grouped-by-page")


@needs_waifu2x
def test_upscale_doubles_a_real_page(gui, tmp_path, test_chapter):
    chapter = tmp_path / "Test Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    shutil.copy(image_paths(test_chapter)[0], chapter / "page.png")
    original_width, original_height = Image.open(chapter / "page.png").size
    gui.page.client_storage.set("upscale_ratio", 2)
    gui.page.client_storage.set("image_format", "png")
    # The real pages are big, so 2x would go past 4K. The 4K limit has its own test.
    gui.page.client_storage.set("limit_upscale_to_4k", False)

    run_submit(gui.UpscaleImagesView, tmp_path / "Test Manga", tmp_path / "out")

    output_image = tmp_path / "out" / "Test Manga" / "Ch 1" / "page.png"
    assert Image.open(output_image).size == (original_width * 2, original_height * 2)


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


@needs_internet
def test_images_to_video_reads_and_voices_real_pages(gui, tmp_path, test_chapter, capsys):
    """
    The slow, full version: Magi reads the text on the real pages, edge-tts says it out loud, and the video is as long as the voice-over needs.
    """
    from moviepy import VideoFileClip

    storage = gui.page.client_storage
    storage.set("use_text_to_speech_azure", True)
    storage.set("tts_engine", "edge")
    storage.set("video_height", "360")

    run_submit(gui.ImagesToVideoView, test_chapter, tmp_path / "out")

    audio_files = [
        file_name
        for _, _, file_names in os.walk(tmp_path / "out")
        for file_name in file_names
        if file_name.endswith(".mp3")
    ]
    videos = [
        os.path.join(folder, file_name)
        for folder, _, file_names in os.walk(tmp_path / "out")
        for file_name in file_names
        if file_name.endswith(".mp4")
    ]
    assert audio_files, "Magi found no text to say out loud on the test pages"
    assert len(videos) == 1
    video = VideoFileClip(videos[0])
    assert video.duration > 2
    video.close()

    # What Magi found was saved (as JSON, from the real results), so making the video again doesn't read the text again.
    saved_magi_data = [
        os.path.join(folder, file_name)
        for folder, _, file_names in os.walk(tmp_path / "out")
        for file_name in file_names
        if file_name == "magi-data.json"
    ]
    assert len(saved_magi_data) == 1
    capsys.readouterr()
    run_submit(gui.ImagesToVideoView, test_chapter, tmp_path / "out")
    assert "get_essential_text_list_in_images" not in capsys.readouterr().out


@needs_internet
def test_mangadex_downloads_real_pages(tmp_path):
    download_test_chapter(tmp_path / "download")

    assert len(image_files(tmp_path / "download")) == TEST_CHAPTER_PAGE_COUNT
    # Each manga has its own folder, and the chapter folder has the chapter's title.
    page = os.path.relpath(image_paths(tmp_path / "download")[0], tmp_path / "download")
    assert os.path.dirname(page) == os.path.join(
        "Dragon Ball (Official Colored)", "Vol. 8 Ch. 93 - Goku's Charge"
    )


@needs_internet
def test_pipeline_runs_every_step_on_a_real_page(gui, tmp_path):
    if not shutil.which("waifu2x-ncnn-vulkan"):
        pytest.skip("waifu2x-ncnn-vulkan isn't installed")

    storage = gui.page.client_storage
    storage.set("use_start_and_end_pages", True)
    storage.set("start_page", "1")
    storage.set("end_page", "3")
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
    # The cover has no panels, but pages 2 and 3 are story pages.
    assert image_files(tmp_path / "out" / "2-panel-by-panel")
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
