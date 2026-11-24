"""Absolute Batman ch. 1 through Panel-By-Panel and Images To Video (voice, 1080p), with the app's own Submit buttons. Run from the worktree with: pytest -p tests.fake_gui <this file> -s"""
import os, time
from tests.fake_gui import fake_event

BASE = os.path.expanduser(r"~/Documents/Panelyze/10-amd-gaming-pc")
PAGES = os.path.join(BASE, "Downloads", "absolute batman", "Chapter_1_Absolute Batman, Vol. 1 The Zoo")
OUT = os.path.join(BASE, "benchmark-absolute-batman-ch1")


def run_submit(view, input_directory, output_directory):
    directories = view.pick_input_output_directories_container
    directories.input_directory = str(input_directory)
    directories.output_directory = str(output_directory)
    directories.handle_submit(fake_event())


def files(folder, extensions):
    return [os.path.join(d, f) for d, _, names in os.walk(folder) for f in names if f.lower().endswith(extensions)]


def test_batman(make_gui, monkeypatch):
    from gui_classes import JobView, PipelineView
    for module in (JobView, PipelineView):
        monkeypatch.setattr(module, "open_directory", lambda path: None)
    gui = make_gui()
    storage = gui.page.client_storage

    for run in (1, 2):
        start = time.time()
        run_submit(gui.MagiPanelByPanelView, PAGES, os.path.join(OUT, f"2-panels-run-{run}"))
        panels = files(os.path.join(OUT, f"2-panels-run-{run}"), (".png", ".jpg", ".webp"))
        print(f"\nPANEL-BY-PANEL run {run}: {time.time() - start:.1f} s, {len(panels)} panels", flush=True)
        assert panels

    storage.set("use_text_to_speech_azure", True)
    storage.set("tts_engine", "edge")
    storage.set("video_height", "1080")
    # Exercises today's fix: the voice-over files are deleted after the video (they used to be locked on Windows).
    storage.set("clean_up_tts_audio_files_folder", True)
    panels_folder = os.path.join(OUT, "2-panels-run-2")
    for run in (1, 2):
        video_folder = os.path.join(OUT, f"4-video-run-{run}")
        start = time.time()
        run_submit(gui.ImagesToVideoView, panels_folder, video_folder)
        videos = files(video_folder, (".mp4",))
        print(f"\nIMAGES TO VIDEO run {run}: {time.time() - start:.1f} s, videos: {videos}", flush=True)
        assert len(videos) == 1
        assert not files(video_folder, (".mp3",)), "voice-over files weren't cleaned up"
        transcripts = files(video_folder, ("transcript.txt",))
        print("transcript:", transcripts, flush=True)
        # Reading the text again each time, instead of the saved results, so run 2 shows the warm speed.
        for saved in files(video_folder, ("magi-data.json",)):
            os.remove(saved)
