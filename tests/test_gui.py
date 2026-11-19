import os
from tests.fake_gui import fake_event

TABS = [
    "MangaDex Downloader",
    "Panel-By-Panel",
    "Upscale Images",
    "Images To Video",
    "Pipeline",
    "Settings",
]


def test_app_opens_on_panel_by_panel(make_gui):
    gui = make_gui()

    assert gui.current_view == "Panel-By-Panel"
    assert gui.page.controls


def test_every_tab_opens_and_reopens(make_gui):
    gui = make_gui()
    # With a step ticked, the Pipeline tab reads the saved settings each time it opens.
    gui.PipelineView.step_checkboxes["Images To Video"].value = True

    # Twice through every tab: the Pipeline tab used to break the second time it was opened.
    for tab in TABS + TABS:
        gui.app_bar.change_view(tab)
        assert gui.current_view == tab
        assert gui.view_element is not None


def test_reset_all_settings_restores_defaults(make_gui):
    gui = make_gui()
    storage = gui.page.client_storage
    storage.set("video_height", "720")
    storage.set("tts_engine", "azure")

    gui.reset_settings_to_default()

    assert storage.get("video_height") == 1080
    assert storage.get("tts_engine") == "edge"


def test_reset_is_blocked_while_a_job_runs(make_gui):
    gui = make_gui()
    gui.page.client_storage.set("video_height", "720")
    gui.is_job_running = True

    gui.reset_settings_to_default()

    assert gui.page.client_storage.get("video_height") == "720"


def test_submit_without_folders_shows_an_error(make_gui):
    gui = make_gui()
    view = gui.MagiPanelByPanelView
    terminal_lines = gui.terminal_output.terminal_output_list_view.controls

    view.pick_input_output_directories_container.handle_submit(fake_event())

    assert "valid input and output directories" in terminal_lines[-1].value
    assert gui.is_job_running is False


def test_only_one_job_runs_at_a_time(make_gui):
    gui = make_gui()
    gui.is_job_running = True
    terminal_lines = gui.terminal_output.terminal_output_list_view.controls

    gui.UpscaleImagesView.pick_input_output_directories_container.handle_submit(
        fake_event()
    )

    assert "Another job is still running" in terminal_lines[-1].value


def test_video_shape_dropdown_saves_the_setting(make_gui):
    gui = make_gui()
    settings = gui.ImagesToVideoView.pick_input_output_directories_container
    dropdown = find_control(settings, lambda c: getattr(c, "label", None) == "Video Shape")

    dropdown.on_change(fake_event(data="9:16"))

    assert gui.page.client_storage.get("video_aspect_ratio") == "9:16"


def test_tts_engine_dropdown_shows_azure_fields(make_gui):
    gui = make_gui()
    tts_settings = find_control(
        gui.ImagesToVideoView,
        lambda c: getattr(c, "label", None) == "Text-To-Speech Engine",
    )
    tts_section = find_control(
        gui.ImagesToVideoView, lambda c: hasattr(c, "azure_key_and_region_col")
    )
    assert tts_section.azure_key_and_region_col.visible is False

    tts_settings.on_change(fake_event(data="azure"))

    assert tts_section.azure_key_and_region_col.visible is True
    assert gui.page.client_storage.get("tts_engine") == "azure"


def find_control(root, matches):
    """
    Search a control and everything inside it for the first control that "matches".
    """
    seen = set()
    stack = [root]

    while stack:
        control = stack.pop()
        if id(control) in seen or control is None:
            continue
        seen.add(id(control))

        if matches(control):
            return control

        stack.extend(control._get_children())

    raise AssertionError("Control not found")


def test_voice_list_loads_in_the_background(make_gui):
    import time

    gui = make_gui()
    tts_section = find_control(
        gui.ImagesToVideoView, lambda c: hasattr(c, "voice_names_dropdown")
    )

    for _ in range(50):
        voice_names = [option.key for option in tts_section.voice_names_dropdown.options]
        if "en-US-GuyNeural" in voice_names:
            break
        time.sleep(0.05)

    assert "en-US-GuyNeural" in voice_names
    assert tts_section.voice_names_dropdown.value == "en-US-AriaNeural"


def test_picked_images_are_processed_like_a_folder_then_cleaned_up(make_gui, tmp_path):
    from types import SimpleNamespace

    chapter = tmp_path / "Ch 1"
    chapter.mkdir()
    for name in ["page_1.png", "page_2.png", "page_3.png"]:
        (chapter / name).write_bytes(b"image")

    gui = make_gui()
    directories = gui.MagiPanelByPanelView.pick_input_output_directories_container
    seen_during_job = {}

    def fake_job(input_directory, output_directory):
        seen_during_job["input_directory"] = input_directory
        seen_during_job["images"] = sorted(os.listdir(input_directory))

    directories.on_submit = fake_job
    picked = [SimpleNamespace(path=str(chapter / "page_1.png")), SimpleNamespace(path=str(chapter / "page_3.png"))]
    directories.pick_input_images_result(fake_event(files=picked))
    directories.output_directory = str(tmp_path / "out")

    directories.handle_submit(fake_event())

    assert os.path.basename(seen_during_job["input_directory"]) == "Ch 1 - 2 images"
    assert seen_during_job["images"] == ["page_1.png", "page_3.png"]
    # The temporary copy is deleted afterwards, and the picked images stay selected.
    assert not os.path.exists(seen_during_job["input_directory"])
    assert directories.input_image_paths == [file.path for file in picked]
    assert directories.input_directory == str(chapter)


def test_reading_direction_dropdown_saves_the_setting(make_gui):
    gui = make_gui()
    assert gui.page.client_storage.get("reading_direction") == "rtl"
    dropdown = find_control(
        gui.MagiPanelByPanelView, lambda c: getattr(c, "label", None) == "Reading Direction"
    )

    dropdown.on_change(fake_event(data="ltr"))

    assert gui.page.client_storage.get("reading_direction") == "ltr"


def test_a_failed_job_shows_a_short_error_and_does_not_crash(make_gui, tmp_path, monkeypatch):
    from gui_classes import UpscaleImagesView

    monkeypatch.setattr(UpscaleImagesView, "get_waifu2x_path", lambda: None)
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"")
    gui = make_gui()

    finished = gui.UpscaleImagesView.start_job(str(tmp_path / "Manga"), str(tmp_path / "out"))

    terminal_lines = [c.value for c in gui.terminal_output.terminal_output_list_view.controls]
    assert finished is False
    assert any('"waifu2x-ncnn-vulkan" was not found' in line for line in terminal_lines)


def test_every_setting_starts_at_its_default(make_gui):
    from default_settings import DEFAULT_SETTINGS

    gui = make_gui()

    for setting_key, default_value in DEFAULT_SETTINGS.items():
        assert gui.page.client_storage.get(setting_key) == default_value, setting_key


def test_reset_keeps_the_azure_key(make_gui):
    gui = make_gui()
    gui.page.client_storage.set("azure_subscription_key", "my-key")

    gui.reset_settings_to_default()

    assert gui.page.client_storage.get("azure_subscription_key") == "my-key"


def test_number_boxes_only_save_valid_numbers(make_gui):
    gui = make_gui()
    height_box = find_control(
        gui.ImagesToVideoView, lambda c: getattr(c, "label", "") and "Video Resolution" in c.label
    )

    height_box.on_change(fake_event(data="abc", control=height_box))
    assert height_box.error_text == "Please enter a valid number."
    assert gui.page.client_storage.get("video_height") == 1080

    height_box.on_change(fake_event(data="720", control=height_box))
    assert height_box.error_text == ""
    assert gui.page.client_storage.get("video_height") == "720"


def test_picking_new_images_during_a_job_never_deletes_them(make_gui, tmp_path):
    from types import SimpleNamespace

    chapter = tmp_path / "Ch 1"
    other_folder = tmp_path / "Other"
    for folder in (chapter, other_folder):
        folder.mkdir()
        (folder / "page_1.png").write_bytes(b"image")

    gui = make_gui()
    directories = gui.MagiPanelByPanelView.pick_input_output_directories_container

    def job_while_the_user_picks_other_images(input_directory, output_directory):
        directories.pick_input_images_result(
            fake_event(files=[SimpleNamespace(path=str(other_folder / "page_1.png"))])
        )

    directories.on_submit = job_while_the_user_picks_other_images
    directories.input_directory = str(chapter)
    directories.output_directory = str(tmp_path / "out")

    directories.handle_submit(fake_event())

    assert (other_folder / "page_1.png").exists()
    assert (chapter / "page_1.png").exists()
    # The newly picked images stay picked for the next Submit.
    assert directories.input_image_paths == [str(other_folder / "page_1.png")]
