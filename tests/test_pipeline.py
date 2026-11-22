import threading
import os
from types import SimpleNamespace

import flet as ft
import pytest

from utils import get_panels_folder
from PIL import Image

import gui_classes.PipelineView as pipeline_module
from gui_classes.PipelineView import (
    PipelineView,
    get_settings_review,
    get_step_output_directory,
)
from utils import get_relative_output_path


def save_image(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", (10, 10)).save(path)


def copy_images(input_directory, output_directory, get_output_chapter_directory):
    """
    Copies every image like the real steps do: the output keeps the path relative to the input folder's parent.
    """
    for directory, _, file_names in os.walk(input_directory):
        for file_name in file_names:
            relative_path = get_relative_output_path(directory, input_directory)
            save_image(
                os.path.join(
                    get_output_chapter_directory(output_directory, relative_path),
                    file_name,
                )
            )


class FakeStepView:
    def __init__(self, name, ran_steps, get_output_chapter_directory=None):
        self.name = name
        self.ran_steps = ran_steps
        self.get_output_chapter_directory = get_output_chapter_directory
        self.cancel_event = threading.Event()

    def get_cancel_message(self):
        return "Cancelling..."

    def cancel_job(self):
        pass

    def start_job(self, input_directory, output_directory):
        self.ran_steps.append((self.name, input_directory))

        if self.get_output_chapter_directory:
            copy_images(
                input_directory, output_directory, self.get_output_chapter_directory
            )
        return True


def make_pipeline_view(tmp_path, monkeypatch, ran_steps, upscale_saves_images=True):
    monkeypatch.setattr(pipeline_module, "open_directory", lambda path: None)

    error_messages = []
    parent_gui = SimpleNamespace(
        page=SimpleNamespace(client_storage={}),
        terminal_output=SimpleNamespace(
            terminal_output_list_view=None,
            update_terminal_with_error_message=error_messages.append,
        ),
        MagiPanelByPanelView=FakeStepView(
            "Panel-By-Panel",
            ran_steps,
            # Where the real Panel-By-Panel saves (never grouped by page in a Pipeline).
            lambda output, relative: get_panels_folder(output, relative),
        ),
        UpscaleImagesView=FakeStepView(
            "Upscale Images",
            ran_steps,
            (lambda output, relative: os.path.join(output, relative))
            if upscale_saves_images
            else None,
        ),
        ImagesToVideoView=FakeStepView("Images To Video", ran_steps),
    )

    # Skip the Flet GUI setup. Only the pipeline logic is tested here.
    view = PipelineView.__new__(PipelineView)
    view.parent_gui = parent_gui
    view.input_directory = str(tmp_path / "One Piece")
    view.output_directory = str(tmp_path / "output")
    # The list of steps and their status under the Run button.
    view.step_status_column = ft.Column()
    view.cancel_button = ft.FilledTonalButton()
    view.cancelled = False
    save_image(str(tmp_path / "One Piece" / "Ch 1" / "page_1.png"))

    return view, error_messages


def get_step_statuses(view):
    # Each row is an icon, the step's name, and its time when it's done.
    return [(row.controls[1].value, row.controls[0].name) for row in view.step_status_column.controls]


def test_each_step_reads_the_folder_the_step_before_it_saved_to(tmp_path, monkeypatch):
    ran_steps = []
    view, error_messages = make_pipeline_view(tmp_path, monkeypatch, ran_steps)

    view.run_pipeline(["Panel-By-Panel", "Upscale Images", "Images To Video"], view.input_directory)

    output = tmp_path / "output"
    assert ran_steps == [
        ("Panel-By-Panel", str(tmp_path / "One Piece")),
        (
            "Upscale Images",
            str(output / "2-panel-by-panel" / "One Piece"),
        ),
        ("Images To Video", str(output / "3-upscale-images" / "One Piece")),
    ]
    assert (output / "3-upscale-images" / "One Piece" / "Ch 1" / "page_1.png").exists()
    assert error_messages == []
    # Every step is ticked under the Run button, with its time.
    assert get_step_statuses(view) == [(step, "check_circle") for step in ("Panel-By-Panel", "Upscale Images", "Images To Video")]
    assert all(row.controls[2].value.endswith("s") for row in view.step_status_column.controls)


def test_pipeline_stops_when_a_step_saves_nothing(tmp_path, monkeypatch):
    ran_steps = []
    view, error_messages = make_pipeline_view(
        tmp_path, monkeypatch, ran_steps, upscale_saves_images=False
    )

    view.run_pipeline(["Upscale Images", "Images To Video"], view.input_directory)

    assert [step for step, _ in ran_steps] == ["Upscale Images"]
    assert "didn't save any images" in error_messages[-1]
    assert get_step_statuses(view) == [("Upscale Images", "cancel"), ("Images To Video", "radio_button_unchecked")]
    assert view.step_status_column.controls[0].controls[2].value == "no images saved"


def test_pipeline_stops_when_a_step_fails(tmp_path, monkeypatch):
    ran_steps = []
    view, error_messages = make_pipeline_view(tmp_path, monkeypatch, ran_steps)
    view.parent_gui.MagiPanelByPanelView.start_job = lambda input_directory, output_directory: False

    view.run_pipeline(["Panel-By-Panel", "Upscale Images"], view.input_directory)

    assert ran_steps == []
    assert 'Pipeline stopped. "Panel-By-Panel" failed' in error_messages[-1]
    # Under the Run button: the step that failed, and the one that never ran.
    assert get_step_statuses(view) == [("Panel-By-Panel", "cancel"), ("Upscale Images", "radio_button_unchecked")]


def run_pipeline_and_get_opened_folders(tmp_path, monkeypatch, steps, chapters):
    ran_steps = []
    view, _ = make_pipeline_view(tmp_path, monkeypatch, ran_steps)
    for chapter in chapters:
        save_image(str(tmp_path / "One Piece" / chapter / "page_1.png"))

    opened_folders = []
    monkeypatch.setattr(pipeline_module, "open_directory", opened_folders.append)
    view.run_pipeline(steps, view.input_directory)
    return opened_folders


def test_one_chapter_opens_the_pipeline_folder_and_the_chapter_folder(tmp_path, monkeypatch):
    opened_folders = run_pipeline_and_get_opened_folders(tmp_path, monkeypatch, ["Panel-By-Panel"], [])

    output = tmp_path / "output"
    assert opened_folders == [
        str(output),
        str(output / "2-panel-by-panel" / "One Piece" / "Ch 1"),
    ]


def test_several_chapters_open_the_pipeline_folder_and_the_last_step_folder(tmp_path, monkeypatch):
    opened_folders = run_pipeline_and_get_opened_folders(
        tmp_path, monkeypatch, ["Panel-By-Panel", "Upscale Images"], ["Ch 2"]
    )

    output = tmp_path / "output"
    assert opened_folders == [str(output), str(output / "3-upscale-images")]


def test_a_video_opens_the_pipeline_folder_and_the_video_folder(tmp_path, monkeypatch):
    opened_folders = run_pipeline_and_get_opened_folders(
        tmp_path, monkeypatch, ["Panel-By-Panel", "Images To Video"], []
    )

    output = tmp_path / "output"
    assert opened_folders == [str(output), str(output / "4-images-to-video")]


def test_step_output_folders_are_numbered_in_order():
    assert get_step_output_directory("/out", "Panel-By-Panel") == os.path.join(
        "/out", "2-panel-by-panel"
    )


def test_settings_review_only_lists_the_selected_steps():
    storage = {
        "video_aspect_ratio": "9:16",
        "video_height": 1080,
        "video_extension": "mp4",
        "use_text_to_speech_azure": True,
        "tts_engine": "edge",
        "azure_voice_name": "en-US-AriaNeural",
    }

    review = get_settings_review(storage, ["Images To Video"])

    assert review == [
        ("Images To Video", "9:16, 1080p, mp4, Text-To-Speech (edge, en-US-AriaNeural)")
    ]


def test_settings_review_says_where_the_reading_direction_comes_from():
    def panel_by_panel_review(storage, steps):
        return dict(get_settings_review(storage, steps))["Panel-By-Panel"]

    assert "Automatic (from MangaDex or comix.to)" in panel_by_panel_review({}, ["Download", "Panel-By-Panel"])
    assert "Automatic (from the images" in panel_by_panel_review({"reading_direction": "auto"}, ["Panel-By-Panel"])
    assert "Left to right (Comics)" in panel_by_panel_review({"reading_direction": "ltr"}, ["Download", "Panel-By-Panel"])


def test_old_images_from_a_previous_run_are_not_used(tmp_path, monkeypatch):
    ran_steps = []
    view, error_messages = make_pipeline_view(
        tmp_path, monkeypatch, ran_steps, upscale_saves_images=False
    )
    # Leftover from an earlier run.
    save_image(str(tmp_path / "output" / "3-upscale-images" / "One Piece" / "Ch 1" / "old.png"))

    view.run_pipeline(["Upscale Images", "Images To Video"], view.input_directory)

    assert [step for step, _ in ran_steps] == ["Upscale Images"]
    assert "didn't save any images" in error_messages[-1]


def get_review_texts(gui):
    from tests.fake_gui import get_all_controls
    import flet as ft

    return [
        control.value
        for control in get_all_controls(gui.PipelineView.review_column)
        if isinstance(control, ft.Text)
    ]


def test_the_review_has_labelled_sections_for_the_steps_the_settings_and_the_final_result(make_gui):
    gui = make_gui()
    pipeline = gui.PipelineView
    pipeline.step_checkboxes["Panel-By-Panel"].value = True
    pipeline.step_checkboxes["Upscale Images"].value = True

    pipeline.refresh_review()
    texts = get_review_texts(gui)

    assert texts[:1] == ["STEPS"]
    # Each step is shown as its number, then its icon, then its name.
    assert texts[1:5] == ["1.", "Panel-By-Panel", "2.", "Upscale Images"]
    assert "SETTINGS EACH STEP WILL USE" in texts
    assert "Panel-By-Panel" in texts and "Upscale Images" in texts
    assert "FINAL RESULT" in texts
    assert "The upscaled images will be saved in:" in texts
    assert os.path.join(pipeline.output_directory, "3-upscale-images") in texts


def test_the_final_result_follows_the_last_step_picked(make_gui):
    gui = make_gui()
    pipeline = gui.PipelineView
    pipeline.step_checkboxes["Images To Video"].value = True

    pipeline.refresh_review()

    assert "The videos will be saved in:" in get_review_texts(gui)


def test_the_review_asks_for_a_step_when_none_is_picked(make_gui):
    gui = make_gui()

    gui.PipelineView.refresh_review()

    assert get_review_texts(gui) == ["Pick at least one step."]


def test_panel_by_panel_reads_the_text_only_when_the_video_will_use_it(tmp_path, monkeypatch):
    ran_steps = []
    view, _ = make_pipeline_view(tmp_path, monkeypatch, ran_steps)
    panel_by_panel = view.parent_gui.MagiPanelByPanelView
    read_text_when_run = []
    run_panel_by_panel = panel_by_panel.start_job
    panel_by_panel.start_job = lambda *args: read_text_when_run.append(
        panel_by_panel.read_text_for_video
    ) or run_panel_by_panel(*args)
    storage = view.parent_gui.page.client_storage
    steps = ["Panel-By-Panel", "Images To Video"]

    storage.update(use_text_to_speech_azure=True)
    view.run_pipeline(steps, view.input_directory)
    # Highlighting needs where the text is on each panel, so the video reads the panels itself.
    storage.update(highlight_text_boxes_in_images=True)
    view.run_pipeline(steps, view.input_directory)
    # A fixed time per image doesn't use the text at all.
    storage.update(use_text_to_speech_azure=False, highlight_text_boxes_in_images=False)
    view.run_pipeline(steps, view.input_directory)

    assert read_text_when_run == [True, False, False]
    # It's only on for the Pipeline's own step.
    assert panel_by_panel.read_text_for_video is False


def test_the_review_says_when_panel_by_panel_reads_the_text():
    storage = {"use_reading_speed_wpm": True}

    review = dict(get_settings_review(storage, ["Panel-By-Panel", "Images To Video"]))

    assert review["Panel-By-Panel"].endswith(", also reads the text for the video")


def test_upscaling_keeps_the_text_panel_by_panel_read_with_the_images(make_gui, tmp_path, monkeypatch):
    import shutil

    import gui_classes.UpscaleImagesView as upscale_module

    gui = make_gui()
    # A fake waifu2x that "upscales" a whole folder by copying its images.
    monkeypatch.setattr(
        upscale_module,
        "upscale_with_waifu2x",
        lambda input_image, output_image, **kwargs: shutil.copytree(input_image, output_image, dirs_exist_ok=True),
    )
    monkeypatch.setattr(
        upscale_module, "ProcessManager", lambda: SimpleNamespace(process=SimpleNamespace(returncode=0))
    )
    chapter = tmp_path / "panels" / "Ch 1"
    save_image(str(chapter / "panel_1.png"))
    (chapter / "panel-text.json").write_text('[["Hello."]]')
    (chapter / "reading-direction.txt").write_text("ltr")
    upscaled_chapter = tmp_path / "upscaled" / "panels" / "Ch 1"

    def upscale():
        gui.UpscaleImagesView.process_image_folder(
            str(chapter), [{"name": "panel_1.png"}], str(tmp_path / "panels"), str(tmp_path / "upscaled")
        )

    upscale()
    assert (upscaled_chapter / "panel-text.json").read_text() == '[["Hello."]]'
    assert (upscaled_chapter / "reading-direction.txt").read_text() == "ltr"

    # Panels made later without the text: the old text must not be used for them.
    (chapter / "panel-text.json").unlink()
    (chapter / "reading-direction.txt").unlink()
    upscale()
    assert not (upscaled_chapter / "panel-text.json").exists()
    assert not (upscaled_chapter / "reading-direction.txt").exists()


def run_panel_by_panel_on_picked_input(gui, tmp_path, monkeypatch):
    """
    Runs only Panel-By-Panel (faked) and returns the chapter folders and pages it was given.
    """
    from tests.fake_gui import fake_event

    given_pages = []
    given_folders = []

    def fake_start_job(input_directory, output_directory):
        given_folders.append(input_directory)
        for directory, _, file_names in os.walk(input_directory):
            for file_name in sorted(file_names):
                given_pages.append(os.path.relpath(os.path.join(directory, file_name), input_directory))
        save_image(os.path.join(output_directory, "x", "1.png"))
        return True

    pipeline = gui.PipelineView
    monkeypatch.setattr(gui.MagiPanelByPanelView, "start_job", fake_start_job)
    pipeline.step_checkboxes["Panel-By-Panel"].value = True
    pipeline.output_directory = str(tmp_path / "out")

    pipeline.handle_run_pipeline(fake_event())
    # The temporary folder is deleted afterwards.
    assert given_folders and not os.path.exists(given_folders[0])
    return given_pages


def test_picked_comic_files_flow_into_panel_by_panel(make_gui, tmp_path, monkeypatch):
    import zipfile
    from tests.fake_gui import fake_event

    gui = make_gui()
    cbz_path = tmp_path / "Invincible 001.cbz"
    with zipfile.ZipFile(cbz_path, "w") as cbz:
        cbz.writestr("2.png", b"2")
        cbz.writestr("1.png", b"1")
    gui.PipelineView.handle_comic_files_picked(
        fake_event(files=[SimpleNamespace(path=str(cbz_path)), SimpleNamespace(path=str(tmp_path / "notes.txt"))])
    )

    assert gui.PipelineView.input_comic_paths == [str(cbz_path)]
    assert run_panel_by_panel_on_picked_input(gui, tmp_path, monkeypatch) == ["001.png", "002.png"]



def test_picking_one_input_clears_the_others(make_gui, tmp_path):
    from tests.fake_gui import fake_event

    gui = make_gui()
    pipeline = gui.PipelineView

    pipeline.handle_comic_files_picked(fake_event(files=[SimpleNamespace(path=str(tmp_path / "a.cbz"))]))
    pipeline.handle_images_picked(fake_event(files=[SimpleNamespace(path=str(tmp_path / "1.png"))]))
    assert pipeline.input_comic_paths == []

    pipeline.handle_directory_picked(fake_event(path=str(tmp_path)), "input")
    assert pipeline.input_image_paths == [] and pipeline.input_directory == str(tmp_path)


@pytest.mark.parametrize(
    "url, expected_downloader",
    [
        ("https://comix.to/title/w25zn-slam-dunk", "comix.to"),
        ("https://mangadex.org/chapter/abc", "MangaDex"),
    ],
)
def test_the_download_step_uses_the_site_the_link_is_from(make_gui, tmp_path, monkeypatch, url, expected_downloader):
    from tests.fake_gui import fake_event

    used = []

    def fake_downloader(name):
        def download(url, output_directory, terminal_output_list_view, storage, cancel_button=None):
            used.append((name, url))
            save_image(os.path.join(output_directory, "Slam Dunk", "Chapter_1", "001.png"))

        return download

    from gui_classes import MangaDexDownloaderView

    monkeypatch.setattr(MangaDexDownloaderView, "download_from_comix", fake_downloader("comix.to"))
    monkeypatch.setattr(MangaDexDownloaderView, "download_from_mangadex", fake_downloader("MangaDex"))
    gui = make_gui()
    pipeline = gui.PipelineView
    pipeline.step_checkboxes["Download"].value = True
    pipeline.mangadex_url_text_field.value = url
    pipeline.output_directory = str(tmp_path / "out")

    pipeline.handle_run_pipeline(fake_event())

    assert used == [(expected_downloader, url)]
    assert (tmp_path / "out" / "1-download" / "Slam Dunk" / "Chapter_1" / "001.png").exists()


def test_the_pipeline_refuses_download_text_that_is_not_a_link(make_gui, tmp_path, monkeypatch):
    from tests.fake_gui import fake_event

    gui = make_gui()
    errors = []
    monkeypatch.setattr(gui.terminal_output, "update_terminal_with_error_message", errors.append)
    pipeline = gui.PipelineView
    pipeline.step_checkboxes["Download"].value = True
    pipeline.mangadex_url_text_field.value = "slam dunk"
    pipeline.output_directory = str(tmp_path / "out")

    pipeline.handle_run_pipeline(fake_event())

    assert errors == ["ERROR: Not a web link (it should start with https://): slam dunk"]
    assert not (tmp_path / "out").exists()


def test_after_a_download_the_next_steps_start_from_the_series_folder(tmp_path):
    from gui_classes.PipelineView import get_next_step_input_directory

    downloads = tmp_path / "1-download"
    (downloads / "Shachou to Sake to Hoshi" / "Ch 8").mkdir(parents=True)
    # So the next steps save to "2-panel-by-panel/Shachou to Sake to Hoshi", not "2-panel-by-panel/1-download/Shachou to Sake to Hoshi".
    assert get_next_step_input_directory("Download", "", str(downloads)) == str(downloads / "Shachou to Sake to Hoshi")

    # A MangaDex list of several series: the whole folder.
    (downloads / "Bleach").mkdir()
    assert get_next_step_input_directory("Download", "", str(downloads)) == str(downloads)


def test_cancel_stops_the_step_that_is_running_and_the_steps_after_it(make_gui, tmp_path, monkeypatch):
    from tests.fake_gui import fake_event

    gui = make_gui()
    pipeline = gui.PipelineView
    for step in ("Panel-By-Panel", "Upscale Images"):
        pipeline.step_checkboxes[step].value = True
    for chapter in ("Ch 1", "Ch 2"):
        save_image(str(tmp_path / "One Piece" / chapter / "page_1.png"))
    pipeline.input_directory = str(tmp_path / "One Piece")
    pipeline.output_directory = str(tmp_path / "out")
    split = []
    seen = []

    def split_and_click_cancel(image_folder, *args):
        split.append(os.path.basename(image_folder))
        seen.append((pipeline.cancel_button.visible, pipeline.cancel_button.disabled))
        pipeline.cancel_button.on_click(fake_event())
        seen.append((pipeline.cancel_button.text, pipeline.cancel_button.disabled))

    monkeypatch.setattr(gui.MagiPanelByPanelView, "process_image_folder", split_and_click_cancel)
    monkeypatch.setattr(gui.UpscaleImagesView, "start_job", lambda *args: pytest.fail("Upscale shouldn't start"))

    pipeline.handle_run_pipeline(fake_event())

    # Shown and clickable while it runs, "Cancelling..." once clicked, and the chapter after the current one isn't split.
    assert seen == [(True, False), ("Cancelling...", True)]
    assert split == ["Ch 1"]
    assert get_step_statuses(pipeline) == [("Panel-By-Panel", "do_not_disturb_on"), ("Upscale Images", "radio_button_unchecked")]
    # Shown as cancelled (with its timer), not as an error.
    panel = gui.terminal_output.progress_panel
    assert panel.title.startswith('Pipeline cancelled at "Panel-By-Panel"')
    assert panel.state == "cancelled" and panel.ended_at is not None
    # Hidden and ready for the next run.
    assert not pipeline.cancel_button.visible and gui.is_job_running is False


def test_cancel_stops_the_download_step(make_gui, tmp_path, monkeypatch):
    from gui_classes import MangaDexDownloaderView
    from tests.fake_gui import fake_event
    from utils import DownloadCancelled, get_cancel_event

    def download_until_cancelled(url, output_directory, terminal_output_list_view, storage, cancel_button=None):
        # Like the real downloaders: Cancel now sets their own flag.
        cancel_event = get_cancel_event(cancel_button)
        cancel_button.on_click(fake_event())
        assert cancel_event.is_set()
        raise DownloadCancelled("Download cancelled")

    monkeypatch.setattr(MangaDexDownloaderView, "download_from_mangadex", download_until_cancelled)
    gui = make_gui()
    pipeline = gui.PipelineView
    pipeline.step_checkboxes["Download"].value = True
    pipeline.step_checkboxes["Panel-By-Panel"].value = True
    pipeline.mangadex_url_text_field.value = "https://mangadex.org/chapter/abc"
    pipeline.output_directory = str(tmp_path / "out")
    monkeypatch.setattr(gui.MagiPanelByPanelView, "start_job", lambda *args: pytest.fail("Panel-By-Panel shouldn't start"))

    pipeline.handle_run_pipeline(fake_event())

    assert get_step_statuses(pipeline) == [("Download", "do_not_disturb_on"), ("Panel-By-Panel", "radio_button_unchecked")]
    assert gui.terminal_output.progress_panel.state == "cancelled"
    assert not pipeline.cancel_button.visible and pipeline.cancel_button.text == "Cancel"


def test_a_step_that_finishes_after_cancel_still_stops_the_next_one(make_gui, tmp_path, monkeypatch):
    from tests.fake_gui import fake_event

    gui = make_gui()
    pipeline = gui.PipelineView
    for step in ("Panel-By-Panel", "Upscale Images"):
        pipeline.step_checkboxes[step].value = True
    save_image(str(tmp_path / "One Piece" / "Ch 1" / "page_1.png"))
    pipeline.input_directory = str(tmp_path / "One Piece")
    pipeline.output_directory = str(tmp_path / "out")

    def split_and_click_cancel(image_folder, images, input_directory, output_directory):
        # Cancel on the last chapter: the chapter still finishes.
        pipeline.cancel_button.on_click(fake_event())
        save_image(os.path.join(output_directory, "One Piece", "Ch 1", "panel_1.png"))

    monkeypatch.setattr(gui.MagiPanelByPanelView, "process_image_folder", split_and_click_cancel)
    monkeypatch.setattr(gui.UpscaleImagesView, "start_job", lambda *args: pytest.fail("Upscale shouldn't start"))

    pipeline.handle_run_pipeline(fake_event())

    assert get_step_statuses(pipeline) == [("Panel-By-Panel", "check_circle"), ("Upscale Images", "do_not_disturb_on")]
