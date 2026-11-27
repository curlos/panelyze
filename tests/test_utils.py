import pytest
from types import SimpleNamespace
import os
import shutil
import sys
from typing import Any, cast

import utils
from utils import (
    ProcessManager,
    construct_directory_structure,
    get_relative_output_path,
    is_image_file,
    is_valid_number,
    output_dir_would_overwrite_input,
)


def test_is_image_file_skips_hidden_files_and_accepts_webp():
    assert is_image_file("page_1.webp")
    assert is_image_file("PAGE_1.JPG")
    assert not is_image_file("._page_1.jpg")
    assert not is_image_file("notes.txt")


def test_construct_directory_structure_skips_hidden_entries(tmp_path):
    chapter = tmp_path / "One Piece" / "Ch 1"
    chapter.mkdir(parents=True)
    (chapter / "page_1.png").write_bytes(b"x")
    (chapter / "._page_1.png").write_bytes(b"x")
    (tmp_path / "One Piece" / ".hidden").mkdir()

    structure = construct_directory_structure(str(tmp_path / "One Piece"))

    assert list(structure["One Piece"].keys()) == ["Ch 1"]
    image_names = [img["name"] for img in structure["One Piece"]["Ch 1"]["__images__"]]
    assert image_names == ["page_1.png"]


def test_is_valid_number_rejects_nan_inf_and_none():
    assert is_valid_number("720")
    assert is_valid_number("720.5")
    assert not is_valid_number("nan")
    assert not is_valid_number("inf")
    assert not is_valid_number("")
    assert not is_valid_number(None)


def test_output_dir_would_overwrite_input(tmp_path):
    manga = tmp_path / "Manga"
    series = manga / "One Piece"
    series.mkdir(parents=True)
    output = tmp_path / "Output"
    output.mkdir()

    # Parent of the input -> outputs would land on top of the original images.
    assert output_dir_would_overwrite_input(str(series), str(manga))
    # Same directory or inside the input.
    assert output_dir_would_overwrite_input(str(series), str(series))
    assert output_dir_would_overwrite_input(str(series), str(series / "out"))
    # A higher-up ancestor is fine: outputs go to "tmp/One Piece/...", not on top of "tmp/Manga/One Piece/...".
    assert not output_dir_would_overwrite_input(str(series), str(tmp_path))
    # A separate directory is fine, even one whose name starts the same.
    assert not output_dir_would_overwrite_input(str(series), str(output))
    assert not output_dir_would_overwrite_input(str(series), str(manga / "One Piece 2"))


def test_the_panels_folder_is_like_every_other_tab_s_and_grouped_panels_get_a_series_folder_of_their_own():
    from utils import get_panels_folder

    assert get_panels_folder("/out", os.path.join("One Piece", "Ch 1")) == os.path.join(
        "/out", "One Piece", "Ch 1"
    )
    assert get_panels_folder(
        "/out", "One Piece/Ch 1", group_by_page=True
    ) == os.path.join("/out", "One Piece (grouped by page)", "Ch 1")
    assert get_panels_folder("/out", "Ch 1/", group_by_page=True) == os.path.join(
        "/out", "Ch 1 (grouped by page)"
    )


def test_paths_overlap(tmp_path):
    out = tmp_path / "out"
    chapter = out / "Series" / "Ch 1"
    chapter.mkdir(parents=True)

    # Re-running Magi on its own output: the folder it would clear IS the input chapter.
    assert utils.paths_overlap(str(chapter), str(chapter))
    assert utils.paths_overlap(str(out), str(chapter))
    assert not utils.paths_overlap(str(tmp_path / "other"), str(chapter))


def test_get_relative_output_path_keeps_series_apart():
    a = get_relative_output_path("/root/Series A/Vol 1/Ch 1", "/root/Series A")
    b = get_relative_output_path("/root/Series B/Vol 1/Ch 1", "/root/Series B/")

    assert a == os.path.join("Series A", "Vol 1", "Ch 1")
    assert b == os.path.join("Series B", "Vol 1", "Ch 1")
    # Images directly inside the picked directory.
    assert get_relative_output_path("/root/Ch 1", "/root/Ch 1") == "Ch 1"


def test_process_manager_reads_every_line_including_stderr():
    child_code = (
        "import sys\n"
        "for i in range(500): print(f'line {i}')\n"
        "print('the error line', file=sys.stderr)\n"
    )

    lines = ProcessManager().monitor_terminal_output([sys.executable, "-c", child_code])

    assert len(lines) == 501
    assert lines[0].strip() == "line 0"
    # Lines end with "\r\n" on Windows.
    assert "the error line" in [line.rstrip("\r\n") for line in lines]


def test_get_all_mangadex_languages_needs_no_process_or_internet(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Should not start a separate process")

    monkeypatch.setattr(ProcessManager, "monitor_terminal_output", fail)

    result = utils.get_all_mangadex_languages()

    assert {"name": "English", "code": "en"} in result["mangadex_languages"]
    assert result["mangadex_languages_by_name"]["Japanese"]["code"] == "ja"
    assert all(language["code"] for language in result["mangadex_languages"])


def test_list_images_is_in_natural_order_and_skips_other_files(tmp_path):
    for name in [
        "page_10.png",
        "page_2.jpg",
        "page_1.webp",
        "notes.txt",
        "._page_3.png",
    ]:
        (tmp_path / name).write_bytes(b"")

    file_names = [os.path.basename(path) for path in utils.list_images(str(tmp_path))]

    assert file_names == ["page_1.webp", "page_2.jpg", "page_10.png"]


def test_folder_scan_sorts_images_naturally(tmp_path):
    # Digits-only sorting used to put "ch2_page1" (21) after "ch1_page10" (110) the wrong way around.
    for name in ["ch1_page10.png", "ch1_page9.png", "ch2_page1.png"]:
        (tmp_path / name).write_bytes(b"")

    images = utils.construct_directory_structure(str(tmp_path))[tmp_path.name][
        "__images__"
    ]

    assert [image["name"] for image in images] == [
        "ch1_page9.png",
        "ch1_page10.png",
        "ch2_page1.png",
    ]


@pytest.mark.parametrize(
    "width, height, upscale_ratio, expected_ratio",
    [
        (1000, 800, 16, 4),  # 4000px, shrunk to 3840px afterwards
        (8000, 6000, 16, 1),  # already bigger than 4K: not upscaled
        (3840, 2000, 2, 1),  # exactly 4K: not upscaled
        (500, 700, 2, 2),  # the chosen ratio is the limit: 1400px
        (300, 200, 32, 16),  # 300 * 16 = 4800px is the first to reach 4K
        (1920, 1080, 4, 2),  # 3840px exactly
    ],
)
def test_capped_upscale_ratio(width, height, upscale_ratio, expected_ratio):
    assert (
        utils.get_capped_upscale_ratio(width, height, upscale_ratio) == expected_ratio
    )


@pytest.mark.parametrize(
    "width, height, upscale_ratio, expected_ratio",
    [
        (350, 429, 32, 8),  # 16x would be 6864px; 8x is 3432px, 1.12x short of 4K
        (
            500,
            1000,
            32,
            4,
        ),  # 4x is 4000px, only a bit past 4K; 2x (2000px) would be 1.9x short of 4K, too much
        (1325, 2035, 32, 2),  # "Best" always does at least one pass
        (600, 700, 2, 2),  # the chosen ratio is the limit, as before
        (320, 160, 32, 8),  # 8x is 2560px, exactly 1.5x short of 4K: still allowed
        (
            300,
            200,
            32,
            16,
        ),  # 16x is 4800px; 8x (2400px) would be 1.6x short of 4K, too much
    ],
)
def test_best_upscale_ratio_stops_short_of_4k_when_the_last_pass_would_go_far_past_it(
    width, height, upscale_ratio, expected_ratio
):
    assert utils.get_best_upscale_ratio(width, height, upscale_ratio) == expected_ratio


def test_picked_images_are_copied_into_a_folder_named_after_them(tmp_path):
    chapter = tmp_path / "Ch 1"
    chapter.mkdir()
    for name in ["page_5.png", "page_6.png", "page_7.png"]:
        (chapter / name).write_bytes(b"image")

    one_image_folder = utils.copy_picked_images_to_folder([str(chapter / "page_5.png")])
    three_images_folder = utils.copy_picked_images_to_folder(
        [str(chapter / name) for name in ["page_5.png", "page_6.png", "page_7.png"]]
    )

    assert os.path.basename(one_image_folder) == "Ch 1 - page_5"
    assert os.listdir(one_image_folder) == ["page_5.png"]
    assert os.path.basename(three_images_folder) == "Ch 1 - 3 images"
    assert sorted(os.listdir(three_images_folder)) == [
        "page_5.png",
        "page_6.png",
        "page_7.png",
    ]


def test_a_picked_image_whose_name_ends_in_a_space_still_gets_a_working_folder(
    tmp_path,
):
    # Windows drops a space at the end of a folder name, and then can't find the files inside it.
    chapter = tmp_path / "Ch 1"
    chapter.mkdir()
    (chapter / "page .png").write_bytes(b"image")

    folder = utils.copy_picked_images_to_folder([str(chapter / "page .png")])

    assert os.path.basename(folder) == "Ch 1 - page"
    assert os.listdir(folder) == ["page .png"]


def test_process_manager_reads_japanese_output(monkeypatch):
    # On Windows, a child Python writes in an older encoding unless it's told to use UTF-8. Some terminals already tell it, which would hide the bug.
    monkeypatch.delenv("PYTHONIOENCODING", raising=False)
    lines = ProcessManager().monitor_terminal_output(
        [sys.executable, "-c", "print('呪術廻戦 ♥')"]
    )

    assert [line.rstrip("\r\n") for line in lines] == ["呪術廻戦 ♥"]


def test_waifu2x_path_uses_the_bundled_copy_in_the_packaged_app(tmp_path, monkeypatch):
    bundled = tmp_path / "waifu2x" / "waifu2x-ncnn-vulkan"
    bundled.parent.mkdir()
    bundled.write_text("")
    # One installed on the computer is never used: only the app's own copies.
    monkeypatch.setattr(
        utils.shutil, "which", lambda name: "/usr/local/bin/waifu2x-ncnn-vulkan"
    )
    monkeypatch.setattr(
        utils, "DOWNLOADED_WAIFU2X_FOLDER", str(tmp_path / "not-downloaded")
    )

    assert utils.get_waifu2x_path() is None

    monkeypatch.setattr(utils.sys, "frozen", True, raising=False)
    monkeypatch.setattr(utils.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert utils.get_waifu2x_path() == str(bundled)


def fake_waifu2x_download(tmp_path, monkeypatch, fail=False, extra_files=None):
    """
    waifu2x isn't installed, and its "download" is a zip made here, laid out like the real one. Returns the list of downloaded links.
    """
    import waifu2x

    program_name = (
        "waifu2x-ncnn-vulkan.exe" if sys.platform == "win32" else "waifu2x-ncnn-vulkan"
    )
    zip_path = make_comic_file(
        tmp_path / "release.zip",
        {
            f"waifu2x-ncnn-vulkan-20250915/{program_name}": b"program",
            "waifu2x-ncnn-vulkan-20250915/models-cunet/a.bin": b"model",
            **(extra_files or {}),
        },
    )
    downloaded = []

    def fake_download_file(url, path, name=None):
        downloaded.append(url)
        if fail:
            raise OSError("No internet")
        shutil.copyfile(zip_path, path)

    folder = str(tmp_path / "Application Support" / "Panelyze" / "waifu2x")
    monkeypatch.setattr(utils, "DOWNLOADED_WAIFU2X_FOLDER", folder)
    monkeypatch.setattr(waifu2x, "DOWNLOADED_WAIFU2X_FOLDER", folder)
    monkeypatch.setattr(waifu2x, "download_file", fake_download_file)
    return downloaded


def test_waifu2x_photo_model_is_not_kept(tmp_path, monkeypatch):
    import waifu2x

    fake_waifu2x_download(
        tmp_path,
        monkeypatch,
        extra_files={"waifu2x-ncnn-vulkan-20250915/models-upconv_7_photo/b.bin": b"b"},
    )

    path = waifu2x.download_waifu2x(report=lambda message: None)

    # Panelyze only uses the models for drawings, so the size before downloading is the size after.
    assert not os.path.exists(
        os.path.join(os.path.dirname(path), "models-upconv_7_photo")
    )


def test_waifu2x_is_downloaded_the_first_time_it_is_needed(tmp_path, monkeypatch):
    import waifu2x

    downloaded = fake_waifu2x_download(tmp_path, monkeypatch)
    assert utils.get_waifu2x_path() is None

    path = waifu2x.download_waifu2x(report=lambda message: None)

    assert path == utils.get_waifu2x_path()
    # Its models are next to it, where "upscale_with_waifu2x" looks for them.
    assert os.path.exists(os.path.join(os.path.dirname(path), "models-cunet", "a.bin"))
    if sys.platform != "win32":
        assert os.access(path, os.X_OK)
    # The second time, it's already there.
    waifu2x.download_waifu2x(report=lambda message: None)
    assert len(downloaded) == 1


def test_a_waifu2x_zip_made_on_a_mac_with_extra_entries_still_works(
    tmp_path, monkeypatch
):
    import waifu2x

    # A zip made on a Mac can have a "__MACOSX" folder, and a stray file next to the program's folder.
    fake_waifu2x_download(
        tmp_path,
        monkeypatch,
        extra_files={
            "__MACOSX/waifu2x-ncnn-vulkan-20250915/._a.bin": b"mac",
            "README.txt": b"read me",
        },
    )

    path = waifu2x.download_waifu2x(report=lambda message: None)

    assert path == utils.get_waifu2x_path()


def test_a_half_finished_waifu2x_folder_is_downloaded_again(tmp_path, monkeypatch):
    import waifu2x

    downloaded = fake_waifu2x_download(tmp_path, monkeypatch)
    # Only the models made it, not the program.
    os.makedirs(os.path.join(utils.DOWNLOADED_WAIFU2X_FOLDER, "models-cunet"))

    path = waifu2x.download_waifu2x(report=lambda message: None)

    assert os.path.exists(path)
    assert len(downloaded) == 1


def test_the_upscale_tab_downloads_waifu2x_and_then_upscales(
    make_gui, tmp_path, monkeypatch
):
    from gui_classes import UpscaleImagesView

    import waifu2x

    fake_waifu2x_download(tmp_path, monkeypatch)
    # The real download (with the fake internet above), not the stand-in every other test uses.
    monkeypatch.setattr(UpscaleImagesView, "download_waifu2x", waifu2x.download_waifu2x)
    gui = make_gui()

    gui.UpscaleImagesView.before_job()

    assert utils.get_waifu2x_path()


def test_download_file_saves_what_it_downloads(tmp_path):
    (tmp_path / "source.zip").write_bytes(b"zip")

    utils.download_file((tmp_path / "source.zip").as_uri(), str(tmp_path / "saved.zip"))

    assert (tmp_path / "saved.zip").read_bytes() == b"zip"


def test_the_waifu2x_download_is_the_one_for_this_computer(monkeypatch):
    import waifu2x

    for platform, system in (
        ("win32", "windows"),
        ("darwin", "macos"),
        ("linux", "linux"),
    ):
        monkeypatch.setattr(waifu2x.sys, "platform", platform)
        assert waifu2x.get_waifu2x_zip_url().endswith(
            f"/20250915/waifu2x-ncnn-vulkan-20250915-{system}.zip"
        )


def test_a_failed_waifu2x_download_leaves_nothing_behind(tmp_path, monkeypatch):
    import waifu2x

    fake_waifu2x_download(tmp_path, monkeypatch, fail=True)

    with pytest.raises(OSError, match="No internet"):
        waifu2x.download_waifu2x(report=lambda message: None)

    assert os.listdir(tmp_path / "Application Support" / "Panelyze") == []
    assert utils.get_waifu2x_path() is None


def test_mangadex_downloader_command_in_the_packaged_app(monkeypatch):
    from download_from_mangadex import get_mangadex_downloader_command

    assert get_mangadex_downloader_command()[1:] == ["-m", "mangadex_downloader"]

    monkeypatch.setattr(utils.sys, "frozen", True, raising=False)

    assert get_mangadex_downloader_command()[1:] == ["--run-mangadex"]


def test_a_finished_command_does_not_open_a_finder_window_in_tests(
    tmp_path, monkeypatch
):
    import subprocess
    import sys

    launched = []
    monkeypatch.setattr(
        subprocess, "run", lambda command, *args, **kwargs: launched.append(command)
    )

    utils.ProcessManager().monitor_terminal_output(
        [sys.executable, "-c", "pass"], None, str(tmp_path)
    )

    # "open" is the command that shows a folder in Finder.
    assert not any(command and command[0] == "open" for command in launched)


def test_a_folder_is_saved_as_a_comic_file_in_reading_order(tmp_path):
    import zipfile

    from utils import save_folder_as_cbz

    chapter = tmp_path / "Ch 1"
    for page, panel in [
        ("page_2", "panel_1.png"),
        ("page_10", "panel_1.png"),
        ("page_2", "panel_10.png"),
        ("page_2", "panel_2.png"),
    ]:
        (chapter / page).mkdir(parents=True, exist_ok=True)
        (chapter / page / panel).write_bytes(f"{page}/{panel}".encode())
    (chapter / "panel-text.json").write_text("[]")

    cbz_path = save_folder_as_cbz(str(chapter))

    assert cbz_path is not None and cbz_path == str(tmp_path / "Ch 1.cbz")
    with zipfile.ZipFile(cbz_path) as cbz:
        assert cbz.namelist() == ["0001.png", "0002.png", "0003.png", "0004.png"]
        # Pages in order (2 before 10), then panels in order inside each page. Only images.
        assert [cbz.read(name).decode() for name in cbz.namelist()] == [
            "page_2/panel_1.png",
            "page_2/panel_2.png",
            "page_2/panel_10.png",
            "page_10/panel_1.png",
        ]


def test_a_panel_comic_file_shows_one_panel_at_a_time_and_reads_right_to_left(tmp_path):
    import zipfile

    from utils import save_folder_as_cbz

    chapter = tmp_path / "Ch 1"
    chapter.mkdir()
    for name in ["panel_1.png", "panel_2.png"]:
        (chapter / name).write_bytes(b"x")

    cbz_path = save_folder_as_cbz(
        str(chapter), reading_direction="rtl", one_image_at_a_time=True
    )
    assert cbz_path is not None
    with zipfile.ZipFile(cbz_path) as cbz:
        assert cbz.namelist() == ["0001.png", "0002.png", "ComicInfo.xml"]
        comic_info = cbz.read("ComicInfo.xml").decode()

    # Every panel is marked as a two-page spread, so apps in two-page view never put two side by side.
    assert (
        '<Page Image="0" DoublePage="true"/><Page Image="1" DoublePage="true"/>'
        in comic_info
    )
    assert "<Manga>YesAndRightToLeft</Manga>" in comic_info


def test_a_comic_file_reads_right_to_left_from_the_saved_reading_direction(tmp_path):
    import zipfile

    from utils import READING_DIRECTION_FILE_NAME, get_comic_info, save_folder_as_cbz

    manga, comic = tmp_path / "Manga", tmp_path / "Comic"
    for chapter, direction in [(manga, "rtl"), (comic, "ltr")]:
        chapter.mkdir()
        (chapter / "001.jpg").write_bytes(b"x")
        (chapter / READING_DIRECTION_FILE_NAME).write_text(direction)

    cbz_path = save_folder_as_cbz(str(manga), reading_direction="auto")
    assert cbz_path is not None
    with zipfile.ZipFile(cbz_path) as cbz:
        comic_info = cbz.read("ComicInfo.xml").decode()
    assert "<Manga>YesAndRightToLeft</Manga>" in comic_info
    assert "DoublePage" not in comic_info
    # 4-koma pages turn right to left too.
    assert "<Manga>YesAndRightToLeft</Manga>" in str(get_comic_info(1, "4koma", False))
    # Left to right is what apps do anyway, so there's nothing to tell them.
    cbz_path = save_folder_as_cbz(str(comic))
    assert cbz_path is not None
    with zipfile.ZipFile(cbz_path) as cbz:
        assert cbz.namelist() == ["0001.jpg"]


def test_a_folder_without_images_makes_no_comic_file(tmp_path):
    from utils import save_folder_as_cbz

    assert save_folder_as_cbz(str(tmp_path)) is None
    assert not (tmp_path.parent / f"{tmp_path.name}.cbz").exists()


def test_a_small_comic_file_has_webp_images_sized_for_tablets_and_grayscale_for_black_and_white(
    tmp_path,
):
    import io
    import zipfile

    from PIL import Image

    from utils import save_folder_as_cbz

    chapter = tmp_path / "Ch 1"
    chapter.mkdir()
    Image.new("RGB", (3000, 1000), (128, 128, 130)).save(chapter / "panel_1.png")
    Image.new("RGB", (500, 400), (40, 140, 230)).save(chapter / "panel_2.png")

    cbz_path = save_folder_as_cbz(str(chapter), size="small")
    assert cbz_path is not None
    with zipfile.ZipFile(cbz_path) as cbz:
        assert cbz.namelist() == ["0001.webp", "0002.webp"]
        black_and_white = Image.open(io.BytesIO(cbz.read("0001.webp")))
        color = Image.open(io.BytesIO(cbz.read("0002.webp")))

    assert black_and_white.size == (2048, 683)
    # WebP has no grayscale mode, but the slight tint is gone: every pixel is pure gray.
    red, green, blue = black_and_white.convert("RGB").split()
    assert red.tobytes() == green.tobytes() == blue.tobytes()
    # Small images aren't made bigger, and color stays color.
    assert color.size == (500, 400) and color.mode == "RGB"


def make_comic_file(path, entries):
    """
    A comic file (a zip) with "entries" as {path inside the file: content}.
    """
    import zipfile

    with zipfile.ZipFile(path, "w") as comic_file:
        for entry_name, content in entries.items():
            comic_file.writestr(entry_name, content)
    return str(path)


def read_pages(folder):
    return [
        (file_name, open(os.path.join(folder, file_name), "rb").read())
        for file_name in sorted(os.listdir(folder))
    ]


def delete_temporary_folder(folder):
    import shutil

    shutil.rmtree(os.path.dirname(folder))


def test_a_cbz_becomes_one_chapter_folder_in_page_order(tmp_path):
    cbz_path = make_comic_file(
        tmp_path / "Invincible 001.cbz", {"2.png": b"2", "10.png": b"10", "1.png": b"1"}
    )

    folder = utils.extract_comic_files_to_folder([cbz_path])

    assert os.path.basename(folder) == "Invincible 001"
    assert read_pages(folder) == [
        ("001.png", b"1"),
        ("002.png", b"2"),
        ("003.png", b"10"),
    ]
    delete_temporary_folder(folder)


def test_two_comic_files_make_two_chapter_folders(tmp_path):
    comics = tmp_path / "Comics"
    comics.mkdir()
    first = make_comic_file(comics / "Issue 1.cbz", {"a.jpg": b"a"})
    second = make_comic_file(comics / "Issue 2.zip", {"b.jpg": b"b"})

    folder = utils.extract_comic_files_to_folder([first, second])

    assert os.path.basename(folder) == "Comics - 2 comic files"
    assert sorted(os.listdir(folder)) == ["Issue 1", "Issue 2"]
    assert read_pages(os.path.join(folder, "Issue 2")) == [("001.jpg", b"b")]
    delete_temporary_folder(folder)


def test_a_comic_file_can_not_write_outside_its_folder(tmp_path):
    cbz_path = make_comic_file(tmp_path / "Evil.cbz", {"../../evil.png": b"evil"})

    folder = utils.extract_comic_files_to_folder([cbz_path])

    assert read_pages(folder) == [("001.png", b"evil")]
    assert not (tmp_path / "evil.png").exists()
    assert not os.path.exists(
        os.path.join(os.path.dirname(os.path.dirname(folder)), "evil.png")
    )
    delete_temporary_folder(folder)


def test_a_comic_file_keeps_only_its_images(tmp_path):
    cbz_path = make_comic_file(
        tmp_path / "Ch 1.cbz",
        {
            "ComicInfo.xml": b"<xml/>",
            "__MACOSX/._1.png": b"metadata",
            ".DS_Store": b"finder",
            "pages/1.png": b"1",
        },
    )

    folder = utils.extract_comic_files_to_folder([cbz_path])

    assert read_pages(folder) == [("001.png", b"1")]
    delete_temporary_folder(folder)


def test_an_epub_gives_its_images(tmp_path):
    epub_path = make_comic_file(
        tmp_path / "Book.epub",
        {
            "mimetype": b"application/epub+zip",
            "OEBPS/images/p1.jpg": b"p1",
            "OEBPS/p1.xhtml": b"<html/>",
        },
    )

    folder = utils.extract_comic_files_to_folder([epub_path])

    assert read_pages(folder) == [("001.jpg", b"p1")]
    delete_temporary_folder(folder)


def test_a_pdf_gives_one_image_per_page(tmp_path):
    from PIL import Image

    pdf_path = str(tmp_path / "Pepper&Carrot.pdf")
    pages = [Image.new("RGB", (100, 150), color) for color in ("red", "green", "blue")]
    pages[0].save(pdf_path, save_all=True, append_images=pages[1:])

    folder = utils.extract_comic_files_to_folder([pdf_path])

    assert sorted(os.listdir(folder)) == ["001.png", "002.png", "003.png"]
    with Image.open(os.path.join(folder, "002.png")) as page:
        assert (
            cast(
                tuple[int, int, int],
                page.convert("RGB").getpixel((page.width // 2, page.height // 2)),
            )[1]
            > 100
        )
    delete_temporary_folder(folder)


def test_only_comic_files_can_be_extracted(tmp_path):
    with pytest.raises(ValueError, match="Not a comic file"):
        utils.extract_comic_files_to_folder([str(tmp_path / "page.png")])


def test_a_cbr_gives_its_pages_in_order(tmp_path):
    # Many .cbr files are really zip files, which bsdtar opens too (real RAR files can't be made in a test).
    cbr_path = make_comic_file(
        tmp_path / "Pirates.cbr", {"p/10.jpg": b"10", "p/2.jpg": b"2"}
    )

    folder = utils.extract_comic_files_to_folder([cbr_path])

    assert read_pages(folder) == [("001.jpg", b"2"), ("002.jpg", b"10")]
    delete_temporary_folder(folder)


def test_a_cbr_with_a_japanese_name_gives_its_pages(tmp_path):
    # Windows' tar.exe can't read Japanese letters in its arguments.
    (tmp_path / "呪術廻戦").mkdir()
    cbr_path = make_comic_file(
        tmp_path / "呪術廻戦" / "呪術廻戦 01.cbr", {"1.jpg": b"1"}
    )

    folder = utils.extract_comic_files_to_folder([cbr_path])

    assert read_pages(folder) == [("001.jpg", b"1")]
    delete_temporary_folder(folder)


def test_a_comic_file_whose_name_ends_in_a_space_still_gives_its_pages(tmp_path):
    # Windows drops a space at the end of a folder name, and then can't find the pages inside it.
    cbz_path = make_comic_file(tmp_path / "Issue 1 .cbz", {"1.jpg": b"1"})

    folder = utils.extract_comic_files_to_folder([cbz_path])

    assert os.path.basename(folder) == "Issue 1"
    assert read_pages(folder) == [("001.jpg", b"1")]
    delete_temporary_folder(folder)


def test_a_cbr_without_bsdtar_gives_a_clear_error(tmp_path, monkeypatch):
    cbr_path = make_comic_file(tmp_path / "Pirates.cbr", {"1.jpg": b"1"})
    monkeypatch.setattr(utils.shutil, "which", lambda name: None)
    # Only bsdtar (or Windows' tar.exe) is missing; other files and folders are still there.
    real_exists = os.path.exists
    monkeypatch.setattr(
        utils.os.path,
        "exists",
        lambda path: "tar" not in os.path.basename(path) and real_exists(path),
    )

    with pytest.raises(RuntimeError, match="need bsdtar"):
        utils.extract_comic_files_to_folder([cbr_path])


def make_chapter_folder(folder, page_count):
    folder.mkdir(parents=True)
    for number in range(1, page_count + 1):
        (folder / f"{number}.png").write_bytes(b"image")


def test_a_picked_series_folder_says_how_many_chapters_and_pages_it_has(tmp_path):
    series = tmp_path / "One Piece"
    make_chapter_folder(series / "Ch 1", 20)
    make_chapter_folder(series / "Ch 2", 22)

    assert utils.get_input_summary(str(series)) == "2 chapters · 42 pages"


def test_a_single_folder_of_images_only_says_how_many_pages(tmp_path):
    chapter = tmp_path / "Ch 1"
    make_chapter_folder(chapter, 1)
    assert utils.get_input_summary(str(chapter)) == "1 page"

    make_chapter_folder(tmp_path / "Ch 2", 22)
    assert utils.get_input_summary(str(tmp_path / "Ch 2")) == "22 pages"


def test_a_folder_without_images_gives_a_warning(tmp_path):
    (tmp_path / "Empty").mkdir()
    (tmp_path / "Empty" / "notes.txt").write_text("hi")

    assert (
        utils.get_input_summary(str(tmp_path / "Empty"))
        == "No images found in this folder"
    )
    assert (
        utils.get_input_summary(str(tmp_path / "Gone"))
        == "No images found in this folder"
    )


def test_picked_images_and_comic_files_are_counted(tmp_path):
    from PIL import Image

    assert utils.get_input_summary(image_paths=["a.png"]) == "1 image"
    assert (
        utils.get_input_summary(image_paths=["a.png", "b.png", "c.png"]) == "3 images"
    )

    cbz = make_comic_file(
        tmp_path / "One.cbz",
        {"1.png": b"1", "2.png": b"2", "ComicInfo.xml": b"x", "__MACOSX/._1.png": b"m"},
    )
    pages = [Image.new("RGB", (50, 50), "red") for _ in range(3)]
    pdf = str(tmp_path / "Two.pdf")
    pages[0].save(pdf, save_all=True, append_images=pages[1:])

    assert utils.get_input_summary(comic_paths=[cbz]) == "1 chapter · 2 pages"
    assert utils.get_input_summary(comic_paths=[cbz, pdf]) == "2 chapters · 5 pages"


def test_a_cbr_is_counted_as_a_chapter_without_its_pages(tmp_path):
    cbr = make_comic_file(tmp_path / "Old.cbr", {"1.jpg": b"1"})
    cbz = make_comic_file(tmp_path / "New.cbz", {"1.png": b"1"})

    # A .cbr's pages can't be counted without opening it, so no total is shown.
    assert utils.get_input_summary(comic_paths=[cbr, cbz]) == "2 chapters"


def test_a_cancel_clicked_before_the_job_set_what_it_stops_stops_it_right_away():
    from types import SimpleNamespace

    # Clicked while it was still starting: the button already says "Cancelling..." and can't be clicked again.
    cancel_button = SimpleNamespace(
        on_click=None, disabled=True, text=utils.CANCELLING_TEXT
    )
    stopped = []

    utils.set_cancel_click(cancel_button, lambda: stopped.append(True))

    assert stopped == [True]


def test_a_program_cancelled_before_it_started_is_stopped_as_soon_as_it_starts():
    import time

    process_manager = ProcessManager()
    process_manager.cancel_process()
    started_at = time.monotonic()

    process_manager.monitor_terminal_output(
        [sys.executable, "-c", "import time; time.sleep(30)"]
    )

    assert (
        process_manager.cancelled
        and process_manager.process is not None
        and process_manager.process.returncode != 0
    )
    assert time.monotonic() - started_at < 10


def test_a_comic_file_that_cannot_be_opened_leaves_nothing_behind(
    tmp_path, monkeypatch
):
    import tempfile
    import zipfile

    broken = tmp_path / "Broken.cbz"
    broken.write_bytes(b"not a zip file")
    made_folders = []
    real_mkdtemp = tempfile.mkdtemp
    monkeypatch.setattr(
        utils.tempfile,
        "mkdtemp",
        lambda *args, **kwargs: (
            made_folders.append(real_mkdtemp(*args, **kwargs)) or made_folders[-1]
        ),
    )

    with pytest.raises(zipfile.BadZipFile):
        utils.extract_comic_files_to_folder([str(broken)])

    assert made_folders and not os.path.exists(made_folders[0])


def test_an_error_while_reading_the_output_stops_the_command():
    def fail(line):
        raise ValueError("can't show this line")

    process_manager = ProcessManager()
    child_code = "import time; print('first line', flush=True); time.sleep(30)"

    process_manager.monitor_terminal_output(
        [sys.executable, "-c", child_code], on_line=fail
    )

    # Not left running in the background (e.g. waifu2x still reading a folder that's being deleted).
    assert (
        process_manager.process is not None
        and process_manager.process.poll() is not None
    )
    assert process_manager.process.returncode != 0


def test_a_comic_file_that_fails_halfway_leaves_nothing_behind(tmp_path):
    from PIL import Image, UnidentifiedImageError
    from utils import save_folder_as_cbz

    chapter = tmp_path / "Ch 1"
    chapter.mkdir()
    Image.new("RGB", (20, 20), "white").save(chapter / "001.png")
    (chapter / "002.png").write_bytes(b"not an image")

    with pytest.raises(UnidentifiedImageError):
        save_folder_as_cbz(str(chapter), size="small")

    assert sorted(os.listdir(tmp_path)) == ["Ch 1"]


def test_a_broken_shortcut_to_an_image_is_skipped(tmp_path):
    from utils import construct_directory_structure

    chapter = tmp_path / "Ch 1"
    chapter.mkdir()
    (chapter / "001.png").write_bytes(b"x")
    # A shortcut (symlink) to an image that was moved or deleted.
    os.symlink(tmp_path / "gone.png", chapter / "002.png")

    assert construct_directory_structure(str(chapter)) == {
        "Ch 1": {"__images__": [{"name": "001.png", "size": 1}]}
    }


def test_the_output_folder_is_the_same_folder_in_another_case(tmp_path):
    from utils import output_dir_would_overwrite_input

    (tmp_path / "Manga" / "One Piece").mkdir(parents=True)

    # Mac disks ignore case: "manga" is the "Manga" folder.
    assert output_dir_would_overwrite_input(
        str(tmp_path / "Manga" / "One Piece"), str(tmp_path / "manga")
    )
    assert output_dir_would_overwrite_input(
        str(tmp_path / "Manga" / "One Piece"),
        str(tmp_path / "manga" / "one piece" / "out"),
    )


def test_comic_file_pages_in_other_image_formats_are_saved_as_png(tmp_path):
    import io
    import shutil
    import zipfile
    from PIL import Image
    from utils import count_comic_file_pages, extract_comic_files_to_folder

    def image_bytes(image_format):
        data = io.BytesIO()
        Image.new("RGB", (8, 8), "white").save(data, image_format)
        return data.getvalue()

    cbz_path = tmp_path / "comic.cbz"
    with zipfile.ZipFile(cbz_path, "w") as cbz:
        cbz.writestr("p1.gif", image_bytes("GIF"))
        cbz.writestr("p2.jpg", image_bytes("JPEG"))
        cbz.writestr("p3.bmp", image_bytes("BMP"))
        cbz.writestr("p10.tiff", image_bytes("TIFF"))

    assert count_comic_file_pages(str(cbz_path)) == 4
    folder = extract_comic_files_to_folder([str(cbz_path)])
    try:
        # One comic file gives a folder named after it with its pages.
        pages_folder = folder
        assert sorted(os.listdir(pages_folder)) == [
            "001.png",
            "002.jpg",
            "003.png",
            "004.png",
        ]
        with Image.open(os.path.join(pages_folder, "001.png")) as page:
            assert page.format == "PNG"
    finally:
        shutil.rmtree(os.path.dirname(folder))


def test_a_16_bit_tiff_page_in_a_comic_file_keeps_its_grays(tmp_path):
    import io
    import shutil
    import zipfile
    import numpy
    from PIL import Image
    from utils import extract_comic_files_to_folder

    # Dark gray, as a 16-bit scan.
    data = io.BytesIO()
    Image.fromarray(numpy.full((8, 8), 16384, dtype=numpy.uint16)).save(data, "TIFF")
    cbz_path = tmp_path / "comic.cbz"
    with zipfile.ZipFile(cbz_path, "w") as cbz:
        cbz.writestr("p1.tif", data.getvalue())

    folder = extract_comic_files_to_folder([str(cbz_path)])
    try:
        with Image.open(os.path.join(folder, "001.png")) as page:
            assert page.convert("L").getpixel((0, 0)) == 64
    finally:
        shutil.rmtree(os.path.dirname(folder))


def test_a_comic_file_that_cant_be_written_says_why(tmp_path):
    from utils import save_folder_as_cbz

    chapter = tmp_path / "Ch 1"
    chapter.mkdir()
    (chapter / "001.png").write_bytes(b"x")
    os.chmod(tmp_path, 0o500)
    try:
        with pytest.raises(PermissionError):
            save_folder_as_cbz(str(chapter))
    finally:
        os.chmod(tmp_path, 0o700)


def test_the_download_tab_folder_in_another_case_is_the_same_folder(tmp_path):
    from utils import get_library_directory

    (tmp_path / "Downloads").mkdir()

    assert (
        get_library_directory(
            str(tmp_path / "downloads"),
            {"output_directory_mangadex": str(tmp_path / "Downloads")},
        )
        is None
    )


def test_a_web_link_in_a_line_can_be_clicked():
    import flet as ft
    from utils import set_text_with_links

    line = ft.Text()
    set_text_with_links(
        line,
        "Couldn't download it. It comes from https://github.com/the-database/MangaJaNai/releases. Try again.",
    )

    assert line.value is None
    spans = line.spans or []
    assert [span.text for span in spans] == [
        "Couldn't download it. It comes from ",
        "https://github.com/the-database/MangaJaNai/releases",
        ". Try again.",
    ]
    assert [bool(span.on_click) for span in spans] == [False, True, False]

    # Clicking it opens it in the browser.
    opened = []
    on_click = spans[1].on_click
    assert on_click is not None
    on_click(cast(Any, SimpleNamespace(page=SimpleNamespace(launch_url=opened.append))))
    assert opened == ["https://github.com/the-database/MangaJaNai/releases"]

    # A line without a link stays plain text.
    set_text_with_links(line, "Upscaling finished!")
    assert line.value == "Upscaling finished!" and not line.spans


def test_the_end_of_a_sentence_is_not_part_of_a_link():
    import flet as ft
    from utils import set_text_with_links

    for text in (
        "(about 2 GB from https://huggingface.co/ragavsachdeva/magiv2).",
        "from https://github.com/the-database/MangaJaNai/releases...",
    ):
        line = ft.Text()
        set_text_with_links(line, text)
        assert [span.text for span in line.spans or [] if span.on_click] == [
            text.split("from ")[1].rstrip(".)")
        ]


def test_quotes_and_brackets_around_a_link_are_not_part_of_it():
    import flet as ft
    from utils import set_text_with_links

    # E.g. an error that shows a list of addresses.
    line = ft.Text()
    set_text_with_links(
        line,
        "Couldn't open ['https://huggingface.co/ragavsachdeva/magiv2'] or \"https://example.com\"",
    )

    assert [span.text for span in line.spans or [] if span.on_click] == [
        "https://huggingface.co/ragavsachdeva/magiv2",
        "https://example.com",
    ]


def test_a_message_about_links_with_no_real_link_stays_plain_text():
    import flet as ft
    from utils import set_text_with_links

    line = ft.Text()
    set_text_with_links(
        line, "Not a web link (it should start with https://): slam dunk"
    )

    assert (
        line.value == "Not a web link (it should start with https://): slam dunk"
        and not line.spans
    )


class FakeResponse:
    def __init__(self, status_code, headers, url, content):
        self.status_code = status_code
        self.headers = headers
        self.url = url
        self.content = content

    def raise_for_status(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeRangeServer:
    """
    Stands in for "requests.Session": sends the parts of "data" asked for, like GitHub does (or the whole file, with "whole_files_only").
    """

    def __init__(self, data, whole_files_only=False):
        self.data = data
        self.whole_files_only = whole_files_only
        self.requests = 0

    def get(self, url, headers, timeout, stream=False):
        self.requests += 1
        start, end = map(int, headers["Range"].removeprefix("bytes=").split("-"))
        if self.whole_files_only:
            return FakeResponse(200, {}, url, self.data)
        return FakeResponse(
            206,
            {"Content-Range": f"bytes {start}-{end}/{len(self.data)}"},
            url,
            self.data[start : end + 1],
        )


def test_a_zip_on_a_server_is_read_without_downloading_all_of_it(tmp_path, monkeypatch):
    import io
    import zipfile

    import requests

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as models_zip:
        models_zip.writestr("2x_small.pth", b"a" * 1000)
        # Random bytes don't compress, so the zip really is big.
        models_zip.writestr("4x_big.pth", os.urandom(5_000_000))
    server = FakeRangeServer(buffer.getvalue())
    monkeypatch.setattr(requests, "Session", lambda: server)

    with utils.open_remote_zip("https://example.com/models.zip") as remote_zip:
        assert remote_zip.read("2x_small.pth") == b"a" * 1000

    # A few small requests (the list of files, then the small one), not the 5 MB one.
    assert server.requests < 10


def test_a_server_that_only_sends_whole_files_is_said_so(monkeypatch):
    import requests

    monkeypatch.setattr(
        requests, "Session", lambda: FakeRangeServer(b"x" * 100, whole_files_only=True)
    )

    with pytest.raises(utils.PartialDownloadNotSupported):
        utils.open_remote_zip("https://example.com/models.zip")


def test_running_out_of_disk_space_gets_a_clear_message(tmp_path, monkeypatch):
    import errno
    from types import SimpleNamespace

    disk_full = OSError(errno.ENOSPC, "No space left on device")
    try:
        try:
            raise disk_full
        except OSError as error:
            # Like a failed download, which says what failed and keeps the cause.
            raise OSError("Couldn't download the model") from error
    except OSError as wrapped:
        assert "ran out of space" in utils.get_error_text(wrapped)
    assert utils.get_error_text(ValueError("Something else")) == "Something else"

    monkeypatch.setattr(
        utils.shutil, "disk_usage", lambda path: SimpleNamespace(free=800_000_000)
    )
    # The folder doesn't have to exist yet (e.g. before the first download).
    with pytest.raises(utils.NotEnoughSpace) as error:
        utils.check_free_space(
            str(tmp_path / "not" / "made" / "yet"), 2_063_693_064, "the Magi model"
        )
    assert utils.get_error_text(error.value).startswith(
        "Not enough space on this computer for the Magi model: it needs 2.06 GB, and 800 MB is free."
    )


def test_a_dropped_connection_is_tried_again(monkeypatch):
    import io
    import zipfile

    import requests

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as models_zip:
        models_zip.writestr("2x_small.pth", b"a" * 1000)
    server = FakeRangeServer(buffer.getvalue())
    real_get = server.get
    failures = []

    def get_with_one_dropped_connection(url, headers, timeout, stream=False):
        # The 2nd request (the first one after checking the server) fails once.
        if server.requests == 1 and not failures:
            failures.append(1)
            server.requests += 1
            raise requests.ConnectionError("Connection reset")
        return real_get(url, headers, timeout, stream)

    server.get = get_with_one_dropped_connection
    monkeypatch.setattr(requests, "Session", lambda: server)
    monkeypatch.setattr(utils.time, "sleep", lambda seconds: None)

    with utils.open_remote_zip("https://example.com/models.zip") as remote_zip:
        assert remote_zip.read("2x_small.pth") == b"a" * 1000
    assert failures == [1]
