import os
from types import SimpleNamespace

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
            lambda output, relative: os.path.join(
                output, "panel-by-panel", "not-grouped-by-page", relative
            ),
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
    save_image(str(tmp_path / "One Piece" / "Ch 1" / "page_1.png"))

    return view, error_messages


def test_each_step_reads_the_folder_the_step_before_it_saved_to(tmp_path, monkeypatch):
    ran_steps = []
    view, error_messages = make_pipeline_view(tmp_path, monkeypatch, ran_steps)

    view.run_pipeline(["Panel-By-Panel", "Upscale Images", "Images To Video"], view.input_directory)

    output = tmp_path / "output"
    assert ran_steps == [
        ("Panel-By-Panel", str(tmp_path / "One Piece")),
        (
            "Upscale Images",
            str(output / "2-panel-by-panel" / "panel-by-panel" / "not-grouped-by-page" / "One Piece"),
        ),
        ("Images To Video", str(output / "3-upscale-images" / "One Piece")),
    ]
    assert (output / "3-upscale-images" / "One Piece" / "Ch 1" / "page_1.png").exists()
    assert error_messages == []


def test_pipeline_stops_when_a_step_saves_nothing(tmp_path, monkeypatch):
    ran_steps = []
    view, error_messages = make_pipeline_view(
        tmp_path, monkeypatch, ran_steps, upscale_saves_images=False
    )

    view.run_pipeline(["Upscale Images", "Images To Video"], view.input_directory)

    assert [step for step, _ in ran_steps] == ["Upscale Images"]
    assert "didn't save any images" in error_messages[-1]


def test_pipeline_stops_when_a_step_fails(tmp_path, monkeypatch):
    ran_steps = []
    view, error_messages = make_pipeline_view(tmp_path, monkeypatch, ran_steps)
    view.parent_gui.MagiPanelByPanelView.start_job = lambda input_directory, output_directory: False

    view.run_pipeline(["Panel-By-Panel", "Upscale Images"], view.input_directory)

    assert ran_steps == []
    assert 'Pipeline stopped. "Panel-By-Panel" failed' in error_messages[-1]


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
        str(output / "2-panel-by-panel" / "panel-by-panel" / "not-grouped-by-page" / "One Piece" / "Ch 1"),
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
    upscaled_chapter = tmp_path / "upscaled" / "panels" / "Ch 1"

    def upscale():
        gui.UpscaleImagesView.process_image_folder(
            str(chapter), [{"name": "panel_1.png"}], str(tmp_path / "panels"), str(tmp_path / "upscaled")
        )

    upscale()
    assert (upscaled_chapter / "panel-text.json").read_text() == '[["Hello."]]'

    # Panels made later without the text: the old text must not be used for them.
    (chapter / "panel-text.json").unlink()
    upscale()
    assert not (upscaled_chapter / "panel-text.json").exists()
