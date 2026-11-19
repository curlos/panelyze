import pytest

from magi import get_mirrored_boxes, reorder_page_result_left_to_right

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
