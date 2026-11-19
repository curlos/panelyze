import os

from copy_panels_to_one_level_directory import (
    copy_panels_to_one_level_directory,
    extract_panel_num,
)


def test_extract_panel_num_returns_an_int():
    assert extract_panel_num("panel_10.png") == 10


def test_panels_are_copied_in_numeric_order(tmp_path):
    grouped = tmp_path / "grouped"
    for page_num, panel_count in [(1, 12), (2, 2)]:
        page_dir = grouped / f"page_{page_num}"
        page_dir.mkdir(parents=True)
        for panel_num in range(1, panel_count + 1):
            (page_dir / f"panel_{panel_num}.png").write_text(f"p{page_num}-{panel_num}")

    flat = tmp_path / "flat"
    copy_panels_to_one_level_directory(str(grouped), str(flat))

    # Page 1 has 12 panels, so panel_10 must be the 10th one (not the 2nd, like with string sorting).
    assert (flat / "panel_2.png").read_text() == "p1-2"
    assert (flat / "panel_10.png").read_text() == "p1-10"
    assert (flat / "panel_13.png").read_text() == "p2-1"
    assert len(os.listdir(flat)) == 14
