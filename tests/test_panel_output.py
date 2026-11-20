import os
from types import SimpleNamespace

import numpy

from tests.fake_pages import drawn_page
from magi import Magi
from tests.fake_gui import fake_event

TWO_PANELS = {"panels": [[0, 0, 50, 50], [50, 50, 100, 100]]}
ONE_PANEL = {"panels": [[0, 0, 100, 100]]}


def get_magi_with_fake_panels(monkeypatch):
    magi = Magi.__new__(Magi)
    monkeypatch.setattr(magi, "predict_panels", lambda pages, reading_direction: [TWO_PANELS, ONE_PANEL])
    return magi


def run_magi(magi, tmp_path, group_by_page):
    pages = [drawn_page() for _ in range(2)]

    magi.get_panels_using_local_cpu(
        pages, "Series/Ch 1", str(tmp_path), group_by_page=group_by_page
    )

    return tmp_path / "panel-by-panel"


def test_not_grouped_by_page_saves_only_the_panels_together(tmp_path, monkeypatch):
    panel_by_panel = run_magi(get_magi_with_fake_panels(monkeypatch), tmp_path, False)

    assert os.listdir(panel_by_panel) == ["not-grouped-by-page"]
    chapter = panel_by_panel / "not-grouped-by-page" / "Series" / "Ch 1"
    # Numbered in reading order across both pages.
    assert sorted(os.listdir(chapter)) == ["panel_1.png", "panel_2.png", "panel_3.png"]


def test_grouped_by_page_saves_only_a_folder_for_each_page(tmp_path, monkeypatch):
    panel_by_panel = run_magi(get_magi_with_fake_panels(monkeypatch), tmp_path, True)

    assert os.listdir(panel_by_panel) == ["grouped-by-page"]
    chapter = panel_by_panel / "grouped-by-page" / "Series" / "Ch 1"
    assert sorted(os.listdir(chapter)) == ["page_1", "page_2"]
    assert sorted(os.listdir(chapter / "page_1")) == ["panel_1.png", "panel_2.png"]
    assert os.listdir(chapter / "page_2") == ["panel_1.png"]


def test_the_temporary_page_folders_are_cleaned_up(tmp_path, monkeypatch):
    import tempfile

    temporary_folders = []
    make_temporary_folder = tempfile.mkdtemp
    monkeypatch.setattr(
        tempfile,
        "mkdtemp",
        lambda *args, **kwargs: temporary_folders.append(make_temporary_folder(*args, **kwargs))
        or temporary_folders[-1],
    )

    run_magi(get_magi_with_fake_panels(monkeypatch), tmp_path, False)

    assert temporary_folders
    assert not any(os.path.exists(folder) for folder in temporary_folders)


def test_group_by_page_is_off_by_default_and_the_checkbox_saves_it(make_gui):
    gui = make_gui()
    view = gui.MagiPanelByPanelView
    checkbox = view.pick_input_output_directories_container.settings_container.content.controls[1].checkbox

    assert gui.page.client_storage.get("group_panels_by_page") is False
    assert checkbox.value is False

    checkbox.on_change(fake_event(data="true"))
    assert gui.page.client_storage.get("group_panels_by_page") is True

    checkbox.on_change(fake_event(data="false"))
    assert gui.page.client_storage.get("group_panels_by_page") is False


def test_the_pipeline_always_saves_panels_together(make_gui, tmp_path, monkeypatch):
    gui = make_gui()
    gui.page.client_storage.set("group_panels_by_page", True)
    view = gui.MagiPanelByPanelView
    group_by_page_used = []

    monkeypatch.setattr(
        "magi.get_magi",
        lambda: type(
            "FakeMagi",
            (),
            {
                "get_panels_for_chapter": lambda self, *args, **kwargs: group_by_page_used.append(
                    kwargs["group_by_page"]
                )
            },
        )(),
    )
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"")

    # Its own tab uses the checkbox. The Pipeline turns it off for its step.
    view.start_job(str(tmp_path / "Manga"), str(tmp_path / "out"))
    gui.PipelineView.run_step("Panel-By-Panel", str(tmp_path / "Manga"), str(tmp_path / "out"))

    assert group_by_page_used == [True, False]
    assert view.ignore_group_by_page is False


def test_panel_by_panel_also_saves_a_comic_file_when_turned_on(make_gui, tmp_path, monkeypatch):
    import zipfile

    gui = make_gui()
    gui.page.client_storage.set("save_as_cbz", "full")
    magi = get_magi_with_fake_panels(monkeypatch)
    monkeypatch.setattr(
        "magi.get_magi",
        lambda: SimpleNamespace(
            get_panels_for_chapter=lambda image_folder, output_directory, **kwargs: magi.get_panels_using_local_cpu(
                [drawn_page()] * 2, "Manga/Ch 1", output_directory
            )
        ),
    )
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"")

    gui.MagiPanelByPanelView.process_image_folder(str(chapter), [], str(tmp_path / "Manga"), str(tmp_path / "out"))

    cbz_path = tmp_path / "out" / "panel-by-panel" / "not-grouped-by-page" / "Manga" / "Ch 1.cbz"
    with zipfile.ZipFile(cbz_path) as cbz:
        assert cbz.namelist() == ["0001.png", "0002.png", "0003.png"]


def test_the_comic_file_setting_is_in_the_app_settings(make_gui):
    import flet as ft
    from tests.fake_gui import get_all_controls

    gui = make_gui()
    dropdown = next(
        control
        for control in get_all_controls(gui.AppSettingsView)
        if isinstance(control, ft.Dropdown) and ".cbz" in control.label
    )

    assert dropdown.value == ""
    dropdown.on_change(fake_event(data="small"))

    assert gui.page.client_storage.get("save_as_cbz") == "small"


def test_show_full_characters_is_off_by_default_and_is_passed_to_magi(make_gui, tmp_path, monkeypatch):
    import magi as magi_module

    gui = make_gui()
    view = gui.MagiPanelByPanelView
    checkbox = view.pick_input_output_directories_container.settings_container.content.controls[2].checkbox
    fake_magi = SimpleNamespace(show_full_characters=None, get_panels_for_chapter=lambda *args, **kwargs: None)
    monkeypatch.setattr(magi_module, "get_magi", lambda: fake_magi)
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"")

    assert checkbox.value is False
    view.start_job(str(tmp_path / "Manga"), str(tmp_path / "out"))
    assert fake_magi.show_full_characters is False

    checkbox.on_change(fake_event(data="true"))
    view.start_job(str(tmp_path / "Manga"), str(tmp_path / "out"))
    assert fake_magi.show_full_characters is True
