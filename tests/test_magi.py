import os
from types import SimpleNamespace

import pytest
import torch
from tqdm import tqdm

import magi as magi_module
from tests.fake_pages import drawn_page
from magi import Magi, get_dialogue_for_each_panel


def test_magi_runs_on_the_mac_gpu_then_an_nvidia_gpu_then_the_cpu(monkeypatch):
    def set_available(mps, cuda):
        monkeypatch.setattr(torch.backends.mps, "is_available", lambda: mps)
        monkeypatch.setattr(torch.cuda, "is_available", lambda: cuda)

    set_available(mps=True, cuda=True)
    assert magi_module.get_device() == "mps"

    set_available(mps=False, cuda=True)
    assert magi_module.get_device() == "cuda"

    set_available(mps=False, cuda=False)
    assert magi_module.get_device() == "cpu"


class FakeModel:
    """
    A stand-in for Magi's model: two pages, where the first has dialogue, a sound effect, then more dialogue.
    """

    def __init__(self, device="mps", fail_on_gpu=False):
        self.device = torch.device(device)
        self.fail_on_gpu = fail_on_gpu
        self.boxes_read = []

    def to(self, device):
        self.device = torch.device(device)
        return self

    def predict_detections_and_associations(self, pages):
        if self.fail_on_gpu and self.device.type != "cpu":
            raise RuntimeError("MPS backend out of memory")

        # "page 1" has text. Any other page has none.
        return [
            {"texts": [[0, 0, 1, 1], [1, 1, 2, 2], [2, 2, 3, 3]], "is_essential_text": [True, False, True]}
            if page == "page 1"
            else {"texts": [], "is_essential_text": []}
            for page in pages
        ]

    def predict_ocr(self, pages, boxes, **kwargs):
        self.boxes_read.append(boxes)
        return [[f"line {index + 1}" for index in range(len(page_boxes))] for page_boxes in boxes]


def get_magi_with_model(model):
    magi = Magi()
    magi._full_model = model
    return magi


def test_only_the_dialogue_is_read_and_the_lists_stay_lined_up():
    model = FakeModel()
    pages = ["page 1", "page 2"]

    results = get_magi_with_model(model).get_per_page_results(pages)

    # The sound effect box is never read.
    assert model.boxes_read == [[[[0, 0, 1, 1], [2, 2, 3, 3]]]]
    # One entry for each text box, with "" for the sound effect, so it still lines up with "texts".
    assert results[0]["ocr"] == ["line 1", "", "line 2"]
    assert results[1]["ocr"] == []


def test_the_text_used_for_the_video_is_only_the_dialogue():
    from SpeechTextParser import SpeechTextParser

    results = get_magi_with_model(FakeModel()).get_per_page_results(["page 1"])

    assert SpeechTextParser().get_essential_text_list_from_magi_data(results) == [["line 1", "line 2"]]


def test_if_the_gpu_fails_magi_runs_again_on_the_cpu_and_stays_there(capsys):
    model = FakeModel(fail_on_gpu=True)
    magi = get_magi_with_model(model)

    results = magi.get_per_page_results(["page 1"])

    assert results[0]["ocr"] == ["line 1", "", "line 2"]
    assert magi._full_model.device.type == "cpu"
    assert "Running it on the CPU instead" in capsys.readouterr().out


def test_a_failure_on_the_cpu_is_not_hidden():
    class BrokenModel(FakeModel):
        def predict_detections_and_associations(self, pages):
            raise RuntimeError("broken")

    with pytest.raises(RuntimeError, match="broken"):
        get_magi_with_model(BrokenModel(device="cpu")).get_per_page_results(["page 1"])


def test_finding_panels_also_falls_back_to_the_cpu(monkeypatch):
    magi = Magi()
    magi._panels_model = SimpleNamespace(device=torch.device("mps"), to=lambda device: SimpleNamespace(device=torch.device(device)))
    attempts = []

    def find_panels(pages, reading_direction="rtl"):
        attempts.append(magi._panels_model.device.type)
        if magi._panels_model.device.type != "cpu":
            raise RuntimeError("MPS backend out of memory")
        return [{"panels": []}]

    monkeypatch.setattr(magi, "find_panels", find_panels)

    assert magi.predict_panels(["page 1"]) == [{"panels": []}]
    assert attempts == ["mps", "cpu"]


# Two panels side by side: the right one is read first (manga).
RIGHT_PANEL = [50, 0, 100, 100]
LEFT_PANEL = [0, 0, 50, 100]


def make_page_text(*lines):
    """
    Each line is (text box, text, is dialogue), in the page's reading order.
    """
    return {
        "texts": [box for box, _, _ in lines],
        "ocr": [text for _, text, _ in lines],
        "is_essential_text": [is_dialogue for _, _, is_dialogue in lines],
    }


def test_each_line_goes_to_the_panel_it_is_in_and_keeps_the_reading_order():
    page_text = make_page_text(
        ([60, 10, 90, 30], "First, in the right panel.", True),
        ([10, 10, 40, 30], "Then the left panel.", True),
        ([60, 50, 90, 70], "BOOM", False),
        ([60, 70, 90, 90], "Back in the right panel?", True),
    )

    assert get_dialogue_for_each_panel(page_text, [RIGHT_PANEL, LEFT_PANEL]) == [
        ["First, in the right panel.", "Back in the right panel?"],
        ["Then the left panel."],
    ]


def test_a_bubble_across_two_panels_goes_to_the_one_it_covers_most():
    page_text = make_page_text(([40, 10, 90, 30], "Mostly on the right.", True))

    assert get_dialogue_for_each_panel(page_text, [RIGHT_PANEL, LEFT_PANEL]) == [
        ["Mostly on the right."],
        [],
    ]


def test_a_bubble_outside_every_panel_goes_to_the_closest_one():
    page_text = make_page_text(([10, 120, 30, 140], "Below the left panel.", True))

    assert get_dialogue_for_each_panel(page_text, [RIGHT_PANEL, LEFT_PANEL]) == [
        [],
        ["Below the left panel."],
    ]


def test_panel_by_panel_saves_the_text_for_each_saved_panel_in_order(tmp_path, monkeypatch):
    import json

    import numpy

    magi = Magi()
    pages = [drawn_page() for _ in range(2)]
    # The middle panel on page 1 is outside the page, so it's skipped and isn't saved.
    panels = [{"panels": [RIGHT_PANEL, [200, 200, 300, 300], LEFT_PANEL]}, {"panels": [[0, 0, 100, 100]]}]
    page_text = [
        make_page_text(([10, 10, 40, 30], "Left.", True), ([60, 10, 90, 30], "Right.", True)),
        make_page_text(([10, 10, 40, 30], "Page two.", True)),
    ]
    monkeypatch.setattr(magi, "predict_panels", lambda chapter_pages, reading_direction: panels)
    monkeypatch.setattr(magi, "get_per_page_results", lambda chapter_pages: page_text)

    magi.get_panels_using_local_cpu(pages, "Series/Ch 1", str(tmp_path), read_text=True)

    chapter = tmp_path / "panel-by-panel" / "not-grouped-by-page" / "Series" / "Ch 1"
    assert sorted(os.listdir(chapter)) == ["panel-text.json", "panel_1.png", "panel_2.png", "panel_3.png"]
    assert json.loads((chapter / "panel-text.json").read_text()) == [["Right."], ["Left."], ["Page two."]]


def test_panel_by_panel_does_not_read_the_text_unless_asked(tmp_path, monkeypatch):
    import numpy

    magi = Magi()
    monkeypatch.setattr(magi, "predict_panels", lambda chapter_pages, reading_direction: [{"panels": [LEFT_PANEL]}])
    monkeypatch.setattr(
        magi, "get_per_page_results", lambda chapter_pages: pytest.fail("the text shouldn't be read")
    )

    magi.get_panels_using_local_cpu(
        [drawn_page()], "Series/Ch 1", str(tmp_path)
    )

    chapter = tmp_path / "panel-by-panel" / "not-grouped-by-page" / "Series" / "Ch 1"
    assert os.listdir(chapter) == ["panel_1.png"]


def test_finding_and_reading_the_text_shows_its_progress(monkeypatch):
    import gui_classes.ProgressPanel as progress_panel

    reports = []
    monkeypatch.setattr(progress_panel, "report_progress", lambda **fields: reports.append(fields))

    get_magi_with_model(FakeModel()).get_per_page_results(["page 1", "page 2"])

    assert reports == [
        {"pages_done": 0, "pages_total": 2, "unit": "images", "detail": "Finding the text"},
        {"pages_done": 1},
        {"pages_done": 2},
        {"pages_done": 0, "pages_total": 2, "unit": "lines", "detail": "Reading the text"},
        {"pages_done": 2},
    ]


def test_the_text_is_read_in_parts_of_exactly_one_batch_of_lines(monkeypatch):
    monkeypatch.setattr(magi_module, "READ_TEXT_BATCH_SIZE", 3)
    model = FakeModel()
    magi = get_magi_with_model(model)
    boxes_on_each_page = [[[0, 0, 1, 1]] * 2, [[0, 0, 1, 1]] * 2, [], [[0, 0, 1, 1]]]

    text = magi.read_text_in_parts(["p1", "p2", "p3", "p4"], boxes_on_each_page, lambda **fields: None, tqdm)

    # Exactly 3 lines at a time, so page 2's lines are split between the two parts.
    assert [sum(map(len, part)) for part in model.boxes_read] == [3, 2]
    assert [len(page_text) for page_text in text] == [2, 2, 0, 1]
