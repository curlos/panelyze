import os

# Anything the Mac GPU can't do runs on the CPU instead of failing. It has to be set before "torch" is imported.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import json
from PIL import Image
import torch
import numpy
from utils import (
    PANEL_TEXT_FILE_NAME,
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
MAGI_MODEL_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "magi_model")
# Only the parts of Magi that find panels (87 MB instead of 2 GB). Built from the full model by "build_panels_model_file".
PANELS_MODEL_FILE = os.path.join(MAGI_MODEL_DIRECTORY, "panels_fp16.safetensors")
PANELS_MODEL_PARTS = ("detection_transformer.", "bbox_predictor.", "class_labels_classifier.")
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


def get_device():
    """
    The fastest place to run Magi on this computer: the Mac GPU, an NVIDIA GPU, or else the CPU.
    """
    if torch.backends.mps.is_available():
        return "mps"

    if torch.cuda.is_available():
        return "cuda"

    return "cpu"


DEVICE_NAMES = {"mps": "the Mac GPU", "cuda": "the NVIDIA GPU", "cpu": "the CPU"}


def load_magi_config(config_file_name):
    from magi_model.configuration_magiv2 import Magiv2Config

    return Magiv2Config.from_json_file(os.path.join(MAGI_MODEL_DIRECTORY, config_file_name))


def load_full_magi_model():
    """
    The whole Magi model (about 2 GB), including the part that reads the text. Downloaded from Hugging Face the first time.
    """
    from magi_model.modelling_magiv2 import Magiv2Model

    return Magiv2Model.from_pretrained(
        "ragavsachdeva/magiv2",
        revision=MAGI_MODEL_REVISION,
        config=load_magi_config("full_config.json"),
    ).eval()


def build_panels_model_file():
    """
    Save just the panel-finding parts of the full Magi model into "PANELS_MODEL_FILE" (87 MB, half precision). The Mac app build bundles this file. When running from source, it's built automatically the first time it's needed.
    """
    from safetensors.torch import save_file

    print("Building the small panels-only Magi model (one time only)...")
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
    weights = {name: weights.float() for name, weights in load_file(PANELS_MODEL_FILE).items()}
    # "strict=False" because the small model leaves out the parts Panel-By-Panel doesn't use (text reading, characters, etc.). But every panel-finding part must be there, or the panels would be garbage.
    missing_weights = model.load_state_dict(weights, strict=False).missing_keys
    missing_panel_weights = [name for name in missing_weights if name.startswith(PANELS_MODEL_PARTS)]
    if missing_panel_weights:
        raise RuntimeError(
            f"The panels model file is incomplete ({len(missing_panel_weights)} parts missing). Delete {PANELS_MODEL_FILE} and try again to rebuild it."
        )

    return model.eval()


def get_mirrored_boxes(boxes, page_width):
    """
    Flip boxes ([x1, y1, x2, y2]) horizontally, as if the page were seen in a mirror.
    """
    return [
        [page_width - x2, y1, page_width - x1, y2] for x1, y1, x2, y2 in boxes
    ]


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
        return list(sort_panels(get_mirrored_boxes(panels, max(panel[2] for panel in panels))))

    return list(range(len(panels)))


def get_grown_panels(panels, texts, characters, character_growth_limit=PANEL_GROWTH_LIMIT, reading_direction="rtl"):
    """
    Magi's panel boxes follow the panel borders, so speech bubbles and characters drawn over a border get cut. Each panel grows to fit the text and characters that are its own (they overlap it the most) but stick out of it.
    It doesn't grow when that would take more than "PANEL_GROWTH_LIMIT" of another panel, so a crop never pulls in the next panel and its dialogue. This also skips Japanese captions in the page margin, which Magi finds as text too.
    Dialogue split between panels is always shown whole in one of them, though, because the reader needs the words (see "grow_to_fit").
    "character_growth_limit=None" always fits the whole character (the "Show full characters" setting).
    """
    grown_panels = [list(panel) for panel in panels]
    position_in_reading_order = {
        index: position for position, index in enumerate(get_panel_reading_order(panels, reading_direction))
    }

    def get_share_taken_of_another_panel(index, grown_panel):
        """
        The most of any other panel that growing panel "index" to "grown_panel" would take (0 to 1).
        """
        return max(
            (
                (get_overlap_area(grown_panel, other) - get_overlap_area(grown_panels[index], other)) / get_box_area(other)
                for other_index, other in enumerate(panels)
                if other_index != index and get_box_area(other) > 0
            ),
            default=0,
        )

    def grow_to_fit(box, margin, min_share, limit, always_show_whole=False):
        overlaps = [get_overlap_area(panel, box) for panel in grown_panels]
        box_area = get_box_area(box)

        # Not in any panel, mostly outside of them, or already all inside one.
        if not overlaps or max(overlaps) == 0 or max(overlaps) < min_share * box_area or max(overlaps) >= 0.999 * box_area:
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
        share_taken = {index: get_share_taken_of_another_panel(index, grown[index]) for index in indices}

        if limit is None or share_taken[indices[0]] <= limit:
            grown_panels[indices[0]] = grown[indices[0]]
            return

        # A bubble split between two panels that its own panel can't fit within the limit: the first of the two in reading order shows it anyway, so the reader sees the whole line the first time they reach it. Text mostly outside the panels (like a caption in the page margin), or running across 3 or more panels (like a chapter title down the side of the page), isn't dialogue the reader needs.
        if always_show_whole and len(panels_it_is_in) == 2 and sum(overlaps) >= SPLIT_TEXT_MIN_INSIDE * box_area:
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
            dialogue_for_each_panel[get_panel_index_of_text(text_box, panel_boxes)].append(text)

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
    4-koma pages are strips of panels stacked top to bottom, read one strip (column) at a time from the right. Panels that share most of their width are in the same column.
    """
    columns = []

    for index in sorted(range(len(panels)), key=lambda index: -(panels[index][0] + panels[index][2])):
        panel = panels[index]
        for column in columns:
            first_panel = panels[column[0]]
            shared_width = min(panel[2], first_panel[2]) - max(panel[0], first_panel[0])
            if shared_width > 0.5 * min(panel[2] - panel[0], first_panel[2] - first_panel[0]):
                column.append(index)
                break
        else:
            columns.append([index])

    return [index for column in columns for index in sorted(column, key=lambda index: panels[index][1])]


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
        position_of_panel = {panel_index: position for position, panel_index in enumerate(panel_order)}
        # "sorted" keeps Magi's own order for text in the same panel.
        text_order = sorted(
            range(len(texts)),
            key=lambda index: position_of_panel[get_panel_index_of_text(texts[index], panels)],
        )
        # The text, what it says and whether it's dialogue all have to stay together.
        for key in ("texts", "ocr", "is_essential_text"):
            values = page_result.get(key)
            if values is not None and len(values) == len(texts):
                page_result[key] = [values[index] for index in text_order]

    return page_result


def apply_reading_direction(per_page_results, chapter_pages, reading_direction):
    if reading_direction == "4koma":
        return [reorder_page_result_four_koma(page_result) for page_result in per_page_results]

    if reading_direction != "ltr":
        return per_page_results

    return [
        reorder_page_result_left_to_right(page_result, page.shape[1])
        for page_result, page in zip(per_page_results, chapter_pages)
    ]


class Magi:
    def __init__(self):
        # Each model is only loaded the first time it's needed.
        self._panels_model = None
        self._full_model = None
        # Panel-By-Panel's "Show full characters" setting: panels grow to fit the whole character, even if that takes a lot of another panel.
        self.show_full_characters = False

    @property
    def panels_model(self):
        if self._panels_model is None:
            self._panels_model = load_panels_magi_model().to(get_device())
        return self._panels_model

    @property
    def full_model(self):
        if self._full_model is None:
            print("Loading the full Magi AI Model to read the text (the first time, this downloads about 2 GB)...")
            device = get_device()
            self._full_model = load_full_magi_model().to(device)
            print(f"Magi will read the text on {DEVICE_NAMES[device]}.")
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
        return self.run_with_cpu_fallback(
            "_panels_model", lambda: self.find_panels(chapter_pages, reading_direction)
        )

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
                detection_output = model._get_detection_transformer_output(**inputs)
                scores, boxes = model._get_predicted_bboxes_and_classes(detection_output)
                # The rest is done on the CPU, with the page sizes.
                scores, boxes = scores.cpu(), boxes.cpu()

            # The same steps Magi's own "predict_detections_and_associations" uses for panels.
            batch_scores, batch_labels = scores.max(-1)
            batch_scores = batch_scores.sigmoid()
            batch_labels = batch_labels.long()
            boxes = center_to_corners_format(boxes)
            page_heights, page_widths = torch.tensor(
                [page.shape[:2] for page in pages]
            ).unbind(1)
            boxes = boxes * torch.stack(
                [page_widths, page_heights, page_widths, page_heights], dim=1
            )[:, None, :]
            panel_indices = model.processor._get_indices_of_panels_to_keep(
                batch_scores, batch_labels, boxes, PANEL_DETECTION_THRESHOLD
            )
            # The same pass also finds the text and characters, so the panels can grow to fit them at no extra cost.
            text_indices = model.processor._get_indices_of_texts_to_keep(
                batch_scores, batch_labels, boxes, TEXT_AND_CHARACTER_DETECTION_THRESHOLD
            )
            character_indices = model.processor._get_indices_of_characters_to_keep(
                batch_scores, batch_labels, boxes, TEXT_AND_CHARACTER_DETECTION_THRESHOLD
            )

            for page_number in range(len(pages)):
                if len(panel_indices[page_number]) == 0:
                    per_page_results.append({"panels": []})
                    continue

                panel_boxes = boxes[page_number][panel_indices[page_number]]
                if len(panel_boxes):
                    panel_boxes = panel_boxes[sort_panels(panel_boxes)]
                per_page_results.append(
                    {
                        "panels": get_grown_panels(
                            panel_boxes.tolist(),
                            boxes[page_number][text_indices[page_number]].tolist(),
                            boxes[page_number][character_indices[page_number]].tolist(),
                            None if self.show_full_characters else PANEL_GROWTH_LIMIT,
                            reading_direction=reading_direction,
                        )
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
            report_progress(
                pages_done=0, pages_total=len(chapter_pages), unit="images", detail="Finding the text"
            )
            for batch_start in tqdm(range(0, len(chapter_pages), FIND_TEXT_BATCH_SIZE)):
                per_page_results += model.predict_detections_and_associations(
                    chapter_pages[batch_start : batch_start + FIND_TEXT_BATCH_SIZE]
                )
                report_progress(pages_done=len(per_page_results))

            dialogue_boxes = [
                [
                    box
                    for box, is_dialogue in zip(result["texts"], result["is_essential_text"])
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

    def read_text_in_parts(self, chapter_pages, boxes_on_each_page, report_progress, tqdm):
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
        report_progress(pages_done=0, pages_total=len(lines), unit="lines", detail="Reading the text")

        with tqdm(total=len(lines)) as progress_bar:
            for part_start in range(0, len(lines), READ_TEXT_BATCH_SIZE):
                part = lines[part_start : part_start + READ_TEXT_BATCH_SIZE]
                page_indexes = sorted({page_index for page_index, _ in part})
                part_text = self.full_model.predict_ocr(
                    [chapter_pages[page_index] for page_index in page_indexes],
                    [
                        [box for line_page_index, box in part if line_page_index == page_index]
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
            pil_image.save(output_path, pnginfo=get_page_height_info(image_as_np_array.shape[0]))
            print(f"Saved: {output_path}")

    def get_data_from_images(self, input_directory, reading_direction="rtl"):
        """
        Everything Magi finds on each page (panels, text boxes, what the text says, which text is dialogue, etc.), in reading order. "reading_direction" is "rtl" (manga), "ltr" (comics) or "4koma" (strips, top to bottom).
        """
        chapter_pages_image_numpy_array = self.get_chapter_pages_image_numpy_array(
            input_directory
        )
        per_page_results = self.get_per_page_results(chapter_pages_image_numpy_array)

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
        "reading_direction" is "rtl" (manga, right to left), "ltr" (comics, left to right) or "4koma" (strips, top to bottom, right strip first).
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
        per_page_results = apply_reading_direction(
            self.predict_panels(chapter_pages_image_numpy_array, reading_direction),
            chapter_pages_image_numpy_array,
            reading_direction,
        )

        grouped_by_page_dir = f"{output_directory}/panel-by-panel/grouped-by-page/{series_and_chapter_name_directory}"
        not_grouped_by_page_dir = f"{output_directory}/panel-by-panel/not-grouped-by-page/{series_and_chapter_name_directory}"
        panels_output_dir = grouped_by_page_dir if group_by_page else not_grouped_by_page_dir

        # Remove this chapter's panels from any previous run first. Otherwise, if this run finds fewer panels or pages, the old leftover panels would get mixed in with the new ones.
        # Never delete a folder that holds the images being processed (e.g. when re-running Magi on its own previous output).
        if os.path.exists(panels_output_dir) and not (
            chapter_input_directory
            and paths_overlap(panels_output_dir, chapter_input_directory)
        ):
            shutil.rmtree(panels_output_dir)

        # Only the chosen version is saved. Not grouped panels are first saved page by page in a temporary folder, so they can be numbered in reading order across the whole chapter.
        pages_dir = (
            grouped_by_page_dir if group_by_page else tempfile.mkdtemp(prefix="panelyze-")
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

            if not group_by_page:
                copy_panels_to_one_level_directory(pages_dir, not_grouped_by_page_dir)
        finally:
            if not group_by_page:
                shutil.rmtree(pages_dir, ignore_errors=True)

        # Only for panels saved together. That's the folder Images To Video reads.
        if read_text and not group_by_page:
            self.save_panel_text(
                chapter_pages_image_numpy_array,
                per_page_results,
                not_grouped_by_page_dir,
                reading_direction,
            )

        return per_page_results

    def save_panel_text(self, chapter_pages, per_page_panels, panels_output_dir, reading_direction):
        """
        Read the dialogue on whole pages and save it as one list of lines for each saved panel, in "PANEL_TEXT_FILE_NAME" next to the panels. Reading whole pages is much faster than reading every panel on its own: Magi looks at each image at the same size, so one page costs about as much as one panel, and a page has several panels.
        """
        from gui_classes.ProgressPanel import report_progress

        print("Reading the text on the pages for Images To Video...")
        report_progress(pages_done=None, pages_total=None, detail="Reading the text on the pages...")
        per_page_text = apply_reading_direction(
            self.get_per_page_results(chapter_pages), chapter_pages, reading_direction
        )

        panel_text = []
        for page, page_panels, page_text in zip(chapter_pages, per_page_panels, per_page_text):
            # The same panels "save_cropped_panels" saves, in the same order, so line "n" belongs to "panel_n".
            panel_boxes = [
                crop_box
                for crop_box in (get_panel_crop_box(bbox, page) for bbox in page_panels["panels"])
                if crop_box is not None
            ]
            panel_text += get_dialogue_for_each_panel(page_text, panel_boxes)

        with open(os.path.join(panels_output_dir, PANEL_TEXT_FILE_NAME), "w", encoding="utf-8") as file:
            json.dump(panel_text, file, ensure_ascii=False, indent=1)
