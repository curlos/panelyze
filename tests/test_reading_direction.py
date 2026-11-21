import pytest

from magi import (
    Magi,
    get_mirrored_boxes,
    get_saved_reading_direction,
    looks_like_four_koma,
    reorder_page_result_four_koma,
    reorder_page_result_left_to_right,
)
from tests.fake_pages import drawn_page
from utils import READING_DIRECTION_FILE_NAME

# A 1000x1000 page with 4 panels in a 2x2 grid.
TOP_LEFT = [0, 0, 490, 490]
TOP_RIGHT = [510, 0, 1000, 490]
BOTTOM_LEFT = [0, 510, 490, 1000]
BOTTOM_RIGHT = [510, 510, 1000, 1000]


def test_mirrored_boxes():
    assert get_mirrored_boxes([[0, 10, 100, 20]], 1000) == [[900, 10, 1000, 20]]


def test_left_to_right_reads_each_row_from_the_left():
    # Magi's own (manga) order: right to left.
    manga_order = {"panels": [TOP_RIGHT, TOP_LEFT, BOTTOM_RIGHT, BOTTOM_LEFT]}

    comic_order = reorder_page_result_left_to_right(manga_order, page_width=1000)

    assert comic_order["panels"] == [TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT]


def test_text_and_what_it_says_stay_together():
    left_bubble = [50, 50, 150, 100]
    right_bubble = [600, 50, 700, 100]
    manga_order = {
        "panels": [TOP_RIGHT, TOP_LEFT],
        "texts": [right_bubble, left_bubble],
        "ocr": ["right says hi", "left says hello"],
        "is_essential_text": [True, False],
    }

    comic_order = reorder_page_result_left_to_right(manga_order, page_width=1000)

    assert comic_order["texts"] == [left_bubble, right_bubble]
    assert comic_order["ocr"] == ["left says hello", "right says hi"]
    assert comic_order["is_essential_text"] == [False, True]


@pytest.mark.parametrize("page_result", [{"panels": []}, {"panels": [], "texts": []}])
def test_pages_without_panels_or_text(page_result):
    assert reorder_page_result_left_to_right(page_result, 1000)["panels"] == []


def get_four_koma_strip(left):
    """
    One 4-koma strip: 4 panels stacked top to bottom, 200 px wide.
    """
    return [[left, top, left + 200, top + 100] for top in (0, 110, 220, 330)]


def test_four_koma_reads_the_right_strip_top_to_bottom_then_the_left_strip():
    right_strip, left_strip = get_four_koma_strip(300), get_four_koma_strip(0)
    # Magi's own order goes row by row: right, left, right, left...
    manga_order = {"panels": [panel for row in zip(right_strip, left_strip) for panel in row]}

    assert reorder_page_result_four_koma(manga_order)["panels"] == right_strip + left_strip


def test_four_koma_text_follows_the_panels_it_is_in():
    right_strip, left_strip = get_four_koma_strip(300), get_four_koma_strip(0)
    in_right_top, in_left_top, in_right_second = [310, 10, 350, 30], [10, 10, 50, 30], [310, 120, 350, 140]
    manga_order = {
        "panels": [right_strip[0], left_strip[0], right_strip[1], left_strip[1]],
        "texts": [in_right_top, in_left_top, in_right_second],
        "ocr": ["right 1", "left 1", "right 2"],
        "is_essential_text": [True, True, True],
    }

    four_koma_order = reorder_page_result_four_koma(manga_order)

    assert four_koma_order["ocr"] == ["right 1", "right 2", "left 1"]
    assert four_koma_order["texts"] == [in_right_top, in_right_second, in_left_top]


def test_four_koma_page_without_panels():
    assert reorder_page_result_four_koma({"panels": []})["panels"] == []


def test_two_strips_of_four_panels_look_like_four_koma():
    four_koma_page = get_four_koma_strip(300) + get_four_koma_strip(0)

    assert looks_like_four_koma([four_koma_page, four_koma_page])


def test_a_normal_manga_page_does_not_look_like_four_koma():
    manga_page = [TOP_RIGHT, TOP_LEFT, BOTTOM_RIGHT, BOTTOM_LEFT]

    assert not looks_like_four_koma([manga_page, manga_page])


def test_strips_of_very_different_widths_do_not_look_like_four_koma():
    uneven_strip = [[0, 0, 200, 100], [0, 110, 120, 210], [0, 220, 200, 320]]

    assert not looks_like_four_koma([uneven_strip])


def test_only_most_pages_have_to_look_like_four_koma():
    four_koma_page = get_four_koma_strip(300) + get_four_koma_strip(0)
    manga_page = [TOP_RIGHT, TOP_LEFT, BOTTOM_RIGHT, BOTTOM_LEFT]

    assert looks_like_four_koma([manga_page, four_koma_page, four_koma_page, []])
    assert not looks_like_four_koma([manga_page, manga_page, four_koma_page])


def test_a_manga_grid_of_two_columns_of_three_does_not_look_like_four_koma():
    grid = [[left, top, left + 400, top + 250] for top in (0, 300, 600) for left in (500, 0)]

    assert not looks_like_four_koma([grid, grid])


def test_pages_of_one_strip_do_not_count_either_way():
    stacked = [[0, top, 1000, top + 300] for top in (0, 330, 660)]
    cover = [[0, 0, 1000, 1000]]
    four_koma_page = get_four_koma_strip(300) + get_four_koma_strip(0)

    assert not looks_like_four_koma([stacked, stacked, cover])
    assert looks_like_four_koma([stacked, stacked, cover, four_koma_page])


def test_a_picked_direction_wins_over_the_saved_one(tmp_path):
    (tmp_path / READING_DIRECTION_FILE_NAME).write_text("ltr")

    assert get_saved_reading_direction("rtl", str(tmp_path)) == "rtl"


@pytest.mark.parametrize("picked", ["auto", None, ""])
def test_automatic_uses_the_direction_saved_by_the_download(tmp_path, picked):
    (tmp_path / READING_DIRECTION_FILE_NAME).write_text("ltr\n")

    assert get_saved_reading_direction(picked, str(tmp_path)) == "ltr"


@pytest.mark.parametrize("saved", [None, "sideways"])
def test_automatic_without_a_good_saved_direction_stays_automatic(tmp_path, saved):
    if saved:
        (tmp_path / READING_DIRECTION_FILE_NAME).write_text(saved)

    assert get_saved_reading_direction("auto", str(tmp_path)) == "auto"


def find_panels_automatically(tmp_path, monkeypatch, page_panels, capsys, saved=None, picked="auto"):
    """
    Run Panel-By-Panel on "picked" with "saved" saved by the download (or nothing), with Magi finding "page_panels" on 2 pages. Returns the directions Magi was asked to find the panels with, the reading order of page 1, and what was printed.
    """
    chapter = tmp_path / "chapter"
    chapter.mkdir()
    if saved:
        (chapter / READING_DIRECTION_FILE_NAME).write_text(saved)
    magi = Magi()
    asked_directions = []

    def predict_panels(chapter_pages, reading_direction):
        asked_directions.append(reading_direction)
        return [{"panels": list(page_panels)} for _ in chapter_pages]

    monkeypatch.setattr(magi, "predict_panels", predict_panels)
    results = magi.get_panels_using_local_cpu(
        [drawn_page(1000, 1000), drawn_page(1000, 1000)],
        "Series/Ch 1",
        str(tmp_path / "out"),
        chapter_input_directory=str(chapter),
        reading_direction=picked,
    )
    return asked_directions, results[0]["panels"], capsys.readouterr().out


def get_saved_panels_direction(tmp_path):
    """
    The direction saved next to the panels by "find_panels_automatically", or None.
    """
    saved = tmp_path / "out" / "panel-by-panel" / "not-grouped-by-page" / "Series" / "Ch 1" / READING_DIRECTION_FILE_NAME
    return saved.read_text() if saved.exists() else None


def test_automatic_reads_four_koma_pages_as_four_koma(tmp_path, monkeypatch, capsys):
    right_strip, left_strip = get_four_koma_strip(300), get_four_koma_strip(0)
    manga_order = [panel for row in zip(right_strip, left_strip) for panel in row]

    asked, order, printed = find_panels_automatically(tmp_path, monkeypatch, manga_order, capsys)

    assert asked == ["rtl"]
    assert order == right_strip + left_strip
    assert "4-koma" in printed


def test_automatic_with_nothing_found_uses_manga_order_and_says_so(tmp_path, monkeypatch, capsys):
    manga_order = [TOP_RIGHT, TOP_LEFT, BOTTOM_RIGHT, BOTTOM_LEFT]

    asked, order, printed = find_panels_automatically(tmp_path, monkeypatch, manga_order, capsys)

    assert asked == ["rtl"]
    assert order == manga_order
    assert "No reading direction found" in printed


def get_four_koma_page_in_manga_order():
    right_strip, left_strip = get_four_koma_strip(300), get_four_koma_strip(0)
    return [panel for row in zip(right_strip, left_strip) for panel in row], right_strip + left_strip


def test_untagged_four_koma_saved_as_manga_order_is_still_read_as_four_koma(tmp_path, monkeypatch, capsys):
    # Like "Bocchi the Rock!": Japanese, but not tagged 4-Koma on MangaDex.
    manga_order, four_koma_order = get_four_koma_page_in_manga_order()

    asked, order, printed = find_panels_automatically(tmp_path, monkeypatch, manga_order, capsys, saved="rtl")

    assert order == four_koma_order
    assert "No reading direction found" not in printed


def test_a_saved_left_to_right_is_used_as_is(tmp_path, monkeypatch, capsys):
    asked, order, printed = find_panels_automatically(
        tmp_path, monkeypatch, [TOP_RIGHT, TOP_LEFT, BOTTOM_RIGHT, BOTTOM_LEFT], capsys, saved="ltr"
    )

    assert asked == ["ltr"]
    assert order == [TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT]


def test_a_picked_manga_order_is_never_changed_to_four_koma(tmp_path, monkeypatch, capsys):
    manga_order, _ = get_four_koma_page_in_manga_order()

    asked, order, printed = find_panels_automatically(tmp_path, monkeypatch, manga_order, capsys, saved="4koma", picked="rtl")

    assert order == manga_order


def test_images_to_video_uses_the_saved_direction_too(tmp_path, monkeypatch):
    (tmp_path / READING_DIRECTION_FILE_NAME).write_text("ltr")
    magi = Magi()
    monkeypatch.setattr(magi, "get_chapter_pages_image_numpy_array", lambda input_directory: [drawn_page(1000, 1000)])
    monkeypatch.setattr(
        magi, "get_per_page_results", lambda pages: [{"panels": [TOP_RIGHT, TOP_LEFT, BOTTOM_RIGHT, BOTTOM_LEFT]}]
    )

    results = magi.get_data_from_images(str(tmp_path), "auto")

    assert results[0]["panels"] == [TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT]


def test_a_direction_saved_by_the_download_goes_along_with_the_panels(tmp_path, monkeypatch, capsys):
    find_panels_automatically(tmp_path, monkeypatch, [TOP_RIGHT, TOP_LEFT], capsys, saved="ltr")

    assert get_saved_panels_direction(tmp_path) == "ltr"


def test_nothing_is_saved_with_the_panels_when_the_download_saved_nothing(tmp_path, monkeypatch, capsys):
    find_panels_automatically(tmp_path, monkeypatch, [TOP_RIGHT, TOP_LEFT], capsys)

    assert get_saved_panels_direction(tmp_path) is None
