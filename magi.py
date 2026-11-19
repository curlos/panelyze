from PIL import Image
import torch
import numpy
import os
from utils import (
    get_relative_output_path,
    list_images,
    paths_overlap,
    time_it,
)
import shutil
from copy_panels_to_one_level_directory import copy_panels_to_one_level_directory


# The exact version of Magi v2 on Hugging Face. Its code is copied into "magi_model/" at this version, and the full weights are downloaded at this version, so future changes to it can't silently change or break the output.
MAGI_MODEL_REVISION = "fbc890fec52977142e8ee00bfe26e9458b65517c"
MAGI_MODEL_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "magi_model")
# Only the parts of Magi that find panels (87 MB instead of 2 GB). Built from the full model by "build_panels_model_file".
PANELS_MODEL_FILE = os.path.join(MAGI_MODEL_DIRECTORY, "panels_fp16.safetensors")
PANELS_MODEL_PARTS = ("detection_transformer.", "bbox_predictor.", "class_labels_classifier.")
# How sure Magi has to be that something is a panel (the same value Magi uses itself).
PANEL_DETECTION_THRESHOLD = 0.2


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


def apply_reading_direction(per_page_results, chapter_pages, reading_direction):
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

    @property
    def panels_model(self):
        if self._panels_model is None:
            self._panels_model = load_panels_magi_model()
        return self._panels_model

    @property
    def full_model(self):
        if self._full_model is None:
            print("Loading the full Magi AI Model to read the text (the first time, this downloads about 2 GB)...")
            self._full_model = load_full_magi_model()
        return self._full_model

    def predict_panels(self, chapter_pages):
        """
        Find the panels on each page, in reading order. Only runs the part of Magi that finds panels, which is about 18x faster than the full model (it skips reading the text and finding characters).
        """
        from transformers.image_transforms import center_to_corners_format
        from magi_model.utils import sort_panels

        model = self.panels_model
        per_page_results = []

        # A few pages at a time, so a long chapter doesn't use too much memory.
        batch_size = 8
        for batch_start in range(0, len(chapter_pages), batch_size):
            pages = chapter_pages[batch_start : batch_start + batch_size]

            with torch.no_grad():
                inputs = model.processor.preprocess_inputs_for_detection(pages)
                detection_output = model._get_detection_transformer_output(**inputs)
                scores, boxes = model._get_predicted_bboxes_and_classes(detection_output)

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

            for page_number in range(len(pages)):
                if len(panel_indices[page_number]) == 0:
                    per_page_results.append({"panels": []})
                    continue

                panel_boxes = boxes[page_number][panel_indices[page_number]]
                if len(panel_boxes):
                    panel_boxes = panel_boxes[sort_panels(panel_boxes)]
                per_page_results.append({"panels": panel_boxes.tolist()})

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
        # No known characters to match against (Panelyze doesn't use character names).
        character_bank = {"images": [], "names": []}

        # Set to "no_grad()" so that there's inference without tracking gradients. Basically, this saves memory and computational resources by turning off gradient tracking.
        with torch.no_grad():
            per_page_results = self.full_model.do_chapter_wide_prediction(
                chapter_pages, character_bank, use_tqdm=True, do_ocr=True
            )

        return per_page_results

    def save_cropped_panels(
        self,
        image_as_np_array,
        predictions,
        output_folder,
    ):
        # Ensure the output directory exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)  # Create the directory if it doesn't exist

        image_height, image_width, _ = image_as_np_array.shape  # Get image dimensions
        bboxes = predictions["panels"]

        for i, bbox in enumerate(bboxes):
            # Ensure coordinates are integers
            x_min, y_min, x_max, y_max = map(int, bbox)

            # Clamp bounding box to image dimensions
            x_min = max(0, min(x_min, image_width))
            y_min = max(0, min(y_min, image_height))
            x_max = max(0, min(x_max, image_width))
            y_max = max(0, min(y_max, image_height))

            # Check if the box is valid after clamping
            if x_max <= x_min or y_max <= y_min:
                print(f"Skipping invalid panel {i + 1}: {bbox}")
                continue

            # Crop the image
            cropped_image = image_as_np_array[y_min:y_max, x_min:x_max]

            # Save the cropped image
            output_path = os.path.join(output_folder, f"panel_{i + 1}.png")

            # Convert the cropped NumPy array to a PIL Image
            pil_image = Image.fromarray(cropped_image)
            pil_image.save(output_path)
            print(f"Saved: {output_path}")

    def get_data_from_images(self, input_directory, reading_direction="rtl"):
        """
        Everything Magi finds on each page (panels, text boxes, what the text says, which text is dialogue, etc.), in reading order. "reading_direction" is "rtl" (manga) or "ltr" (comics).
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
    ):
        """
        "reading_direction" is "rtl" (manga, right to left) or "ltr" (comics, left to right).
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
            )

        get_panels()

    def get_panels_using_local_cpu(
        self,
        chapter_pages_image_numpy_array,
        series_and_chapter_name_directory,
        output_directory,
        chapter_input_directory="",
        reading_direction="rtl",
    ):
        per_page_results = apply_reading_direction(
            self.predict_panels(chapter_pages_image_numpy_array),
            chapter_pages_image_numpy_array,
            reading_direction,
        )

        panel_by_panel_input_dir = f"{output_directory}/panel-by-panel/grouped-by-page/{series_and_chapter_name_directory}"
        panel_by_panel_output_dir = f"{output_directory}/panel-by-panel/not-grouped/{series_and_chapter_name_directory}"

        # Remove this chapter's panels from any previous run first. Otherwise, if this run finds fewer panels or pages, the old leftover panels would get mixed in with the new ones.
        for previous_run_dir in [panel_by_panel_input_dir, panel_by_panel_output_dir]:
            # Never delete a folder that holds the images being processed (e.g. when re-running Magi on its own previous output).
            if os.path.exists(previous_run_dir) and not (
                chapter_input_directory
                and paths_overlap(previous_run_dir, chapter_input_directory)
            ):
                shutil.rmtree(previous_run_dir)

        for i, (image_as_np_array, page_result_predictions) in enumerate(
            zip(chapter_pages_image_numpy_array, per_page_results)
        ):
            self.save_cropped_panels(
                image_as_np_array,
                page_result_predictions,
                f"{output_directory}/panel-by-panel/grouped-by-page/{series_and_chapter_name_directory}/page_{i + 1}",
            )

        copy_panels_to_one_level_directory(
            panel_by_panel_input_dir, panel_by_panel_output_dir
        )

        return per_page_results
