import os
import sys
from types import SimpleNamespace

import pytest
import flet as ft

from tests.fake_gui import fake_event, get_all_controls, get_shown_text

TABS = [
    "Download",
    "Panel-By-Panel",
    "Upscale Images",
    "Images To Video",
    "Pipeline",
    "Settings",
]


def test_a_new_video_is_timed_by_the_voice_and_only_its_settings_show(make_gui):
    gui = make_gui()
    controls = list(get_all_controls(gui.ImagesToVideoView))

    # The three ways to time a panel are one choice: only the voice is picked.
    radio_group = next(
        control for control in controls if isinstance(control, ft.RadioGroup)
    )
    assert radio_group.value == "use_text_to_speech_azure"
    from gui_classes.SettingsImagesToVideo import SettingsImagesToVideo

    settings = next(
        control for control in controls if isinstance(control, SettingsImagesToVideo)
    )
    for setting_key, choice in settings.radio_group_dict.items():
        assert choice["toggle_elem"].visible == (
            setting_key == "use_text_to_speech_azure"
        ), setting_key


def test_the_download_tab_links_each_site_so_a_link_can_be_found_there(make_gui):
    gui = make_gui()

    links = {
        span.text: span.url
        for control in get_all_controls(gui.MangaDexDownloaderView)
        if isinstance(control, ft.Text) and control.spans
        for span in control.spans
    }

    assert links == {
        "MangaDex": "https://mangadex.org",
        "comix.to": "https://comix.to",
        "Internet Archive": "https://archive.org/details/comics",
    }
    # "Any web page" is any site, so it isn't a link.
    assert any(
        isinstance(control, ft.Text) and control.value == "Any web page"
        for control in get_all_controls(gui.MangaDexDownloaderView)
    )


def test_every_tooltip_is_a_box_on_top_of_the_page(make_gui):
    gui = make_gui()
    views = [
        gui.app_bar,
        gui.terminal_output,
        gui.MangaDexDownloaderView,
        gui.MagiPanelByPanelView,
        gui.UpscaleImagesView,
        gui.ImagesToVideoView,
        gui.PipelineView,
        gui.AppSettingsView,
    ]
    tooltips = [
        control.tooltip
        for view in views
        for control in get_all_controls(view)
        if getattr(control, "tooltip", None)
    ]

    # Not plain text floating over the page (see "Nord.tooltip").
    assert len(tooltips) > 10
    assert all(
        isinstance(tooltip, ft.Tooltip) and tooltip.bgcolor and tooltip.border
        for tooltip in tooltips
    )


def test_app_opens_on_download(make_gui):
    gui = make_gui()

    # A new user has nothing to split into panels yet, so the first step is pasting a link.
    assert gui.current_view == "Download"
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


def test_the_terminal_stays_on_the_page_when_switching_tabs(make_gui):
    gui = make_gui()
    page_controls_before = list(gui.page.controls)

    for tab in TABS:
        gui.app_bar.change_view(tab)

        # Taking the terminal off the page would reset its scroll position.
        assert gui.page.controls == page_controls_before
        assert gui.terminal_output.page is gui.page
        assert gui.view_slot.content is gui.view_element


def test_the_settings_page_shows_which_gpu_the_ai_models_use(make_gui):
    import time

    from gui_classes import Nord

    gui = make_gui()
    assert gui.AppSettingsView.device_text.value == "Checking..."

    # Found in the background the first time the page is opened (a fixed answer in tests, see "conftest.py").
    gui.app_bar.change_view("Settings")
    for _ in range(100):
        if gui.AppSettingsView.device_text.spans:
            break
        time.sleep(0.02)

    spans = gui.AppSettingsView.device_text.spans
    # "Checking..." is gone (Flet would show it in front of the spans).
    assert not gui.AppSettingsView.device_text.value
    assert (
        "".join(span.text for span in spans)
        == "The AI models run on the Test GPU. Not used: the Old GPU (PyTorch can't run on it)."
    )
    # Every GPU's name stands out, used or not.
    assert [
        span.text for span in spans if span.style and span.style.color == Nord.DEVICE
    ] == ["Test GPU", "Old GPU"]


def test_reset_all_settings_restores_defaults(make_gui):
    gui = make_gui()
    storage = gui.page.client_storage
    storage.set("video_height", "720")
    storage.set("tts_engine", "azure")

    gui.reset_settings_to_default()

    assert storage.get("video_height") == 1080
    assert storage.get("tts_engine") == "edge"


def test_reset_all_settings_puts_every_setting_back_and_the_tabs_show_it(make_gui):
    from default_settings import DEFAULT_SETTINGS
    from tests.test_mangadex_folders import find_checkbox

    gui = make_gui()
    storage = gui.page.client_storage
    for setting_key in DEFAULT_SETTINGS:
        storage.set(setting_key, "changed")

    gui.reset_settings_to_default()

    for setting_key, default_value in DEFAULT_SETTINGS.items():
        assert storage.get(setting_key) == default_value, setting_key
    # The tabs are made again, so they show the defaults too (this one is on by default).
    assert (
        find_checkbox(
            gui.MagiPanelByPanelView,
            "Split very tall panels for phones (never through text)",
        ).value
        is True
    )


def test_reset_keeps_the_settings_page_shows_its_defaults_and_a_message_for_a_few_seconds(
    make_gui, monkeypatch, tmp_path
):
    from gui_classes import AppSettingsView

    monkeypatch.setattr(AppSettingsView, "RESET_MESSAGE_SECONDS", 0.01)
    gui = make_gui()
    gui.app_bar.change_view("Settings")
    settings_page = gui.AppSettingsView
    settings_page.start_tab_dropdown.value = "Pipeline"
    settings_page.cbz_dropdown.value = "full"
    settings_page.cbz_dropdown.helper_text = AppSettingsView.CBZ_DESCRIPTIONS["full"]
    storage = gui.page.client_storage
    storage.set("start_tab", "Pipeline")
    storage.set("save_as_cbz", "full")
    storage.set("panelyze_folder", str(tmp_path))
    settings_page.panelyze_folder_text.value = str(tmp_path)

    gui.reset_settings_to_default()

    # The same page (so it stays scrolled where it was), showing the defaults.
    assert (
        gui.AppSettingsView is settings_page and gui.view_slot.content is settings_page
    )
    assert settings_page.start_tab_dropdown.value == "Download"
    assert settings_page.cbz_dropdown.value == "no"
    # The description under the .cbz choice goes with it ("No" has none).
    assert settings_page.cbz_dropdown.helper_text == ""
    assert settings_page.panelyze_folder_text.value != str(tmp_path)
    # A normal window: the message is next to the button.
    beside, above = (
        settings_page.reset_message_beside,
        settings_page.reset_message_above,
    )
    button_row = next(
        control
        for control in get_all_controls(settings_page)
        if isinstance(control, ft.Row)
        and any(
            getattr(button, "text", "") == "Reset All Settings"
            for button in control.controls
        )
    )
    assert beside in button_row.controls and beside.visible and not above.visible

    # A narrow window: above the button (next to it doesn't fit, and under it is out of view). Clicking again also starts the few seconds over.
    first_timer = settings_page.hide_reset_message_timer
    gui.is_narrow = True
    gui.reset_settings_to_default()
    section_controls = next(
        control
        for control in get_all_controls(settings_page)
        if isinstance(control, ft.Column) and button_row in control.controls
    ).controls
    assert section_controls.index(above) == section_controls.index(button_row) - 1
    assert above.visible and not beside.visible
    assert (
        settings_page.hide_reset_message_timer is not first_timer
        and first_timer.finished.is_set()
    )

    settings_page.hide_reset_message_timer.join(timeout=5)
    assert not above.visible and not beside.visible


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

    # The output folder already has a default, so only the input is missing.
    assert "valid input directory" in terminal_lines[-1].value
    assert gui.is_job_running is False


def test_only_one_job_runs_at_a_time(make_gui):
    gui = make_gui()
    gui.is_job_running = True
    terminal_lines = gui.terminal_output.terminal_output_list_view.controls
    directories = gui.UpscaleImagesView.pick_input_output_directories_container
    submitted = []
    directories.on_submit = lambda *args: submitted.append(args)

    directories.handle_submit(fake_event())

    assert "Another job is still running" in terminal_lines[-1].value
    assert submitted == []


def test_video_shape_dropdown_saves_the_setting(make_gui):
    gui = make_gui()
    settings = gui.ImagesToVideoView.pick_input_output_directories_container
    dropdown = find_control(
        settings, lambda c: getattr(c, "label", None) == "Video Shape"
    )

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

    voice_names = []
    # Up to 10 s, for a slow Mac (e.g. GitHub's).
    for _ in range(200):
        voice_names = [
            option.key for option in tts_section.voice_names_dropdown.options
        ]
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
    picked = [
        SimpleNamespace(path=str(chapter / "page_1.png")),
        SimpleNamespace(path=str(chapter / "page_3.png")),
    ]
    directories.pick_input_images_result(fake_event(files=picked))
    directories.output_directory = str(tmp_path / "out")

    directories.handle_submit(fake_event())

    assert os.path.basename(seen_during_job["input_directory"]) == "Ch 1 - 2 images"
    assert seen_during_job["images"] == ["page_1.png", "page_3.png"]
    # The temporary copy is deleted afterwards, and the picked images stay selected.
    assert not os.path.exists(seen_during_job["input_directory"])
    assert directories.input_image_paths == [file.path for file in picked]
    assert directories.input_directory == str(chapter)


def test_picked_comic_files_are_processed_like_a_folder_in_each_tab(make_gui, tmp_path):
    import zipfile
    from types import SimpleNamespace

    cbz_path = tmp_path / "Invincible 001.cbz"
    with zipfile.ZipFile(cbz_path, "w") as cbz:
        cbz.writestr("1.png", b"1")

    gui = make_gui()
    directories = gui.UpscaleImagesView.pick_input_output_directories_container
    seen_during_job = []
    directories.on_submit = lambda input_directory, output_directory: (
        seen_during_job.append((input_directory, sorted(os.listdir(input_directory))))
    )
    directories.output_directory = str(tmp_path / "out")

    directories.pick_input_comic_files_result(
        fake_event(files=[SimpleNamespace(path=str(cbz_path))])
    )
    assert directories.input_directory_row_text.value == "Invincible 001.cbz"
    directories.handle_submit(fake_event())

    assert [(os.path.basename(folder), pages) for folder, pages in seen_during_job] == [
        ("Invincible 001", ["001.png"])
    ]
    # The temporary folder is deleted afterwards.
    assert not os.path.exists(seen_during_job[0][0])


def test_a_comic_file_that_can_not_be_opened_shows_an_error_in_the_tab(
    make_gui, tmp_path, monkeypatch
):
    from types import SimpleNamespace

    broken_cbz = tmp_path / "Broken.cbz"
    broken_cbz.write_bytes(b"not a zip file")
    gui = make_gui()
    directories = gui.UpscaleImagesView.pick_input_output_directories_container
    errors = []
    monkeypatch.setattr(
        gui.terminal_output, "update_terminal_with_error_message", errors.append
    )
    directories.output_directory = str(tmp_path / "out")
    directories.pick_input_comic_files_result(
        fake_event(files=[SimpleNamespace(path=str(broken_cbz))])
    )

    directories.handle_submit(fake_event())

    assert errors == ["ERROR: File is not a zip file"]
    assert gui.is_job_running is False


def test_reading_direction_dropdown_saves_the_setting(make_gui):
    gui = make_gui()
    assert gui.page.client_storage.get("reading_direction") == "auto"
    dropdown = find_control(
        gui.MagiPanelByPanelView,
        lambda c: getattr(c, "label", None) == "Reading Direction",
    )

    dropdown.on_change(fake_event(data="ltr"))

    assert gui.page.client_storage.get("reading_direction") == "ltr"


def test_a_failed_job_shows_a_short_error_and_does_not_crash(
    make_gui, tmp_path, monkeypatch
):
    from gui_classes import UpscaleImagesView

    def no_internet():
        raise OSError("No internet")

    monkeypatch.setattr(UpscaleImagesView, "download_waifu2x", no_internet)
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"")
    gui = make_gui()

    finished = gui.UpscaleImagesView.start_job(
        str(tmp_path / "Manga"), str(tmp_path / "out")
    )

    terminal_lines = [
        get_shown_text(c)
        for c in gui.terminal_output.terminal_output_list_view.controls
    ]
    assert finished is False
    assert any(
        '"waifu2x-ncnn-vulkan" couldn\'t be downloaded (No internet)' in line
        for line in terminal_lines
    )


def test_every_setting_starts_at_its_default(make_gui):
    from default_settings import DEFAULT_SETTINGS

    gui = make_gui()

    for setting_key, default_value in DEFAULT_SETTINGS.items():
        assert gui.page.client_storage.get(setting_key) == default_value, setting_key


def test_upscaled_images_are_webp_by_default_and_stop_at_4k(make_gui):
    # WebP files are smaller than PNG.
    storage = make_gui().page.client_storage

    assert storage.get("image_format") == "webp"
    assert storage.get("limit_upscale_to_4k") is True


def test_open_log_file_opens_the_log_or_says_there_is_none_yet(
    make_gui, tmp_path, monkeypatch
):
    from gui_classes import AppSettingsView

    gui = make_gui()
    opened, errors = [], []
    monkeypatch.setattr(AppSettingsView, "open_directory", opened.append)
    monkeypatch.setattr(
        gui.terminal_output, "update_terminal_with_error_message", errors.append
    )
    log_file = tmp_path / "panelyze.log"
    monkeypatch.setattr(AppSettingsView, "LOG_FILE_PATH", str(log_file))

    gui.AppSettingsView.open_log_file()
    assert opened == [] and "no log file yet" in errors[0]

    log_file.write_text("started")
    gui.AppSettingsView.open_log_file()
    assert opened == [str(log_file)]


def test_open_logs_folder_opens_the_folder_with_the_past_runs(
    make_gui, tmp_path, monkeypatch
):
    from gui_classes import AppSettingsView

    gui = make_gui()
    opened = []
    monkeypatch.setattr(AppSettingsView, "open_directory", opened.append)
    monkeypatch.setattr(AppSettingsView, "LOG_FOLDER", str(tmp_path))

    button = next(
        control
        for control in get_all_controls(gui.AppSettingsView)
        if isinstance(control, ft.ElevatedButton) and control.text == "Open Logs Folder"
    )
    assert button.on_click is not None
    button.on_click(fake_event())

    assert opened == [str(tmp_path)]


def test_report_a_problem_opens_the_github_issues(make_gui):
    gui = make_gui()

    button = next(
        control
        for control in get_all_controls(gui.AppSettingsView)
        if isinstance(control, ft.ElevatedButton) and control.text == "Report a Problem"
    )

    assert button.url == "https://github.com/curlos/panelyze/issues/new/choose"


def test_about_shows_the_version_and_links_to_the_repo(make_gui):
    gui = make_gui()
    controls = list(get_all_controls(gui.AppSettingsView))

    assert any(
        isinstance(control, ft.Text) and control.value == "Panelyze 1.0.0"
        for control in controls
    )
    button = next(
        control
        for control in controls
        if isinstance(control, ft.ElevatedButton) and control.text == "View on GitHub"
    )
    assert button.url == "https://github.com/curlos/panelyze"


def test_logs_are_kept_where_the_system_keeps_app_logs():
    from gui_classes.AppOutput import LOG_FILE_PATH

    if sys.platform == "win32":
        expected_folder = os.path.join(os.environ["LOCALAPPDATA"], "Panelyze", "Logs")
    else:
        expected_folder = os.path.expanduser(
            os.path.join("~", "Library", "Logs", "Panelyze")
        )
    assert os.path.dirname(LOG_FILE_PATH) == expected_folder


def test_videos_clean_up_their_working_folders_by_default(make_gui):
    # Most people only want the video: the voice-over mp3s and the highlighted copies of the images are deleted once it's made.
    storage = make_gui().page.client_storage

    assert storage.get("clean_up_tts_audio_files_folder") is True
    assert storage.get("clean_up_images_with_highlighted_text_boxes_folder") is True


def test_reset_keeps_the_azure_key(make_gui):
    gui = make_gui()
    gui.page.client_storage.set("azure_subscription_key", "my-key")

    gui.reset_settings_to_default()

    assert gui.page.client_storage.get("azure_subscription_key") == "my-key"


def test_number_boxes_only_save_valid_numbers(make_gui):
    gui = make_gui()
    duration_box = find_control(
        gui.ImagesToVideoView,
        lambda c: getattr(c, "label", "") and "Minimum Image Duration" in c.label,
    )

    duration_box.on_change(fake_event(data="abc", control=duration_box))
    assert duration_box.error_text == "Please enter a valid number."
    assert gui.page.client_storage.get("minimum_image_duration") == 3

    duration_box.on_change(fake_event(data="4", control=duration_box))
    assert duration_box.error_text == ""
    assert gui.page.client_storage.get("minimum_image_duration") == "4"


def test_the_video_resolution_is_picked_from_a_list_from_360p_to_4k(make_gui):
    gui = make_gui()
    dropdown = find_control(
        gui.ImagesToVideoView, lambda c: getattr(c, "label", "") == "Video Resolution"
    )

    assert [option.key for option in dropdown.options] == [
        "360",
        "480",
        "720",
        "1080",
        "1440",
        "2160",
    ]
    assert dropdown.value == "1080"

    dropdown.on_change(fake_event(data="2160"))

    assert gui.page.client_storage.get("video_height") == "2160"


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


def test_a_picked_input_shows_what_was_found_in_it(make_gui, tmp_path):
    from types import SimpleNamespace

    series = tmp_path / "One Piece"
    for chapter, pages in [("Ch 1", 3), ("Ch 2", 2)]:
        (series / chapter).mkdir(parents=True)
        for number in range(pages):
            (series / chapter / f"{number}.png").write_bytes(b"image")
    gui = make_gui()
    directories = gui.UpscaleImagesView.pick_input_output_directories_container

    directories.pick_input_files_result(fake_event(path=str(series)))
    assert directories.input_directory_row_text.value == "One Piece"
    assert directories.input_summary_text.value == "2 chapters · 5 pages"
    assert directories.selected_input_directory_row.visible
    assert not directories.pick_input_directory_column.visible

    directories.pick_input_images_result(
        fake_event(
            files=[
                SimpleNamespace(path=str(series / "Ch 1" / f"{number}.png"))
                for number in range(3)
            ]
        )
    )
    assert directories.input_summary_text.value == "3 images"

    directories.handle_clear_input_directory(fake_event())
    assert directories.pick_input_directory_column.visible
    assert not directories.selected_input_directory_row.visible


def test_each_job_tab_has_a_button_that_says_what_it_does(make_gui):
    gui = make_gui()

    buttons = {
        view_name: getattr(
            gui, view_name
        ).pick_input_output_directories_container.submit_button.text
        for view_name in [
            "MagiPanelByPanelView",
            "UpscaleImagesView",
            "ImagesToVideoView",
        ]
    }

    assert buttons == {
        "MagiPanelByPanelView": "Split Into Panels",
        "UpscaleImagesView": "Upscale",
        "ImagesToVideoView": "Create Video",
    }
    assert gui.MangaDexDownloaderView.download_button.text == "Download"
    assert gui.PipelineView.run_button.text == "Run Pipeline"


def get_locked_controls(directories):
    return [
        directories.pick_input_directory_column,
        directories.selected_input_directory_row,
        directories.selected_output_directory_row,
        directories.clear_button,
        directories.settings_container,
        directories.submit_button,
    ]


def test_a_job_tab_can_not_be_changed_while_its_job_runs(make_gui, tmp_path):
    gui = make_gui()
    directories = gui.UpscaleImagesView.pick_input_output_directories_container
    directories.output_directory = str(tmp_path / "out")
    (tmp_path / "Ch 1").mkdir()
    (tmp_path / "Ch 1" / "1.png").write_bytes(b"image")
    directories.set_input_directory(str(tmp_path / "Ch 1"))
    locked_during_the_job = []
    directories.on_submit = lambda input_directory, output_directory: (
        locked_during_the_job.append(
            [control.disabled for control in get_locked_controls(directories)]
        )
    )
    assert not any(control.disabled for control in get_locked_controls(directories))

    directories.handle_submit(fake_event())

    # The input, the output folder, the settings and the buttons were all locked, and are free again afterwards.
    assert locked_during_the_job == [[True] * 6]
    assert not any(control.disabled for control in get_locked_controls(directories))


def test_a_job_tab_is_unlocked_again_when_its_job_fails(make_gui, tmp_path):
    gui = make_gui()
    directories = gui.UpscaleImagesView.pick_input_output_directories_container
    directories.output_directory = str(tmp_path / "out")
    (tmp_path / "Ch 1").mkdir()
    directories.set_input_directory(str(tmp_path / "Ch 1"))

    def failing_job(input_directory, output_directory):
        raise RuntimeError("It broke.")

    directories.on_submit = failing_job
    directories.handle_submit(fake_event())

    assert not any(control.disabled for control in get_locked_controls(directories))
    assert gui.is_job_running is False


def get_download_tab_controls(tab):
    return [
        tab.mangadex_url_text_field,
        tab.output_row,
        tab.settings,
        tab.download_button,
    ]


@pytest.mark.parametrize("outcome", ["finishes", "fails"])
def test_the_download_tab_can_not_be_changed_while_it_downloads_but_can_be_cancelled(
    make_gui, tmp_path, monkeypatch, outcome
):
    from gui_classes import MangaDexDownloaderView

    gui = make_gui()
    gui.page.client_storage.set("output_directory_mangadex", str(tmp_path))
    tab = gui.MangaDexDownloaderView
    seen = []

    def download(*arguments):
        seen.append(
            (
                [control.disabled for control in get_download_tab_controls(tab)],
                tab.cancel_button.disabled,
                tab.cancel_button.visible,
            )
        )
        if outcome == "fails":
            raise RuntimeError("It broke.")
        return "Downloaded something"

    monkeypatch.setattr(MangaDexDownloaderView, "download_from_mangadex", download)
    tab.mangadex_url_text_field.value = "https://mangadex.org/title/x"

    tab.handle_download(fake_event())

    # The link, the output folder, the settings and the Download button are locked, and Cancel is there to be clicked.
    assert seen == [([True, True, True, True], False, True)]
    assert not any(control.disabled for control in get_download_tab_controls(tab))


def test_a_pipeline_locks_itself_and_no_other_tab_can_be_opened_while_it_runs(
    make_gui, monkeypatch
):
    gui = make_gui()
    gui.app_bar.change_view("Pipeline")
    pipeline = gui.PipelineView
    pipeline.step_checkboxes["Panel-By-Panel"].value = True
    pipeline.input_directory = os.path.abspath(os.sep)
    pipeline.output_directory = os.path.abspath(os.sep)
    other_tabs = [
        "Download",
        "Panel-By-Panel",
        "Upscale Images",
        "Images To Video",
        "Settings",
    ]

    def get_pipeline_state():
        return [
            *(checkbox.disabled for checkbox in pipeline.step_checkboxes.values()),
            pipeline.mangadex_url_text_field.disabled,
            pipeline.input_column.disabled,
            pipeline.output_row.disabled,
            pipeline.run_button.disabled,
            pipeline.run_button.opacity == 0.5,
        ]

    seen = []

    def run_pipeline_that_fails(selected_steps, input_directory):
        # Trying to open another tab does nothing: a click, a shortcut, or the arrow keys on a focused tab.
        gui.app_bar.change_view("Download")
        gui.handle_keyboard_shortcut(
            SimpleNamespace(key="1", ctrl=True, meta=True, alt=False, shift=False)
        )
        gui.focused_tab = "Pipeline"
        gui.handle_keyboard_shortcut(
            SimpleNamespace(
                key="Arrow Right", ctrl=False, meta=False, alt=False, shift=False
            )
        )
        seen.append((get_pipeline_state(), gui.current_view, gui.is_job_running))
        raise RuntimeError("It broke.")

    monkeypatch.setattr(pipeline, "run_pipeline", run_pipeline_that_fails)
    monkeypatch.setattr(
        pipeline, "get_error_before_running", lambda selected_steps: None
    )

    pipeline.handle_run_pipeline(fake_event())

    pipeline_state, current_view, job_running = seen[0]
    assert all(pipeline_state) and current_view == "Pipeline" and job_running
    # Everything is free again, also after a failure.
    assert not any(get_pipeline_state()) and gui.is_job_running is False
    assert all(gui.app_bar.buttons[tab].opacity == 1 for tab in other_tabs)
    # The tabs were made again when the job ended, so none of them has the keyboard focus.
    assert gui.focused_tab is None
    gui.app_bar.change_view("Download")
    assert gui.current_view == "Download"


def test_a_job_can_be_cancelled_and_stops_before_the_next_chapter(
    make_gui, tmp_path, monkeypatch
):
    from PIL import Image

    gui = make_gui()
    tab = gui.UpscaleImagesView
    directories = tab.pick_input_output_directories_container
    for chapter in ("Ch 1", "Ch 2"):
        (tmp_path / "in" / chapter).mkdir(parents=True)
        Image.new("RGB", (10, 10)).save(tmp_path / "in" / chapter / "1.png")
    directories.set_input_directory(str(tmp_path / "in"))
    directories.output_directory = str(tmp_path / "out")
    processed = []
    shown_while_running = []

    def process_image_folder(image_folder, images, input_directory, output_directory):
        processed.append(os.path.basename(image_folder))
        shown_while_running.append(
            (directories.cancel_button.visible, directories.clear_button.visible)
        )
        directories.cancel_button.on_click(fake_event())

    monkeypatch.setattr(tab, "process_image_folder", process_image_folder)
    directories.handle_submit(fake_event())

    assert processed == ["Ch 1"]
    assert shown_while_running == [(True, False)]  # Cancel takes Clear's place
    assert directories.clear_button.visible is True
    assert directories.cancel_button.visible is False
    # Ready for the next job.
    assert (directories.cancel_button.disabled, directories.cancel_button.text) == (
        False,
        "Cancel",
    )
    # Cleared, so a Pipeline that runs this tab later isn't stopped by it.
    assert not tab.cancel_event.is_set()
    assert gui.terminal_output.progress_panel.state == "cancelled"
    assert gui.is_job_running is False


def test_cancelling_an_upscale_stops_waifu2x_at_once(make_gui):
    gui = make_gui()
    tab = gui.UpscaleImagesView
    stopped = []
    tab.process_manager = SimpleNamespace(cancel_process=lambda: stopped.append(True))

    tab.pick_input_output_directories_container.cancel_button.on_click(fake_event())

    assert stopped == [True]
    assert tab.cancel_event.is_set()


def test_the_error_of_a_failed_job_stays_in_the_status_view(
    make_gui, tmp_path, monkeypatch
):
    from PIL import Image

    gui = make_gui()
    tab = gui.UpscaleImagesView
    directories = tab.pick_input_output_directories_container
    (tmp_path / "in").mkdir()
    Image.new("RGB", (10, 10)).save(tmp_path / "in" / "1.png")
    directories.set_input_directory(str(tmp_path / "in"))
    directories.output_directory = str(tmp_path / "out")

    def broken(image_folder, images, input_directory, output_directory):
        raise RuntimeError("The disk is full.")

    monkeypatch.setattr(tab, "process_image_folder", broken)
    directories.handle_submit(fake_event())

    panel = gui.terminal_output.progress_panel
    assert panel.state == "failed"
    assert panel.title == tab.failed_text
    assert panel.detail == "The disk is full."
    assert panel.timer_text.value.startswith("Took ")


def test_clicking_cancel_says_right_away_when_the_job_will_stop_and_can_not_be_clicked_twice(
    make_gui, monkeypatch
):
    gui = make_gui()
    tab = gui.UpscaleImagesView
    directories = tab.pick_input_output_directories_container
    panel = gui.terminal_output.progress_panel
    panel.start("Upscaling images...")
    tab.janai_is_running = True
    stopped = []
    directories.on_cancel = lambda: stopped.append(True)

    directories.cancel_button.on_click(fake_event())
    directories.cancel_button.on_click(fake_event())

    assert panel.title.startswith("Cancelling after the image being upscaled")
    assert directories.cancel_button.disabled is True
    assert directories.cancel_button.text == "Cancelling..."
    assert stopped == [True]


def test_upscale_says_waifu2x_is_stopped_at_once(make_gui):
    gui = make_gui()
    tab = gui.UpscaleImagesView
    gui.terminal_output.progress_panel.start("Upscaling images...")

    tab.pick_input_output_directories_container.cancel_button.on_click(fake_event())

    assert (
        gui.terminal_output.progress_panel.title
        == "Stopping waifu2x, then resizing the images that finished..."
    )


def test_while_a_job_runs_every_other_tab_is_faded_and_says_what_it_waits_for(
    make_gui, tmp_path, monkeypatch
):
    from PIL import Image

    gui = make_gui()
    gui.app_bar.change_view("Upscale Images")
    tab = gui.UpscaleImagesView
    directories = tab.pick_input_output_directories_container
    (tmp_path / "in").mkdir()
    Image.new("RGB", (10, 10)).save(tmp_path / "in" / "1.png")
    directories.set_input_directory(str(tmp_path / "in"))
    directories.output_directory = str(tmp_path / "out")
    other_tabs = [
        "Download",
        "Panel-By-Panel",
        "Images To Video",
        "Pipeline",
        "Settings",
    ]

    def get_tab_state(tab_name):
        button = gui.app_bar.buttons[tab_name]
        tooltip = button.content.tooltip
        return button.opacity, tooltip.message if tooltip else None

    seen = []
    button_opacity = []
    monkeypatch.setattr(
        tab,
        "process_image_folder",
        lambda *args: (
            seen.extend(get_tab_state(name) for name in other_tabs + ["Upscale Images"])
            or button_opacity.append(directories.submit_button.opacity)
        ),
    )

    directories.handle_submit(fake_event())

    # A tab that shows its name has no tooltip, unless it says why it can't be opened.
    assert seen == [
        (0.5, 'Wait for "Upscale" to finish (only one job runs at a time)')
    ] * 5 + [(1, None)]
    # Its own main button is faded too, and back to normal afterwards.
    assert button_opacity == [0.5] and directories.submit_button.opacity == 1
    assert get_tab_state("Download") == (1, None)


def test_two_clicks_at_once_start_only_one_job(make_gui):
    import threading

    gui = make_gui()
    terminal_lines = gui.terminal_output.terminal_output_list_view.controls
    started = []
    ready = threading.Barrier(8)

    def click():
        # Flet runs each click in its own thread; they all try to start at the same moment.
        ready.wait()
        started.append(gui.try_to_start_job("Upscale"))

    threads = [threading.Thread(target=click) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert started.count(True) == 1
    errors = [line.value for line in terminal_lines if "Another job" in str(line.value)]
    assert (
        errors
        == ["ERROR: Another job is still running. Please wait for it to finish."] * 7
    )


def test_a_refused_second_job_leaves_the_running_job_as_it_is(make_gui):
    gui = make_gui()
    panel = gui.terminal_output.progress_panel
    assert gui.try_to_start_job("Upscale Images")
    panel.start("Upscaling images...")
    terminal_lines = gui.terminal_output.terminal_output_list_view.controls

    # E.g. a double-click on Download while the first click's job is starting.
    assert not gui.try_to_start_job("Download")

    assert "Another job is still running" in terminal_lines[-1].value
    # The Status view still shows the job that's running, with its timer.
    assert panel.state == "running" and panel.ended_at is None


@pytest.mark.parametrize("output", ["parent", "same", "inside"])
def test_a_job_is_refused_when_its_output_could_overwrite_the_input(
    make_gui, tmp_path, monkeypatch, output
):
    gui = make_gui()
    view = gui.UpscaleImagesView
    chapter = tmp_path / "One Piece" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "panel_1.png").write_bytes(b"original")
    output_directory = {
        "parent": tmp_path / "One Piece",
        "same": chapter,
        "inside": chapter / "out",
    }[output]
    processed = []
    monkeypatch.setattr(
        view, "process_image_folder", lambda *args: processed.append(args)
    )

    assert view.start_job(str(chapter), str(output_directory)) is False

    assert processed == []
    assert (chapter / "panel_1.png").read_bytes() == b"original"
    terminal_lines = gui.terminal_output.terminal_output_list_view.controls
    assert (
        "can't be inside the input directory or be its parent"
        in terminal_lines[-1].value
    )


def fail_the_first_time(original):
    """
    "original", except that its first call fails, like an update on a control that isn't on the page.
    """
    failed = False

    def fail_once(*args, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise AssertionError("Control must be added to the page first")
        return original(*args, **kwargs)

    return fail_once


@pytest.mark.parametrize("tab", ["Upscale Images", "Download", "Pipeline"])
def test_a_job_that_fails_as_it_starts_never_leaves_the_app_locked(
    make_gui, monkeypatch, tmp_path, tab
):
    gui = make_gui()
    gui.app_bar.change_view(tab)
    if tab == "Upscale Images":
        directories = gui.UpscaleImagesView.pick_input_output_directories_container
        monkeypatch.setattr(
            directories.submit_button,
            "update",
            fail_the_first_time(directories.submit_button.update),
        )
        directories.handle_submit(fake_event())
    elif tab == "Download":
        view = gui.MangaDexDownloaderView
        view.mangadex_url_text_field.value = "https://mangadex.org/title/x"
        monkeypatch.setattr(
            view.download_button,
            "update",
            fail_the_first_time(view.download_button.update),
        )
        view.handle_download(fake_event())
    else:
        pipeline = gui.PipelineView
        pipeline.step_checkboxes["Panel-By-Panel"].value = True
        pipeline.input_directory = str(tmp_path)
        pipeline.output_directory = str(tmp_path)
        monkeypatch.setattr(
            pipeline, "set_locked", fail_the_first_time(pipeline.set_locked)
        )
        pipeline.handle_run_pipeline(fake_event())

    # The error is shown, and every tab can be used again.
    assert gui.is_job_running is False
    terminal_lines = gui.terminal_output.terminal_output_list_view.controls
    assert "Control must be added to the page first" in terminal_lines[-1].value
