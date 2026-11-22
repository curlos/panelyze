import os

import numpy
import pytest

from tests.fake_pages import drawn_page
from magi import Magi, get_webtoon_safety_net, join_webtoon_strip, looks_like_webtoon, remove_junk_panels, remove_repeated_webtoon_panels, split_tall_panel


def blank(height, width):
    return numpy.full((height, width, 3), 255, dtype=numpy.uint8)


def test_the_chapter_is_joined_into_one_strip_at_the_most_common_width():
    pages = [blank(300, 100), blank(500, 100), blank(400, 200)]

    strip = join_webtoon_strip(pages)

    # The 200 px wide image is scaled to 100 px wide, so it's 200 px tall.
    assert strip.shape == (1000, 100, 3)


def fake_magi_that_sees(strip, true_panels):
    """
    A Magi whose "find_panels" returns, for each window of the strip, the part of each true panel inside it (in the window's own coordinates), like Magi cutting off panels at the window's edges.
    """
    magi = Magi()

    def find_panels(windows, reading_direction="rtl"):
        results = []
        for window in windows:
            top = (window.ctypes.data - strip.ctypes.data) // strip.strides[0]
            bottom = top + window.shape[0]
            results.append(
                {
                    "panels": [
                        [x0, max(y0, top) - top, x1, min(y1, bottom) - top]
                        for x0, y0, x1, y1 in true_panels
                        if y0 < bottom and y1 > top
                    ]
                }
            )
        return results

    magi.find_panels = find_panels
    return magi


def test_each_panel_is_found_once_from_the_window_that_sees_it_whole():
    # 100 px wide, so the windows are 200 px tall and move down 100 px at a time.
    strip = blank(600, 100)
    true_panels = [[10, 20, 90, 90], [10, 150, 90, 240]]
    for x0, y0, x1, y1 in true_panels:
        strip[y0:y1, x0:x1] = drawn_page(y1 - y0, x1 - x0)

    panels = fake_magi_that_sees(strip, true_panels).find_webtoon_panels(strip)["panels"]

    assert panels == true_panels


def test_a_panel_taller_than_a_window_step_is_joined_back_together():
    strip = blank(600, 100)
    # 290 px tall: every window cuts it off.
    tall_panel = [10, 300, 90, 590]

    panels = fake_magi_that_sees(strip, [tall_panel]).find_webtoon_panels(strip)["panels"]

    assert panels == [tall_panel]


def draw_square(strip, x0, y0, size):
    strip[y0 : y0 + size, x0 : x0 + size] = 0


def test_art_magi_missed_becomes_its_own_panel():
    strip = blank(2000, 400)
    panel = [20, 20, 380, 300]
    # A big square far from the panel: like a soft-edged panel Magi didn't find.
    draw_square(strip, 100, 1000, 250)

    panels = get_webtoon_safety_net(strip, [panel])

    assert panels[0] == panel
    assert len(panels) == 2
    x0, y0, x1, y1 = panels[1]
    # Trimmed to the square plus a small margin, not the strip's whole 400 px width.
    assert x0 < 100 < 350 < x1 and y0 < 1000 < 1250 < y1
    assert x1 - x0 < 320 and y1 - y0 < 320


def test_art_sticking_out_of_a_panel_is_added_to_that_panel():
    strip = blank(2000, 400)
    panel = [20, 20, 380, 300]
    # Like a speech bubble hanging below the panel.
    draw_square(strip, 150, 310, 100)

    panels = get_webtoon_safety_net(strip, [panel])

    assert len(panels) == 1
    assert panels[0][3] > 410


@pytest.mark.parametrize("background", [255, 0])
def test_plain_backgrounds_and_specks_are_not_panels(background):
    # A plain black or white stretch, and a small mark like a watermark.
    strip = numpy.full((2000, 400, 3), background, dtype=numpy.uint8)
    strip[1500:1540, 200:240] = 255 - background

    assert get_webtoon_safety_net(strip, []) == []


def test_panel_by_panel_joins_a_webtoon_chapter_and_leaves_the_text_to_the_video(tmp_path, monkeypatch):
    magi = Magi()
    pages_seen = []

    def predict_panels(chapter_pages, reading_direction):
        pages_seen.extend(page.shape for page in chapter_pages)
        return [{"panels": [[0, 0, 100, 100], [0, 300, 100, 500]]}]

    monkeypatch.setattr(magi, "predict_panels", predict_panels)
    monkeypatch.setattr(magi, "get_per_page_results", lambda chapter_pages: pytest.fail("the text shouldn't be read"))

    magi.get_panels_using_local_cpu(
        [drawn_page(300, 100), drawn_page(300, 100)], "Series/Ch 1", str(tmp_path), reading_direction="webtoon", read_text=True
    )

    assert pages_seen == [(600, 100, 3)]
    chapter = tmp_path / "Series" / "Ch 1"
    assert sorted(os.listdir(chapter)) == ["panel_1.png", "panel_2.png"]


def test_a_small_mark_next_to_a_panel_is_added_to_it():
    strip = blank(2000, 400)
    panel = [20, 20, 300, 300]
    # Like the last letter of a title, just outside the panel Magi found.
    draw_square(strip, 330, 150, 24)

    panels = get_webtoon_safety_net(strip, [panel])

    assert len(panels) == 1
    assert panels[0][2] > 354


def test_a_chapter_of_very_tall_images_looks_like_a_webtoon():
    manga_pages = [blank(1600, 1100) for _ in range(3)]
    webtoon_images = [blank(9000, 700) for _ in range(3)]

    assert not looks_like_webtoon(manga_pages)
    assert looks_like_webtoon(webtoon_images)


def test_a_webtoon_picked_as_manga_is_still_split_as_a_webtoon(tmp_path, monkeypatch):
    magi = Magi()
    directions = []

    def predict_panels(chapter_pages, reading_direction):
        directions.append(reading_direction)
        return [{"panels": [[0, 0, 700, 500]]}]

    monkeypatch.setattr(magi, "predict_panels", predict_panels)

    magi.get_panels_using_local_cpu([blank(9000, 700), blank(9000, 700)], "Series/Ch 1", str(tmp_path), reading_direction="rtl")

    assert directions == ["webtoon"]


# 100 px wide, so a phone screen is 217 px tall and panels over 434 px are split.
def tall_page(height):
    page = blank(height, 100)
    # Art everywhere, with quiet white gaps at 300 and 600, like panel borders.
    page[:, :, :] = numpy.tile(numpy.arange(100, dtype=numpy.uint8)[None, :, None] * 2, (height, 1, 3))
    page[290:310] = 255
    page[590:610] = 255
    return page


def test_short_panels_are_not_split():
    page = tall_page(900)

    assert split_tall_panel([0, 0, 100, 400], page, []) == [[0, 0, 100, 400]]


def test_a_very_tall_panel_is_split_at_its_quiet_rows_and_nothing_is_lost():
    page = tall_page(900)

    pieces = split_tall_panel([0, 0, 100, 900], page, [])

    # 900 px is about 4.1 screens, so 5 pieces, cut in the white gaps where possible, covering the whole panel.
    assert pieces[0][1] == 0 and pieces[-1][3] == 900
    assert all(piece[3] == next_piece[1] for piece, next_piece in zip(pieces, pieces[1:]))
    cuts = [piece[3] for piece in pieces[:-1]]
    assert any(290 <= cut <= 310 for cut in cuts)


def test_a_tall_panel_is_never_split_through_text():
    page = tall_page(900)
    # A speech bubble over the white gap at 300.
    bubble = [10, 250, 90, 350]

    pieces = split_tall_panel([0, 0, 100, 900], page, [bubble])

    # At least 12 px clear of the bubble, for its outline.
    assert not any(250 - 12 < piece[3] < 350 + 12 for piece in pieces[:-1])


def test_a_thin_sliver_is_not_split_even_though_it_is_tall_for_its_width():
    # 600 px wide page: a phone screen as wide as it is 1,302 px tall. The sliver is 40 x 900.
    page = blank(1000, 600)
    page[:, 100:140] = drawn_page(1000, 40)

    assert split_tall_panel([100, 0, 140, 900], page, []) == [[100, 0, 140, 900]]


def faint_watermark():
    mark = blank(80, 80)
    mark[20:60, 20:60] = 225  # pale grey, like a faded logo
    mark[35:45, 30:50] = 210
    return mark


def faint_petal(x):
    """
    A pale outlined shape, like a falling petal, different for each "x".
    """
    from PIL import Image, ImageDraw

    petal = Image.fromarray(blank(80, 80))
    ImageDraw.Draw(petal).ellipse([x, 20, x + 25, 60], outline=(225, 205, 205), width=2)
    return numpy.array(petal)


def test_blank_panels_and_repeated_watermarks_are_left_out_but_faint_art_stays():
    # Page 1: a black box, a real panel, and a watermark. Page 2: two more copies of the watermark and two different petals.
    page_1 = numpy.concatenate([numpy.zeros((80, 80, 3), numpy.uint8), drawn_page(80, 80), faint_watermark()], axis=1)
    page_2 = numpy.concatenate([faint_watermark(), faint_watermark(), faint_petal(5), faint_petal(45)], axis=1)
    results = [
        {"panels": [[0, 0, 80, 80], [80, 0, 160, 80], [160, 0, 240, 80]]},
        {"panels": [[0, 0, 80, 80], [80, 0, 160, 80], [160, 0, 240, 80], [240, 0, 320, 80]]},
    ]

    kept = remove_junk_panels(results, [page_1, page_2])

    assert kept[0]["panels"] == [[80, 0, 160, 80]]
    # The two petals are faint too, but different from each other and from the watermark.
    assert kept[1]["panels"] == [[160, 0, 240, 80], [240, 0, 320, 80]]


def test_a_sliver_showing_only_what_another_panel_shows_is_left_out():
    strip = blank(600, 400)
    big_panel = [0, 100, 300, 400]
    strip[100:400, 0:300] = drawn_page(300, 300)
    # A sliver overlapping the panel's right edge. Its only text is inside the big panel, and its art is too.
    sliver = [280, 80, 320, 420]
    text = [200, 150, 290, 200]

    assert remove_repeated_webtoon_panels(strip, [big_panel, sliver], [text]) == [big_panel]


def test_a_panel_with_text_no_other_panel_shows_is_kept():
    strip = blank(600, 400)
    big_panel = [0, 100, 300, 400]
    strip[100:400, 0:300] = drawn_page(300, 300)
    # A floating speech bubble: its text isn't in any other panel.
    bubble = [310, 450, 390, 520]
    text = [320, 460, 380, 510]

    assert sorted(remove_repeated_webtoon_panels(strip, [big_panel, bubble], [text])) == sorted([big_panel, bubble])


def test_a_full_size_panel_inside_a_bigger_one_is_kept():
    strip = blank(800, 400)
    strip[100:700, 0:400] = drawn_page(600, 400)
    big_slice = [0, 100, 400, 700]
    panel_inside = [20, 200, 380, 500]

    assert sorted(remove_repeated_webtoon_panels(strip, [big_slice, panel_inside], [])) == sorted([big_slice, panel_inside])


def test_soft_art_no_other_panel_shows_is_kept():
    strip = blank(800, 400)
    strip[100:400, 0:300] = drawn_page(300, 300)
    big_panel = [0, 100, 300, 400]
    # A sliver of pale, soft art (like a falling petal) away from every panel: little detail, but nothing else shows it.
    petal = [320, 500, 380, 700]
    strip[520:680, 330:370] = 235

    assert sorted(remove_repeated_webtoon_panels(strip, [big_panel, petal], [])) == sorted([big_panel, petal])
