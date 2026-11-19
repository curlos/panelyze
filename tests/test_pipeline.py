import os
from types import SimpleNamespace

from PIL import Image

import gui_classes.PipelineView as pipeline_module
from gui_classes.PipelineView import (
    PipelineView,
    get_settings_review_lines,
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
        terminal_output=SimpleNamespace(
            terminal_output_list_view=None,
            update_terminal_with_error_message=error_messages.append,
        ),
        MagiPanelByPanelView=FakeStepView(
            "Panel-By-Panel",
            ran_steps,
            lambda output, relative: os.path.join(
                output, "panel-by-panel", "not-grouped", relative
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
            str(output / "2-panel-by-panel" / "panel-by-panel" / "not-grouped" / "One Piece"),
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

    review_lines = get_settings_review_lines(storage, ["Images To Video"])

    assert review_lines == [
        "Images To Video: 9:16, 1080p, mp4, Text-To-Speech (edge, en-US-AriaNeural)"
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
