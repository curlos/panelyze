from PIL import Image
from transformers import AutoModel
import torch

import numpy as np
import os

model = AutoModel.from_pretrained("ragavsachdeva/magiv2", trust_remote_code=True).eval()


def read_image(path_to_image):
    with open(path_to_image, "rb") as file:
        # Converts the image to grayscale (most manga are black and white) and I'm guessing this is necessary for the AI to properly detect the different panels, characters, and text.
        image = Image.open(file)
        image = np.array(image)
    return image


chapter_directory = "Dragon Ball (Official Colored)/Ch 229"
chapter_directory = "One Piece (Official Colored)/Ch. 567"
chapter_directory = "One Piece (Official Colored)/[PowerManga] Vol. 44 Ch. 427"

# Get all image file paths from the directory
chapter_pages = [
    os.path.join(chapter_directory, file)
    for file in sorted(os.listdir(chapter_directory))
    if file.lower().endswith((".png", ".jpg", ".jpeg"))
]

character_bank = {"images": [], "names": []}

chapter_pages = [read_image(x) for x in chapter_pages]
character_bank["images"] = [read_image(x) for x in character_bank["images"]]

print(chapter_pages)

with torch.no_grad():
    per_page_results = model.do_chapter_wide_prediction(
        chapter_pages, character_bank, use_tqdm=True, do_ocr=True
    )


def save_cropped_panels(image_as_np_array, predictions, output_folder):
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
        Image.fromarray(cropped_image).save(output_path)
        print(f"Saved: {output_path}")


for i, (image_as_np_array, page_result_predictions) in enumerate(
    zip(chapter_pages, per_page_results)
):
    save_cropped_panels(
        image_as_np_array,
        page_result_predictions,
        f"panel-by-panel/{chapter_directory}/page_{i + 1}",
    )
