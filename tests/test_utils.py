import pytest
import os
import sys

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


def test_paths_overlap(tmp_path):
    out = tmp_path / "out"
    chapter = out / "panel-by-panel" / "not-grouped-by-page" / "Series" / "Ch 1"
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
    assert "the error line\n" in lines


def test_get_all_mangadex_languages_needs_no_process_or_internet(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Should not start a separate process")

    monkeypatch.setattr(ProcessManager, "monitor_terminal_output", fail)

    result = utils.get_all_mangadex_languages()

    assert {"name": "English", "code": "en"} in result["mangadex_languages"]
    assert result["mangadex_languages_by_name"]["Japanese"]["code"] == "ja"
    assert all(language["code"] for language in result["mangadex_languages"])


def test_list_images_is_in_natural_order_and_skips_other_files(tmp_path):
    for name in ["page_10.png", "page_2.jpg", "page_1.webp", "notes.txt", "._page_3.png"]:
        (tmp_path / name).write_bytes(b"")

    file_names = [os.path.basename(path) for path in utils.list_images(str(tmp_path))]

    assert file_names == ["page_1.webp", "page_2.jpg", "page_10.png"]


def test_folder_scan_sorts_images_naturally(tmp_path):
    # Digits-only sorting used to put "ch2_page1" (21) after "ch1_page10" (110) the wrong way around.
    for name in ["ch1_page10.png", "ch1_page9.png", "ch2_page1.png"]:
        (tmp_path / name).write_bytes(b"")

    images = utils.construct_directory_structure(str(tmp_path))[tmp_path.name]["__images__"]

    assert [image["name"] for image in images] == ["ch1_page9.png", "ch1_page10.png", "ch2_page1.png"]


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
    assert utils.get_capped_upscale_ratio(width, height, upscale_ratio) == expected_ratio


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
    assert sorted(os.listdir(three_images_folder)) == ["page_5.png", "page_6.png", "page_7.png"]


def test_waifu2x_path_uses_the_bundled_copy_in_the_packaged_app(tmp_path, monkeypatch):
    bundled = tmp_path / "waifu2x" / "waifu2x-ncnn-vulkan"
    bundled.parent.mkdir()
    bundled.write_text("")
    monkeypatch.setattr(utils.shutil, "which", lambda name: "/usr/local/bin/waifu2x-ncnn-vulkan")

    assert utils.get_waifu2x_path() == "/usr/local/bin/waifu2x-ncnn-vulkan"

    monkeypatch.setattr(utils.sys, "frozen", True, raising=False)
    monkeypatch.setattr(utils.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert utils.get_waifu2x_path() == str(bundled)


def test_mangadex_downloader_command_in_the_packaged_app(monkeypatch):
    from download_from_mangadex import get_mangadex_downloader_command

    assert get_mangadex_downloader_command()[1:] == ["-m", "mangadex_downloader"]

    monkeypatch.setattr(utils.sys, "frozen", True, raising=False)

    assert get_mangadex_downloader_command()[1:] == ["--run-mangadex"]


def test_a_finished_command_does_not_open_a_finder_window_in_tests(tmp_path, monkeypatch):
    import subprocess
    import sys

    launched = []
    monkeypatch.setattr(subprocess, "run", lambda command, *args, **kwargs: launched.append(command))

    utils.ProcessManager().monitor_terminal_output(
        [sys.executable, "-c", "pass"], None, str(tmp_path)
    )

    # "open" is the command that shows a folder in Finder.
    assert not any(command and command[0] == "open" for command in launched)


def test_a_folder_is_saved_as_a_comic_file_in_reading_order(tmp_path):
    import zipfile

    from utils import save_folder_as_cbz

    chapter = tmp_path / "Ch 1"
    for page, panel in [("page_2", "panel_1.png"), ("page_10", "panel_1.png"), ("page_2", "panel_10.png"), ("page_2", "panel_2.png")]:
        (chapter / page).mkdir(parents=True, exist_ok=True)
        (chapter / page / panel).write_bytes(f"{page}/{panel}".encode())
    (chapter / "panel-text.json").write_text("[]")

    cbz_path = save_folder_as_cbz(str(chapter))

    assert cbz_path == str(tmp_path / "Ch 1.cbz")
    with zipfile.ZipFile(cbz_path) as cbz:
        assert cbz.namelist() == ["0001.png", "0002.png", "0003.png", "0004.png"]
        # Pages in order (2 before 10), then panels in order inside each page. Only images.
        assert [cbz.read(name).decode() for name in cbz.namelist()] == [
            "page_2/panel_1.png",
            "page_2/panel_2.png",
            "page_2/panel_10.png",
            "page_10/panel_1.png",
        ]


def test_a_folder_without_images_makes_no_comic_file(tmp_path):
    from utils import save_folder_as_cbz

    assert save_folder_as_cbz(str(tmp_path)) is None
    assert not (tmp_path.parent / f"{tmp_path.name}.cbz").exists()


def test_a_small_comic_file_has_webp_images_sized_for_tablets_and_grayscale_for_black_and_white(tmp_path):
    import io
    import zipfile

    from PIL import Image

    from utils import save_folder_as_cbz

    chapter = tmp_path / "Ch 1"
    chapter.mkdir()
    Image.new("RGB", (3000, 1000), (128, 128, 130)).save(chapter / "panel_1.png")
    Image.new("RGB", (500, 400), (40, 140, 230)).save(chapter / "panel_2.png")

    with zipfile.ZipFile(save_folder_as_cbz(str(chapter), size="small")) as cbz:
        assert cbz.namelist() == ["0001.webp", "0002.webp"]
        black_and_white = Image.open(io.BytesIO(cbz.read("0001.webp")))
        color = Image.open(io.BytesIO(cbz.read("0002.webp")))

    assert black_and_white.size == (2048, 683)
    # WebP has no grayscale mode, but the slight tint is gone: every pixel is pure gray.
    red, green, blue = black_and_white.convert("RGB").split()
    assert red.tobytes() == green.tobytes() == blue.tobytes()
    # Small images aren't made bigger, and color stays color.
    assert color.size == (500, 400) and color.mode == "RGB"
