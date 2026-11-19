import os

import flet as ft

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
    assert PANELYZE_FOLDER == os.path.expanduser("~/Documents/Panelyze")


def test_the_job_tabs_start_with_their_default_output_folder(make_gui):
    gui = make_gui()

    for view_name in ["MagiPanelByPanelView", "UpscaleImagesView", "ImagesToVideoView"]:
        directories = get_directories(gui, view_name)
        expected_folder = default_folder(OUTPUT_SETTINGS[view_name])

        assert directories.output_directory == expected_folder
        assert directories.output_directory_row_text.value == expected_folder
        assert directories.selected_output_directory_row.visible
        assert not directories.pick_output_directory_column.visible
        # Nothing is saved as picked until the user picks a folder.
        assert gui.page.client_storage.get(OUTPUT_SETTINGS[view_name]) == ""

    assert gui.PipelineView.output_directory == default_folder("output_directory_pipeline")


def test_a_picked_output_folder_is_remembered_and_can_go_back_to_the_default(make_gui, tmp_path):
    gui = make_gui()
    directories = get_directories(gui, "UpscaleImagesView")

    directories.pick_output_files_result(fake_event(path=str(tmp_path)))

    assert directories.output_directory == str(tmp_path)
    assert gui.page.client_storage.get("output_directory_upscale_images") == str(tmp_path)
    # A new window (the app opened again) uses it.
    assert get_directories(make_gui_again(gui), "UpscaleImagesView").output_directory == str(tmp_path)

    directories.handle_clear_output_directory(fake_event())

    assert directories.output_directory == default_folder("output_directory_upscale_images")
    assert gui.page.client_storage.get("output_directory_upscale_images") == ""


def make_gui_again(gui):
    import gui as gui_module

    return gui_module.GUI(gui.page)


def test_reset_all_settings_goes_back_to_the_default_output_folders(make_gui, tmp_path):
    gui = make_gui()
    get_directories(gui, "ImagesToVideoView").pick_output_files_result(fake_event(path=str(tmp_path)))
    gui.change_panelyze_folder(str(tmp_path / "Panelyze"))

    gui.reset_settings_to_default()

    assert (
        get_directories(gui, "ImagesToVideoView").output_directory
        == default_folder("output_directory_images_to_video")
    )
    assert gui.page.client_storage.get("panelyze_folder") == PANELYZE_FOLDER


def test_the_pipeline_remembers_its_output_folder(make_gui, tmp_path):
    gui = make_gui()

    gui.PipelineView.handle_directory_picked(fake_event(path=str(tmp_path)), "output")

    assert gui.PipelineView.output_directory == str(tmp_path)
    assert gui.page.client_storage.get("output_directory_pipeline") == str(tmp_path)

    gui.PipelineView.set_output_directory("")
    assert gui.PipelineView.output_directory == default_folder("output_directory_pipeline")
    assert gui.page.client_storage.get("output_directory_pipeline") == ""


def test_changing_the_panelyze_folder_moves_every_tool_that_has_no_folder_of_its_own(make_gui, tmp_path):
    gui = make_gui()
    get_directories(gui, "UpscaleImagesView").pick_output_files_result(fake_event(path=str(tmp_path / "mine")))
    new_folder = str(tmp_path / "Panelyze")

    gui.change_panelyze_folder(new_folder)

    assert get_directories(gui, "MagiPanelByPanelView").output_directory == default_folder(
        "output_directory_panel_by_panel", new_folder
    )
    assert gui.PipelineView.output_directory == default_folder("output_directory_pipeline", new_folder)
    assert gui.MangaDexDownloaderView.output_directory_text.value == default_folder(
        "output_directory_mangadex", new_folder
    )
    # A tab with its own folder keeps it.
    assert get_directories(gui, "UpscaleImagesView").output_directory == str(tmp_path / "mine")
    # The Settings page shows the new folder.
    assert gui.AppSettingsView.panelyze_folder_text.value == new_folder


def test_picking_a_folder_in_settings_makes_a_panelyze_folder_inside_it(make_gui, tmp_path):
    gui = make_gui()
    settings = gui.AppSettingsView

    settings.pick_panelyze_folder_result(fake_event(path=str(tmp_path / "Downloads")))
    assert gui.page.client_storage.get("panelyze_folder") == str(tmp_path / "Downloads" / "Panelyze")

    # Already called "Panelyze", so no second one is added.
    settings.pick_panelyze_folder_result(fake_event(path=str(tmp_path / "Panelyze")))
    assert gui.page.client_storage.get("panelyze_folder") == str(tmp_path / "Panelyze")

    # Cancelled.
    gui.AppSettingsView.pick_panelyze_folder_result(fake_event(path=None))
    assert gui.page.client_storage.get("panelyze_folder") == str(tmp_path / "Panelyze")


def test_the_settings_page_scrolls_when_it_does_not_fit(make_gui):
    settings = make_gui().AppSettingsView

    assert settings.expand
    assert settings.content.scroll == ft.ScrollMode.AUTO


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
    results = tmp_path / "out" / "panel-by-panel" / "not-grouped-by-page" / "One Piece"
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

    finish_job(gui, "UpscaleImagesView", tmp_path / "panels" / "One Piece", tmp_path / "out")

    assert get_directories(gui, "ImagesToVideoView").input_directory == str(results)


def test_grouped_by_page_panels_are_not_passed_on(make_gui, tmp_path):
    gui = make_gui()
    gui.page.client_storage.set("group_panels_by_page", True)
    (tmp_path / "out" / "panel-by-panel" / "not-grouped-by-page" / "One Piece").mkdir(parents=True)

    finish_job(gui, "MagiPanelByPanelView", tmp_path / "One Piece", tmp_path / "out")

    assert get_directories(gui, "UpscaleImagesView").input_directory == ""


def test_a_folder_the_user_picked_is_not_replaced_but_one_filled_in_by_the_app_is(make_gui, tmp_path):
    gui = make_gui()
    upscale_directories = get_directories(gui, "UpscaleImagesView")
    for series in ["One Piece", "Naruto"]:
        (tmp_path / "out" / "panel-by-panel" / "not-grouped-by-page" / series).mkdir(parents=True)

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
