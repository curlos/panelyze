import flet as ft

from download_from_mangadex import (
    get_mangadex_progress_reporter,
    parse_mangadex_progress_line,
)
from gui_classes.ProgressPanel import ProgressPanel, report_progress


# Real lines from mangadex-downloader.
PAGE_LINE = "[INFO] Downloading [Setsu Scans & Les Poroïniens] Volume. 6 Chapter. 42 - Boss and His Best Friend page 7\n"
FINISHED_LINE = '[INFO] Finished download chapter 42 from manga "Shachou to Sake to Hoshi"\n'


def test_mangadex_lines_are_understood():
    assert parse_mangadex_progress_line(PAGE_LINE) == (
        "page",
        "Volume. 6 Chapter. 42 - Boss and His Best Friend",
        7,
    )
    assert parse_mangadex_progress_line(FINISHED_LINE) == ("finished", "42")


def test_other_mangadex_lines_are_ignored():
    for line in [
        "[INFO] Found chapter 42 from manga \"Shachou to Sake to Hoshi\"\n",
        "File sizes: 100%|████| 546k/546k [00:00<00:00, 17.3MB/s]\n",
        "[INFO] Downloading file 'cover.jpg'\n",
        "",
    ]:
        assert parse_mangadex_progress_line(line) is None


def test_mangadex_reporter_shows_the_page_and_counts_finished_chapters():
    panel = ProgressPanel()
    report_line = get_mangadex_progress_reporter()

    report_line(PAGE_LINE)
    assert "Downloading Volume. 6 Chapter. 42 - Boss and His Best Friend, page 7" in panel.status_text.value

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

    finished = gui.MagiPanelByPanelView.start_job(str(tmp_path / "Manga"), str(tmp_path / "out"))

    assert finished is True
    assert seen == ["Chapter 1 of 3", "Chapter 2 of 3", "Chapter 3 of 3"]
    assert panel.title_text.value == "Panel-By-Panel conversion finished!"
    assert panel.progress_bar.value == 1


def test_the_idle_panel_has_an_icon_and_a_friendly_normal_weight_text():
    panel = ProgressPanel()

    assert panel.title_text.value == "Ready. Pick your folders and press Submit."
    assert panel.title_text.weight is None
    assert panel.status_icon.visible
    assert panel.status_icon.name == ft.Icons.PLAY_CIRCLE_OUTLINE
    assert not panel.running_ring.visible
    assert not panel.progress_bar.visible


def test_the_panel_shows_a_ring_while_running_then_a_check_or_an_error():
    panel = ProgressPanel()

    panel.start("Working...")
    assert panel.running_ring.visible
    assert not panel.status_icon.visible
    assert panel.progress_bar.visible

    panel.finish("Done!")
    assert not panel.running_ring.visible
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

    report_progress(chapter=2, chapters=5, group_label="Folder", pages_done=3, pages_total=12, unit="images")

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
    monkeypatch.setattr("gui_classes.UpscaleImagesView.get_waifu2x_path", lambda: "/fake/waifu2x")
    view.process_image_folder = lambda *args: seen.append(panel.status_text.value)

    view.start_job(str(tmp_path / "Images"), str(tmp_path / "out"))

    assert seen == ["Folder 1 of 2", "Folder 2 of 2"]
