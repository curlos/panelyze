import sys

import flet as ft
import pytest

import gui_classes.ProgressPanel as progress_panel_module
from download_from_mangadex import (
    get_mangadex_progress_reporter,
    parse_mangadex_progress_line,
)
from gui_classes import Nord
from gui_classes.ProgressPanel import ProgressPanel, report_progress
from tests.fake_gui import get_shown_text


@pytest.fixture(autouse=True)
def sizes_counted_like_finder(monkeypatch):
    # The sizes in these tests are written the Mac's way, on every computer (File Explorer's way is tested on its own).
    monkeypatch.setattr(progress_panel_module, "USE_FILE_EXPLORER_SIZES", False)


# Real lines from mangadex-downloader.
PAGE_LINE = "[INFO] Downloading [Setsu Scans & Les Poroïniens] Volume. 6 Chapter. 42 - Boss and His Best Friend page 7\n"
FINISHED_LINE = (
    '[INFO] Finished download chapter 42 from manga "Shachou to Sake to Hoshi"\n'
)


def test_mangadex_lines_are_understood():
    assert parse_mangadex_progress_line(PAGE_LINE) == (
        "page",
        "Volume. 6 Chapter. 42 - Boss and His Best Friend",
        7,
    )
    assert parse_mangadex_progress_line(FINISHED_LINE) == ("finished", "42")


def test_other_mangadex_lines_are_ignored():
    for line in [
        '[INFO] Found chapter 42 from manga "Shachou to Sake to Hoshi"\n',
        "File sizes: 100%|████| 546k/546k [00:00<00:00, 17.3MB/s]\n",
        "[INFO] Downloading file 'cover.jpg'\n",
        "",
    ]:
        assert parse_mangadex_progress_line(line) is None


def test_mangadex_reporter_shows_the_page_and_counts_finished_chapters():
    panel = ProgressPanel()
    report_line = get_mangadex_progress_reporter()

    report_line(PAGE_LINE)
    assert (
        "Downloading Volume. 6 Chapter. 42 - Boss and His Best Friend, page 7"
        in str(panel.status_text.value)
    )

    report_line(FINISHED_LINE)
    assert panel.status_text.value == "1 chapter(s) downloaded"

    report_line(PAGE_LINE)
    assert panel.status_text.value.startswith("1 chapter(s) downloaded · Downloading")


def test_progress_panel_shows_chapters_pages_and_the_bar():
    panel = ProgressPanel()
    panel.start("Upscaling images...")

    # Not known yet, so the bar keeps moving.
    assert panel.progress_bar.value is None

    report_progress(chapter=2, chapters=4, pages_done=10, pages_total=20)

    assert panel.title_text.value == "Upscaling images..."
    assert panel.status_text.value == "Chapter 2 of 4 · 10 of 20 pages"
    # One chapter done and half of the second one: 1.5 of 4.
    assert panel.progress_bar.value == 0.375

    panel.finish("Upscaling finished!")
    assert panel.progress_bar.value == 1


def test_the_status_view_says_where_the_ai_model_runs_only_for_that_job():
    panel = ProgressPanel()
    panel.start("Finding the panels...")
    assert not panel.device_text.visible

    report_progress(device="AMD Radeon RX 6700 XT")
    assert panel.device_text.visible
    assert get_shown_text(panel.device_text) == "Running on the AMD Radeon RX 6700 XT"
    # The GPU's name stands out.
    assert panel.device_text.spans[1].text == "AMD Radeon RX 6700 XT"
    style = panel.device_text.spans[1].style
    assert style is not None and style.color == Nord.DEVICE

    panel.finish("Done.")
    assert get_shown_text(panel.device_text) == "Ran on the AMD Radeon RX 6700 XT"

    # The next job (e.g. a download) doesn't use an AI model.
    panel.start("Downloading...")
    assert not panel.device_text.visible


def test_the_status_view_scrolls_when_the_terminal_is_too_small_for_it():
    panel = ProgressPanel()

    assert (
        isinstance(panel.content, ft.Column)
        and panel.content.scroll == ft.ScrollMode.ALWAYS
    )


def test_a_single_folder_is_not_called_chapter_1_of_1():
    panel = ProgressPanel()
    panel.start("Working...")

    report_progress(chapter=1, chapters=1, pages_done=3, pages_total=12)

    assert panel.status_text.value == "3 of 12 pages"
    assert panel.progress_bar.value == 0.25


def test_pipeline_step_is_shown_before_the_title():
    panel = ProgressPanel()
    report_progress(prefix="Step 2 of 4")
    panel.start("Converting to Panel-By-Panel...")

    assert panel.title_text.value == "Step 2 of 4 · Converting to Panel-By-Panel..."

    report_progress(prefix="")
    assert panel.title_text.value == "Converting to Panel-By-Panel..."


def test_reporting_without_a_panel_does_nothing(monkeypatch):
    monkeypatch.setattr("gui_classes.ProgressPanel.current_progress_panel", None)

    report_progress(pages_done=1, pages_total=2)


def test_the_progress_tab_is_shown_first_and_switches_to_the_raw_output(make_gui):
    gui = make_gui()
    terminal_output = gui.terminal_output

    assert terminal_output.progress_panel.visible
    assert terminal_output.terminal_output_list_view.visible

    terminal_output.show_tab("raw_output")
    assert not terminal_output.progress_panel.visible
    # The raw output stays on the page under the progress panel, so its scroll position is kept.
    assert terminal_output.terminal_output_list_view.visible

    terminal_output.show_tab("progress")
    assert terminal_output.progress_panel.visible


def test_a_job_reports_each_chapter(make_gui, tmp_path):
    for chapter_name in ["Ch 1", "Ch 2", "Ch 3"]:
        chapter = tmp_path / "Manga" / chapter_name
        chapter.mkdir(parents=True)
        (chapter / "page_1.png").write_bytes(b"")
    gui = make_gui()
    panel = gui.terminal_output.progress_panel
    seen = []

    gui.MagiPanelByPanelView.process_image_folder = (
        lambda image_folder, images, input_directory, output_directory: seen.append(
            panel.status_text.value
        )
    )

    finished = gui.MagiPanelByPanelView.start_job(
        str(tmp_path / "Manga"), str(tmp_path / "out")
    )

    assert finished is True
    assert seen == ["Chapter 1 of 3", "Chapter 2 of 3", "Chapter 3 of 3"]
    assert panel.title_text.value == "Panel-By-Panel conversion finished!"
    assert panel.progress_bar.value == 1


def test_the_idle_panel_has_an_icon_and_a_friendly_normal_weight_text():
    panel = ProgressPanel()

    assert panel.title_text.value == "Ready. Pick your input, then press the button."
    assert panel.title_text.weight is None
    assert panel.status_icon.visible
    assert panel.status_icon.name == ft.Icons.PLAY_CIRCLE_OUTLINE
    assert not panel.progress_bar.visible


def test_the_panel_shows_an_hourglass_while_running_then_a_check_or_an_error():
    panel = ProgressPanel()

    # Not a second spinning ring: the terminal's title bar has one.
    panel.start("Working...")
    assert panel.status_icon.name == ft.Icons.HOURGLASS_TOP
    assert panel.progress_bar.visible

    panel.finish("Done!")
    assert panel.status_icon.name == ft.Icons.CHECK_CIRCLE
    assert panel.progress_bar.visible

    panel.start("Working...")
    panel.finish("It failed.", success=False)
    assert panel.status_icon.name == ft.Icons.ERROR
    assert panel.status_icon.visible
    # A bar that stops partway isn't left on screen.
    assert not panel.progress_bar.visible


def test_the_terminal_title_is_bold(make_gui):
    assert make_gui().terminal_output.title_text.weight == ft.FontWeight.BOLD


def test_upscaling_counts_images_and_folders_not_pages_and_chapters():
    panel = ProgressPanel()
    panel.start("Upscaling images...")

    report_progress(
        chapter=2,
        chapters=5,
        group_label="Folder",
        pages_done=3,
        pages_total=12,
        unit="images",
    )

    assert panel.status_text.value == "Folder 2 of 5 · 3 of 12 images"


def test_a_single_image_is_not_called_images():
    panel = ProgressPanel()
    panel.start("Upscaling images...")

    report_progress(pages_done=0, pages_total=1, unit="images")

    assert panel.status_text.value == "0 of 1 image"


def test_a_new_job_goes_back_to_pages_and_chapters():
    panel = ProgressPanel()
    report_progress(group_label="Folder", unit="images")

    panel.start("Converting to Panel-By-Panel...")
    report_progress(chapter=1, chapters=2, pages_done=1, pages_total=8)

    assert panel.status_text.value == "Chapter 1 of 2 · 1 of 8 pages"


def test_the_upscale_job_reports_folders_and_images(make_gui, tmp_path, monkeypatch):
    for folder_name in ["Set 1", "Set 2"]:
        folder = tmp_path / "Images" / folder_name
        folder.mkdir(parents=True)
        (folder / "a.png").write_bytes(b"")
    gui = make_gui()
    panel = gui.terminal_output.progress_panel
    seen = []
    view = gui.UpscaleImagesView
    view.process_image_folder = lambda *args: seen.append(panel.status_text.value)

    view.start_job(str(tmp_path / "Images"), str(tmp_path / "out"))

    assert seen == ["Folder 1 of 2", "Folder 2 of 2"]


def test_an_error_before_anything_ran_shows_in_the_status_view_and_the_raw_output(
    make_gui,
):
    terminal_output = make_gui().terminal_output
    panel = terminal_output.progress_panel

    terminal_output.update_terminal_with_error_message(
        "ERROR: Not a web link (it should start with https://): aaa"
    )

    assert panel.state == "failed"
    assert panel.title_text.value == "Something went wrong"
    # Without the "ERROR:" prefix, and with a pointer to the Raw Output.
    assert (
        panel.status_text.value == "Not a web link (it should start with https://): aaa"
    )
    assert panel.error_hint_text.visible
    assert panel.status_icon.name == ft.Icons.ERROR
    assert not panel.progress_bar.visible
    raw_lines = [
        control.value for control in terminal_output.terminal_output_list_view.controls
    ]
    assert "ERROR: Not a web link (it should start with https://): aaa" in raw_lines


def test_an_error_in_the_middle_of_a_job_goes_under_the_title_that_says_what_failed():
    panel = ProgressPanel()
    panel.start("Downloading from comix.to...")
    panel.finish("Download from comix.to failed.", success=False)

    panel.show_error(
        "ERROR: Downloading from comix.to needs Google Chrome or Microsoft Edge installed."
    )

    assert panel.title_text.value == "Download from comix.to failed."
    assert (
        panel.status_text.value
        == "Downloading from comix.to needs Google Chrome or Microsoft Edge installed."
    )


def test_an_old_failure_does_not_give_a_new_error_its_title():
    panel = ProgressPanel()
    panel.start("Downloading from comix.to...")
    panel.finish("Download from comix.to failed.", success=False)
    panel.show_error("ERROR: Couldn't download any chapters.")

    # Later, before any new job, something else goes wrong.
    panel.show_error("ERROR: Not a web link (it should start with https://): aaa")

    assert panel.title_text.value == "Something went wrong"
    assert (
        panel.status_text.value == "Not a web link (it should start with https://): aaa"
    )


def test_a_new_job_clears_the_error():
    panel = ProgressPanel()
    panel.show_error("ERROR: Something broke")

    panel.start("Downloading...")

    assert panel.state == "running"
    assert panel.status_text.value == ""
    assert not panel.error_hint_text.visible


def test_an_error_opens_a_collapsed_terminal_and_shows_the_status_view(make_gui):
    terminal_output = make_gui().terminal_output
    terminal_output.toggle_terminal_visibility(None)
    terminal_output.show_tab("raw_output")
    assert not terminal_output.output_area.visible

    terminal_output.update_terminal_with_error_message(
        "ERROR: Please pick an input directory."
    )

    assert terminal_output.output_area.visible
    assert terminal_output.progress_panel.visible
    assert (
        terminal_output.progress_panel.status_text.value
        == "Please pick an input directory."
    )


def test_the_status_tab_is_called_status(make_gui):
    terminal_output = make_gui().terminal_output

    assert terminal_output.progress_tab_button.text == "Status"
    assert terminal_output.raw_output_tab_button.text == "Raw Output"


def test_a_cancelled_job_is_shown_as_cancelled_with_a_neutral_icon():
    panel = ProgressPanel()
    panel.start("Downloading from comix.to...")

    panel.finish("Download cancelled.", success=False, cancelled=True)

    assert panel.state == "cancelled"
    assert panel.title_text.value == "Download cancelled."
    assert panel.status_icon.name == ft.Icons.CANCEL_OUTLINED
    assert panel.status_icon.color != Nord.RED_TEXT
    assert not panel.progress_bar.visible


def test_an_error_clears_the_counts_that_were_shown_while_it_ran():
    panel = ProgressPanel()
    panel.start("Downloading from the web page...")
    report_progress(chapter=1, chapters=1, pages_done=1, pages_total=1, unit="images")
    panel.finish("Download from the web page failed.", success=False)

    panel.show_error("ERROR: No comic pages found on this page.")

    assert panel.status_text.value == "No comic pages found on this page."


def test_the_raw_output_says_it_is_empty_until_there_is_a_line(make_gui):
    from utils import add_line_to_terminal_output_list_view

    terminal_output = make_gui().terminal_output
    empty_message = terminal_output.raw_output_empty_text

    assert empty_message.visible
    assert empty_message.value.startswith("Nothing here yet")

    add_line_to_terminal_output_list_view(
        terminal_output.terminal_output_list_view, "Opening the page"
    )
    assert not empty_message.visible

    # And it comes back if the lines are cleared.
    terminal_output.terminal_output_list_view.controls.clear()
    terminal_output.terminal_output_list_view.update()
    assert empty_message.visible


def test_an_error_also_takes_the_empty_message_away(make_gui):
    terminal_output = make_gui().terminal_output

    terminal_output.update_terminal_with_error_message("ERROR: Something broke")

    assert not terminal_output.raw_output_empty_text.visible


def test_a_duration_is_written_as_days_hours_minutes_and_seconds():
    from gui_classes.ProgressPanel import format_duration

    assert [
        format_duration(seconds)
        for seconds in (0, 42, 185, 3600, 3723, 3 * 3600 + 41 * 60, 93784)
    ] == [
        "0s",
        "42s",
        "3m5s",
        "1h0m0s",
        "1h2m3s",
        "3h41m0s",
        "1d2h3m4s",
    ]


def test_the_timer_runs_while_a_job_runs_and_says_how_long_it_took_when_it_is_over(
    monkeypatch,
):
    from gui_classes import ProgressPanel as progress_module

    now = [100.0]
    monkeypatch.setattr(progress_module.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(
        progress_module.threading,
        "Thread",
        lambda **kwargs: type("Thread", (), {"start": lambda self: None})(),
    )
    panel = progress_module.ProgressPanel()
    assert panel.get_timer_text() == ""

    panel.start("Upscaling images...")
    now[0] = 165.0
    assert panel.get_timer_text() == "1m5s"
    panel.total_started_at = 90.0
    assert panel.get_timer_text() == "1m5s · total 1m15s"

    panel.finish("Done")
    now[0] = 999.0
    assert panel.timer_text.value == "Took 1m5s"


def test_a_size_is_written_the_way_finder_shows_it():
    from gui_classes.ProgressPanel import format_size

    assert [
        format_size(size)
        for size in (0, 512, 5300, 412_000_000, 1_234_000_000, 3_000_000_000_000)
    ] == [
        "0 B",
        "512 B",
        "5.3 KB",
        "412 MB",
        "1.2 GB",
        "3.0 TB",
    ]


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="File Explorer's sizes are written by Windows itself",
)
def test_a_size_is_written_the_way_file_explorer_shows_it_on_windows(monkeypatch):
    from gui_classes.ProgressPanel import format_size

    monkeypatch.setattr(progress_panel_module, "USE_FILE_EXPLORER_SIZES", True)
    # Slam Dunk ch. 1 from comix.to: 70,413,414 bytes is 67.1 MB in File Explorer (70.4 MB in Finder). Explorer counts 1 KB as 1024 bytes, keeps 3 digits without rounding up, and goes to the next unit at 1000.
    # These are English Windows' texts: Windows writes them in the user's language and number format (e.g. "67,1 MB" in German), as Explorer does.
    assert format_size(70_413_414) == "67.1 MB"
    assert [
        format_size(size) for size in (512, 1023, 5300, 1_024_000, 1_234_000_000)
    ] == [
        "512 bytes",
        "1023 bytes",
        "5.17 KB",
        "0.97 MB",
        "1.14 GB",
    ]


def test_the_status_view_shows_how_much_the_job_has_saved_as_it_reports_progress(
    monkeypatch, tmp_path
):
    from gui_classes import ProgressPanel as progress_module

    now = [100.0]
    monkeypatch.setattr(progress_module.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(
        progress_module.threading,
        "Thread",
        lambda **kwargs: type("Thread", (), {"start": lambda self: None})(),
    )
    (tmp_path / "old.png").write_bytes(b"x" * 5000)
    panel = progress_module.ProgressPanel()
    panel.start("Upscaling images...")
    panel.watch_output_folder(str(tmp_path))
    assert panel.get_timer_text() == "0s · 0 B"

    (tmp_path / "1.png").write_bytes(b"x" * 2000)
    now[0] = 102.0
    panel.update_progress(pages_done=1)
    # Measured by the timer (each second), after the job said a page was done.
    panel.measure_output_if_changed()
    assert panel.get_timer_text() == "2s · 2.0 KB"

    # Not measured again when the job didn't report anything.
    (tmp_path / "2.png").write_bytes(b"x" * 2000)
    panel.measure_output_if_changed()
    assert panel.get_timer_text() == "2s · 2.0 KB"

    # But always when it's over.
    panel.finish("Done")
    assert panel.get_timer_text() == "Took 2s · 4.0 KB"


def test_the_size_says_how_much_of_it_is_comic_files(monkeypatch, tmp_path):
    from gui_classes import ProgressPanel as progress_module

    monkeypatch.setattr(
        progress_module.threading,
        "Thread",
        lambda **kwargs: type("Thread", (), {"start": lambda self: None})(),
    )
    (tmp_path / "Ch 1").mkdir()
    (tmp_path / "Ch 1.cbz").write_bytes(b"x" * 9000)
    panel = progress_module.ProgressPanel()
    panel.start("Downloading...")
    panel.watch_output_folder(str(tmp_path))

    (tmp_path / "Ch 2").mkdir()
    (tmp_path / "Ch 2" / "001.png").write_bytes(b"x" * 80_000)
    (tmp_path / "Ch 2.cbz").write_bytes(b"x" * 157_000)
    panel.finish("Downloaded")

    assert panel.get_timer_text().endswith(
        " · 237 KB (80.0 KB images + 157 KB .cbz files)"
    )


def test_a_video_s_size_says_how_much_is_the_video_and_its_audio(monkeypatch, tmp_path):
    from gui_classes import ProgressPanel as progress_module

    monkeypatch.setattr(
        progress_module.threading,
        "Thread",
        lambda **kwargs: type("Thread", (), {"start": lambda self: None})(),
    )
    panel = progress_module.ProgressPanel()
    panel.start("Creating the video...")
    panel.watch_output_folder(str(tmp_path))

    (tmp_path / "Ch 1.mp4").write_bytes(b"x" * 400_000)
    (tmp_path / "Ch 1" / "audio-files").mkdir(parents=True)
    (tmp_path / "Ch 1" / "audio-files" / "panel_1.mp3").write_bytes(b"x" * 380_000)
    (tmp_path / "Ch 1" / "magi-data.json").write_bytes(b"x" * 70_000)
    # Under 1% of it, so it's left out of the split (but still in the total).
    (tmp_path / "Ch 1" / "transcript.txt").write_bytes(b"x" * 10)
    panel.finish("Done")

    assert panel.get_timer_text().endswith(
        " · 850 KB (400 KB video + 380 KB audio + 70.0 KB other)"
    )


def test_one_kind_of_file_isn_t_split(monkeypatch, tmp_path):
    from gui_classes import ProgressPanel as progress_module

    monkeypatch.setattr(
        progress_module.threading,
        "Thread",
        lambda **kwargs: type("Thread", (), {"start": lambda self: None})(),
    )
    panel = progress_module.ProgressPanel()
    panel.start("Downloading...")
    panel.watch_output_folder(str(tmp_path))

    (tmp_path / "001.jpg").write_bytes(b"x" * 23_000)
    # A downloader's own small files.
    (tmp_path / "download-info.json").write_bytes(b"x" * 100)
    panel.finish("Downloaded")

    assert panel.get_timer_text().endswith(" · 23.1 KB")


def test_a_video_shows_its_stages(monkeypatch):
    from gui_classes import ProgressPanel as progress_module

    monkeypatch.setattr(
        progress_module.threading,
        "Thread",
        lambda **kwargs: type("Thread", (), {"start": lambda self: None})(),
    )
    panel = progress_module.ProgressPanel()
    panel.start("Creating the video...")
    assert not panel.stages_text.visible

    stages = ("Reading the text", "Making the voice-over", "Writing the video")
    panel.update_progress(stages=stages, stage="Reading the text")
    assert (
        panel.stages_text.value
        == "● Reading the text   ○ Making the voice-over   ○ Writing the video"
    )
    panel.update_progress(
        stage="Making the voice-over", pages_done=3, pages_total=40, unit="images"
    )
    assert (
        panel.stages_text.value
        == "✓ Reading the text   ● Making the voice-over   ○ Writing the video"
    )
    assert panel.status_text.value == "3 of 40 images"

    panel.finish("Video has been created!")
    assert (
        panel.stages_text.value
        == "✓ Reading the text   ✓ Making the voice-over   ✓ Writing the video"
    )

    # The next job doesn't have stages.
    panel.start("Upscaling images...")
    assert not panel.stages_text.visible


def test_a_link_in_an_error_can_be_clicked_in_the_status_view():
    panel = ProgressPanel()

    panel.show_error(
        "ERROR: Couldn't download the Magi model. It comes from https://huggingface.co/ragavsachdeva/magiv2"
    )

    assert [span.text for span in panel.status_text.spans or [] if span.on_click] == [
        "https://huggingface.co/ragavsachdeva/magiv2"
    ]
