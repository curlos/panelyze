"""
Settings → Storage. Every folder here is a fake one in "tmp_path" (see "keep_storage_in_tmp_path" in conftest.py): the tests never read or delete the real downloads, models or Hugging Face cache.
"""

import os
import time

import flet as ft

import default_settings
from gui_classes.ProgressPanel import get_download_detail
import janai
import storage
import utils
from storage import get_output_directory as real_get_output_directory
from storage import get_panelyze_folder as real_get_panelyze_folder
from tests.fake_gui import (
    FakeClientStorage,
    fake_event,
    get_all_controls,
    get_shown_text,
)


def write_file(path, size=10):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as file:
        file.write(b"x" * size)


def use_real_saved_folders(monkeypatch):
    # conftest.py puts the saved files in "tmp_path". These tests check where they really are.
    monkeypatch.setattr(storage, "get_output_directory", real_get_output_directory)
    monkeypatch.setattr(storage, "get_panelyze_folder", real_get_panelyze_folder)


def get_row(rows, name):
    return next(row for row in rows if row.name == name)


def test_the_size_counts_files_and_folders_and_a_link_only_once(tmp_path):
    write_file(str(tmp_path / "model" / "blobs" / "abc"), 1000)
    os.makedirs(tmp_path / "model" / "snapshots")
    # Like the Hugging Face cache: a link in "snapshots" to the file in "blobs".
    os.symlink(
        tmp_path / "model" / "blobs" / "abc", tmp_path / "model" / "snapshots" / "abc"
    )
    write_file(str(tmp_path / "file.pth"), 50)

    size = storage.get_size(
        [str(tmp_path / "model"), str(tmp_path / "file.pth"), str(tmp_path / "gone")]
    )

    link_size = os.lstat(tmp_path / "model" / "snapshots" / "abc").st_size
    assert size == 1000 + 50 + link_size


def test_from_source_only_this_worktrees_own_folder_is_shown(tmp_path, monkeypatch):
    use_real_saved_folders(monkeypatch)
    panelyze_folder = tmp_path / "Panelyze"
    this_worktree = panelyze_folder / "33-storage"
    monkeypatch.setattr(default_settings, "DEV_OUTPUT_FOLDER", str(this_worktree))
    write_file(str(panelyze_folder / "other-worktree" / "Downloads" / "page.png"))

    rows = storage.get_saved_files_rows(FakeClientStorage())

    assert [row.name for row in rows] == [
        "Downloads",
        "Panel-By-Panel",
        "Upscaled Images",
        "Videos",
        "Pipeline",
    ]
    for row in rows:
        assert row.paths == [row.folder_to_open]
        assert row.folder_to_open.startswith(str(this_worktree) + os.sep)
        assert row.can_delete
    assert get_row(rows, "Upscaled Images").paths == [
        str(this_worktree / "Upscaled Images")
    ]


def test_in_the_app_a_folder_picked_in_a_tab_is_shown_but_not_deleted(
    tmp_path, monkeypatch
):
    use_real_saved_folders(monkeypatch)
    client_storage = FakeClientStorage()
    client_storage.set("panelyze_folder", str(tmp_path / "Panelyze"))
    client_storage.set("output_directory_images_to_video", str(tmp_path / "Desktop"))

    rows = storage.get_saved_files_rows(client_storage)

    assert get_row(rows, "Downloads").paths == [
        str(tmp_path / "Panelyze" / "Downloads")
    ]
    assert get_row(rows, "Downloads").can_delete
    assert get_row(rows, "Videos").paths == [str(tmp_path / "Desktop")]
    assert not get_row(rows, "Videos").can_delete


def test_waifu2x_can_only_be_deleted_when_the_app_downloaded_it(monkeypatch):
    # One installed on the computer isn't the app's (and isn't used).
    monkeypatch.setattr(utils.shutil, "which", lambda name: "/opt/waifu2x/waifu2x")
    row = storage.get_waifu2x_row()
    assert row.status == storage.NOT_DOWNLOADED and row.download and not row.can_delete

    # Inside the packaged app.
    monkeypatch.setattr(utils, "is_running_as_packaged_app", lambda: True)
    assert storage.get_waifu2x_row().status == storage.BUILT_IN

    write_file(os.path.join(utils.DOWNLOADED_WAIFU2X_FOLDER, "waifu2x-ncnn-vulkan"))
    row = storage.get_waifu2x_row()
    assert row.status == storage.DOWNLOADED and row.can_delete
    assert row.paths == [utils.DOWNLOADED_WAIFU2X_FOLDER]


def test_deleting_one_upscale_model_leaves_the_others(tmp_path):
    for file_name in janai.MANGA_MODEL_FILES.values():
        write_file(os.path.join(janai.MODELS_FOLDER, file_name))
    write_file(
        os.path.join(
            janai.MODELS_FOLDER,
            "2x_MangaJaNai_1200p_V1_ESRGAN_70k-256.mlpackage",
            "model.bin",
        )
    )
    rows = storage.get_model_rows()
    manga_row = get_row(rows, "MangaJaNai (7 models)")
    color_row = get_row(rows, "IllustrationJaNai")
    assert manga_row.status == storage.DOWNLOADED and len(manga_row.paths) == 8
    assert color_row.status == storage.NOT_DOWNLOADED and not color_row.can_delete

    write_file(os.path.join(janai.MODELS_FOLDER, janai.COLOR_MODEL_FILE))
    write_file(os.path.join(janai.MODELS_FOLDER, "something-else.txt"))
    storage.delete_paths(manga_row)

    assert sorted(os.listdir(janai.MODELS_FOLDER)) == [
        janai.COLOR_MODEL_FILE,
        "something-else.txt",
    ]
    assert (
        get_row(storage.get_model_rows(), "IllustrationJaNai").status
        == storage.DOWNLOADED
    )


def test_deleting_an_upscale_model_also_forgets_it_if_it_s_loaded(monkeypatch):
    color_path = os.path.join(janai.MODELS_FOLDER, janai.COLOR_MODEL_FILE)
    manga_path = os.path.join(janai.MODELS_FOLDER, janai.MANGA_MODEL_FILES[1200])
    write_file(color_path)
    write_file(manga_path)
    monkeypatch.setattr(
        janai,
        "_loaded_upscalers",
        {(color_path, False): "loaded", (manga_path, True): "loaded"},
    )

    storage.delete_paths(get_row(storage.get_model_rows(), "IllustrationJaNai"))

    # So the next upscale downloads and loads it again. The other model stays loaded.
    assert janai._loaded_upscalers == {(manga_path, True): "loaded"}


def test_the_manga_models_download_once_for_all_seven(monkeypatch):
    downloads = []
    monkeypatch.setattr(
        janai, "download_model_file", lambda name, url: downloads.append((name, url))
    )

    storage.download_manga_models()

    assert downloads == [(janai.MANGA_MODEL_FILES[1200], janai.MANGA_MODELS_ZIP_URL)]


def test_deleting_magi_only_deletes_its_own_folders_in_the_hugging_face_cache():
    cache = storage.get_hugging_face_cache()
    # Magi v2 doesn't download ResNet-50 on its own (it comes in Magi's file), so an old one in the cache isn't Magi's.
    other_folders = ["models--someone--other-app", "models--timm--resnet50.a1_in1k"]
    for folder in (*storage.MAGI_CACHE_FOLDERS, *other_folders):
        write_file(os.path.join(cache, folder, "blobs", "abc"))
    # A download that stopped half-way: the folder is there, but not the model file.
    row = storage.get_magi_row()
    assert row.status == storage.NOT_DOWNLOADED and row.can_delete and row.download
    write_file(
        os.path.join(
            cache,
            storage.MAGI_CACHE_FOLDERS[0],
            "snapshots",
            storage.MAGI_MODEL_REVISION,
            "pytorch_model.bin",
        )
    )
    row = storage.get_magi_row()
    assert row.status == storage.DOWNLOADED and row.can_delete

    storage.delete_paths(row)

    assert sorted(os.listdir(cache)) == sorted(other_folders)
    assert storage.get_magi_row().status == storage.NOT_DOWNLOADED


def test_the_magi_link_and_panels_model_are_the_same_as_magis():
    import magi

    assert storage.MAGI_PAGE_URL == magi.MAGI_MODEL_PAGE_URL
    assert storage.MAGI_MODEL_REVISION == magi.MAGI_MODEL_REVISION
    assert (
        os.path.join(
            default_settings.CODE_FOLDER, "magi_model", "panels_fp16.safetensors"
        )
        == magi.PANELS_MODEL_FILE
    )


def test_a_download_shows_how_much_is_done(tmp_path, monkeypatch):
    from gui_classes import ProgressPanel

    class FakeResponse:
        headers = {"Content-Length": str(3_000_000)}

        def __init__(self):
            self.chunks = [b"x" * 1_500_000, b"x" * 1_500_000]

        def read(self, size):
            return self.chunks.pop(0) if self.chunks else b""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    import urllib.request

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse()
    )
    reported = []
    monkeypatch.setattr(
        ProgressPanel, "report_progress", lambda **fields: reported.append(fields)
    )

    utils.download_file(
        "https://example.com/a.zip", str(tmp_path / "a.zip"), name="waifu2x"
    )

    assert os.path.getsize(tmp_path / "a.zip") == 3_000_000
    assert reported == [
        {
            "detail": get_download_detail("Downloading waifu2x: 1.5 MB of 3.0 MB"),
            "fraction_done": 0.5,
        },
        {
            "detail": get_download_detail("Downloading waifu2x: 3.0 MB of 3.0 MB"),
            "fraction_done": 1.0,
        },
        {"detail": None, "fraction_done": None},
    ]


def test_a_failed_download_stops_saying_it_is_downloading(tmp_path, monkeypatch):
    from gui_classes import ProgressPanel

    class BrokenResponse:
        headers = {"Content-Length": str(3_000_000)}

        def read(self, size):
            raise OSError("Connection reset")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    import urllib.request

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *args, **kwargs: BrokenResponse()
    )
    reported = []
    monkeypatch.setattr(
        ProgressPanel, "report_progress", lambda **fields: reported.append(fields)
    )

    try:
        utils.download_file("https://example.com/a.zip", str(tmp_path / "a.zip"))
    except OSError:
        pass

    assert reported == [{"detail": None, "fraction_done": None}]


def test_a_failed_best_model_download_leaves_no_half_downloaded_zip(monkeypatch):
    def broken_download(url, path, name=None):
        write_file(path, size=1000)
        raise OSError("Connection reset")

    monkeypatch.setattr(janai, "download_file", broken_download)

    try:
        janai.download_model_file(janai.COLOR_MODEL_FILE, janai.COLOR_MODEL_ZIP_URL)
    except OSError:
        pass

    assert os.listdir(janai.MODELS_FOLDER) == []


def open_storage(make_gui):
    gui = make_gui()
    gui.app_bar.change_view("Settings")
    section = gui.AppSettingsView.storage_section
    for _ in range(100):
        if section.sizes is not None:
            break
        time.sleep(0.02)
    return gui, section


def get_buttons(control, text):
    return [
        button
        for button in get_all_controls(control)
        if (
            isinstance(button, (ft.ElevatedButton, ft.TextButton))
            and button.text == text
        )
        # The rows' buttons are only icons, with their name in a tooltip.
        or (
            isinstance(button, ft.IconButton)
            and isinstance(button.tooltip, ft.Tooltip)
            and button.tooltip.message == text
        )
    ]


def click(button):
    assert button.on_click is not None
    button.on_click(fake_event())


def test_settings_shows_each_folders_size(make_gui):
    write_file(
        os.path.join(storage.get_panelyze_folder(None), "Downloads", "page.png"), 2000
    )
    write_file(os.path.join(janai.MODELS_FOLDER, janai.COLOR_MODEL_FILE), 5000)

    gui, section = open_storage(make_gui)

    texts = [
        control.value or "".join(span.text or "" for span in control.spans or [])
        for control in get_all_controls(section)
        if isinstance(control, ft.Text)
    ]
    # The Download folder's size, and the total's after "All saved files".
    assert "All saved files" in texts and texts.count("2.0 KB") == 2
    assert "Downloaded · 5.0 KB" in texts
    assert "Not downloaded · 236 MB" in texts
    assert any(
        "From https://github.com/the-database/MangaJaNai/releases" in text
        for text in texts
    )
    assert section.log_size_text.value == "Current log: 0 B · all logs: 0 B"


def test_delete_asks_first_and_only_deletes_that_folder(make_gui):
    downloads = os.path.join(storage.get_panelyze_folder(None), "Downloads")
    videos = os.path.join(storage.get_panelyze_folder(None), "Videos")
    write_file(os.path.join(downloads, "page.png"))
    write_file(os.path.join(videos, "video.mp4"))
    gui, section = open_storage(make_gui)

    # The first Delete in the "Saved files" group (after the free space line): the Downloads folder's.
    click(get_buttons(section.controls[1], "Delete")[0])
    dialog = gui.page.dialog
    assert dialog.open and "can't be undone" in get_shown_text(dialog.content)
    assert os.path.exists(downloads)

    click(get_buttons(dialog, "Delete")[0])

    assert not dialog.open
    assert not os.path.exists(downloads) and os.path.exists(videos)


def test_a_deleted_model_is_said_to_come_back(make_gui):
    write_file(os.path.join(janai.MODELS_FOLDER, janai.COLOR_MODEL_FILE))
    gui, section = open_storage(make_gui)
    row = get_row(section.model_rows, "IllustrationJaNai")

    section.confirm_delete(row)

    assert "downloaded again the next time it's needed" in get_shown_text(
        gui.page.dialog.content
    )


def test_nothing_can_be_deleted_or_downloaded_while_a_job_runs(make_gui):
    downloads = os.path.join(storage.get_panelyze_folder(None), "Downloads")
    write_file(os.path.join(downloads, "page.png"))
    gui, section = open_storage(make_gui)
    gui.try_to_start_job("Upscale")
    errors = []
    gui.terminal_output.update_terminal_with_error_message = errors.append

    section.render()
    buttons = get_buttons(section, "Delete") + get_buttons(section, "Download")
    assert buttons and all(button.disabled for button in buttons)

    # A dialog opened just before the job started.
    section.delete([section.saved_files_rows[0]], ft.AlertDialog())
    assert os.path.exists(downloads) and gui.running_job_name == "Upscale"


def test_no_job_can_start_while_something_is_being_deleted(make_gui, monkeypatch):
    gui, section = open_storage(make_gui)
    job_was_running = []
    monkeypatch.setattr(
        storage, "delete_paths", lambda row: job_was_running.append(gui.is_job_running)
    )

    section.delete([section.saved_files_rows[0]], ft.AlertDialog())

    assert job_was_running == [True]
    assert not gui.is_job_running


def test_download_runs_as_a_job_and_shows_its_error(make_gui):
    gui, section = open_storage(make_gui)
    row = get_row(section.model_rows, "IllustrationJaNai")
    job_was_running = []
    errors = []
    gui.terminal_output.update_terminal_with_error_message = errors.append

    def fake_download():
        job_was_running.append(gui.is_job_running)
        raise OSError("No internet")

    row.download = fake_download
    section.download(row)

    assert job_was_running == [True]
    assert not gui.is_job_running
    assert errors == ["ERROR: No internet"]

    # Only one job at a time.
    gui.try_to_start_job("Upscale")
    job_was_running.clear()
    section.download(row)
    assert job_was_running == []


def test_a_download_by_another_library_shows_how_much_is_done(tmp_path, monkeypatch):
    from gui_classes import ProgressPanel

    reported = []
    monkeypatch.setattr(
        ProgressPanel, "report_progress", lambda **fields: reported.append(fields)
    )
    folder = tmp_path / "models--ragavsachdeva--magiv2"

    with utils.report_folder_download("the Magi model", folder, 2000, interval=0.01):
        write_file(str(folder / "blobs" / "model.incomplete"), size=1000)
        # Plenty of checks (every 0.01 s), even on a busy computer.
        time.sleep(1)

    assert {
        "detail": get_download_detail("Downloading the Magi model: 1.0 KB of 2.0 KB"),
        "fraction_done": 0.5,
    } in reported
    assert reported[-1] == {"detail": None, "fraction_done": None}


def test_nothing_is_said_when_the_model_was_already_downloaded(tmp_path, monkeypatch):
    from gui_classes import ProgressPanel

    reported = []
    monkeypatch.setattr(
        ProgressPanel, "report_progress", lambda **fields: reported.append(fields)
    )
    write_file(str(tmp_path / "blobs" / "model"), size=1000)

    with utils.report_folder_download("the Magi model", tmp_path, 2000, interval=0.01):
        time.sleep(0.1)

    assert reported == [{"detail": None, "fraction_done": None}]


def test_the_emotion_model_is_listed_and_only_its_own_folder_is_deleted():
    import EmotionAnalyzer
    from EmotionAnalyzer import EMOTION_CACHE_FOLDER

    cache = storage.get_hugging_face_cache()
    row = storage.get_emotion_row()
    assert row.status == storage.NOT_DOWNLOADED and row.download and not row.paths

    write_file(os.path.join(cache, EMOTION_CACHE_FOLDER, "blobs", "abc"))
    write_file(os.path.join(cache, "models--someone--other-app", "blobs", "abc"))
    # Stopped half-way: deletable, and can be downloaded again.
    row = storage.get_emotion_row()
    assert row.status == storage.NOT_DOWNLOADED and row.can_delete
    write_file(
        os.path.join(
            cache,
            EMOTION_CACHE_FOLDER,
            "snapshots",
            EmotionAnalyzer.EMOTION_MODEL_REVISION,
            "pytorch_model.bin",
        )
    )
    row = storage.get_emotion_row()
    assert row.status == storage.DOWNLOADED and row.can_delete

    storage.delete_paths(row)

    assert os.listdir(cache) == ["models--someone--other-app"]


def test_storage_says_how_much_space_is_free_on_each_disk(tmp_path, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        storage.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(free=50_400_000_000, total=494_000_000_000),
    )

    # Folders that don't exist yet count for the disk they'd be on: here, all the same one.
    disks = storage.get_disks(
        [str(tmp_path / "Panelyze" / "Videos"), *storage.get_model_folders()]
    )

    assert [(free, total) for _, free, total in disks] == [
        (50_400_000_000, 494_000_000_000)
    ]


def test_delete_all_asks_first_and_only_deletes_the_tools_own_folders(make_gui):
    panelyze_folder = storage.get_panelyze_folder(None)
    downloads = os.path.join(panelyze_folder, "Downloads")
    videos = os.path.join(panelyze_folder, "Videos")
    # Something else in the Panelyze folder, which isn't a tool's folder.
    notes = os.path.join(panelyze_folder, "My notes")
    for folder in (downloads, videos, notes):
        write_file(os.path.join(folder, "file"))
    gui, section = open_storage(make_gui)

    click(get_buttons(section, "Delete all saved files")[0])
    dialog = gui.page.dialog
    message = get_shown_text(dialog.content)
    assert "Downloads" in message and "Videos" in message
    assert "My notes" not in message and "can't be undone" in message
    assert os.path.exists(downloads)

    click(get_buttons(dialog, "Delete")[0])

    assert not os.path.exists(downloads) and not os.path.exists(videos)
    assert os.path.exists(notes)
