import contextlib
import functools
import os
import subprocess
import threading
from typing import cast

# Anything the Mac GPU can't do runs on the CPU instead of failing. It has to be set before "torch" is imported.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import json
from PIL import Image
import torch
import numpy
from utils import (
    PANEL_TEXT_FILE_NAME,
    READING_DIRECTION_FILE_NAME,
    get_panels_folder,
    remove_old_panels,
    get_relative_output_path,
    list_images,
    paths_overlap,
    time_it,
)
import shutil
import tempfile
from copy_panels_to_one_level_directory import copy_panels_to_one_level_directory
from janai import get_page_height_info


# The exact version of Magi v2 on Hugging Face. Its code is copied into "magi_model/" at this version, and the full weights are downloaded at this version, so future changes to it can't silently change or break the output.
MAGI_MODEL_REVISION = "fbc890fec52977142e8ee00bfe26e9458b65517c"
# Where the Magi model comes from, shown when it's downloaded (and when that fails).
MAGI_MODEL_PAGE_URL = "https://huggingface.co/ragavsachdeva/magiv2"
MAGI_MODEL_DIRECTORY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "magi_model"
)
# Only the parts of Magi that find panels (87 MB instead of 2 GB). Built from the full model by "build_panels_model_file".
PANELS_MODEL_FILE = os.path.join(MAGI_MODEL_DIRECTORY, "panels_fp16.safetensors")
PANELS_MODEL_PARTS = (
    "detection_transformer.",
    "bbox_predictor.",
    "class_labels_classifier.",
)
# How sure Magi has to be that something is a panel (the same value Magi uses itself).
PANEL_DETECTION_THRESHOLD = 0.2
# How sure Magi has to be that something is text or a character before a panel grows to fit it.
TEXT_AND_CHARACTER_DETECTION_THRESHOLD = 0.3
# The most of another panel a panel may take when it grows to fit a speech bubble or character sticking out of it. Across 25 test chapters, 30% never pulled in another panel's dialogue, while 70% did 17 times. 40% let Japanese captions in the page margin swallow panels again, and showed some characters twice (see "benchmarks/panel-cropping.md").
PANEL_GROWTH_LIMIT = 0.3
# Room left around a speech bubble a panel grows to fit, so the bubble's outline isn't cut.
TEXT_MARGIN = 12
# Text split between two panels is only treated as dialogue to always show whole if at least this much of it is inside them. Captions in the page margin are mostly outside.
SPLIT_TEXT_MIN_INSIDE = 0.5
# Webtoons are too tall for Magi, which shrinks every image to at most 1333 px tall. So it looks at a window 2 screens tall (2x the strip's width), moving down 1 screen at a time: every panel up to 1 screen tall is whole in some window.
WEBTOON_WINDOW_SCREENS = 2
# How much smaller the strip is when looking for art Magi missed (see "get_webtoon_safety_net").
WEBTOON_DETAIL_SCALE = 4
# A chapter whose images are mostly more than this many times taller than wide is split as a webtoon, whatever reading direction was picked.
WEBTOON_IMAGE_HEIGHT_RATIO = 2.5
# On a 4-koma page, the narrowest panel in a strip is at least this share of the widest one's width (see "looks_like_four_koma_page").
FOUR_KOMA_MIN_WIDTH_SHARE = 0.8
# A phone screen is about 19.5 x 9, so about 2.17 times taller than wide.
PHONE_SCREEN_HEIGHT_RATIO = 2.17
# Panels taller than this many phone screens are split into screen-sized pieces (see "split_tall_panel"). Across 10 webtoon chapters, 17 of 1,178 panels were; no manga panel comes close.
TALL_PANEL_SCREENS = 2
# A panel whose lightest and darkest pixels (ignoring the 1% at each end) are closer than this, out of 255, is blank (see "remove_junk_panels").
BLANK_PANEL_SPREAD = 12
# How different (out of 255, on average) two faint images can be and still be copies of a watermark. Watermark copies were under 1 apart; falling petals in "Under the Oak Tree" were never closer than 10.
WATERMARK_MAX_DIFFERENCE = 8
# A webtoon panel is a repeat if less than this share of it is detailed art no other panel shows (see "remove_repeated_webtoon_panels").
REPEATED_PANEL_MAX_NEW_DETAIL = 0.05
# Only slivers narrower than this share of the strip can be repeats. In Lookism, full-size panels inside a bigger safety-net slice were being dropped.
REPEATED_PANEL_MAX_WIDTH = 0.3
# A character only counts as a panel's own if at least this much of it is inside the panel.
CHARACTER_MIN_SHARE = 0.3
# How many images Magi looks at in one go when finding the text, and how many lines of text it reads in one go.
# One image at a time is fastest: images looked at together are all padded to the size of the biggest one, and panels (and some pages, like double-page spreads) are all different sizes. On 50 panels: 60s one at a time vs 163s eight at a time.
FIND_TEXT_BATCH_SIZE = 1
# Lines read together all wait for the longest one to finish, so smaller groups are faster. On 110 lines: about 60s for 4 to 8 at a time vs 94s for 32.
READ_TEXT_BATCH_SIZE = 8


_shared_magi = None


def get_magi():
    """
    The one Magi model the whole app shares (Panel-By-Panel, Images To Video and the Pipeline). It's big and slow to load, so it's only loaded the first time it's needed.
    """
    global _shared_magi

    if _shared_magi is None:
        print("Loading the Magi AI Model (this can take a minute the first time)...")
        _shared_magi = Magi()

    return _shared_magi


_device_choice_lock = threading.Lock()


def get_device_choice():
    """
    Where the AI models run on this computer, a sentence saying so (shown in Settings and printed once), and the names of the devices in it, as (device, sentence, device_names). The device is the Mac GPU ("mps"), an NVIDIA or AMD GPU (PyTorch calls both "cuda"), or else the CPU. It's only worked out once: trying a GPU sets it up, which takes some of its memory for the whole run. The Settings page and a job can ask at the same time, so the second one waits for the first one's answer.
    """
    with _device_choice_lock:
        return find_device_choice()


@functools.cache
def find_device_choice():
    device = "cpu"
    working_gpus = []
    skipped_gpus = []
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        # A PC can show more than one GPU, like a graphics card and the CPU's built-in graphics. Use the most powerful one that works: AMD's PyTorch only runs on the chips it was installed for. Compute units say which is most powerful (memory doesn't: built-in graphics reports a share of the computer's memory).
        gpus = range(torch.cuda.device_count())
        working_gpus = [index for index in gpus if gpu_works(index)]
        skipped_gpus = [
            torch.cuda.get_device_name(index)
            for index in gpus
            if index not in working_gpus
        ]
        if working_gpus:
            device = f"cuda:{max(working_gpus, key=lambda index: torch.cuda.get_device_properties(index).multi_processor_count)}"

    sentence = f"The AI models run on the {get_device_name(device)}"
    if len(working_gpus) > 1:
        sentence += f" (the most powerful of the {len(working_gpus)} GPUs)"
    if device == "cpu":
        sentence += ", since there's no GPU they can run on (slower)"
    sentence += "."
    if skipped_gpus:
        sentence += f" Not used: the {', the '.join(skipped_gpus)} (PyTorch can't run on {'it' if len(skipped_gpus) == 1 else 'them'})."
    print(sentence)
    return device, sentence, [get_device_name(device), *skipped_gpus]


def get_device():
    return get_device_choice()[0]


def get_device_name(device):
    """
    The name of "device" ("cuda:1", "mps", "cpu" or a torch.device), as the computer calls it: "AMD Radeon RX 6700 XT", "NVIDIA GeForce RTX 4070", "Apple M1" or "CPU".
    """
    device = torch.device(device)
    if device.type == "cuda":
        return torch.cuda.get_device_name(device.index or 0)
    if device.type == "mps":
        return get_mac_chip_name()
    return "CPU"


@functools.cache
def get_mac_chip_name():
    """
    "Apple M1", "Apple M2 Pro", ...: a Mac's GPU is part of its chip, and PyTorch can't tell its name, so macOS is asked. "Mac GPU" if it can't say, or on an Intel Mac (there it's the Intel CPU's name, not the GPU's).
    """
    try:
        chip_name = subprocess.run(
            ["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "Mac GPU"
    return chip_name if chip_name.startswith("Apple") else "Mac GPU"


def report_device(model):
    """
    Shows in the Status view where "model" runs (see "ProgressPanel.get_device_text").
    """
    from gui_classes.ProgressPanel import report_progress

    report_progress(device=get_device_name(model.device))


def gpu_works(index):
    """
    Whether PyTorch can run on GPU "index". On a chip it has no code for, even adding 1 fails ("invalid kernel file").
    """
    try:
        (torch.ones(1, device=f"cuda:{index}") + 1).item()
        return True
    except RuntimeError:
        return False


# Panel-By-Panel's stages, shown in the Status view (see "ProgressPanel.get_stages_text"). The text stages are Images To Video's too (see VideoCreatorFromImages.py).
FINDING_PANELS_STAGE = "Finding the panels"
SAVING_PANELS_STAGE = "Saving the panels"
FINDING_TEXT_STAGE = "Finding the text"
READING_TEXT_STAGE = "Reading the text"


def load_magi_config(config_file_name):
    from magi_model.configuration_magiv2 import Magiv2Config

    return Magiv2Config.from_json_file(
        os.path.join(MAGI_MODEL_DIRECTORY, config_file_name)
    )


def load_full_magi_model():
    """
    The whole Magi model (2.06 GB), including the part that reads the text. Downloaded from Hugging Face the first time.
    """
    from huggingface_hub import try_to_load_from_cache
    from magi_model.modelling_magiv2 import Magiv2Model

    from gui_classes.ProgressPanel import DOWNLOAD_ONCE_DETAIL, show_extra_stage
    from storage import MAGI_DOWNLOAD_BYTES, get_hugging_face_cache
    from utils import check_free_space, report_folder_download

    is_downloaded = isinstance(
        try_to_load_from_cache(
            "ragavsachdeva/magiv2",
            "pytorch_model.bin",
            revision=MAGI_MODEL_REVISION,
            cache_dir=get_hugging_face_cache(),
        ),
        str,
    )
    # Hugging Face downloads it with its own code, so its progress in the Status view comes from watching its folder grow.
    magi_cache_folder = os.path.join(
        get_hugging_face_cache(), "models--ragavsachdeva--magiv2"
    )
    if not is_downloaded:
        check_free_space(
            get_hugging_face_cache(), MAGI_DOWNLOAD_BYTES, "the Magi model"
        )
    try:
        with (
            contextlib.nullcontext()
            if is_downloaded
            else show_extra_stage(
                "Downloading Magi (full model, one time only)", DOWNLOAD_ONCE_DETAIL
            ),
            report_folder_download(
                "the Magi model", magi_cache_folder, MAGI_DOWNLOAD_BYTES
            ),
        ):
            # "cast": with some transformers versions, the type checker thinks it can return a tuple (it only does with "output_loading_info").
            model = cast(
                Magiv2Model,
                Magiv2Model.from_pretrained(
                    "ragavsachdeva/magiv2",
                    revision=MAGI_MODEL_REVISION,
                    config=load_magi_config("full_config.json"),
                ),
            )
    except OSError as error:
        raise OSError(
            f"Couldn't download the Magi AI model (check your internet connection): {error}. It comes from {MAGI_MODEL_PAGE_URL}"
        ) from error
    return model.eval()


def build_panels_model_file():
    """
    Save just the panel-finding parts of the full Magi model into "PANELS_MODEL_FILE" (87 MB, half precision). The Mac app build bundles this file. When running from source, it's built automatically the first time it's needed.
    """
    from safetensors.torch import save_file

    print(
        f"Building the small panels-only Magi model (one time only, from the full model at {MAGI_MODEL_PAGE_URL})."
    )
    full_model = load_full_magi_model()
    panels_model_weights = {
        name: (weights.half() if weights.is_floating_point() else weights).contiguous()
        for name, weights in full_model.state_dict().items()
        if name.startswith(PANELS_MODEL_PARTS)
    }
    # Write to a temporary file first, so quitting halfway can't leave a broken model file behind.
    save_file(panels_model_weights, PANELS_MODEL_FILE + ".tmp")
    os.replace(PANELS_MODEL_FILE + ".tmp", PANELS_MODEL_FILE)


def load_panels_magi_model():
    from safetensors.torch import load_file
    from magi_model.modelling_magiv2 import Magiv2Model

    if not os.path.exists(PANELS_MODEL_FILE):
        build_panels_model_file()

    model = Magiv2Model(load_magi_config("panels_config.json"))
    weights = {
        name: weights.float() for name, weights in load_file(PANELS_MODEL_FILE).items()
    }
    # "strict=False" because the small model leaves out the parts Panel-By-Panel doesn't use (text reading, characters, etc.). But every panel-finding part must be there, or the panels would be garbage.
    missing_weights = model.load_state_dict(weights, strict=False).missing_keys
    missing_panel_weights = [
        name for name in missing_weights if name.startswith(PANELS_MODEL_PARTS)
    ]
    if missing_panel_weights:
        raise RuntimeError(
            f"The panels model file is incomplete ({len(missing_panel_weights)} parts missing). Delete {PANELS_MODEL_FILE} and try again to rebuild it."
        )

    return model.eval()


def get_mirrored_boxes(boxes, page_width):
    """
    Flip boxes ([x1, y1, x2, y2]) horizontally, as if the page were seen in a mirror.
    """
    return [[page_width - x2, y1, page_width - x1, y2] for x1, y1, x2, y2 in boxes]


def reorder_page_result_left_to_right(page_result, page_width):
    """
    Magi always puts panels and text in manga reading order (right to left). For comics (left to right), sort the mirrored boxes with Magi's own sorting, so its rules (rows, overlapping panels, etc.) work the same way, just from the other side.
    """
    from magi_model.utils import sort_panels, sort_text_boxes_in_reading_order

    page_result = dict(page_result)
    panels = list(page_result.get("panels") or [])

    if panels:
        panel_order = sort_panels(get_mirrored_boxes(panels, page_width))
        panels = [panels[index] for index in panel_order]
        page_result["panels"] = panels

    texts = list(page_result.get("texts") or [])

    if texts:
        text_order = sort_text_boxes_in_reading_order(
            get_mirrored_boxes(texts, page_width),
            get_mirrored_boxes(panels, page_width),
        )
        # The text, what it says and whether it's dialogue all have to stay together.
        for key in ("texts", "ocr", "is_essential_text"):
            values = page_result.get(key)
            if values is not None and len(values) == len(texts):
                page_result[key] = [values[index] for index in text_order]

    return page_result


def get_panel_crop_box(bbox, page):
    """
    The part of the page a panel is cut from: the panel's box in whole pixels, kept inside the page. "None" if nothing is left of it (the panel is then skipped).
    """
    page_height, page_width = page.shape[:2]
    x_min, y_min, x_max, y_max = map(int, bbox)

    x_min = max(0, min(x_min, page_width))
    y_min = max(0, min(y_min, page_height))
    x_max = max(0, min(x_max, page_width))
    y_max = max(0, min(y_max, page_height))

    if x_max <= x_min or y_max <= y_min:
        return None

    return [x_min, y_min, x_max, y_max]


def get_overlap_area(box, other_box):
    width = min(box[2], other_box[2]) - max(box[0], other_box[0])
    height = min(box[3], other_box[3]) - max(box[1], other_box[1])
    return max(0, width) * max(0, height)


def get_box_area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def get_panel_reading_order(panels, reading_direction):
    """
    The indices of "panels" (in manga order, as Magi sorts them) in the order they're read in "reading_direction".
    """
    from magi_model.utils import sort_panels

    if reading_direction == "4koma":
        return get_four_koma_panel_order(panels)

    if reading_direction == "ltr" and panels:
        # Mirrored, like "reorder_page_result_left_to_right". Any width works, since only the order matters.
        return list(
            sort_panels(get_mirrored_boxes(panels, max(panel[2] for panel in panels)))
        )

    return list(range(len(panels)))


def get_grown_panels(
    panels,
    texts,
    characters,
    character_growth_limit: float | None = PANEL_GROWTH_LIMIT,
    reading_direction="rtl",
):
    """
    Magi's panel boxes follow the panel borders, so speech bubbles and characters drawn over a border get cut. Each panel grows to fit the text and characters that are its own (they overlap it the most) but stick out of it.
    It doesn't grow when that would take more than "PANEL_GROWTH_LIMIT" of another panel, so a crop never pulls in the next panel and its dialogue. This also skips Japanese captions in the page margin, which Magi finds as text too.
    Dialogue split between panels is always shown whole in one of them, though, because the reader needs the words (see "grow_to_fit").
    "character_growth_limit=None" always fits the whole character (the "Show full characters" setting).
    """
    grown_panels = [list(panel) for panel in panels]
    position_in_reading_order = {
        index: position
        for position, index in enumerate(
            get_panel_reading_order(panels, reading_direction)
        )
    }

    def get_share_taken_of_another_panel(index, grown_panel):
        """
        The most of any other panel that growing panel "index" to "grown_panel" would take (0 to 1).
        """
        return max(
            (
                (
                    get_overlap_area(grown_panel, other)
                    - get_overlap_area(grown_panels[index], other)
                )
                / get_box_area(other)
                for other_index, other in enumerate(panels)
                if other_index != index and get_box_area(other) > 0
            ),
            default=0,
        )

    def grow_to_fit(box, margin, min_share, limit, always_show_whole=False):
        overlaps = [get_overlap_area(panel, box) for panel in grown_panels]
        box_area = get_box_area(box)

        # Not in any panel, mostly outside of them, or already all inside one.
        if (
            not overlaps
            or max(overlaps) == 0
            or max(overlaps) < min_share * box_area
            or max(overlaps) >= 0.999 * box_area
        ):
            return

        # The panels it's in, in reading order.
        panels_it_is_in = sorted(
            (index for index, overlap in enumerate(overlaps) if overlap > 0),
            key=lambda index: position_in_reading_order[index],
        )
        # Its own panel (the one it overlaps the most) first. Text can also go in the other panels it's in.
        indices = sorted(panels_it_is_in, key=lambda index: -overlaps[index])
        if not always_show_whole:
            indices = indices[:1]

        grown = {
            index: [
                min(grown_panels[index][0], box[0] - margin),
                min(grown_panels[index][1], box[1] - margin),
                max(grown_panels[index][2], box[2] + margin),
                max(grown_panels[index][3], box[3] + margin),
            ]
            for index in indices
        }
        share_taken = {
            index: get_share_taken_of_another_panel(index, grown[index])
            for index in indices
        }

        if limit is None or share_taken[indices[0]] <= limit:
            grown_panels[indices[0]] = grown[indices[0]]
            return

        # A bubble split between two panels that its own panel can't fit within the limit: the first of the two in reading order shows it anyway, so the reader sees the whole line the first time they reach it. Text mostly outside the panels (like a caption in the page margin), or running across 3 or more panels (like a chapter title down the side of the page), isn't dialogue the reader needs.
        if (
            always_show_whole
            and len(panels_it_is_in) == 2
            and sum(overlaps) >= SPLIT_TEXT_MIN_INSIDE * box_area
        ):
            grown_panels[panels_it_is_in[0]] = grown[panels_it_is_in[0]]
            return

        # Otherwise, another panel it's in can fit it, within the limit.
        for index in indices[1:]:
            if share_taken[index] <= limit:
                grown_panels[index] = grown[index]
                return

    for text in texts:
        grow_to_fit(text, TEXT_MARGIN, 0, PANEL_GROWTH_LIMIT, always_show_whole=True)

    for character in characters:
        grow_to_fit(character, 0, CHARACTER_MIN_SHARE, character_growth_limit)

    return grown_panels


def get_distance_between_centers(box, other_box):
    return (
        ((box[0] + box[2]) - (other_box[0] + other_box[2])) ** 2
        + ((box[1] + box[3]) - (other_box[1] + other_box[3])) ** 2
    ) ** 0.5


def get_dialogue_for_each_panel(page_result, panel_boxes):
    """
    The dialogue Magi read on a whole page, split up by the panel each line is in: the panel its text box overlaps the most, or the closest panel if it's in none (e.g. a bubble in the gutter between panels). The lines stay in the page's reading order.
    """
    dialogue_for_each_panel = [[] for _ in panel_boxes]

    if not panel_boxes:
        return dialogue_for_each_panel

    for text_box, text, is_dialogue in zip(
        page_result["texts"], page_result["ocr"], page_result["is_essential_text"]
    ):
        if is_dialogue:
            dialogue_for_each_panel[
                get_panel_index_of_text(text_box, panel_boxes)
            ].append(text)

    return dialogue_for_each_panel


def get_panel_index_of_text(text_box, panel_boxes):
    """
    The panel a text box belongs to: the one it overlaps the most, or the closest one if it's in none.
    """
    text_box = [float(value) for value in text_box]
    overlaps = [get_overlap_area(text_box, panel_box) for panel_box in panel_boxes]

    if max(overlaps) > 0:
        return overlaps.index(max(overlaps))

    return min(
        range(len(panel_boxes)),
        key=lambda index: get_distance_between_centers(text_box, panel_boxes[index]),
    )


def get_four_koma_panel_order(panels):
    """
    4-koma pages are strips of panels stacked top to bottom, read one strip (column) at a time from the right.
    """
    columns = get_four_koma_columns(panels)
    return [
        index
        for column in columns
        for index in sorted(column, key=lambda index: panels[index][1])
    ]


def get_four_koma_columns(panels):
    """
    The indices of "panels" grouped into columns, from the right. Panels that share most of their width are in the same column.
    """
    columns = []

    for index in sorted(
        range(len(panels)), key=lambda index: -(panels[index][0] + panels[index][2])
    ):
        panel = panels[index]
        for column in columns:
            first_panel = panels[column[0]]
            shared_width = min(panel[2], first_panel[2]) - max(panel[0], first_panel[0])
            if shared_width > 0.5 * min(
                panel[2] - panel[0], first_panel[2] - first_panel[0]
            ):
                column.append(index)
                break
        else:
            columns.append([index])

    return columns


def looks_like_four_koma_page(panels):
    """
    Whether a page is 2 strips of 4 panels each, all about the same width, like a 4-koma page. None for a page of just one strip: it's read top to bottom either way, and a manga page of stacked full-width panels looks the same. (A normal manga grid, like 2 columns of 3, isn't 4-koma.)
    """
    columns = get_four_koma_columns(panels)
    if len(columns) == 1:
        return None
    if len(columns) != 2:
        return False

    for column in columns:
        widths = [panels[index][2] - panels[index][0] for index in column]
        if len(column) != 4 or min(widths) < FOUR_KOMA_MIN_WIDTH_SHARE * max(widths):
            return False

    return True


def looks_like_four_koma(per_page_panels):
    """
    Whether most of the chapter's pages (not counting pages of one strip, see "looks_like_four_koma_page") look like 4-koma pages.
    """
    answers = [
        looks_like_four_koma_page(panels) for panels in per_page_panels if panels
    ]
    answers = [answer for answer in answers if answer is not None]
    return bool(answers) and sum(answers) > len(answers) / 2


def get_saved_reading_direction(reading_direction, chapter_directory):
    """
    The reading direction to use for a chapter. A direction picked in the app always wins. For "auto" (Automatic), it's the one the MangaDex download saved next to the images (see "READING_DIRECTION_FILE_NAME"), or still "auto" if there isn't one, to be guessed from the images.
    """
    if reading_direction and reading_direction != "auto":
        return reading_direction

    path = (
        os.path.join(chapter_directory, READING_DIRECTION_FILE_NAME)
        if chapter_directory
        else ""
    )
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as file:
            saved_direction = file.read().strip()
        if saved_direction in ("rtl", "ltr", "4koma", "webtoon"):
            print(f"Reading direction from the MangaDex download: {saved_direction}")
            return saved_direction

    return "auto"


def get_reading_direction_from_panels(per_page_results, nothing_saved=True):
    """
    For "auto" in manga order (saved by the download, or nothing saved): 4-koma if the pages look like 4-koma strips, otherwise manga order. MangaDex doesn't tag every 4-koma, so a saved "rtl" is checked too.
    """
    if looks_like_four_koma(
        [page_result.get("panels") or [] for page_result in per_page_results]
    ):
        print(
            "These pages look like 4-koma strips, so they're read as 4-koma (right strip first)."
        )
        return "4koma"

    if nothing_saved:
        print(
            "No reading direction found, using manga order (right to left). "
            "Pick 'Left to right (Comics)' if this is a Western comic."
        )
    return "rtl"


def get_automatic_reading_direction(reading_direction, chapter_directory):
    """
    "(reading_direction, is_automatic, nothing_saved)" for a chapter: the direction to find the panels with ("auto" becomes manga order until "get_reading_direction_from_panels" decides), whether it was "Automatic", and whether the download saved nothing.
    """
    is_automatic = reading_direction in (None, "", "auto")
    reading_direction = get_saved_reading_direction(
        reading_direction, chapter_directory
    )
    nothing_saved = reading_direction == "auto"
    return ("rtl" if nothing_saved else reading_direction), is_automatic, nothing_saved


def reorder_page_result_four_koma(page_result):
    """
    Put the panels in 4-koma order (see "get_four_koma_panel_order"), and the text in the order of the panels it's in.
    """
    page_result = dict(page_result)
    panels = list(page_result.get("panels") or [])

    if not panels:
        return page_result

    panel_order = get_four_koma_panel_order(panels)
    page_result["panels"] = [panels[index] for index in panel_order]
    texts = list(page_result.get("texts") or [])

    if texts:
        position_of_panel = {
            panel_index: position for position, panel_index in enumerate(panel_order)
        }
        # "sorted" keeps Magi's own order for text in the same panel.
        text_order = sorted(
            range(len(texts)),
            key=lambda index: position_of_panel[
                get_panel_index_of_text(texts[index], panels)
            ],
        )
        # The text, what it says and whether it's dialogue all have to stay together.
        for key in ("texts", "ocr", "is_essential_text"):
            values = page_result.get(key)
            if values is not None and len(values) == len(texts):
                page_result[key] = [values[index] for index in text_order]

    return page_result


def join_webtoon_strip(chapter_pages):
    """
    A webtoon chapter as one long image: its images stacked top to bottom, all at the most common width. Panels split between two image files become whole again.
    """
    widths = [page.shape[1] for page in chapter_pages]
    width = max(set(widths), key=widths.count)
    parts = [
        page
        if page.shape[1] == width
        else numpy.array(
            Image.fromarray(page).resize(
                (width, round(page.shape[0] * width / page.shape[1]))
            )
        )
        for page in chapter_pages
    ]
    return numpy.concatenate(parts)


def get_webtoon_safety_net(strip, panels):
    """
    Webtoon art Magi missed (soft-edged panels, sound effects between panels, narration on black) so none of it is lost. Only "detail" counts as art (lines, edges, text), not flat black, plain color or soft fades.
    A blob of missed detail touching a panel (like a bubble sticking out of it, or one letter of a title) is added to that panel, unless it's bigger than the panel. Any other blob becomes a panel of its own, trimmed to its content. Specks like watermarks and icons are left out.
    Returns the panels with the additions. Works at 1/4 size, which is plenty for this and saves memory.
    """
    from scipy import ndimage

    scale = WEBTOON_DETAIL_SCALE
    height, width = strip.shape[:2]
    gray = numpy.asarray(
        Image.fromarray(strip)
        .convert("L")
        .resize((max(1, width // scale), max(1, height // scale))),
        dtype=int,
    )
    # Thickened a little, so a line of text is one block.
    detail = ndimage.binary_dilation(get_detail(gray), iterations=2)

    # A panel's own border line sits just outside Magi's box, so detail that close counts as the panel's.
    border = 24 // scale
    covered = numpy.zeros(detail.shape, bool)
    for panel in panels:
        x0, y0, x1, y1 = [int(value) // scale for value in panel]
        covered[
            max(0, y0 - border) : y1 + 1 + border, max(0, x0 - border) : x1 + 1 + border
        ] = True
    missed = detail & ~covered

    # Missed detail within about 40 px of itself is one blob.
    blobs, _ = ndimage.label(
        ndimage.binary_dilation(missed, structure=numpy.ones((11, 11), bool))
    )  # pyright: ignore[reportGeneralTypeIssues]
    panels = [list(panel) for panel in panels]
    new_panels = []

    for index, area in enumerate(ndimage.find_objects(blobs)):
        blob = missed[area] & (blobs[area] == index + 1)
        ys, xs = numpy.nonzero(blob)
        box = [
            max(0, (area[1].start + xs.min()) * scale - 16),
            max(0, (area[0].start + ys.min()) * scale - 16),
            min(width, (area[1].start + xs.max() + 1) * scale + 16),
            min(height, (area[0].start + ys.max() + 1) * scale + 16),
        ]
        touching = [
            panel
            for panel in panels
            if panel[1] - 40 <= box[3]
            and box[1] <= panel[3] + 40
            and panel[0] - 40 <= box[2]
            and box[0] <= panel[2] + 40
        ]
        if touching:
            panel = min(
                touching, key=lambda panel: max(0, panel[1] - box[3], box[1] - panel[3])
            )
            if get_box_area(box) <= get_box_area(panel):
                panel[:] = [
                    min(panel[0], box[0]),
                    min(panel[1], box[1]),
                    max(panel[2], box[2]),
                    max(panel[3], box[3]),
                ]
                continue

        # Too small to be a panel on its own: a watermark, an icon, a stray mark. (Small art touching a panel, like one letter of a title, was added to it above.)
        if (
            blob.sum() < 150
            or box[3] - box[1] < 60
            or (box[2] - box[0] < 160 and box[3] - box[1] < 160)
        ):
            continue

        new_panels.append(box)

    return panels + new_panels


def looks_like_webtoon(chapter_pages):
    """
    Whether most of the chapter's images are far taller than a page (see "WEBTOON_IMAGE_HEIGHT_RATIO"), like a webtoon's. A manga page is about 1.4 times taller than wide; webtoon images are 3 to 25 times.
    """
    tall_images = [
        page
        for page in chapter_pages
        if page.shape[0] > WEBTOON_IMAGE_HEIGHT_RATIO * page.shape[1]
    ]
    return len(tall_images) > len(chapter_pages) / 2


def split_tall_panel(panel, page, texts):
    """
    A panel taller than "TALL_PANEL_SCREENS" phone screens (as wide as the page) is split into phone-screen-sized pieces, so on a phone it fills the screen instead of being a thin, unreadable strip. Nothing is left out: the pieces together are the whole panel.
    Each cut is at the quietest rows (white space, a panel border, little detail) near an even split, and never through text. Art can be cut, since the rest of it is in the next piece.
    The screen is as wide as the page, not the panel: a thin sliver isn't "many screens tall", and splitting it would only make tiny pieces.
    """
    crop_box = get_panel_crop_box(panel, page)
    if crop_box is None:
        return [panel]

    x0, y0, x1, y1 = crop_box
    height = y1 - y0
    screen_height = PHONE_SCREEN_HEIGHT_RATIO * page.shape[1]
    if height <= TALL_PANEL_SCREENS * screen_height:
        return [panel]

    gray = page[y0:y1, x0:x1].mean(axis=2)
    # How much each row changes, from left to right and from the row above. A cut needs a few quiet rows in a row, not one.
    detail = numpy.abs(numpy.diff(gray, axis=1)).sum(axis=1)
    detail[1:] += numpy.abs(numpy.diff(gray, axis=0)).sum(axis=1)
    detail = numpy.convolve(detail, numpy.ones(15) / 15, "same")

    # Never through text (with a little room for the bubble's outline).
    for text in texts:
        if text[0] < x1 and text[2] > x0:
            detail[max(0, int(text[1]) - 12 - y0) : max(0, int(text[3]) + 12 - y0)] = (
                numpy.inf
            )

    pieces = int(numpy.ceil(height / screen_height))
    cuts = [0]
    for piece in range(1, pieces):
        even_cut = piece * height // pieces
        low = max(int(even_cut - screen_height / 3), cuts[-1] + int(screen_height / 3))
        high = min(int(even_cut + screen_height / 3), height - int(screen_height / 3))
        if low < high and numpy.isfinite(detail[low:high]).any():
            cuts.append(low + int(numpy.argmin(detail[low:high])))
    cuts.append(height)

    return [[x0, y0 + top, x1, y0 + bottom] for top, bottom in zip(cuts, cuts[1:])]


def get_detail(gray):
    """
    Where an image has detail (lines, edges, text), as True/False for each pixel. Flat color and soft fades have none.
    """
    detail = numpy.zeros(gray.shape, bool)
    detail[:, 1:] |= numpy.abs(numpy.diff(gray, axis=1)) > 40
    detail[1:, :] |= numpy.abs(numpy.diff(gray, axis=0)) > 40
    return detail


def remove_junk_panels(per_page_results, chapter_pages):
    """
    Leave out panels with nothing to read or see:
    - Blank ones: almost one flat color, like an all-white or all-black box.
    - A scanlator's watermark, which Magi boxes as a panel each time it's stamped between panels: a faint image with nearly identical copies 2 or more times in the chapter.
    Soft art and decorative bits like falling petals stay: they aren't one flat color, and they're never identical copies.
    """
    junk, faint_images = set(), []

    for page_number, (page, page_result) in enumerate(
        zip(chapter_pages, per_page_results)
    ):
        for panel_number, panel in enumerate(page_result["panels"]):
            crop_box = get_panel_crop_box(panel, page)
            if crop_box is None:
                continue

            x0, y0, x1, y1 = crop_box
            gray = Image.fromarray(page[y0:y1, x0:x1]).convert("L")
            small = numpy.asarray(gray.resize((64, 64)), dtype=float)

            if (
                numpy.percentile(small, 99) - numpy.percentile(small, 1)
                < BLANK_PANEL_SPREAD
            ):
                junk.add((page_number, panel_number))
            elif (small < 200).mean() < 0.02:
                # Faint: compared without the white around it, so copies boxed a little differently still match.
                ys, xs = numpy.nonzero(numpy.asarray(gray) < 245)
                if len(xs):
                    thumbnail = gray.crop(
                        (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
                    ).resize((24, 24))
                    faint_images.append(
                        (
                            (page_number, panel_number),
                            numpy.asarray(thumbnail, dtype=float),
                        )
                    )

    for key, thumbnail in faint_images:
        copies = sum(
            numpy.abs(thumbnail - other).mean() < WATERMARK_MAX_DIFFERENCE
            for _, other in faint_images
        )
        # "copies" includes the image itself.
        if copies >= 3:
            junk.add(key)

    if junk:
        print(f"Left out {len(junk)} blank or watermark panel(s).")

    return [
        {
            **page_result,
            "panels": [
                panel
                for panel_number, panel in enumerate(page_result["panels"])
                if (page_number, panel_number) not in junk
            ],
        }
        for page_number, page_result in enumerate(per_page_results)
    ]


def remove_repeated_webtoon_panels(strip, panels, texts):
    """
    A thin webtoon sliver whose content is all shown in other panels, like one holding the end of a speech bubble the next panel shows whole: all the text touching it is inside another panel, and almost none of its detailed art is outside the others.
    Only slivers narrower than "REPEATED_PANEL_MAX_WIDTH" of the strip are checked. A full-size panel inside a bigger one (like a slice the safety net added) is kept: it's the cleaner of the two.
    The smallest panels are checked first, and only against panels that are kept.
    """
    panels = sorted(panels, key=get_box_area)
    kept = list(panels)

    for panel in panels:
        others = [other for other in kept if other is not panel]
        crop_box = get_panel_crop_box(panel, strip)
        if (
            crop_box is None
            or not others
            or crop_box[2] - crop_box[0] > REPEATED_PANEL_MAX_WIDTH * strip.shape[1]
        ):
            continue

        touching_texts = [text for text in texts if get_overlap_area(text, panel) > 0]
        if not all(
            any(
                get_overlap_area(text, other) >= 0.95 * get_box_area(text)
                for other in others
            )
            for text in touching_texts
        ):
            continue

        x0, y0, x1, y1 = crop_box
        own_detail = get_detail(strip[y0:y1, x0:x1].mean(axis=2))
        inside_others = numpy.zeros(own_detail.shape, bool)
        for other in others:
            ox0, oy0, ox1, oy1 = [int(value) for value in other]
            inside_others[
                max(0, oy0 - y0) : max(0, oy1 - y0), max(0, ox0 - x0) : max(0, ox1 - x0)
            ] = True

        # It needs proof that it's shown elsewhere: its text is in another panel, or most of it is. Soft art like falling petals has little detail, but that alone doesn't mean another panel shows it.
        is_shown_elsewhere = touching_texts or inside_others.mean() >= 0.8
        if (
            is_shown_elsewhere
            and (own_detail & ~inside_others).mean() < REPEATED_PANEL_MAX_NEW_DETAIL
        ):
            kept.remove(panel)

    return kept


def apply_reading_direction(per_page_results, chapter_pages, reading_direction):
    if reading_direction == "4koma":
        return [
            reorder_page_result_four_koma(page_result)
            for page_result in per_page_results
        ]

    if reading_direction != "ltr":
        return per_page_results

    return [
        reorder_page_result_left_to_right(page_result, page.shape[1])
        for page_result, page in zip(per_page_results, chapter_pages)
    ]


class Magi:
    # Panel-By-Panel's "Split very tall panels for phones" setting (see "split_tall_panel").
    split_tall_panels = True

    def __init__(self):
        # Each model is only loaded the first time it's needed.
        self._panels_model = None
        self._full_model = None
        # Panel-By-Panel's "Show full characters" setting: panels grow to fit the whole character, even if that takes a lot of another panel.
        self.show_full_characters = False

    @property
    def panels_model(self):
        if self._panels_model is None:
            from gui_classes.ProgressPanel import PYTORCH_LOAD_DETAIL, show_extra_stage

            # A step of its own in the Status view (a few seconds, the first time in each run of the app).
            with show_extra_stage(
                "Loading Magi (panels) into PyTorch", PYTORCH_LOAD_DETAIL
            ):
                self._panels_model = load_panels_magi_model().to(get_device())  # pyright: ignore[reportArgumentType]
        report_device(self._panels_model)
        return self._panels_model

    @property
    def full_model(self):
        if self._full_model is None:
            from gui_classes.ProgressPanel import format_size
            from storage import MAGI_DOWNLOAD_BYTES

            print(
                f"Loading the full Magi AI Model to read the text (the first time, this downloads {format_size(MAGI_DOWNLOAD_BYTES)} from {MAGI_MODEL_PAGE_URL})."
            )
            from gui_classes.ProgressPanel import PYTORCH_LOAD_DETAIL, show_extra_stage

            # Its download, the first time, is a step of its own before this one (see "load_full_magi_model").
            with show_extra_stage(
                "Loading Magi (full model) into PyTorch", PYTORCH_LOAD_DETAIL
            ):
                self._full_model = load_full_magi_model().to(get_device())  # pyright: ignore[reportArgumentType]
        report_device(self._full_model)
        return self._full_model

    def run_with_cpu_fallback(self, model_attribute, run):
        """
        Run "run()" with the model in "model_attribute" ("_panels_model" or "_full_model"). If it fails on the GPU (e.g. it ran out of memory), move that model to the CPU, which is slower but works, and run it again there. It stays on the CPU from then on.
        """
        try:
            return run()
        except RuntimeError as error:
            model = getattr(self, model_attribute)
            if model is None or model.device.type == "cpu":
                raise

            print(f"Magi failed on the GPU ({error}). Running it on the CPU instead.")
            setattr(self, model_attribute, model.to("cpu"))
            return run()

    def predict_panels(self, chapter_pages, reading_direction="rtl"):
        if reading_direction == "webtoon":
            return self.run_with_cpu_fallback(
                "_panels_model",
                lambda: [self.find_webtoon_panels(strip) for strip in chapter_pages],
            )

        return self.run_with_cpu_fallback(
            "_panels_model", lambda: self.find_panels(chapter_pages, reading_direction)
        )

    def find_webtoon_panels(self, strip):
        """
        The panels on a webtoon strip (see "join_webtoon_strip"), top to bottom, and the text boxes, as one page's result. Magi looks at overlapping windows (see "WEBTOON_WINDOW_SCREENS"). A panel cut off by a window's top or bottom edge is skipped there, since the next window sees it whole. The same panel found in two windows is kept once.
        """
        height, width = strip.shape[:2]
        window_height = WEBTOON_WINDOW_SCREENS * width
        window_tops = list(range(0, max(1, height - width), width))
        windows = [strip[top : top + window_height] for top in window_tops]
        whole_panels, cut_off_panels, texts = [], [], []

        # Webtoons are read left to right, like comics.
        for top, window, result in zip(
            window_tops, windows, self.find_panels(windows, "ltr")
        ):
            # Text seen in two windows is listed twice, which is fine: it's only used to not split a panel through text.
            texts += [
                [text[0], text[1] + top, text[2], text[3] + top]
                for text in result.get("texts", [])
            ]
            for panel in result["panels"]:
                is_cut_off = (panel[1] < 4 and top > 0) or (
                    panel[3] > window.shape[0] - 4 and top + window.shape[0] < height
                )
                (cut_off_panels if is_cut_off else whole_panels).append(
                    [panel[0], panel[1] + top, panel[2], panel[3] + top]
                )

        def is_same_panel(panel, other):
            return get_overlap_area(panel, other) > 0.6 * min(
                get_box_area(panel), get_box_area(other)
            )

        panels = []
        for panel in sorted(whole_panels, key=lambda panel: -get_box_area(panel)):
            if not any(is_same_panel(panel, kept) for kept in panels):
                panels.append(panel)

        # A panel taller than 1 screen is cut off in every window: its pieces are joined back together.
        tall_panels = []
        for piece in cut_off_panels:
            if any(is_same_panel(piece, kept) for kept in panels):
                continue
            for tall_panel in tall_panels:
                if get_overlap_area(piece, tall_panel) > 0:
                    tall_panel[:] = [
                        min(tall_panel[0], piece[0]),
                        min(tall_panel[1], piece[1]),
                        max(tall_panel[2], piece[2]),
                        max(tall_panel[3], piece[3]),
                    ]
                    break
            else:
                tall_panels.append(list(piece))
        panels += [
            panel
            for panel in tall_panels
            if not any(is_same_panel(panel, kept) for kept in panels)
        ]

        panels = remove_repeated_webtoon_panels(
            strip, get_webtoon_safety_net(strip, panels), texts
        )
        panels = sorted(panels, key=lambda panel: (panel[1], panel[0]))
        return {"panels": panels, "texts": texts}

    def find_panels(self, chapter_pages, reading_direction="rtl"):
        """
        Find the panels on each page, in manga reading order ("apply_reading_direction" changes it for other formats). "reading_direction" decides which panel a speech bubble split between two panels goes in (see "get_grown_panels"). Only runs the part of Magi that finds panels, which is about 18x faster than the full model (it skips reading the text and finding characters).
        """
        from transformers.image_transforms import center_to_corners_format
        from magi_model.utils import sort_panels
        from gui_classes.ProgressPanel import report_progress

        model = self.panels_model
        per_page_results = []

        # A few pages at a time, so a long chapter doesn't use too much memory.
        batch_size = 8
        report_progress(pages_done=0, pages_total=len(chapter_pages))
        for batch_start in range(0, len(chapter_pages), batch_size):
            pages = chapter_pages[batch_start : batch_start + batch_size]

            with torch.no_grad():
                inputs = model.move_to_device(
                    model.processor.preprocess_inputs_for_detection(pages)
                )
                detection_output = model._get_detection_transformer_output(**inputs)  # pyright: ignore[reportCallIssue]
                scores, boxes = model._get_predicted_bboxes_and_classes(
                    detection_output
                )
                # The rest is done on the CPU, with the page sizes.
                scores, boxes = scores.cpu(), boxes.cpu()

            # The same steps Magi's own "predict_detections_and_associations" uses for panels.
            batch_scores, batch_labels = scores.max(-1)
            batch_scores = batch_scores.sigmoid()
            batch_labels = batch_labels.long()
            boxes = cast(torch.Tensor, center_to_corners_format(boxes))
            page_heights, page_widths = torch.tensor(
                [page.shape[:2] for page in pages]
            ).unbind(1)
            boxes = (
                boxes
                * torch.stack(
                    [page_widths, page_heights, page_widths, page_heights], dim=1
                )[:, None, :]
            )
            panel_indices = model.processor._get_indices_of_panels_to_keep(
                batch_scores, batch_labels, boxes, PANEL_DETECTION_THRESHOLD
            )
            # The same pass also finds the text and characters, so the panels can grow to fit them at no extra cost.
            text_indices = model.processor._get_indices_of_texts_to_keep(
                batch_scores,
                batch_labels,
                boxes,
                TEXT_AND_CHARACTER_DETECTION_THRESHOLD,
            )
            character_indices = model.processor._get_indices_of_characters_to_keep(
                batch_scores,
                batch_labels,
                boxes,
                TEXT_AND_CHARACTER_DETECTION_THRESHOLD,
            )

            for page_number in range(len(pages)):
                # Kept so a very tall panel is never split through text (see "split_tall_panel").
                texts = boxes[page_number][text_indices[page_number]].tolist()
                if len(panel_indices[page_number]) == 0:
                    per_page_results.append({"panels": [], "texts": texts})
                    continue

                panel_boxes = boxes[page_number][panel_indices[page_number]]
                if len(panel_boxes):
                    panel_boxes = panel_boxes[sort_panels(panel_boxes)]
                per_page_results.append(
                    {
                        "panels": get_grown_panels(
                            panel_boxes.tolist(),
                            texts,
                            boxes[page_number][character_indices[page_number]].tolist(),
                            None if self.show_full_characters else PANEL_GROWTH_LIMIT,
                            reading_direction=reading_direction,
                        ),
                        "texts": texts,
                    }
                )

            report_progress(
                pages_done=len(per_page_results), pages_total=len(chapter_pages)
            )

        return per_page_results

    def get_image_as_numpy_array(self, image_path: str) -> numpy.ndarray:
        """
        Read an image path, convert it to a numpy array, and ensure it has 3 dimensions (RGB format).
        """
        with open(image_path, "rb") as file:
            pillow_image = Image.open(file)

            # Ensure the image is in RGB mode
            if pillow_image.mode != "RGB":
                pillow_image = pillow_image.convert("RGB")

            # Convert to numpy array
            image_numpy_array = numpy.array(pillow_image)

        return image_numpy_array

    def get_chapter_pages_image_numpy_array(self, chapter_directory):
        """
        From the passed in "chapter_directory", get the image numpy array of all of the image files in that directory.
        """
        return [
            self.get_image_as_numpy_array(image_path)
            for image_path in list_images(chapter_directory)
        ]

    def get_per_page_results(self, chapter_pages):
        return self.run_with_cpu_fallback(
            "_full_model", lambda: self.find_and_read_dialogue(chapter_pages)
        )

    def find_and_read_dialogue(self, chapter_pages):
        """
        Find the text boxes on each page, then read only the dialogue (the boxes Magi marks as "is_essential_text"). Sound effects and background text are never used, so reading them would be wasted time. They get "" in "ocr", so "ocr" still has one entry for each text box.
        """
        from tqdm import tqdm
        from gui_classes.ProgressPanel import report_progress

        model = self.full_model
        per_page_results = []

        # Set to "no_grad()" so that there's inference without tracking gradients. Basically, this saves memory and computational resources by turning off gradient tracking.
        with torch.no_grad():
            # "stage" moves Images To Video's stages line on (see "VideoCreatorFromImages.create_video_from_images").
            report_progress(
                stage=FINDING_TEXT_STAGE,
                pages_done=0,
                pages_total=len(chapter_pages),
                unit="images",
                # No line of its own: the steps already say it (FINDING_TEXT_STAGE).
                detail=None,
            )
            for batch_start in tqdm(range(0, len(chapter_pages), FIND_TEXT_BATCH_SIZE)):
                per_page_results += model.predict_detections_and_associations(
                    chapter_pages[batch_start : batch_start + FIND_TEXT_BATCH_SIZE]
                )
                report_progress(pages_done=len(per_page_results))

            dialogue_boxes = [
                [
                    box
                    for box, is_dialogue in zip(
                        result["texts"], result["is_essential_text"]
                    )
                    if is_dialogue
                ]
                for result in per_page_results
            ]
            dialogue_on_each_page = self.read_text_in_parts(
                chapter_pages, dialogue_boxes, report_progress, tqdm
            )

        for result, dialogue in zip(per_page_results, dialogue_on_each_page):
            dialogue = iter(dialogue)
            result["ocr"] = [
                next(dialogue) if is_dialogue else ""
                for is_dialogue in result["is_essential_text"]
            ]

        return per_page_results

    def read_text_in_parts(
        self, chapter_pages, boxes_on_each_page, report_progress, tqdm
    ):
        """
        Read the text in "boxes_on_each_page" exactly "READ_TEXT_BATCH_SIZE" lines at a time (a page's lines can be split between two parts), so the progress can show how many lines have been read. Bigger parts would be slower: lines read together all wait for the longest one.
        """
        # Every line as (page number, text box), in reading order.
        lines = [
            (page_index, box)
            for page_index, boxes in enumerate(boxes_on_each_page)
            for box in boxes
        ]
        text_on_each_page = [[] for _ in chapter_pages]
        # Each is one text box (a speech bubble or a caption), not a line of words.
        report_progress(
            stage=READING_TEXT_STAGE,
            pages_done=0,
            pages_total=len(lines),
            unit="text boxes",
            # No line of its own: the steps already say it (READING_TEXT_STAGE).
            detail=None,
        )

        with tqdm(total=len(lines)) as progress_bar:
            for part_start in range(0, len(lines), READ_TEXT_BATCH_SIZE):
                part = lines[part_start : part_start + READ_TEXT_BATCH_SIZE]
                page_indexes = sorted({page_index for page_index, _ in part})
                part_text = self.full_model.predict_ocr(
                    [chapter_pages[page_index] for page_index in page_indexes],
                    [
                        [
                            box
                            for line_page_index, box in part
                            if line_page_index == page_index
                        ]
                        for page_index in page_indexes
                    ],
                    batch_size=READ_TEXT_BATCH_SIZE,
                )

                for page_index, page_text in zip(page_indexes, part_text):
                    text_on_each_page[page_index] += page_text

                progress_bar.update(len(part))
                report_progress(pages_done=part_start + len(part))

        return text_on_each_page

    def save_cropped_panels(
        self,
        image_as_np_array,
        predictions,
        output_folder,
    ):
        # Ensure the output directory exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)  # Create the directory if it doesn't exist

        bboxes = predictions["panels"]

        for i, bbox in enumerate(bboxes):
            crop_box = get_panel_crop_box(bbox, image_as_np_array)

            if crop_box is None:
                print(f"Skipping invalid panel {i + 1}: {bbox}")
                continue

            x_min, y_min, x_max, y_max = crop_box

            # Crop the image
            cropped_image = image_as_np_array[y_min:y_max, x_min:x_max]

            # Save the cropped image
            output_path = os.path.join(output_folder, f"panel_{i + 1}.png")

            # Convert the cropped NumPy array to a PIL Image
            pil_image = Image.fromarray(cropped_image)
            # The page's height goes in the panel's file, because the "Best" upscaler (MangaJaNai) picks its model by the page's height.
            pil_image.save(
                output_path, pnginfo=get_page_height_info(image_as_np_array.shape[0])
            )
            print(f"Saved: {output_path}")

    def get_data_from_images(self, input_directory, reading_direction="rtl"):
        """
        Everything Magi finds on each page (panels, text boxes, what the text says, which text is dialogue, etc.), in reading order. "reading_direction" is "auto" (see "get_saved_reading_direction"), "rtl" (manga), "ltr" (comics), "4koma" (strips, top to bottom) or "webtoon" (vertical scroll).
        """
        chapter_pages_image_numpy_array = self.get_chapter_pages_image_numpy_array(
            input_directory
        )
        per_page_results = self.get_per_page_results(chapter_pages_image_numpy_array)

        reading_direction, is_automatic, nothing_saved = (
            get_automatic_reading_direction(reading_direction, input_directory)
        )
        if is_automatic and reading_direction == "rtl":
            reading_direction = get_reading_direction_from_panels(
                per_page_results, nothing_saved
            )

        return apply_reading_direction(
            per_page_results, chapter_pages_image_numpy_array, reading_direction
        )

    def get_panels_for_chapter(
        self,
        input_directory,
        output_directory,
        selected_input_directory,
        reading_direction="rtl",
        group_by_page=False,
        read_text=False,
    ):
        """
        "reading_direction" is "auto" (from the MangaDex download, or else guessed from the images: see "get_saved_reading_direction"), "rtl" (manga, right to left), "ltr" (comics, left to right), "4koma" (strips, top to bottom, right strip first) or "webtoon" (vertical scroll: the chapter is joined into one strip, see "find_webtoon_panels").
        "group_by_page" saves each page's panels in their own "page_x" folder. Otherwise, all of the chapter's panels are saved together, numbered in reading order.
        "read_text" also reads the dialogue on the pages and saves it next to the panels (see "save_panel_text"), so Images To Video doesn't have to read the text on every panel later.
        "selected_input_directory" is the top-level directory the user picked. The output path keeps the whole path from that directory down (e.g. "One Piece/Vol 1/Ch 1") so different series don't overwrite each other.
        """
        print(f"Starting panel-by-panel conversion for: {input_directory}")

        series_and_chapter_name_directory = get_relative_output_path(
            input_directory, selected_input_directory
        )
        chapter_pages_image_numpy_array = self.get_chapter_pages_image_numpy_array(
            input_directory
        )

        @time_it(custom_execution_time_name="Magi AI Model Convert to Panel-by-Panel")
        def get_panels():
            self.get_panels_using_local_cpu(
                chapter_pages_image_numpy_array,
                series_and_chapter_name_directory,
                output_directory,
                chapter_input_directory=input_directory,
                reading_direction=reading_direction,
                group_by_page=group_by_page,
                read_text=read_text,
            )

        get_panels()

    def get_panels_using_local_cpu(
        self,
        chapter_pages_image_numpy_array,
        series_and_chapter_name_directory,
        output_directory,
        chapter_input_directory="",
        reading_direction="rtl",
        group_by_page=False,
        read_text=False,
    ):
        panels_output_dir = get_panels_folder(
            output_directory, series_and_chapter_name_directory, group_by_page
        )
        # E.g. Magi re-run on its own earlier output: the new panels would replace the images being split.
        if chapter_input_directory and paths_overlap(
            panels_output_dir, chapter_input_directory
        ):
            raise RuntimeError(
                f"The panels would be saved over the images being split ({chapter_input_directory}). Please pick a different output folder."
            )

        reading_direction, is_automatic, nothing_saved = (
            get_automatic_reading_direction(reading_direction, chapter_input_directory)
        )

        if reading_direction != "webtoon" and looks_like_webtoon(
            chapter_pages_image_numpy_array
        ):
            print(
                "These images are much taller than pages, so they're split as a webtoon (vertical scroll)."
            )
            reading_direction = "webtoon"

        if reading_direction == "webtoon":
            chapter_pages_image_numpy_array = [
                join_webtoon_strip(chapter_pages_image_numpy_array)
            ]

        from gui_classes.ProgressPanel import report_progress

        # The stages shown in the Status view, like Images To Video's. The text is only read here for a Pipeline that also makes a video (see "save_panel_text").
        reads_text = read_text and not group_by_page and reading_direction != "webtoon"
        report_progress(
            stages=(
                FINDING_PANELS_STAGE,
                SAVING_PANELS_STAGE,
                *((FINDING_TEXT_STAGE, READING_TEXT_STAGE) if reads_text else ()),
            ),
            stage=FINDING_PANELS_STAGE,
            # Each chapter starts counting pages again (the text stages of the chapter before count text boxes).
            unit="pages",
        )
        per_page_predictions = self.predict_panels(
            chapter_pages_image_numpy_array, reading_direction
        )
        # The 4-koma check needs the panels, so with "Automatic" they're found in manga order first.
        if is_automatic and reading_direction == "rtl":
            reading_direction = get_reading_direction_from_panels(
                per_page_predictions, nothing_saved
            )

        per_page_results = apply_reading_direction(
            per_page_predictions,
            chapter_pages_image_numpy_array,
            reading_direction,
        )

        if self.split_tall_panels:
            per_page_results = [
                {
                    **page_result,
                    "panels": [
                        piece
                        for panel in page_result["panels"]
                        for piece in split_tall_panel(
                            panel, page, page_result.get("texts") or []
                        )
                    ],
                }
                for page, page_result in zip(
                    chapter_pages_image_numpy_array, per_page_results
                )
            ]

        per_page_results = remove_junk_panels(
            per_page_results, chapter_pages_image_numpy_array
        )

        # Remove this chapter's panels from any previous run first. Otherwise, if this run finds fewer panels or pages, the old leftover panels would get mixed in with the new ones. (It's never the folder being split: see the check at the top.)
        remove_old_panels(panels_output_dir)

        # Only the chosen version is saved. Not grouped panels are first saved page by page in a temporary folder, so they can be numbered in reading order across the whole chapter.
        pages_dir = (
            panels_output_dir if group_by_page else tempfile.mkdtemp(prefix="panelyze-")
        )

        report_progress(
            stage=SAVING_PANELS_STAGE,
            pages_done=0,
            pages_total=len(per_page_results),
            detail=None,
        )
        try:
            for i, (image_as_np_array, page_result_predictions) in enumerate(
                zip(chapter_pages_image_numpy_array, per_page_results)
            ):
                self.save_cropped_panels(
                    image_as_np_array,
                    page_result_predictions,
                    f"{pages_dir}/page_{i + 1}",
                )
                report_progress(pages_done=i + 1)

            if not group_by_page:
                copy_panels_to_one_level_directory(pages_dir, panels_output_dir)

            # A direction saved by the MangaDex download goes along with the panels, so Images To Video (on "Automatic") reads their text in the same order.
            if is_automatic and not nothing_saved:
                os.makedirs(panels_output_dir, exist_ok=True)
                with open(
                    os.path.join(panels_output_dir, READING_DIRECTION_FILE_NAME),
                    "w",
                    encoding="utf-8",
                ) as file:
                    file.write(reading_direction)
        finally:
            if not group_by_page:
                shutil.rmtree(pages_dir, ignore_errors=True)

        # Only for panels saved together. That's the folder Images To Video reads. A webtoon strip is far too tall for Magi to read its text in one go, so Images To Video reads it from the panels instead.
        if read_text and not group_by_page and reading_direction != "webtoon":
            self.save_panel_text(
                chapter_pages_image_numpy_array,
                per_page_results,
                panels_output_dir,
                reading_direction,
            )

        return per_page_results

    def save_panel_text(
        self, chapter_pages, per_page_panels, panels_output_dir, reading_direction
    ):
        """
        Read the dialogue on whole pages and save it as one list of lines for each saved panel, in "PANEL_TEXT_FILE_NAME" next to the panels. Reading whole pages is much faster than reading every panel on its own: Magi looks at each image at the same size, so one page costs about as much as one panel, and a page has several panels.
        """
        from gui_classes.ProgressPanel import report_progress

        print("Reading the text on the pages for Images To Video...")
        report_progress(
            pages_done=None, pages_total=None, detail="Reading the text on the pages..."
        )
        per_page_text = apply_reading_direction(
            self.get_per_page_results(chapter_pages), chapter_pages, reading_direction
        )

        panel_text = []
        for page, page_panels, page_text in zip(
            chapter_pages, per_page_panels, per_page_text
        ):
            # The same panels "save_cropped_panels" saves, in the same order, so line "n" belongs to "panel_n".
            panel_boxes = [
                crop_box
                for crop_box in (
                    get_panel_crop_box(bbox, page) for bbox in page_panels["panels"]
                )
                if crop_box is not None
            ]
            panel_text += get_dialogue_for_each_panel(page_text, panel_boxes)

        with open(
            os.path.join(panels_output_dir, PANEL_TEXT_FILE_NAME), "w", encoding="utf-8"
        ) as file:
            json.dump(panel_text, file, ensure_ascii=False, indent=1)
