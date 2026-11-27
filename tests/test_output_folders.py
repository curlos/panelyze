import os

import flet as ft
import pytest

from default_settings import OUTPUT_SUBFOLDERS, PANELYZE_FOLDER
from tests.fake_gui import fake_event

OUTPUT_SETTINGS = {
    "MangaDexDownloaderView": "output_directory_mangadex",
    "MagiPanelByPanelView": "output_directory_panel_by_panel",
    "UpscaleImagesView": "output_directory_upscale_images",
    "ImagesToVideoView": "output_directory_images_to_video",
    "PipelineView": "output_directory_pipeline",
}


def get_directories(gui, view_name):
    return getattr(gui, view_name).pick_input_output_directories_container


def default_folder(output_setting_key, panelyze_folder=PANELYZE_FOLDER):
    return os.path.join(panelyze_folder, OUTPUT_SUBFOLDERS[output_setting_key])


def test_every_tool_has_its_own_default_output_folder_in_documents():
    folders = [default_folder(key) for key in OUTPUT_SETTINGS.values()]

    assert len(set(folders)) == len(folders)
    assert all(os.path.dirname(folder) == PANELYZE_FOLDER for folder in folders)
    assert PANELYZE_FOLDER == os.path.join(
        os.path.expanduser("~"), "Documents", "Panelyze"
    )


def test_the_job_tabs_start_with_their_default_output_folder(make_gui):
    gui = make_gui()

    for view_name in ["MagiPanelByPanelView", "UpscaleImagesView", "ImagesToVideoView"]:
        directories = get_directories(gui, view_name)
        expected_folder = default_folder(OUTPUT_SETTINGS[view_name])

        assert directories.output_directory == expected_folder
        assert directories.output_directory_row_text.value == expected_folder
        assert directories.selected_output_directory_row.visible
        # Nothing is saved as picked until the user picks a folder.
        assert gui.page.client_storage.get(OUTPUT_SETTINGS[view_name]) == ""

    assert gui.PipelineView.output_directory == default_folder(
        "output_directory_pipeline"
    )


@pytest.mark.parametrize(
    "view_name", ["MagiPanelByPanelView", "UpscaleImagesView", "ImagesToVideoView"]
)
def test_the_clear_button_empties_the_input_and_goes_back_to_the_default_output_folder(
    make_gui, tmp_path, view_name
):
    gui = make_gui()
    directories = get_directories(gui, view_name)
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "1.png").write_bytes(b"")
    directories.pick_input_files_result(fake_event(path=str(tmp_path / "Manga")))
    directories.pick_output_files_result(fake_event(path=str(tmp_path / "out")))

    directories.handle_clear_all_directories(fake_event())

    assert not directories.input_directory
    assert (
        directories.pick_input_directory_column.visible
        and not directories.selected_input_directory_row.visible
    )
    assert directories.output_directory == default_folder(OUTPUT_SETTINGS[view_name])


def test_a_picked_output_folder_is_remembered_and_can_go_back_to_the_default(
    make_gui, tmp_path
):
    gui = make_gui()
    directories = get_directories(gui, "UpscaleImagesView")

    directories.pick_output_files_result(fake_event(path=str(tmp_path)))

    assert directories.output_directory == str(tmp_path)
    assert gui.page.client_storage.get("output_directory_upscale_images") == str(
        tmp_path
    )
    # A new window (the app opened again) uses it.
    assert get_directories(
        make_gui_again(gui), "UpscaleImagesView"
    ).output_directory == str(tmp_path)

    directories.handle_clear_output_directory(fake_event())

    assert directories.output_directory == default_folder(
        "output_directory_upscale_images"
    )
    assert gui.page.client_storage.get("output_directory_upscale_images") == ""


def make_gui_again(gui):
    import gui as gui_module

    return gui_module.GUI(gui.page)


def test_reset_all_settings_goes_back_to_the_default_output_folders(make_gui, tmp_path):
    gui = make_gui()
    get_directories(gui, "ImagesToVideoView").pick_output_files_result(
        fake_event(path=str(tmp_path))
    )
    gui.change_panelyze_folder(str(tmp_path / "Panelyze"))

    gui.reset_settings_to_default()

    assert get_directories(gui, "ImagesToVideoView").output_directory == default_folder(
        "output_directory_images_to_video"
    )
    assert gui.page.client_storage.get("panelyze_folder") == PANELYZE_FOLDER


def test_the_pipeline_remembers_its_output_folder(make_gui, tmp_path):
    gui = make_gui()

    gui.PipelineView.handle_directory_picked(fake_event(path=str(tmp_path)), "output")

    assert gui.PipelineView.output_directory == str(tmp_path)
    assert gui.page.client_storage.get("output_directory_pipeline") == str(tmp_path)

    gui.PipelineView.set_output_directory("")
    assert gui.PipelineView.output_directory == default_folder(
        "output_directory_pipeline"
    )
    assert gui.page.client_storage.get("output_directory_pipeline") == ""


def test_changing_the_panelyze_folder_moves_every_tool_that_has_no_folder_of_its_own(
    make_gui, tmp_path
):
    gui = make_gui()
    get_directories(gui, "UpscaleImagesView").pick_output_files_result(
        fake_event(path=str(tmp_path / "mine"))
    )
    new_folder = str(tmp_path / "Panelyze")

    gui.change_panelyze_folder(new_folder)

    assert get_directories(
        gui, "MagiPanelByPanelView"
    ).output_directory == default_folder("output_directory_panel_by_panel", new_folder)
    assert gui.PipelineView.output_directory == default_folder(
        "output_directory_pipeline", new_folder
    )
    assert gui.MangaDexDownloaderView.output_directory_text.value == default_folder(
        "output_directory_mangadex", new_folder
    )
    # A tab with its own folder keeps it.
    assert get_directories(gui, "UpscaleImagesView").output_directory == str(
        tmp_path / "mine"
    )
    # The Settings page shows the new folder.
    assert gui.AppSettingsView.panelyze_folder_text.value == new_folder


def test_picking_a_folder_in_settings_makes_a_panelyze_folder_inside_it(
    make_gui, tmp_path
):
    gui = make_gui()
    settings = gui.AppSettingsView
    # An empty current folder, so no "files stay where they are" question is asked.
    gui.page.client_storage.set("panelyze_folder", str(tmp_path / "empty"))

    settings.pick_panelyze_folder_result(fake_event(path=str(tmp_path / "Downloads")))
    assert gui.page.client_storage.get("panelyze_folder") == str(
        tmp_path / "Downloads" / "Panelyze"
    )

    # Already called "Panelyze", so no second one is added.
    settings.pick_panelyze_folder_result(fake_event(path=str(tmp_path / "Panelyze")))
    assert gui.page.client_storage.get("panelyze_folder") == str(tmp_path / "Panelyze")

    # Cancelled.
    gui.AppSettingsView.pick_panelyze_folder_result(fake_event(path=None))
    assert gui.page.client_storage.get("panelyze_folder") == str(tmp_path / "Panelyze")


def test_the_settings_page_scrolls_when_it_does_not_fit(make_gui):
    settings = make_gui().AppSettingsView

    assert settings.expand
    assert settings.content.scroll == ft.ScrollMode.ALWAYS


def test_the_panelyze_folder_cannot_change_while_a_job_runs(make_gui, tmp_path):
    gui = make_gui()
    gui.is_job_running = True

    gui.change_panelyze_folder(str(tmp_path))

    assert gui.page.client_storage.get("panelyze_folder") == PANELYZE_FOLDER


def test_the_mangadex_tab_remembers_its_output_folder(make_gui, tmp_path):
    gui = make_gui()
    view = gui.MangaDexDownloaderView

    view.pick_output_directory_result(fake_event(path=str(tmp_path)))

    assert view.output_directory_text.value == str(tmp_path)
    assert gui.page.client_storage.get("output_directory_mangadex") == str(tmp_path)


def finish_job(gui, view_name, input_directory, output_directory):
    view = getattr(gui, view_name)
    view.start_job = lambda input_directory, output_directory: True
    view.open_output_directory_when_finished = False
    view.handle_submit(str(input_directory), str(output_directory))


def test_panel_by_panel_fills_in_the_upscale_tab_input(make_gui, tmp_path):
    gui = make_gui()
    results = tmp_path / "out" / "One Piece"
    results.mkdir(parents=True)

    finish_job(gui, "MagiPanelByPanelView", tmp_path / "One Piece", tmp_path / "out")

    upscale_directories = get_directories(gui, "UpscaleImagesView")
    assert upscale_directories.input_directory == str(results)
    assert upscale_directories.input_was_filled_in_by_app
    assert upscale_directories.input_directory_row_text.value == "One Piece"


def test_upscale_fills_in_the_video_tab_input(make_gui, tmp_path):
    gui = make_gui()
    results = tmp_path / "out" / "One Piece"
    results.mkdir(parents=True)

    finish_job(
        gui, "UpscaleImagesView", tmp_path / "panels" / "One Piece", tmp_path / "out"
    )

    assert get_directories(gui, "ImagesToVideoView").input_directory == str(results)


def test_grouped_by_page_panels_are_not_passed_on(make_gui, tmp_path):
    gui = make_gui()
    gui.page.client_storage.set("group_panels_by_page", True)
    (tmp_path / "out" / "One Piece").mkdir(parents=True)

    finish_job(gui, "MagiPanelByPanelView", tmp_path / "One Piece", tmp_path / "out")

    assert get_directories(gui, "UpscaleImagesView").input_directory == ""


def test_a_folder_the_user_picked_is_not_replaced_but_one_filled_in_by_the_app_is(
    make_gui, tmp_path
):
    gui = make_gui()
    upscale_directories = get_directories(gui, "UpscaleImagesView")
    for series in ["One Piece", "Naruto"]:
        (tmp_path / "out" / series).mkdir(parents=True)

    upscale_directories.pick_input_files_result(fake_event(path=str(tmp_path / "mine")))
    finish_job(gui, "MagiPanelByPanelView", tmp_path / "One Piece", tmp_path / "out")
    assert upscale_directories.input_directory == str(tmp_path / "mine")

    upscale_directories.handle_clear_input_directory(fake_event())
    finish_job(gui, "MagiPanelByPanelView", tmp_path / "One Piece", tmp_path / "out")
    assert upscale_directories.input_was_filled_in_by_app
    finish_job(gui, "MagiPanelByPanelView", tmp_path / "Naruto", tmp_path / "out")
    assert upscale_directories.input_directory.endswith("Naruto")


def test_a_download_fills_in_the_panel_by_panel_tab_input(make_gui, tmp_path):
    gui = make_gui()
    (tmp_path / "Old Manga").mkdir()
    newest = tmp_path / "New Manga"
    newest.mkdir()
    os.utime(tmp_path / "Old Manga", (1, 1))

    gui.MangaDexDownloaderView.fill_in_panel_by_panel_input(str(tmp_path))

    directories = get_directories(gui, "MagiPanelByPanelView")
    assert directories.input_directory == str(newest)
    assert directories.input_was_filled_in_by_app


def test_running_from_source_saves_everything_in_the_repos_own_folder(
    tmp_path, monkeypatch
):
    import default_settings

    worktree = tmp_path / "17-second-downloader"
    worktree.mkdir()
    (worktree / ".git").write_text(
        "gitdir: /repos/panelyze-main/.git/worktrees/17-second-downloader"
    )
    main_repo = tmp_path / "panelyze-main"
    (main_repo / ".git").mkdir(parents=True)

    worktree_folder = default_settings.get_dev_output_folder(str(worktree))
    assert worktree_folder is not None and worktree_folder == os.path.join(
        PANELYZE_FOLDER, "17-second-downloader"
    )
    assert default_settings.get_dev_output_folder(str(main_repo)) == os.path.join(
        PANELYZE_FOLDER, "panelyze-main"
    )
    # The packaged app (no ".git") keeps the normal folders.
    assert default_settings.get_dev_output_folder(str(tmp_path)) is None

    monkeypatch.setattr(default_settings, "DEV_OUTPUT_FOLDER", worktree_folder)
    # Even with folders saved in the (shared) settings: the Panelyze folder, or one picked for a tool (e.g. in the packaged app).
    storage = {
        "panelyze_folder": PANELYZE_FOLDER,
        "output_directory_pipeline": str(tmp_path / "picked"),
    }
    assert default_settings.get_output_directory(
        storage, "output_directory_pipeline"
    ) == os.path.join(worktree_folder, "Pipeline")
    assert not default_settings.can_pick_output_folders()


def test_output_folders_can_not_be_picked_when_running_from_source(
    make_gui, monkeypatch
):
    import default_settings

    def is_output_folder_button(control):
        return (
            getattr(getattr(control, "tooltip", None), "message", None)
            in (
                "Pick a different output folder",
                "Use the default output folder",
            )
            or getattr(control, "text", None) == "Change Output Folder"
        )

    def get_shown_output_folder_buttons(gui):
        """
        The output folder buttons that are on screen: neither hidden themselves nor inside something hidden.
        """
        views = [
            gui.PipelineView,
            gui.MangaDexDownloaderView,
            gui.MagiPanelByPanelView,
            gui.UpscaleImagesView,
            gui.ImagesToVideoView,
        ]
        shown = []

        def walk(control):
            if control.visible is False:
                return
            if is_output_folder_button(control):
                shown.append(control)
            for child in control._get_children():
                walk(child)

        for view in views:
            walk(view)
        return shown

    # The packaged app: in all 5 tabs (Pipeline, Downloader and 3 tabs with 2 buttons each).
    assert len(get_shown_output_folder_buttons(make_gui())) == 10

    monkeypatch.setattr(
        default_settings, "DEV_OUTPUT_FOLDER", "/Documents/Panelyze/panelyze-main"
    )
    assert get_shown_output_folder_buttons(make_gui()) == []


def test_each_tab_opens_the_folder_with_what_it_made(make_gui, tmp_path):
    gui = make_gui()
    out = tmp_path / "out"
    (out / "One Piece").mkdir(parents=True)
    (out / "One Piece (grouped by page)").mkdir()

    # Upscale and Images To Video: "<output>/<series>", like the input.
    for view in (gui.UpscaleImagesView, gui.ImagesToVideoView):
        assert view.get_folder_to_open(
            str(tmp_path / "Manga" / "One Piece"), str(out)
        ) == str(out / "One Piece")
        # Nothing made there: the whole output folder.
        assert view.get_folder_to_open(
            str(tmp_path / "Manga" / "Bleach"), str(out)
        ) == str(out)

    panel_by_panel = gui.MagiPanelByPanelView
    assert panel_by_panel.get_folder_to_open(
        str(tmp_path / "Manga" / "One Piece"), str(out)
    ) == str(out / "One Piece")
    gui.page.client_storage.set("group_panels_by_page", True)
    assert panel_by_panel.get_folder_to_open(
        str(tmp_path / "Manga" / "One Piece"), str(out)
    ) == str(out / "One Piece (grouped by page)")
    assert gui.UpscaleImagesView.open_output_directory_when_finished

    # One chapter's video is "<output>/Ch 1.mp4", next to a "Ch 1" folder with only its transcript and audio.
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "panel_1.png").write_bytes(b"")
    (out / "Ch 1").mkdir()
    assert gui.ImagesToVideoView.get_folder_to_open(str(chapter), str(out)) == str(out)


def test_changing_the_folder_says_the_files_saved_so_far_stay_in_the_old_one(
    make_gui, tmp_path
):
    gui = make_gui()
    settings = gui.AppSettingsView
    old_folder = tmp_path / "Old" / "Panelyze"
    (old_folder / "Downloads").mkdir(parents=True)
    gui.page.client_storage.set("panelyze_folder", str(old_folder))

    settings.pick_panelyze_folder_result(fake_event(path=str(tmp_path / "New")))

    # Nothing changes until it's confirmed, and the message names both folders.
    dialog = gui.page.dialog
    assert dialog.open
    message = "".join(span.text for span in dialog.content.spans)
    assert str(tmp_path / "New" / "Panelyze") in message
    assert f"stay in {old_folder}. They aren't moved." in message
    assert gui.page.client_storage.get("panelyze_folder") == str(old_folder)

    # Cancel keeps the old folder.
    cancel, change = dialog.actions
    cancel.on_click(None)
    assert not dialog.open
    assert gui.page.client_storage.get("panelyze_folder") == str(old_folder)

    # "Change Folder" changes it, and the old files are left alone.
    settings.pick_panelyze_folder_result(fake_event(path=str(tmp_path / "New")))
    gui.page.dialog.actions[1].on_click(None)
    assert gui.page.client_storage.get("panelyze_folder") == str(
        tmp_path / "New" / "Panelyze"
    )
    assert (old_folder / "Downloads").is_dir()


def test_use_default_folder_also_asks_when_the_current_folder_has_files(
    make_gui, tmp_path
):
    gui = make_gui()
    old_folder = tmp_path / "Panelyze"
    (old_folder / "Videos").mkdir(parents=True)
    gui.page.client_storage.set("panelyze_folder", str(old_folder))

    gui.AppSettingsView.ask_to_change_panelyze_folder(PANELYZE_FOLDER)

    assert gui.page.dialog.open
    assert gui.page.client_storage.get("panelyze_folder") == str(old_folder)


def test_a_folder_with_only_hidden_files_counts_as_empty(make_gui, tmp_path):
    gui = make_gui()
    old_folder = tmp_path / "Panelyze"
    old_folder.mkdir()
    # Finder adds this when the folder is just opened.
    (old_folder / ".DS_Store").write_bytes(b"")
    gui.page.client_storage.set("panelyze_folder", str(old_folder))

    gui.AppSettingsView.ask_to_change_panelyze_folder(str(tmp_path / "New"))

    assert gui.page.dialog is None
    assert gui.page.client_storage.get("panelyze_folder") == str(tmp_path / "New")


def test_a_folder_that_cannot_be_read_is_asked_about(make_gui, tmp_path, monkeypatch):
    gui = make_gui()
    old_folder = tmp_path / "Panelyze"
    old_folder.mkdir()
    gui.page.client_storage.set("panelyze_folder", str(old_folder))

    def refuse(path):
        raise PermissionError(path)

    # Like macOS not allowing the app into Documents or an external drive.
    monkeypatch.setattr(os, "scandir", refuse)
    gui.AppSettingsView.ask_to_change_panelyze_folder(str(tmp_path / "New"))

    assert gui.page.dialog.open
    assert gui.page.client_storage.get("panelyze_folder") == str(old_folder)


def test_no_question_is_asked_while_a_job_runs(make_gui, tmp_path):
    gui = make_gui()
    old_folder = tmp_path / "Panelyze"
    (old_folder / "Videos").mkdir(parents=True)
    gui.page.client_storage.set("panelyze_folder", str(old_folder))
    gui.is_job_running = True

    gui.AppSettingsView.ask_to_change_panelyze_folder(str(tmp_path / "New"))

    # The usual "can't change the folder while a job is running" message instead.
    assert gui.page.dialog is None
    assert gui.page.client_storage.get("panelyze_folder") == str(old_folder)
