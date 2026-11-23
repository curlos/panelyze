import json
import os
from types import SimpleNamespace

import numpy
import pytest
from PIL import Image, ImageDraw, ImageFont

import translate
from gui_classes.PipelineView import PIPELINE_STEPS, get_settings_review, get_step_output_directory
from gui_classes.TranslateView import get_translate_settings
from tests.fake_gui import get_all_controls
from utils import READING_DIRECTION_FILE_NAME, DownloadCancelled

SETTINGS = {
    "engine": "ollama",
    "model": "qwen3-vl:8b-instruct",
    "api_key": "",
    "source_language": "japanese",
    "target_language": "english",
    "keep_honorifics": True,
    "font": "Bubble Sans",
    "send_page_image": True,
}


def make_bubble_page(text_box=(160, 120, 200, 260)):
    """
    A grey page with one black-outlined speech bubble, and black "text" strokes inside it. (A light area over a quarter of the page counts as background, not a bubble.)
    """
    page = Image.new("RGB", (800, 600), (150, 150, 150))
    draw = ImageDraw.Draw(page)
    draw.ellipse((60, 60, 340, 340), fill="white", outline="black", width=4)
    # Letter-sized marks in columns, like vertical Japanese text.
    x0, y0, x1, y1 = text_box
    for x in range(x0 + 4, x1 - 8, 14):
        for y in range(y0 + 4, y1 - 12, 16):
            draw.rectangle((x, y, x + 9, y + 11), fill="black")
    return page


def get_dark_pixels(page, area=None):
    pixels = numpy.asarray(page.convert("L"))
    if area:
        left, top, right, bottom = [int(value) for value in area]
        pixels = pixels[top:bottom, left:right]
    return int((pixels < 100).sum())


def test_every_line_number_is_required_in_the_answer():
    schema = translate.get_translation_schema(3)
    assert schema["properties"]["lines"]["required"] == ["1", "2", "3"]
    assert schema["properties"]["lines"]["additionalProperties"] is False


def test_the_translation_comes_back_in_the_order_of_the_lines(monkeypatch):
    sent = {}

    def fake_llm(settings, system_prompt, request_text, image, schema):
        sent.update(system_prompt=system_prompt, request_text=request_text, image=image)
        # "2" is answered empty (e.g. a sound effect), "3" is missing.
        return json.dumps({"lines": {"1": " Hello! ", "2": ""}, "new_glossary": [{"name": "トウフ", "translation": "Tofu", "note": "boy"}]})

    monkeypatch.setattr(translate, "ask_llm", fake_llm)
    texts, glossary = translate.translate_page(
        SETTINGS, make_bubble_page(), [(1, 1, 5, 5), (6, 6, 9, 9), (10, 10, 20, 20)], ["こんにちは", "ドン", "え"], None, []
    )

    assert texts == ["Hello!", "", ""]
    assert glossary[0]["translation"] == "Tofu"
    assert "1: こんにちは\n2: ドン\n3: え" in sent["request_text"]
    assert sent["image"] is not None


def test_the_image_setting_sends_no_image(monkeypatch):
    images = []
    monkeypatch.setattr(translate, "ask_llm", lambda settings, system_prompt, request_text, image, schema: images.append(image) or '{"lines": {"1": "Hi"}, "new_glossary": []}')

    translate.translate_page({**SETTINGS, "send_page_image": False}, make_bubble_page(), [(1, 1, 5, 5)], ["やあ"], None, [])

    assert images == [None]


def test_a_pure_translation_model_gets_one_line_at_a_time_with_the_lines_before_it(monkeypatch):
    asked = []

    def fake_line(model, source_language, target_language, line, earlier_lines):
        asked.append((line, list(earlier_lines)))
        return {"やあ": "Hey.", "ド": "Doh"}[line]

    monkeypatch.setattr(translate, "ask_ollama_line", fake_line)
    monkeypatch.setattr(translate, "ask_llm", lambda *args: pytest.fail("a pure translation model never gets the page request"))
    previous_page = [{"source": "おはよう", "text": "Morning."}, {"source": "ゴゴ", "text": ""}]

    texts, glossary = translate.translate_page({**SETTINGS, "model": translate.PLAMO_8B}, make_bubble_page(), [(1, 1, 5, 5)] * 3, ["やあ", "...", "ド"], previous_page, [])

    # "…" has no letters, so it isn't sent at all.
    assert (texts, glossary) == (["Hey.", "", "Doh"], [])
    assert asked == [("やあ", [("おはよう", "Morning.")]), ("ド", [("おはよう", "Morning."), ("やあ", "Hey.")])]


def test_plamo_and_translategemma_get_their_own_prompt_formats(monkeypatch):
    import requests

    sent = []

    def fake_post(url, json, timeout):
        sent.append((url, json))
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"response": " Hey. ", "message": {"content": "Hola."}})

    monkeypatch.setattr(requests, "post", fake_post)

    assert translate.ask_ollama_line(translate.PLAMO_2B, "japanese", "english", "やあ", [("おはよう", "Morning.")]) == "Hey."
    assert translate.ask_ollama_line("translategemma:4b", "english", "spanish", "Hi.", []) == "Hola."

    (plamo_url, plamo), (gemma_url, gemma) = sent
    assert plamo_url.endswith("/api/generate") and plamo["raw"]
    assert plamo["prompt"].endswith("<|plamo:tag|>input<|plamo:msg|>やあ<|plamo:tag|>output<|plamo:key|>lang<|plamo:val|>en<|plamo:msg|>")
    assert "おはよう<|plamo:tag|>output<|plamo:key|>lang<|plamo:val|>en<|plamo:msg|>Morning." in plamo["prompt"]
    assert gemma_url.endswith("/api/chat")
    assert gemma["messages"][0]["content"].startswith("You are a professional English (en) to Spanish (es) translator.")
    assert gemma["messages"][0]["content"].endswith("into Spanish:\n\n\nHi.")


def test_plamo_is_only_for_japanese_to_english(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: SimpleNamespace(json=lambda: {"models": [{"name": translate.PLAMO_8B}]}))
    settings = {**SETTINGS, "model": translate.PLAMO_8B}

    translate.check_engine_ready(settings)
    with pytest.raises(RuntimeError, match="only translates Japanese to English"):
        translate.check_engine_ready({**settings, "source_language": "spanish"})
    assert translate.is_pair_supported("translategemma:12b", "spanish", "english")


def test_a_model_is_only_downloaded_with_room_to_spare_and_can_be_removed(monkeypatch):
    import requests

    assert "needs 10.1 GB" in translate.get_room_for_model_error("translategemma:12b", 9.5)
    assert translate.get_room_for_model_error("translategemma:12b", 10.2) is None

    progress = []
    parts = [b'{"status": "pulling manifest"}', b'{"status": "pulling a", "digest": "a", "total": 2000000000, "completed": 1000000000}', b"", b'{"status": "pulling b", "digest": "b", "total": 1000000000, "completed": 1000000000}', b'{"status": "success"}']

    class FakeResponse:
        status_code = 200
        text = ""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def raise_for_status(self):
            pass

        def iter_lines(self):
            return iter(parts)

    monkeypatch.setattr(translate, "get_free_disk_gb", lambda: 100)
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResponse())
    assert translate.download_ollama_model("translategemma:4b", report=lambda done, total: progress.append((done, total)))
    assert progress == [(1, 2), (2, 3)]
    # Cancelled: it stops reading, and says it didn't finish.
    assert translate.download_ollama_model("translategemma:4b", is_cancelled=lambda: True) is False

    parts[1:] = [b'{"error": "pull model manifest: file does not exist"}']
    with pytest.raises(RuntimeError, match="couldn't download"):
        translate.download_ollama_model("translategemma:4b")

    monkeypatch.setattr(translate, "get_free_disk_gb", lambda: 1)
    with pytest.raises(RuntimeError, match="Not enough free disk space"):
        translate.download_ollama_model("translategemma:4b")

    deleted = []
    monkeypatch.setattr(requests, "delete", lambda url, json, timeout: deleted.append(json) or FakeResponse())
    translate.delete_ollama_model("translategemma:4b")
    assert deleted == [{"model": "translategemma:4b"}]


def test_the_honorifics_setting_reaches_the_prompt():
    assert "Keep Japanese honorifics" in translate.get_system_prompt("japanese", "english", True)
    assert "instead of honorifics" in translate.get_system_prompt("japanese", "english", False)
    # Other languages have no honorifics to keep.
    assert "instead of honorifics" in translate.get_system_prompt("spanish", "english", True)
    assert "Spanish manga pages into English" in translate.get_system_prompt("spanish", "english", True)


def test_the_glossary_and_the_previous_page_are_sent_with_the_page():
    request = translate.get_page_request(
        ["おはよう"],
        [{"source": "社長", "text": "Boss"}, {"source": "ドン", "text": ""}],
        [{"name": "石墨", "translation": "Ishizumi", "note": "man, calm"}],
    )

    assert "石墨: Ishizumi (man, calm)" in request
    assert "社長 -> Boss" in request
    assert "ドン" not in request
    assert request.endswith("This page:\n1: おはよう")


def test_a_box_found_twice_becomes_one_box_around_both():
    boxes, bubbles = translate.remove_repeated_boxes([(10, 10, 50, 100), (12, 5, 48, 110), (200, 200, 220, 220)], [3, 3, None])
    assert boxes == [(10, 5, 50, 110), (200, 200, 220, 220)]
    assert bubbles == [3, None]


def test_the_same_text_found_in_its_bubble_and_on_the_art_is_lettered_once():
    # Like Dragon Tofu ch. 24 page 04: one bubble read twice (with one OCR slip), plus a different line next to it.
    on_art, in_bubble, other = ((490, 471, 639, 730), (490, 471, 639, 730), None), ((498, 487, 650, 615), (498, 487, 650, 615), 7), ((221, 605, 261, 737), (221, 605, 261, 737), 8)

    lines, sources = translate.remove_repeated_lines([on_art, in_bubble, other], ["チャンホと大刀のギルドが優勝とは驚いたな", "チャンボと大刀のギルドが優勝とは驚いたな", "僕たちが3位とれたのもね"])

    assert lines == [in_bubble, other]
    assert sources == ["チャンボと大刀のギルドが優勝とは驚いたな", "僕たちが3位とれたのもね"]


def test_a_translation_still_in_japanese_counts_as_empty(monkeypatch):
    monkeypatch.setattr(translate, "ask_llm", lambda *args: json.dumps({"lines": {"1": "ド.", "2": "Chanbo-kun!", "3": "Thanks, Tanaka (田中)."}, "new_glossary": []}))
    texts, _ = translate.translate_page(SETTINGS, make_bubble_page(), [(1, 1, 5, 5)] * 3, ["ド", "チャンボくん!", "ありがとう田中"], None, [])
    # Only the Japanese is dropped, and a line with no letters left is empty.
    assert texts == ["", "Chanbo-kun!", "Thanks, Tanaka ()."]


def test_a_bubble_inside_a_sound_effects_box_stays_its_own_line_and_text_on_the_art_that_overlaps_is_joined():
    # Like Shachou ch. 3 page 2: a big sound effect's box drawn around a speech bubble's box.
    sound_effect, in_bubble, overlapping_caption = (100, 100, 700, 400), (200, 200, 300, 350), (600, 120, 800, 300)

    boxes, bubbles = translate.remove_repeated_boxes([sound_effect, in_bubble, overlapping_caption], [None, 5, None])

    assert boxes == [(100, 100, 800, 400), in_bubble]
    assert bubbles == [None, 5]


def test_boxes_next_to_each_other_in_one_bubble_become_one_line():
    groups = translate.group_by_bubble(
        [(100, 100, 120, 130), (100, 135, 120, 200), (300, 100, 320, 200), (100, 300, 120, 320)],
        [7, 7, 7, None],
    )

    assert groups == [((100, 100, 120, 200), 7), ((300, 100, 320, 200), 7), ((100, 300, 120, 320), None)]


def test_a_line_is_read_from_all_the_text_in_its_bubble_not_only_magis_box():
    # Magi's box covers only the bottom of the text (like "終了" at the end of a caption).
    page = make_bubble_page()
    lines = translate.get_lines(page, [(160, 220, 200, 260)])

    assert len(lines) == 1
    text_box, magi_box, bubble = lines[0]
    assert magi_box == (160, 220, 200, 260) and bubble is not None
    x0, y0, x1, y1 = text_box
    assert y0 <= 125 and x0 <= 164 and x1 >= 196


def test_a_bubble_is_erased_inside_but_keeps_its_outline():
    page = make_bubble_page()
    box = (160, 120, 200, 260)
    light_areas = translate.get_light_areas(page)
    bubble = translate.get_bubble(light_areas, box)
    outline_before = get_dark_pixels(page, (50, 50, 350, 70))

    color, areas = translate.erase_in_bubble(page, light_areas, bubble, box, [box])

    assert bubble is not None
    assert color == (255, 255, 255)
    # The text's area (inside the curve of the outline) is clean.
    assert get_dark_pixels(page, (140, 110, 260, 270)) == 0
    assert get_dark_pixels(page, (50, 50, 350, 70)) == outline_before
    # The lettering areas are inside the bubble, and some are wider than the tall, narrow text box.
    for left, top, right, bottom in areas:
        assert 60 < left and right < 340 and 60 < top and bottom < 340
    assert max(right - left for left, _, right, _ in areas) > box[2] - box[0]


def test_a_drawing_on_a_plain_white_panel_is_not_taken_for_text():
    # A white panel (under a quarter of the page) with a character drawn in it, and narration with no bubble.
    page = Image.new("RGB", (1000, 1000), (150, 150, 150))
    draw = ImageDraw.Draw(page)
    draw.rectangle((50, 50, 450, 450), fill="white", outline="black", width=4)
    draw.ellipse((200, 150, 420, 420), outline="black", width=6)
    draw.line((230, 300, 390, 300), fill="black", width=4)
    for y in range(90, 230, 16):
        draw.rectangle((90, y, 99, y + 11), fill="black")
    box = (86, 86, 104, 230)
    drawing_before = get_dark_pixels(page, (190, 140, 430, 430))

    [(text_box, magi_box, bubble)] = translate.get_lines(page, [box])
    translate.erase_in_bubble(page, translate.get_light_areas(page), bubble, magi_box, [magi_box])

    assert bubble is not None
    assert text_box[2] < 150 and text_box[3] < 260
    assert get_dark_pixels(page, (190, 140, 430, 430)) == drawing_before
    assert get_dark_pixels(page, (86, 86, 104, 230)) == 0


def test_two_bubbles_that_touch_each_keep_the_other_ones_text():
    # Two bubbles joined into one light area, with a line of text in each.
    page = Image.new("RGB", (1000, 800), (150, 150, 150))
    draw = ImageDraw.Draw(page)
    draw.ellipse((100, 100, 400, 400), fill="white", outline="black", width=4)
    draw.ellipse((360, 100, 660, 400), fill="white", outline="black", width=4)
    # An opening through both outlines where they cross, like two bubbles drawn as one.
    draw.rectangle((350, 220, 410, 280), fill="white")
    for x0 in (230, 490):
        for y in range(180, 320, 16):
            draw.rectangle((x0, y, x0 + 9, y + 11), fill="black")
    left_box, right_box = (226, 176, 244, 320), (486, 176, 504, 320)
    light_areas = translate.get_light_areas(page)
    bubble = translate.get_bubble(light_areas, left_box)
    assert bubble == translate.get_bubble(light_areas, right_box)

    _, areas = translate.erase_in_bubble(page, light_areas, bubble, left_box, [left_box, right_box])

    assert get_dark_pixels(page, left_box) == 0
    assert get_dark_pixels(page, right_box) > 0
    assert all(area[2] < 400 for area in areas)


def test_box_numbers_stay_on_the_image_for_a_box_at_the_top():
    image = translate.get_numbered_page_image(Image.new("RGB", (800, 600), "white"), [(0, 0, 40, 100)])
    red = numpy.asarray(image)[:30, :40]
    assert ((red[..., 0] > 200) & (red[..., 1] < 80)).sum() > 100


def test_the_text_only_prompt_doesnt_talk_about_the_image():
    prompt = translate.get_system_prompt("japanese", "english", True, has_image=False)
    assert "image" not in prompt and "picture" not in prompt and "red number" not in prompt
    assert "Check the picture" in translate.get_system_prompt("japanese", "english", True, has_image=True)


def test_ollama_gets_the_schema_with_thinking_off_and_retries_for_models_without_thinking(monkeypatch):
    import requests

    bodies = []

    def fake_post(url, json, timeout):
        bodies.append(dict(json))
        if "think" in json:
            return SimpleNamespace(status_code=400, text='"qwen" does not support thinking')
        return SimpleNamespace(status_code=200, text="", raise_for_status=lambda: None, json=lambda: {"message": {"content": "{}"}})

    monkeypatch.setattr(requests, "post", fake_post)
    image = Image.new("RGB", (10, 10))

    assert translate.ask_ollama("qwen", "system", "request", image, {"type": "object"}) == "{}"
    assert bodies[0]["think"] is False and bodies[0]["format"] == {"type": "object"}
    assert bodies[0]["messages"][1]["images"]
    assert "think" not in bodies[1]


def test_claude_and_chatgpt_are_asked_for_json_and_a_refusal_is_explained(monkeypatch):
    import anthropic
    import openai

    claude_calls, openai_calls = [], []

    class FakeClaude:
        def __init__(self, api_key, max_retries):
            self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            claude_calls.append(kwargs)
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="{}")])

    class FakeOpenAI:
        def __init__(self, api_key, base_url, max_retries):
            openai_calls.append(base_url)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            openai_calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None, refusal="no"))])

    monkeypatch.setattr(anthropic, "Anthropic", FakeClaude)
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    schema = translate.get_translation_schema(1)

    assert translate.ask_claude("claude-opus-5-5", "key", "system", "request", Image.new("RGB", (10, 10)), schema) == "{}"
    assert claude_calls[0]["output_config"]["format"] == {"type": "json_schema", "schema": schema}
    assert claude_calls[0]["fallbacks"] == "default" and claude_calls[0]["messages"][0]["content"][0]["type"] == "image"

    with pytest.raises(RuntimeError, match="Gemini declined"):
        translate.ask_openai_compatible("gemini", "gemini-3.8-flash", "key", "system", "request", None, schema)
    assert openai_calls[0] == translate.OPENAI_BASE_URLS["gemini"]
    assert openai_calls[1]["response_format"]["json_schema"]["strict"] is True


def test_text_on_a_flat_background_is_filled_and_text_on_artwork_goes_to_lama(monkeypatch):
    painted = []
    monkeypatch.setattr(translate, "paint_over_with_lama", lambda page, box: painted.append(box))

    flat = Image.new("RGB", (200, 200), (20, 20, 20))
    ImageDraw.Draw(flat).line((90, 90, 110, 110), fill="white", width=4)
    color, _ = translate.erase_box(flat, (85, 85, 115, 115))
    assert color == (20, 20, 20)
    assert flat.getpixel((100, 100)) == (20, 20, 20)

    artwork = Image.fromarray(numpy.random.default_rng(0).integers(0, 255, (200, 200, 3), dtype=numpy.uint8))
    color, _ = translate.erase_box(artwork, (85, 85, 115, 115))
    assert color is None
    assert painted == [(85, 85, 115, 115)]


def make_captions_page():
    """
    Two caption boxes side by side on a white page, both open at the top to the page's white margin (so neither is a closed bubble), each with a column of "text". The right one ends in "…" dots below Magi's box.
    """
    page = Image.new("RGB", (600, 400), "white")
    draw = ImageDraw.Draw(page)
    draw.rectangle((0, 300, 599, 399), fill=(120, 120, 120))
    for left in (100, 230):
        draw.line((left, 50, left, 300), fill="black", width=3)
        draw.line((left + 110, 50, left + 110, 300), fill="black", width=3)
        draw.line((left, 300, left + 110, 300), fill="black", width=3)
    for x0 in (145, 270):
        for y in range(80, 180, 24):
            draw.rectangle((x0, y, x0 + 19, y + 19), fill="black")
    for y in (203, 209):
        draw.rectangle((278, y, 281, y + 3), fill="black")
    return page


def test_a_captions_dots_below_magis_box_are_erased_but_not_the_caption_next_to_it():
    page = make_captions_page()
    left_text_before = get_dark_pixels(page, (140, 75, 170, 200))

    color, [area] = translate.erase_box(page, (266, 76, 294, 200))

    assert color == (255, 255, 255)
    assert get_dark_pixels(page, (266, 76, 294, 240)) == 0
    assert get_dark_pixels(page, (140, 75, 170, 200)) == left_text_before
    # The lettering area grows over the caption's white but stops before its borders.
    assert 232 < area[0] < 266 and 294 < area[2] < 340 and area[3] < 300


def test_lettering_picks_the_area_its_text_fits_biggest_in():
    page = Image.new("RGB", (600, 400), "white")
    tall, wide = (20, 20, 60, 380), (200, 100, 580, 200)

    translate.fit_and_draw_text(page, [tall, wide], "Your report is late!", os.path.join(translate.FONTS_FOLDER, translate.FONTS["Bubble Sans"]), (255, 255, 255))

    assert get_dark_pixels(page, tall) == 0
    assert get_dark_pixels(page, wide) > 0


def test_lettering_stays_inside_its_area_and_shrinks_to_fit():
    page = Image.new("RGB", (400, 400), "white")
    area = (100, 100, 200, 160)
    font_path = os.path.join(translate.FONTS_FOLDER, translate.FONTS["Bubble Sans"])

    translate.fit_and_draw_text(page, [area], "This is a long line that has to shrink a lot to fit in here", font_path, (255, 255, 255))

    assert get_dark_pixels(page, area) > 0
    assert get_dark_pixels(page) == get_dark_pixels(page, area)


def test_every_font_is_bundled_with_its_license():
    for font_file in translate.FONTS.values():
        assert os.path.exists(os.path.join(translate.FONTS_FOLDER, font_file))
    licenses = [name for name in os.listdir(translate.FONTS_FOLDER) if name.startswith("OFL")]
    assert len(licenses) == len(translate.FONTS)


class FakeMagi:
    def __init__(self, boxes):
        self.boxes = boxes

    def find_text_boxes(self, pages, text_detection_threshold=0.3):
        self.threshold = text_detection_threshold
        return [{"texts": self.boxes, "panels": []} for _ in pages]

    def run_with_cpu_fallback(self, model_attribute, run):
        return run()


def make_chapter(folder, page_count=2):
    os.makedirs(folder, exist_ok=True)
    for number in range(page_count):
        make_bubble_page().save(os.path.join(folder, f"{number:02}.png"))
    with open(os.path.join(folder, READING_DIRECTION_FILE_NAME), "w") as file:
        file.write("rtl")
    return sorted(name for name in os.listdir(folder) if name.endswith(".png"))


def run_translate_chapter(monkeypatch, tmp_path, chapter, answers, cancel_after=None, settings=SETTINGS, gpu_share=None, report_progress=lambda **fields: None):
    import magi

    requests = []
    monkeypatch.setattr(translate, "get_ollama_gpu_share", lambda model: gpu_share)
    # Magi's box covers only the bottom of the text, so the line's box comes from the bubble.
    monkeypatch.setattr(magi, "get_magi", lambda: FakeMagi([[160.2, 200, 200, 260]]))
    monkeypatch.setattr(translate, "read_japanese", lambda pages, boxes: [["おはよう"] for _ in pages])

    def fake_llm(settings, system_prompt, request_text, image, schema):
        requests.append(request_text)
        if cancel_after is not None and len(requests) > cancel_after:
            raise AssertionError("asked after cancelling")
        return json.dumps(answers.pop(0))

    monkeypatch.setattr(translate, "ask_llm", fake_llm)
    input_folder = str(tmp_path / "in" / "Tofu" / chapter)
    names = make_chapter(input_folder)
    output_folder = str(tmp_path / "out" / "Tofu" / chapter)
    cancelled = iter([False] * (cancel_after or 99) + [True] * 99)

    def raise_if_cancelled():
        if next(cancelled):
            raise RuntimeError("cancelled")

    translate.translate_chapter(input_folder, names, output_folder, settings, report_progress=report_progress, raise_if_cancelled=raise_if_cancelled)
    return output_folder, requests


def test_a_chapter_is_translated_saved_and_its_glossary_kept_for_the_next_chapter(monkeypatch, tmp_path):
    answers = [
        {"lines": {"1": "Morning."}, "new_glossary": [{"name": "石墨", "translation": "Ishizumi", "note": "man"}]},
        {"lines": {"1": "Morning!"}, "new_glossary": []},
    ]
    output_folder, requests = run_translate_chapter(monkeypatch, tmp_path, "Ch 1", answers)

    saved = json.load(open(os.path.join(output_folder, translate.TRANSLATION_FILE_NAME), encoding="utf-8"))
    assert [page["lines"][0]["text"] for page in saved["pages"]] == ["Morning.", "Morning!"]
    assert saved["pages"][0]["lines"][0]["box"][1] < 130
    assert sorted(os.listdir(output_folder)) == ["00.png", "01.png", READING_DIRECTION_FILE_NAME, translate.TRANSLATION_FILE_NAME]
    # The second page is sent with the first one's translation.
    assert "おはよう -> Morning." in requests[1]
    # The Japanese marks are gone (they filled about half the box) and the English is lettered in.
    text_area = (160, 120, 200, 260)
    translated_page = Image.open(os.path.join(output_folder, "00.png"))
    assert 0 < get_dark_pixels(translated_page, text_area) < get_dark_pixels(make_bubble_page(), text_area) / 2
    glossary_path = tmp_path / "out" / "Tofu" / translate.GLOSSARY_FILE_NAME
    assert json.load(open(glossary_path, encoding="utf-8"))[0]["name"] == "石墨"

    # The next chapter of the series gets the glossary.
    _, requests = run_translate_chapter(monkeypatch, tmp_path, "Ch 2", [{"lines": {"1": "Hi"}, "new_glossary": []}] * 2)
    assert "石墨: Ishizumi" in requests[0]


def test_translating_again_reuses_the_saved_lines_without_asking_the_llm(monkeypatch, tmp_path):
    output_folder, _ = run_translate_chapter(monkeypatch, tmp_path, "Ch 1", [{"lines": {"1": "Morning."}, "new_glossary": []}] * 2)
    # A line fixed by hand is kept.
    path = os.path.join(output_folder, translate.TRANSLATION_FILE_NAME)
    saved = json.load(open(path, encoding="utf-8"))
    saved["pages"][0]["lines"][0]["text"] = "Good morning."
    json.dump(saved, open(path, "w", encoding="utf-8"))

    _, requests = run_translate_chapter(monkeypatch, tmp_path, "Ch 1", [])

    assert requests == []
    assert json.load(open(path, encoding="utf-8"))["pages"][0]["lines"][0]["text"] == "Good morning."


def test_a_sound_effect_left_alone_is_still_lettered_once_fixed_by_hand(monkeypatch, tmp_path):
    monkeypatch.setattr(translate, "is_left_alone", lambda *args: True)
    output_folder, _ = run_translate_chapter(monkeypatch, tmp_path, "Ch 1", [{"lines": {"1": "Doh"}, "new_glossary": []}] * 2)
    path = os.path.join(output_folder, translate.TRANSLATION_FILE_NAME)
    saved = json.load(open(path, encoding="utf-8"))
    assert saved["pages"][0]["lines"][0]["text"] == ""

    saved["pages"][0]["lines"][0]["text"] = "Rumble"
    json.dump(saved, open(path, "w", encoding="utf-8"))
    run_translate_chapter(monkeypatch, tmp_path, "Ch 1", [])

    assert json.load(open(path, encoding="utf-8"))["pages"][0]["lines"][0]["text"] == "Rumble"


def test_cancel_stops_between_pages_and_keeps_the_pages_done(monkeypatch, tmp_path):
    with pytest.raises(RuntimeError, match="cancelled"):
        run_translate_chapter(monkeypatch, tmp_path, "Ch 1", [{"lines": {"1": "Hi"}, "new_glossary": []}] * 2, cancel_after=1)

    saved = json.load(open(tmp_path / "out" / "Tofu" / "Ch 1" / translate.TRANSLATION_FILE_NAME, encoding="utf-8"))
    assert [page["file"] for page in saved["pages"]] == ["00.png"]


def test_a_translation_into_another_language_is_made_again(monkeypatch, tmp_path):
    run_translate_chapter(monkeypatch, tmp_path, "Ch 1", [{"lines": {"1": "Morning."}, "new_glossary": []}] * 2)

    _, requests = run_translate_chapter(
        monkeypatch, tmp_path, "Ch 1", [{"lines": {"1": "Buenos días."}, "new_glossary": []}] * 2, settings={**SETTINGS, "target_language": "spanish"}
    )

    assert len(requests) == 2


def test_a_single_chapter_keeps_its_glossary_next_to_it(monkeypatch, tmp_path):
    from gui_classes import TranslateView as translate_view_module

    calls = []
    monkeypatch.setattr(translate_view_module, "translate_chapter", lambda *args, **kwargs: calls.append(kwargs["glossary_folder"]))
    view = SimpleNamespace(settings=SETTINGS, raise_if_cancelled=lambda: None, parent_gui=SimpleNamespace(page=SimpleNamespace(client_storage={})))
    process = translate_view_module.TranslateView.process_image_folder

    # A series folder was picked: the glossary is shared by its chapters.
    process(view, str(tmp_path / "Tofu" / "Ch 1"), [], str(tmp_path / "Tofu"), str(tmp_path / "out"))
    # Only a chapter was picked: it gets its own.
    process(view, str(tmp_path / "Ch 1"), [], str(tmp_path / "Ch 1"), str(tmp_path / "out"))

    assert calls == [str(tmp_path / "out" / "Tofu"), str(tmp_path / "out" / "Ch 1")]


def test_ollama_problems_are_explained_before_any_work(monkeypatch):
    import requests

    def not_running(*args, **kwargs):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "get", not_running)
    with pytest.raises(RuntimeError, match="Ollama isn't running"):
        translate.check_engine_ready(SETTINGS)

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: SimpleNamespace(json=lambda: {"models": [{"name": "qwen3:8b"}]}))
    with pytest.raises(RuntimeError, match=r"isn't downloaded yet.*Manage Ollama models"):
        translate.check_engine_ready(SETTINGS)
    translate.check_engine_ready({**SETTINGS, "model": "qwen3:8b"})

    with pytest.raises(RuntimeError, match="not on this computer"):
        translate.check_engine_ready({**SETTINGS, "model": "gemma4:cloud"})


def test_a_missing_api_key_is_explained(monkeypatch):
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        translate.check_engine_ready({**SETTINGS, "engine": "gemini", "model": "gemini-3.8-flash", "api_key": ""})

    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    assert translate.get_api_key("claude", "") == "from-env"
    assert translate.get_api_key("claude", "typed") == "typed"
    assert translate.get_api_key("ollama", "") == ""


def test_the_tab_settings_use_each_translators_own_model_and_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(translate, "utils_load_dotenv", lambda: None)
    monkeypatch.setattr(translate, "get_ram_gb", lambda: 16)
    assert get_translate_settings({})["model"] == translate.PLAMO_8B
    assert get_translate_settings({"translate_from": "spanish"})["model"] == "translategemma:12b"

    storage = {"translate_engine": "chatgpt", "translate_models": {"ollama": "qwen3:8b"}, "translate_api_keys": {"chatgpt": "key"}, "translate_send_page_image": False}
    settings = get_translate_settings(storage)

    assert (settings["model"], settings["api_key"], settings["send_page_image"]) == ("gpt-6-sol", "key", False)


def test_translate_is_the_pipeline_step_right_after_the_download(monkeypatch):
    monkeypatch.setattr(translate, "get_ram_gb", lambda: 16)
    assert PIPELINE_STEPS[:3] == ["Download", "Translate", "Panel-By-Panel"]
    assert get_step_output_directory("/out", "Translate") == os.path.join("/out", "2-translate")
    assert get_step_output_directory("/out", "Images To Video") == os.path.join("/out", "5-images-to-video")
    assert get_settings_review({}, ["Translate"]) == [("Translate", "Japanese to English, Ollama (free, runs on this computer): PLaMo 3 Translate 8B")]


def test_a_model_too_big_for_the_memory_is_flagged_and_unknown_memory_counts_as_fitting(monkeypatch):
    assert translate.is_too_big(6.0, 8)
    assert not translate.is_too_big(6.0, 16)
    assert not translate.is_too_big(9.1, 16)
    assert translate.is_too_big(17.0, 16)
    assert not translate.is_too_big(17.0, None)

    def no_sysconf(name):
        raise AttributeError(name)

    monkeypatch.setattr(os, "sysconf", no_sysconf, raising=False)
    assert translate.get_ram_gb() is None


def test_ollama_says_how_much_of_the_model_is_on_the_graphics_card(monkeypatch):
    import requests

    loaded = {"models": [{"name": "big:latest", "model": "big:latest", "size": 20, "size_vram": 10}]}
    monkeypatch.setattr(requests, "get", lambda url, timeout: SimpleNamespace(json=lambda: loaded))
    assert translate.get_ollama_gpu_share("big") == 0.5
    assert translate.get_ollama_gpu_share("other") is None


def test_a_model_partly_on_the_processor_gets_a_warning_once(monkeypatch, tmp_path):
    details = []
    answers = [{"lines": {"1": "Morning."}, "new_glossary": []}] * 2

    run_translate_chapter(monkeypatch, tmp_path, "Ch 1", answers, gpu_share=0.4, report_progress=lambda **fields: details.append(fields.get("detail")))

    warnings = [detail for detail in details if detail and "40% of it fits on the graphics card" in detail]
    assert len(warnings) == 1


def test_each_line_says_how_many_letters_fit():
    request = translate.get_page_request(["おはよう", "ひっ!"], None, [], letters_that_fit=[40, 6])

    assert request.endswith("This page:\n1 (~40 letters): おはよう\n2 (~6 letters): ひっ!")
    assert "how many letters fit" in translate.get_system_prompt("japanese", "english", True)


def test_a_white_background_the_text_is_written_on_joins_the_text_on_the_art_but_a_small_bubble_keeps_it():
    # Like Shachou ch. 3 page 3: a caption on the art next to text Magi found in a big white panel background, and a small bubble with text spilling out of it.
    on_art, in_background = (100, 100, 200, 300), (150, 100, 400, 300)
    sizes = {7: 500_000, 8: 20_000}

    boxes, bubbles = translate.remove_repeated_boxes([on_art, in_background, (420, 100, 450, 200)], [None, 7, 7], lambda bubble, box: 0.1, sizes.get)
    assert boxes == [(100, 100, 400, 300), (420, 100, 450, 200)]
    assert bubbles == [None, None]

    boxes, bubbles = translate.remove_repeated_boxes([(100, 100, 180, 220), (120, 110, 180, 210)], [None, 8], lambda bubble, box: 0.4, sizes.get)
    assert boxes == [(100, 100, 180, 220)]
    assert bubbles == [8]


def test_long_words_are_split_at_syllables_to_fit():
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    font = ImageFont.truetype(os.path.join(translate.FONTS_FOLDER, translate.FONTS["Bubble Sans"]), 20)
    import pyphen

    hyphenator = pyphen.Pyphen(lang="en_US", left=3, right=3)
    width = draw.textlength("THE PROBLEM", font=font)

    lines = translate.wrap_text(draw, "THE PROBLEM IS INTERPERSONAL RELATIONSHIPS", font, width, hyphenator)

    assert any(line.endswith("-") for line in lines)
    assert all(draw.textlength(line, font=font) <= width for line in lines)
    assert "".join(line.rstrip("-") if line.endswith("-") else line + " " for line in lines).split() == "THE PROBLEM IS INTERPERSONAL RELATIONSHIPS".split()


def test_a_big_sound_effect_on_the_art_is_skipped_but_not_dialogue_or_a_flat_caption():
    artwork = numpy.random.default_rng(0).integers(0, 255, (2000, 1400, 3), dtype=numpy.uint8)
    white = numpy.full((2000, 1400, 3), 255, dtype=numpy.uint8)

    assert translate.is_big_text_on_art(artwork, (100, 100, 700, 400), "ゴゴゴゴ")
    assert not translate.is_big_text_on_art(artwork, (100, 100, 250, 400), "めちゃくちゃ裏目に出てる")
    assert not translate.is_big_text_on_art(white, (100, 100, 700, 400), "ゴゴゴゴ")


def test_lone_marks_on_the_art_and_a_huge_sound_effect_on_a_white_wall_are_left_alone_but_never_dialogue():
    # Like Dragon Tofu ch. 24 (1133 pixels tall): ッ and "…" on the art, ウオオオオオ on a white wall that counts as a light area.
    page = numpy.full((1133, 800, 3), 255, dtype=numpy.uint8)
    bubble = 7

    assert translate.is_left_alone(page, (484, 191, 517, 229), "ッ", None)
    assert translate.is_left_alone(page, (538, 875, 569, 925), "...", None)
    assert translate.is_left_alone(page, (199, 1, 776, 293), "ウオオオオオ", bubble)
    assert not translate.is_left_alone(page, (100, 100, 250, 300), "いちいち気を遣われたら", None)
    # The biggest dialogue in the tests (6% of the page's height), a lone "?" and a short shout in a bubble.
    assert not translate.is_left_alone(page, (202, 761, 483, 1140), "今年のレースは最後までハラハラどきどきでした!", bubble)
    assert not translate.is_left_alone(page, (584, 1048, 625, 1082), "?", bubble)
    assert not translate.is_left_alone(page, (566, 488, 677, 677), "負け犬...だまれ", bubble)


def test_text_on_the_art_stays_in_its_panel():
    panels = [(0, 0, 500, 500), (520, 0, 1000, 500)]

    assert translate.clip_to_panel((400, 100, 560, 200), panels) == (400, 100, 500, 200)
    assert translate.clip_to_panel((400, 600, 560, 700), panels) == (400, 600, 560, 700)


def test_text_on_the_art_never_erases_a_bubble_inside_it(monkeypatch, tmp_path):
    # A big box on the art (e.g. a sound effect) drawn around a speech bubble: the art is painted over, the bubble is put back.
    import magi

    page = Image.fromarray(numpy.random.default_rng(0).integers(0, 150, (600, 800, 3), dtype=numpy.uint8))
    draw = ImageDraw.Draw(page)
    draw.ellipse((300, 200, 500, 400), fill="white", outline="black", width=4)
    for y in range(240, 360, 16):
        draw.rectangle((395, y, 405, y + 11), fill="black")
    folder = tmp_path / "in"
    folder.mkdir()
    page.save(folder / "00.png")
    bubble_before = numpy.asarray(page)[250:350, 350:450].copy()

    monkeypatch.setattr(magi, "get_magi", lambda: FakeMagi([[100, 100, 700, 500], [390, 236, 410, 362]]))
    # Many letters, so it isn't skipped as a big sound effect.
    monkeypatch.setattr(translate, "read_japanese", lambda pages, boxes: [["ゴ" * 1000, "あ"] for _ in pages])
    monkeypatch.setattr(translate, "ask_llm", lambda *args: json.dumps({"lines": {"1": "Rumble", "2": ""}, "new_glossary": []}))
    monkeypatch.setattr(translate, "get_ollama_gpu_share", lambda model: None)
    monkeypatch.setattr(translate, "paint_over_with_lama", lambda page, box: ImageDraw.Draw(page).rectangle(box, fill=(255, 0, 0)))

    translate.translate_chapter(str(folder), ["00.png"], str(tmp_path / "out"), SETTINGS)

    result = numpy.asarray(Image.open(tmp_path / "out" / "00.png").convert("RGB"))
    assert (result[150, 150] == (255, 0, 0)).all()
    assert (result[250:350, 350:450] == bubble_before).all()


def test_dialogue_always_ends_with_punctuation():
    assert translate.end_with_punctuation("Good morning") == "Good morning."
    assert translate.end_with_punctuation("'That person' also said") == "'That person' also said."
    assert translate.end_with_punctuation('"Just do one thing at a time"') == '"Just do one thing at a time."'
    assert translate.end_with_punctuation("Ah!") == "Ah!"
    assert translate.end_with_punctuation("Section Chief Kenichi Ishizumi (37)") == "Section Chief Kenichi Ishizumi (37)"
    assert translate.end_with_punctuation("") == ""


def test_lines_in_speech_bubbles_are_marked_in_the_request():
    request = translate.get_page_request(["挨拶だ", "ゴゴゴ"], None, [], letters_that_fit=[20, 10], in_bubble=[True, False], reminder="Lines 1 were left empty.")

    assert "1 (speech bubble, ~20 letters): 挨拶だ\n2 (~10 letters): ゴゴゴ" in request
    assert request.endswith("Lines 1 were left empty.")


def test_a_bubble_line_left_empty_is_asked_for_again_and_ends_with_a_period(monkeypatch, tmp_path):
    answers = [{"lines": {"1": ""}, "new_glossary": []}, {"lines": {"1": "Greetings"}, "new_glossary": []}, {"lines": {"1": "Morning!"}, "new_glossary": []}]

    output_folder, requests = run_translate_chapter(monkeypatch, tmp_path, "Ch 1", answers)

    saved = json.load(open(os.path.join(output_folder, translate.TRANSLATION_FILE_NAME), encoding="utf-8"))
    assert [page["lines"][0]["text"] for page in saved["pages"]] == ["Greetings.", "Morning!"]
    assert "were left empty" in requests[1]


def test_a_per_minute_limit_is_waited_out_and_a_daily_limit_stops(monkeypatch):
    import httpx
    import openai

    waits = []
    monkeypatch.setattr(translate.time, "sleep", waits.append)
    too_many = openai.RateLimitError("429", response=httpx.Response(429, request=httpx.Request("POST", "https://example.com")), body=None)
    answers = iter([too_many, too_many, '{"lines": {}}'])

    def fake_ask(*args):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(translate, "ask_openai_compatible", fake_ask)
    settings = {**SETTINGS, "engine": "gemini", "model": "gemini-3.6-flash", "api_key": "key"}

    assert translate.ask_llm(settings, "system", "request", None, {}) == '{"lines": {}}'
    assert waits == [20, 40]

    answers = iter([too_many] * 4)
    with pytest.raises(RuntimeError, match="usage limit for gemini-3.6-flash .free accounts have a daily limit"):
        translate.ask_llm(settings, "system", "request", None, {})


def test_gemini_lists_only_the_text_models_the_key_can_use_newest_first(monkeypatch):
    import requests

    asked = []
    models = {"models": [
        {"name": "models/gemini-3.6-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-3.8-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-3.8-flash-tts", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
    ]}

    def fake_get(url, params=None, timeout=None):
        asked.append(url)
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: models)

    monkeypatch.setattr(requests, "get", fake_get)

    assert translate.list_models("gemini", "key") == ["gemini-3.8-flash", "gemini-3.6-flash"]
    assert translate.list_models("gemini", "") == []
    assert len(asked) == 1


def test_a_wrong_key_or_no_connection_gives_an_empty_list(monkeypatch):
    import requests

    def offline(*args, **kwargs):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(requests, "get", offline)

    assert translate.list_models("gemini", "key") == []
    assert translate.list_models("ollama") == []


def test_the_model_is_picked_from_a_list_with_no_box_to_type_in(monkeypatch):
    import flet as ft
    from fake_gui import FakePage
    from gui_classes import SettingsTranslate

    monkeypatch.setattr(ft.Control, "update", lambda self, *args, **kwargs: None)
    monkeypatch.setattr(SettingsTranslate, "list_models", lambda engine, api_key="": ["gemini-3.8-flash", "gemini-3.6-flash"] if api_key else [])
    monkeypatch.setattr(SettingsTranslate, "get_api_key", lambda engine, saved_key: saved_key)
    page = FakePage()
    page.client_storage.set("translate_engine", "gemini")
    settings = SettingsTranslate.SettingsTranslate(page)

    assert not any(isinstance(control, ft.TextField) and control.label == "Model" for control in settings.inner_content)
    # No key yet: only the default model, and a hint.
    assert [option.key for option in settings.model_dropdown.options] == [translate.DEFAULT_MODELS["gemini"]]
    assert "API key" in settings.model_dropdown.helper_text

    settings.save_api_key("key")
    settings.refresh_models()
    assert [option.key for option in settings.model_dropdown.options][-2:] == ["gemini-3.8-flash", "gemini-3.6-flash"]

    settings.handle_model_picked(SimpleNamespace(data="gemini-3.6-flash"))
    assert page.client_storage.get("translate_models") == {"gemini": "gemini-3.6-flash"}


@pytest.mark.parametrize("color", [(255, 255, 255), None])
def test_lettering_never_runs_past_its_area_however_narrow(color):
    font_path = os.path.join(translate.FONTS_FOLDER, translate.FONTS["Bubble Sans"])
    for width in range(30, 200, 10):
        page = Image.new("RGB", (400, 400), (128, 128, 128))
        area = (100, 100, 100 + width, 260)

        translate.fit_and_draw_text(page, [area], "The problem is interpersonal relationships.", font_path, color)

        changed = (numpy.asarray(page) != 128).any(axis=2)
        left, top, right, bottom = area
        changed[top:bottom, left:right] = False
        assert not changed.any(), f"text ran past a {width} px wide area"


def test_ollama_models_are_grouped_by_memory_and_can_be_downloaded_and_removed_from_the_settings(make_gui, monkeypatch):
    import flet as ft
    from gui_classes import Nord, SettingsTranslate

    installed = {translate.PLAMO_8B: 5.3, "llama3:8b": 4.7}
    monkeypatch.setattr(SettingsTranslate, "list_installed_ollama_models", lambda: dict(installed))
    monkeypatch.setattr(SettingsTranslate, "get_ram_gb", lambda: 16)
    monkeypatch.setattr(translate, "get_ram_gb", lambda: 16)
    monkeypatch.setattr(SettingsTranslate, "get_free_disk_gb", lambda: 50)
    gui = make_gui()
    settings = gui.TranslateView.pick_input_output_directories_container.settings_container

    options = {option.key: option for option in settings.model_dropdown.options}
    assert [key for key in options if key.startswith("heading")] == ["heading-8", "heading-16", "heading-32", "heading-other"]
    assert options["heading-16"].disabled and options["heading-16"].text == "FOR 16 GB RAM OR MORE"
    assert "installed" in options[translate.PLAMO_8B].text and not options[translate.PLAMO_8B].disabled
    assert options["translategemma:27b"].disabled
    assert "llama3:8b" in options
    settings.handle_model_picked(SimpleNamespace(data="llama3:8b"))
    assert settings.model_dropdown.helper_text == "Downloaded with Ollama outside Panelyze, so it hasn't been tested here."
    settings.page.client_storage.set("translate_models", {})
    settings.refresh_models()
    # The line under the list says what the picked model (the default) is good and bad at.
    assert settings.model_dropdown.helper_text == translate.OLLAMA_MODELS[translate.PLAMO_8B]["about"]

    # PLaMo only knows Japanese to English.
    settings.handle_model_picked(SimpleNamespace(data=translate.PLAMO_8B))
    settings.handle_source_language_change(SimpleNamespace(data="spanish"))
    assert "ollama" not in settings.page.client_storage.get("translate_models")
    plamo = next(option for option in settings.model_dropdown.options if option.key == translate.PLAMO_8B)
    assert plamo.disabled and "Japanese to English only" in plamo.text
    # A picked PLaMo is dropped for other languages. The default follows the languages until a model is picked, and PLaMo goes to the bottom of its section.
    assert settings.model_dropdown.value == "translategemma:12b"
    keys = [option.key for option in settings.model_dropdown.options]
    assert keys[keys.index("heading-16") + 1 : keys.index("heading-32")] == ["translategemma:12b", "ministral-3:8b", translate.PLAMO_8B]
    assert plamo.content.color == Nord.TEXT_MUTED

    settings.refresh_manage_models()
    texts = [control.value for control in get_all_controls(settings.manage_models_list) if isinstance(control, ft.Text)]
    # The model picked in the Model list (here the default for Spanish) is highlighted.
    selected = [control for control in get_all_controls(settings.manage_models_list) if isinstance(control, ft.Text) and control.color == Nord.ACCENT]
    assert [control.value for control in selected] == ["TranslateGemma 12B · 8.1 GB on disk"]
    assert "Downloaded · selected" not in texts and "Not downloaded · selected" in texts
    assert "For 8 GB RAM or more" in texts and "Other downloaded models" in texts and "50 GB free" in texts[0] and "show up here too" in texts[0]

    # Uninstall asks to be sure first (Cancel keeps it), then removes it.
    removed = []
    monkeypatch.setattr(SettingsTranslate, "delete_ollama_model", lambda model: removed.append(model) or installed.pop(model))
    settings.ask_to_uninstall("llama3:8b")
    dialog = settings.page.dialog
    assert dialog.title.value == "Remove llama3:8b?" and dialog.content.value == "This frees 4.7 GB of disk space. Using it again means downloading it again."
    cancel, remove = dialog.actions
    cancel.on_click(None)
    assert removed == [] and settings.page.dialog is None
    settings.ask_to_uninstall("llama3:8b")
    settings.page.dialog.actions[1].on_click(None)
    assert removed == ["llama3:8b"] and settings.page.dialog is None
    assert gui.terminal_output.progress_panel.title == "Removed llama3:8b. 4.7 GB of disk space freed."
    assert not gui.is_job_running

    # Downloading shows its progress in the Status view.
    seen = []

    def fake_download(model, report, is_cancelled):
        report(4.0, 8.1)
        seen.append((gui.terminal_output.progress_panel.pages_done, gui.terminal_output.progress_panel.pages_total, gui.terminal_output.progress_panel.unit))
        installed[model] = 8.1
        return True

    monkeypatch.setattr(SettingsTranslate, "download_ollama_model", fake_download)
    settings.download_model("translategemma:12b")
    assert seen == [(4.0, 8.1, "GB")]
    assert "Downloaded TranslateGemma 12B" in gui.terminal_output.progress_panel.title
    assert "installed" in next(option.text for option in settings.model_dropdown.options if option.key == "translategemma:12b")


def test_the_model_manager_still_works_after_switching_translators_and_says_when_ollama_isnt_running(make_gui, monkeypatch):
    import flet as ft
    from gui_classes import SettingsTranslate

    gui = make_gui()
    settings = gui.TranslateView.pick_input_output_directories_container.settings_container
    tile = settings.manage_models

    settings.handle_engine_change(SimpleNamespace(data="gemini"))
    assert settings.manage_models is tile and not tile.visible and tile in settings.inner_content
    settings.handle_engine_change(SimpleNamespace(data="ollama"))
    assert tile.visible

    monkeypatch.setattr(SettingsTranslate, "list_installed_ollama_models", lambda: None)
    settings.refresh_manage_models()
    assert "Ollama isn't running" in settings.manage_models_list.controls[0].value

    # While a download runs: a Cancel button at the top, the other buttons off.
    monkeypatch.setattr(SettingsTranslate, "list_installed_ollama_models", lambda: {})
    seen = {}

    def fake_download(model, report, is_cancelled):
        buttons = [control for control in get_all_controls(settings.manage_models_list) if isinstance(control, ft.TextButton)]
        seen["cancel"] = buttons[0].text
        seen["others_off"] = all(button.disabled for button in buttons[1:])
        buttons[0].on_click(None)
        return not is_cancelled()

    monkeypatch.setattr(SettingsTranslate, "download_ollama_model", fake_download)
    settings.download_model("translategemma:4b")
    assert seen == {"cancel": "Cancel the download", "others_off": True}
    assert "cancelled" in gui.terminal_output.progress_panel.title
    assert not any(isinstance(control, ft.TextButton) and control.text == "Cancel the download" for control in get_all_controls(settings.manage_models_list))


@pytest.mark.parametrize("source_language, threshold", [("japanese", 0.1), ("spanish", 0.3)])
def test_magi_looks_harder_for_japanese_text_than_for_english_or_spanish(monkeypatch, tmp_path, source_language, threshold):
    import magi

    fake_magi = FakeMagi([[160.2, 200, 200, 260]])
    monkeypatch.setattr(magi, "get_magi", lambda: fake_magi)
    monkeypatch.setattr(translate, "read_japanese", lambda pages, boxes: [["おはよう"] for _ in pages])
    monkeypatch.setattr(translate, "read_latin", lambda magi, pages, boxes: [["Hola"] for _ in pages])
    monkeypatch.setattr(translate, "ask_llm", lambda *args: json.dumps({"lines": {"1": "Hi."}, "new_glossary": []}))
    folder = str(tmp_path / "in")

    translate.translate_chapter(folder, make_chapter(folder), str(tmp_path / "out"), {**SETTINGS, "source_language": source_language})

    assert fake_magi.threshold == threshold


def test_spaces_go_between_japanese_characters_but_stay_between_english_words():
    assert translate.clean_japanese("白 優奈 (主人公の妹)") == "白優奈(主人公の妹)"
    assert translate.clean_japanese("ＹＵＩＣＨＩ'S ROOM ") == "YUICHI'S ROOM"


@pytest.mark.parametrize("ram_gb, source_language, model", [
    (16, "japanese", "hf.co/pfnet/plamo-3-translate-8b-GGUF:Q4_K_M"),
    (16, "spanish", "translategemma:12b"),
    (64, "english", "translategemma:12b"),
    (8, "japanese", "hf.co/pfnet/plamo-3-translate-2b-GGUF:Q4_K_M"),
    (8, "spanish", "qwen3-vl:4b-instruct"),
    (None, "japanese", "hf.co/pfnet/plamo-3-translate-8b-GGUF:Q4_K_M"),
])
def test_the_default_ollama_model_is_the_best_that_fits_the_computer_and_knows_the_languages(monkeypatch, ram_gb, source_language, model):
    monkeypatch.setattr(translate, "get_ram_gb", lambda: ram_gb)
    assert translate.get_default_model("ollama", source_language, "english") == model
    assert translate.get_default_model("claude", source_language, "english") == "claude-opus-5-5"


def test_the_default_skips_a_model_without_room_to_download_unless_its_already_downloaded(monkeypatch):
    monkeypatch.setattr(translate, "get_ram_gb", lambda: 16)
    # 6 GB free: no room for TranslateGemma 12B (8.1 + 2 GB) or Ministral 8B (6.0 + 2 GB), so the best 8 GB pick.
    monkeypatch.setattr(translate, "get_free_disk_gb", lambda: 6)
    assert translate.get_default_model("ollama", "spanish", "english") == "qwen3-vl:4b-instruct"
    monkeypatch.setattr(translate, "list_installed_ollama_models", lambda: {"translategemma:12b": 8.1})
    assert translate.get_default_model("ollama", "spanish", "english") == "translategemma:12b"


def test_translate_downloads_a_missing_model_first_and_cancel_stops_it(make_gui, monkeypatch):
    from gui_classes import TranslateView

    gui = make_gui()
    view = gui.TranslateView
    view.settings = {"engine": "ollama", "model": "translategemma:12b"}
    downloads, seen = [], []

    def fake_download(model, report, is_cancelled):
        report(2.0, 8.1)
        panel = gui.terminal_output.progress_panel
        seen.append((panel.pages_done, panel.pages_total, panel.unit, panel.detail, view.get_cancel_message()))
        downloads.append(model)
        return not is_cancelled()

    monkeypatch.setattr(TranslateView, "download_ollama_model", fake_download)
    monkeypatch.setattr(TranslateView, "list_installed_ollama_models", lambda: {})
    view.download_model_if_needed()
    assert downloads == ["translategemma:12b"]
    assert seen == [(2.0, 8.1, "GB", "Downloading TranslateGemma 12B before translating", "Cancelling the download...")]
    assert view.get_cancel_message() == view.cancel_message

    # Cancel stops it, with a message.
    view.cancel_event.set()
    with pytest.raises(DownloadCancelled, match="Cancelled the download of TranslateGemma 12B"):
        view.download_model_if_needed()
    view.cancel_event.clear()

    # Already downloaded, or another translator: nothing to download.
    monkeypatch.setattr(TranslateView, "list_installed_ollama_models", lambda: {"translategemma:12b": 8.1})
    view.download_model_if_needed()
    view.settings = {"engine": "gemini", "model": "gemini-3.8-flash"}
    view.download_model_if_needed()
    assert len(downloads) == 2


def test_removing_a_suggested_model_names_it_like_the_list_does(make_gui, monkeypatch):
    from gui_classes import SettingsTranslate

    monkeypatch.setattr(SettingsTranslate, "list_installed_ollama_models", lambda: {translate.PLAMO_8B: 5.3})
    monkeypatch.setattr(SettingsTranslate, "delete_ollama_model", lambda model: None)
    gui = make_gui()
    settings = gui.TranslateView.pick_input_output_directories_container.settings_container

    settings.ask_to_uninstall(translate.PLAMO_8B)
    assert settings.page.dialog.title.value == "Remove PLaMo 3 Translate 8B?"
    settings.page.dialog.actions[1].on_click(None)

    assert gui.terminal_output.progress_panel.title == "Removed PLaMo 3 Translate 8B. 5.3 GB of disk space freed."
