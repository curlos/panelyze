import os
from types import SimpleNamespace
from typing import Any, cast

import pytest

from tests.fake_pages import drawn_page
from magi import Magi
from tests.fake_gui import fake_event

TWO_PANELS = {"panels": [[0, 0, 50, 50], [50, 50, 100, 100]]}
ONE_PANEL = {"panels": [[0, 0, 100, 100]]}


def get_magi_with_fake_panels(monkeypatch):
    magi = Magi.__new__(Magi)
    monkeypatch.setattr(
        magi, "predict_panels", lambda pages, reading_direction: [TWO_PANELS, ONE_PANEL]
    )
    return magi


def run_magi(magi, tmp_path, group_by_page):
    pages = [drawn_page() for _ in range(2)]

    magi.get_panels_using_local_cpu(
        pages, "Series/Ch 1", str(tmp_path), group_by_page=group_by_page
    )

    return tmp_path


def test_not_grouped_by_page_saves_only_the_panels_together(tmp_path, monkeypatch):
    panel_by_panel = run_magi(get_magi_with_fake_panels(monkeypatch), tmp_path, False)

    # Saved like every other tab's output: "<output>/<series>/<chapter>".
    assert os.listdir(panel_by_panel / "Series") == ["Ch 1"]
    chapter = panel_by_panel / "Series" / "Ch 1"
    # Numbered in reading order across both pages.
    assert sorted(os.listdir(chapter)) == ["panel_1.png", "panel_2.png", "panel_3.png"]


def test_grouped_by_page_saves_only_a_folder_for_each_page(tmp_path, monkeypatch):
    panel_by_panel = run_magi(get_magi_with_fake_panels(monkeypatch), tmp_path, True)

    # In a folder of its own, so it never mixes with panels that aren't grouped.
    assert os.listdir(panel_by_panel) == ["Series (grouped by page)"]
    chapter = panel_by_panel / "Series (grouped by page)" / "Ch 1"
    assert sorted(os.listdir(chapter)) == ["page_1", "page_2"]
    assert sorted(os.listdir(chapter / "page_1")) == ["panel_1.png", "panel_2.png"]
    assert os.listdir(chapter / "page_2") == ["panel_1.png"]


def test_a_new_run_replaces_only_the_old_panels_and_keeps_other_files(
    tmp_path, monkeypatch
):
    # The output folder can be picked, so the chapter's folder might also hold other files (e.g. a downloaded chapter's pages).
    chapter = tmp_path / "Series" / "Ch 1"
    chapter.mkdir(parents=True)
    for name in ["001.png", "panel_9.png", "panel-text.json", "reading-direction.txt"]:
        (chapter / name).write_bytes(b"old")
    (chapter / "page_4").mkdir()

    run_magi(get_magi_with_fake_panels(monkeypatch), tmp_path, False)

    assert sorted(os.listdir(chapter)) == [
        "001.png",
        "panel_1.png",
        "panel_2.png",
        "panel_3.png",
    ]
    assert (chapter / "001.png").read_bytes() == b"old"


def test_the_temporary_page_folders_are_cleaned_up(tmp_path, monkeypatch):
    import tempfile

    temporary_folders = []
    make_temporary_folder = tempfile.mkdtemp
    monkeypatch.setattr(
        tempfile,
        "mkdtemp",
        lambda *args, **kwargs: (
            temporary_folders.append(make_temporary_folder(*args, **kwargs))
            or temporary_folders[-1]
        ),
    )

    run_magi(get_magi_with_fake_panels(monkeypatch), tmp_path, False)

    assert temporary_folders
    assert not any(os.path.exists(folder) for folder in temporary_folders)


def test_group_by_page_is_off_by_default_and_the_checkbox_saves_it(make_gui):
    gui = make_gui()
    view = gui.MagiPanelByPanelView
    checkbox = view.pick_input_output_directories_container.settings_container.content.controls[
        1
    ].checkbox

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
                "get_panels_for_chapter": lambda self, *args, **kwargs: (
                    group_by_page_used.append(kwargs["group_by_page"])
                )
            },
        )(),
    )
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"")

    # Its own tab uses the checkbox. The Pipeline turns it off for its step.
    view.start_job(str(tmp_path / "Manga"), str(tmp_path / "out"))
    gui.PipelineView.run_step(
        "Panel-By-Panel", str(tmp_path / "Manga"), str(tmp_path / "out")
    )

    assert group_by_page_used == [True, False]
    assert view.ignore_group_by_page is False


def test_panels_grouped_by_page_are_also_saved_as_a_comic_file(
    make_gui, tmp_path, monkeypatch
):
    import zipfile

    gui = make_gui()
    gui.page.client_storage.set("save_as_cbz", "full")
    gui.page.client_storage.set("group_panels_by_page", True)
    magi = get_magi_with_fake_panels(monkeypatch)
    monkeypatch.setattr(
        "magi.get_magi",
        lambda: SimpleNamespace(
            get_panels_for_chapter=lambda image_folder, output_directory, **kwargs: (
                magi.get_panels_using_local_cpu(
                    [drawn_page()] * 2,
                    "Manga/Ch 1",
                    output_directory,
                    group_by_page=kwargs["group_by_page"],
                )
            )
        ),
    )
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"")

    gui.MagiPanelByPanelView.process_image_folder(
        str(chapter), [], str(tmp_path / "Manga"), str(tmp_path / "out")
    )

    comic_files = [
        os.path.join(folder, name)
        for folder, _, names in os.walk(tmp_path / "out")
        for name in names
        if name.endswith(".cbz")
    ]
    assert len(comic_files) == 1
    with zipfile.ZipFile(comic_files[0]) as cbz:
        # Every panel of both pages (2 + 1), in reading order.
        assert [name for name in cbz.namelist() if name.endswith(".png")] == [
            "0001.png",
            "0002.png",
            "0003.png",
        ]


def test_panel_by_panel_also_saves_a_comic_file_when_turned_on(
    make_gui, tmp_path, monkeypatch
):
    import zipfile

    gui = make_gui()
    gui.page.client_storage.set("save_as_cbz", "full")
    magi = get_magi_with_fake_panels(monkeypatch)
    monkeypatch.setattr(
        "magi.get_magi",
        lambda: SimpleNamespace(
            get_panels_for_chapter=lambda image_folder, output_directory, **kwargs: (
                magi.get_panels_using_local_cpu(
                    [drawn_page()] * 2, "Manga/Ch 1", output_directory
                )
            )
        ),
    )
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"")

    gui.MagiPanelByPanelView.process_image_folder(
        str(chapter), [], str(tmp_path / "Manga"), str(tmp_path / "out")
    )

    cbz_path = tmp_path / "out" / "Manga" / "Ch 1.cbz"
    with zipfile.ZipFile(cbz_path) as cbz:
        assert cbz.namelist() == ["0001.png", "0002.png", "0003.png", "ComicInfo.xml"]
        # One panel at a time, even in an app's two-page view.
        comic_info = cbz.read("ComicInfo.xml").decode()
    assert comic_info.count('DoublePage="true"') == 3
    # "Automatic" with no direction saved by a download: Magi cut the panels in manga order.
    assert "<Manga>YesAndRightToLeft</Manga>" in comic_info

    # A direction picked in the app is used.
    gui.page.client_storage.set("reading_direction", "ltr")
    gui.MagiPanelByPanelView.process_image_folder(
        str(chapter), [], str(tmp_path / "Manga"), str(tmp_path / "out")
    )
    with zipfile.ZipFile(cbz_path) as cbz:
        assert "<Manga>" not in cbz.read("ComicInfo.xml").decode()


def test_the_comic_file_setting_is_in_the_app_settings(make_gui):
    import flet as ft
    from tests.fake_gui import get_all_controls

    gui = make_gui()
    dropdown = next(
        control
        for control in get_all_controls(gui.AppSettingsView)
        if isinstance(control, ft.Dropdown) and ".cbz" in str(control.label)
    )

    # "No" (saved as "") is "no" in the dropdown, since a choice with an empty key shows nothing in the box.
    assert dropdown.value == "no"
    assert dropdown.on_change is not None
    dropdown.on_change(fake_event(data="small"))
    assert gui.page.client_storage.get("save_as_cbz") == "small"

    dropdown.on_change(fake_event(data="no"))
    assert gui.page.client_storage.get("save_as_cbz") == ""


def test_show_full_characters_is_off_by_default_and_is_passed_to_magi(
    make_gui, tmp_path, monkeypatch
):
    import magi as magi_module

    gui = make_gui()
    view = gui.MagiPanelByPanelView
    checkbox = view.pick_input_output_directories_container.settings_container.content.controls[
        2
    ].checkbox
    fake_magi = SimpleNamespace(
        show_full_characters=None, get_panels_for_chapter=lambda *args, **kwargs: None
    )
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


def test_split_tall_panels_is_on_by_default_and_its_checkbox_is_passed_to_magi(
    make_gui, tmp_path, monkeypatch
):
    import magi as magi_module

    gui = make_gui()
    view = gui.MagiPanelByPanelView
    from tests.test_mangadex_folders import find_checkbox

    checkbox = find_checkbox(
        view, "Split very tall panels for phones (never through text)"
    ).checkbox
    fake_magi = SimpleNamespace(
        split_tall_panels=None,
        show_full_characters=None,
        get_panels_for_chapter=lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(magi_module, "get_magi", lambda: fake_magi)
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"")

    assert checkbox.value is True and checkbox.on_change is not None
    view.start_job(str(tmp_path / "Manga"), str(tmp_path / "out"))
    assert fake_magi.split_tall_panels is True

    checkbox.on_change(fake_event(data="false"))
    view.start_job(str(tmp_path / "Manga"), str(tmp_path / "out"))
    assert fake_magi.split_tall_panels is False


@pytest.mark.parametrize("split_tall_panels, panel_count", [(True, 6), (False, 3)])
def test_split_tall_panels_decides_whether_panels_are_split(
    tmp_path, monkeypatch, split_tall_panels, panel_count
):
    import magi as magi_module

    # Every panel "is tall" here and splits in two.
    monkeypatch.setattr(
        magi_module, "split_tall_panel", lambda panel, page, texts: [panel, panel]
    )
    magi = get_magi_with_fake_panels(monkeypatch)
    magi.split_tall_panels = split_tall_panels

    chapter = run_magi(magi, tmp_path, False) / "Series" / "Ch 1"

    assert len(os.listdir(chapter)) == panel_count


def test_a_chapter_already_split_into_panels_is_skipped_until_something_changes(
    make_gui, tmp_path, monkeypatch
):
    gui = make_gui()
    storage = gui.page.client_storage
    magi = get_magi_with_fake_panels(monkeypatch)
    splits = []

    def get_panels_for_chapter(image_folder, output_directory, **kwargs):
        splits.append(1)
        magi.get_panels_using_local_cpu(
            [drawn_page()] * 2, "Manga/Ch 1", output_directory
        )

    monkeypatch.setattr(
        "magi.get_magi",
        lambda: SimpleNamespace(get_panels_for_chapter=get_panels_for_chapter),
    )
    chapter = tmp_path / "Manga" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "01.png").write_bytes(b"page")
    panels = tmp_path / "out" / "Manga" / "Ch 1"

    def split():
        gui.MagiPanelByPanelView.process_image_folder(
            str(chapter),
            [{"name": "01.png"}],
            str(tmp_path / "Manga"),
            str(tmp_path / "out"),
        )
        return len(splits)

    assert split() == 1
    assert "panels-info.json" in os.listdir(panels)
    # Same pages and settings: kept.
    assert split() == 1
    # A setting that changes the panels.
    storage.set("show_full_characters", True)
    assert split() == 2
    assert split() == 2
    # "Split into panels again even if already split".
    storage.set("split_panels_again", True)
    assert split() == 3
    storage.set("split_panels_again", False)
    # A page that changed.
    (chapter / "01.png").write_bytes(b"a new page")
    assert split() == 4
    # The text is needed for a video now (a Pipeline that makes one).
    gui.MagiPanelByPanelView.read_text_for_video = True
    assert split() == 5
    gui.MagiPanelByPanelView.read_text_for_video = False
    # On "Automatic", a direction a download saved next to the pages changes the order.
    split()
    (chapter / "reading-direction.txt").write_text("ltr")
    assert split() == 7
    # Panels that were deleted.
    for name in os.listdir(panels):
        if name.startswith("panel_"):
            os.remove(panels / name)
    assert split() == 8


def test_the_result_line_says_when_chapters_were_already_split(
    make_gui, tmp_path, monkeypatch
):
    gui = make_gui()
    view = gui.MagiPanelByPanelView
    magi = get_magi_with_fake_panels(monkeypatch)
    monkeypatch.setattr(
        "magi.get_magi",
        lambda: SimpleNamespace(
            get_panels_for_chapter=lambda image_folder, output_directory, selected_input_directory, **kwargs: (
                magi.get_panels_using_local_cpu(
                    [drawn_page()] * 2,
                    os.path.relpath(
                        image_folder, os.path.dirname(selected_input_directory)
                    ),
                    output_directory,
                )
            )
        ),
    )

    def add_chapter(chapter):
        (tmp_path / "Manga" / chapter).mkdir(parents=True)
        (tmp_path / "Manga" / chapter / "01.png").write_bytes(chapter.encode())

    add_chapter("Ch 1")
    results = []
    monkeypatch.setattr(
        gui.terminal_output,
        "hide_loading_text",
        lambda text, *args, **kwargs: results.append(text),
    )

    def run(input_directory):
        assert view.start_job(str(input_directory), str(tmp_path / "out"))
        return results[-1]

    assert run(tmp_path / "Manga") == "Panel-By-Panel conversion finished!"
    assert run(tmp_path / "Manga") == "Already split into panels (kept): Ch 1"
    add_chapter("Ch 2")
    assert (
        run(tmp_path / "Manga")
        == "Panel-By-Panel conversion finished! 1 of 2 chapters was already split (kept)."
    )
    assert run(tmp_path / "Manga") == "Already split into panels (kept): 2 chapters"


def test_the_picked_folder_says_how_many_new_chapters_will_be_split(
    make_gui, tmp_path, monkeypatch
):
    from gui_classes.WrappingCheckbox import WrappingCheckbox
    from tests.fake_gui import get_all_controls

    gui = make_gui()
    view = gui.MagiPanelByPanelView
    directories = view.pick_input_output_directories_container
    directories.output_directory = str(tmp_path / "out")
    magi = get_magi_with_fake_panels(monkeypatch)
    monkeypatch.setattr(
        "magi.get_magi",
        lambda: SimpleNamespace(
            get_panels_for_chapter=lambda image_folder, output_directory, selected_input_directory, **kwargs: (
                magi.get_panels_using_local_cpu(
                    [drawn_page()] * 2,
                    os.path.relpath(
                        image_folder, os.path.dirname(selected_input_directory)
                    ),
                    output_directory,
                )
            )
        ),
    )

    def add_chapter(chapter):
        (tmp_path / "Manga" / chapter).mkdir(parents=True)
        (tmp_path / "Manga" / chapter / "01.png").write_bytes(chapter.encode())

    def get_summary():
        directories.set_input_directory(str(tmp_path / "Manga"))
        return directories.input_summary_text.value

    add_chapter("Ch 1")
    add_chapter("Ch 2")
    assert get_summary() == "2 chapters · 2 pages"

    # Through the button: the line is up to date right after the run.
    directories.set_input_directory(str(tmp_path / "Manga"))
    directories.handle_submit(fake_event())
    assert (
        directories.input_summary_text.value
        == "2 chapters · 2 pages · already split, nothing new to split"
    )

    add_chapter("Ch 3")
    assert get_summary() == "3 chapters · 3 pages · only 1 new chapter to split"

    # A setting that changes the panels: every chapter will be split again, and the line says so right away.
    checkbox = next(
        control
        for control in get_all_controls(view)
        if isinstance(control, WrappingCheckbox)
        and "full characters"
        in str(cast(Any, control.controls[1]).content.controls[-1].value)
    )
    checkbox.checkbox.value = True
    assert checkbox.checkbox.on_change is not None
    checkbox.checkbox.on_change(fake_event(data="true"))
    assert directories.input_summary_text.value == "3 chapters · 3 pages"
    checkbox.handle_label_click(None)
    assert (
        directories.input_summary_text.value
        == "3 chapters · 3 pages · only 1 new chapter to split"
    )

    # The reading direction, "Split into panels again" and another output folder.
    dropdown = next(
        control
        for control in get_all_controls(view)
        if getattr(control, "label", None) == "Reading Direction"
    )
    dropdown.on_change(fake_event(data="ltr"))
    assert directories.input_summary_text.value == "3 chapters · 3 pages"
    dropdown.on_change(fake_event(data="auto"))
    gui.page.client_storage.set("split_panels_again", True)
    directories.refresh_input_summary()
    assert directories.input_summary_text.value == "3 chapters · 3 pages"
    gui.page.client_storage.set("split_panels_again", False)
    directories.show_output_directory(str(tmp_path / "other"))
    assert directories.input_summary_text.value == "3 chapters · 3 pages"


def test_panel_by_panel_shows_its_stages_finding_then_saving_the_panels(
    tmp_path, monkeypatch
):
    import gui_classes.ProgressPanel as progress_module

    reported = []
    monkeypatch.setattr(
        progress_module, "report_progress", lambda **fields: reported.append(fields)
    )

    run_magi(get_magi_with_fake_panels(monkeypatch), tmp_path, False)

    assert reported[0] == {
        "stages": ("Finding the panels", "Saving the panels"),
        "stage": "Finding the panels",
        "unit": "pages",
    }
    saving = reported.index(
        {
            "stage": "Saving the panels",
            "pages_done": 0,
            "pages_total": 2,
            "detail": None,
        }
    )
    # Each page's panels are counted as they're saved.
    assert reported[saving + 1 :] == [{"pages_done": 1}, {"pages_done": 2}]


def test_panels_are_never_saved_over_the_images_being_split(tmp_path, monkeypatch):
    import pytest
    from PIL import Image

    # Panel-By-Panel run on its own earlier output: "Panels/One Piece" picked, saving to "Panels". The chapter's panels would be saved in "Panels/One Piece/Ch 1" itself.
    chapter = tmp_path / "Panels" / "One Piece" / "Ch 1"
    chapter.mkdir(parents=True)
    Image.new("RGB", (200, 300), "red").save(chapter / "panel_1.png")
    original = (chapter / "panel_1.png").read_bytes()
    magi = Magi()
    magi.split_tall_panels = False
    monkeypatch.setattr(
        magi,
        "predict_panels",
        lambda pages, reading_direction: [
            {"panels": [[0, 0, 100, 100]], "texts": []} for _ in pages
        ],
    )

    with pytest.raises(RuntimeError, match="would be saved over the images"):
        magi.get_panels_for_chapter(
            str(chapter),
            str(tmp_path / "Panels"),
            str(tmp_path / "Panels" / "One Piece"),
            reading_direction="rtl",
        )

    assert sorted(os.listdir(chapter)) == ["panel_1.png"]
    assert (chapter / "panel_1.png").read_bytes() == original
