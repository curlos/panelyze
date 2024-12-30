from PIL import Image
from transformers import AutoModel
import torch
import numpy
import os
from utils import select_folder
import requests
import time
import base64
import json

using_google_colab = True


def get_image_as_numpy_array(image_path: str) -> numpy.ndarray:
    """
    Read an image path and convert it to a numpy array.
    """
    with open(image_path, "rb") as file:
        pillow_image = Image.open(file)
        image_numpy_array = numpy.array(pillow_image)
    return image_numpy_array


def get_chapter_pages_image_numpy_array(chapter_directory):
    """
    From the passed in "chapter_directory", get the image numpy array of all of the image files in that directory.
    """
    sorted_chapter_directory = sorted(os.listdir(chapter_directory))
    files_that_are_images = [
        file
        for file in sorted_chapter_directory
        if file.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    chapter_pages_image_paths = [
        os.path.join(chapter_directory, file) for file in files_that_are_images
    ]

    chapter_pages_image_numpy_array = [
        get_image_as_numpy_array(image_path) for image_path in chapter_pages_image_paths
    ]

    return chapter_pages_image_numpy_array


def get_character_bank():
    """
    Get the character bank to use for the manga page (s) that the model will look through and detect the characters in those pages.
    """
    character_bank = {"images": [], "names": []}
    character_bank["images"] = [
        get_image_as_numpy_array(x) for x in character_bank["images"]
    ]

    return character_bank


def get_per_page_results(magi_model, chapter_pages, character_bank):
    # Set to "no_grad()" so that there's inference without tracking gradients. Basically, this saves memory and computational resources by turning off gradient tracking.
    with torch.no_grad():
        per_page_results = magi_model.do_chapter_wide_prediction(
            chapter_pages, character_bank, use_tqdm=True, do_ocr=True
        )

    return per_page_results


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


def get_panels_for_chapter(magi_model):
    chapter_directory = select_folder()
    panels_parent_directory = select_folder()

    chapter_pages_image_numpy_array = get_chapter_pages_image_numpy_array(
        chapter_directory
    )
    character_bank = get_character_bank()

    print("Starting timer...")
    # Start the timer
    start_time = time.time()

    print(chapter_directory)
    print(panels_parent_directory)

    # Wasn't able to fully get this working but if Google Colab did work, then in theory send the request to Colab and it would use the Magi Model on there and do all the computationally expensive operations on the superior GPUs on Colab and give me the numpy array results here and do the rest of the operations on this local code.
    if using_google_colab:
        print("Sending request to Google Colab!")

        colab_url = (
            "https://4b9b-35-224-78-55.ngrok-free.app/process-images-with-magi-model"
        )

        print(chapter_pages_image_numpy_array)

        # Encode each NumPy array into base64
        encoded_arrays = [
            {
                "data": base64.b64encode(array.tobytes()).decode("utf-8"),
                "shape": array.shape,
                "dtype": str(array.dtype),
            }
            for array in chapter_pages_image_numpy_array
        ]

        # Create the payload
        data = {
            "chapter_pages_image_numpy_array": encoded_arrays,
            "character_bank": character_bank,
        }

        payload_size = len(json.dumps(data))
        print(f"Payload size: {payload_size} bytes")

        response = requests.post(
            colab_url,
            json=data,
        )

        if response.status_code == 200:
            per_page_results = response.json()

        print("From Google Colab!")
        print(per_page_results)
        print("From Google Colab!")
    else:
        per_page_results = get_per_page_results(
            magi_model, chapter_pages_image_numpy_array, character_bank
        )

    for i, (image_as_np_array, page_result_predictions) in enumerate(
        zip(chapter_pages_image_numpy_array, per_page_results)
    ):
        save_cropped_panels(
            image_as_np_array,
            page_result_predictions,
            f"{panels_parent_directory}/{chapter_directory}/page_{i + 1}",
        )

    # Calculate and print the total time taken
    end_time = time.time()
    total_time = end_time - start_time
    print(
        f"Magi AI Model Panel-by-Panel conversion time taken: {total_time:.2f} seconds"
    )


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    # Use the pre-trained MagiV2 model that can help us detect panels, characters, text, and more from manga pages.
    magi_model = AutoModel.from_pretrained(
        "ragavsachdeva/magiv2", trust_remote_code=True
    ).eval()

    get_panels_for_chapter(magi_model)
