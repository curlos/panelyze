import pytest

from magi import get_mirrored_boxes, reorder_page_result_four_koma, reorder_page_result_left_to_right

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
