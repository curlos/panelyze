import sys
from PIL import Image
from transformers import AutoModel
import torch
import numpy
import os
from utils import select_folder, get_last_two_directories, time_it
import requests
import time
import base64
import json
import flet as ft
from copy_panels_to_one_level_directory import copy_panels_to_one_level_directory


class Magi:
    def __init__(self, terminal_output_list_view=None):
        self.using_google_colab = False
        self.magi_model = None
        self.terminal_output_list_view = terminal_output_list_view

        if not self.using_google_colab:
            self.magi_model = AutoModel.from_pretrained(
                "ragavsachdeva/magiv2", trust_remote_code=True
            ).eval()

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
            self.get_image_as_numpy_array(image_path)
            for image_path in chapter_pages_image_paths
        ]

        return chapter_pages_image_numpy_array

    def get_character_bank(self):
        """
        Get the character bank to use for the manga page (s) that the model will look through and detect the characters in those pages.
        """
        character_bank = {"images": [], "names": []}
        character_bank["images"] = [
            self.get_image_as_numpy_array(x) for x in character_bank["images"]
        ]

        return character_bank

    def get_per_page_results(self, chapter_pages, character_bank):
        # TODO: Look at this later to output lines from the terminal. Need to output tqdm lines through stderr.
        # # Save the original stdout and stderr
        # original_stdout = sys.stdout
        # original_stderr = sys.stderr

        # # Create StreamInterceptors for both stdout and stderr
        # stdout_interceptor = StreamInterceptor(
        #     original_stdout, self.real_time_output_callback
        # )
        # stderr_interceptor = StreamInterceptor(
        #     original_stderr, self.real_time_output_callback
        # )

        # try:
        #     # Redirect both stdout and stderr
        #     # sys.stdout = stdout_interceptor
        #     # sys.stderr = stderr_interceptor

        #     # Perform the task while redirecting both streams
        #     # Set to "no_grad()" so that there's inference without tracking gradients. Basically, this saves memory and computational resources by turning off gradient tracking.
        #     with torch.no_grad():
        #         per_page_results = self.magi_model.do_chapter_wide_prediction(
        #             chapter_pages, character_bank, use_tqdm=True, do_ocr=True
        #         )
        # finally:
        #     # Restore stdout and stderr to their original states
        #     sys.stdout = original_stdout
        #     sys.stderr = original_stderr

        # Set to "no_grad()" so that there's inference without tracking gradients. Basically, this saves memory and computational resources by turning off gradient tracking.
        with torch.no_grad():
            per_page_results = self.magi_model.do_chapter_wide_prediction(
                chapter_pages, character_bank, use_tqdm=True, do_ocr=True
            )

        return per_page_results

    # Example usage of the real-time output callback
    def real_time_output_callback(self, message):
        if self.terminal_output_list_view:
            self.terminal_output_list_view.controls.append(
                ft.Text(message, color="white")
            )

        sys.__stdout__.write(f"Captured: {message}")
        sys.__stdout__.flush()

    def save_cropped_panels(
        self,
        image_as_np_array,
        predictions,
        output_folder,
        flet_page_client_storage=None,
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

    def get_panels_for_chapter(
        self, input_directory, output_directory, flet_page_client_storage=None
    ):
        series_and_chapter_name_directory = get_last_two_directories(input_directory)

        chapter_pages_image_numpy_array = self.get_chapter_pages_image_numpy_array(
            input_directory
        )
        character_bank = self.get_character_bank()

        @time_it(custom_execution_time_name="Magi AI Model Convert to Panel-by-Panel")
        def get_panels():
            if self.using_google_colab:
                self.get_panels_using_google_colab(
                    chapter_pages_image_numpy_array,
                    character_bank,
                    series_and_chapter_name_directory,
                    output_directory,
                )
            else:
                self.get_panels_using_local_cpu(
                    chapter_pages_image_numpy_array,
                    character_bank,
                    series_and_chapter_name_directory,
                    output_directory,
                    flet_page_client_storage,
                )

        get_panels()

    def get_panels_using_google_colab(
        self,
        chapter_pages_image_numpy_array,
        character_bank,
        series_and_chapter_name_directory,
        output_directory,
    ):
        # TODO: Note: I have not passed in "flet_page_client_storage" to the parameters here since I'm not currently testing Google Colab but just know that if I do want to test Google Colab with the Flet GUI in the future, there's some new code that has to be updated. All of the most recent updates are in the "get_panels_using_local_cpu" method below.
        # Wasn't able to fully get this working but if Google Colab did work, then in theory send the request to Colab and it would use the Magi Model on there and do all the computationally expensive operations on the superior GPUs on Colab and give me the numpy array results here and do the rest of the operations on this local code.
        if self.using_google_colab:
            google_colab_ngrok_server_url_parts = {
                "base": "https://93c1-34-125-70-89.ngrok-free.app/",
                "route": "process-images-with-magi-model",
            }
            base, route = google_colab_ngrok_server_url_parts.values()
            google_colab_ngrok_server_url = base + route

            # Encode each NumPy array into base64
            encoded_arrays = [
                {
                    "data": base64.b64encode(array.tobytes()).decode("utf-8"),
                    "shape": array.shape,
                    "dtype": str(array.dtype),
                }
                for array in chapter_pages_image_numpy_array
            ]

            page_num = 0

            # Go through each image's "encoded_array" and send it in the payload to Google Colab's Flask server (the server must be running for this to work).
            for encoded_array in encoded_arrays:
                # Each image (or page in this case), has an encoded array. The Magi Model has a function called "do_chapter_wide_predictions" that will expect an array of image numpy arrays.
                # However, because I'm sending this as a payload to the Flask server and that payload has a max MB of 16MB, if I tried to send all of the page images at once, it'd fail.
                # If there are 15 images on average in one chapter and each image is 2 MB, that's 32 MB which is over the limit.
                # So, because of that, I'm making one request per image to the server with that image in the payload as it'd be very rare if not impossible for 1 manga page to be over 16MB.
                local_encoded_arrays_of_current = [encoded_array]
                # Create the payload
                data = {
                    "chapter_pages_image_numpy_array": local_encoded_arrays_of_current,
                    # TODO: Character Bank is always going to be empty for now but maybe I can do something with it later (unlikely though as it'd required a lot of individual work and it's not a required feature).
                    "character_bank": character_bank,
                }

                payload_size = len(json.dumps(data))
                print(
                    f"Payload size: {payload_size} bytes"
                )  # Payload CANNOT be over 16MB. Watch out for colorspreads/covers and other big images.

                try:
                    # Send the request to the server where Google Colab will use it's faster GPUs (like the A100 GPU) to run the Magi Model on the image numpy array that is sent in the payload.
                    response = requests.post(
                        google_colab_ngrok_server_url, json=data, verify=False
                    )

                    print(response)

                    if response.status_code == 200:
                        per_page_results = response.json()

                    image_as_np_array = chapter_pages_image_numpy_array[page_num]
                    page_result_predictions = per_page_results[0]

                    # This will save the cropped panels one page at a time.
                    self.save_cropped_panels(
                        image_as_np_array,
                        page_result_predictions,
                        f"{output_directory}/panel-by-panel/grouped-by-page/{series_and_chapter_name_directory}/page_{page_num + 1}",
                    )

                    page_num += 1
                except Exception as e:
                    print(e)

    def get_panels_using_local_cpu(
        self,
        chapter_pages_image_numpy_array,
        character_bank,
        series_and_chapter_name_directory,
        output_directory,
        flet_page_client_storage,
    ):
        # If the Magi Model is being ran on the local machine (like a Macbook), then send all of the Chapter's images in a batch at once.
        # We're not making a request to an external server so no limit on how big the numpy array is.
        per_page_results = self.get_per_page_results(
            chapter_pages_image_numpy_array, character_bank
        )

        for i, (image_as_np_array, page_result_predictions) in enumerate(
            zip(chapter_pages_image_numpy_array, per_page_results)
        ):
            self.save_cropped_panels(
                image_as_np_array,
                page_result_predictions,
                f"{output_directory}/panel-by-panel/grouped-by-page/{series_and_chapter_name_directory}/page_{i + 1}",
                flet_page_client_storage,
            )

        panel_by_panel_input_dir = f"{output_directory}/panel-by-panel/grouped-by-page/{series_and_chapter_name_directory}"
        panel_by_panel_output_dir = f"{output_directory}/panel-by-panel/not-grouped/{series_and_chapter_name_directory}"

        copy_panels_to_one_level_directory(
            panel_by_panel_input_dir, panel_by_panel_output_dir
        )


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    magi = Magi()

    input_directory = select_folder()
    output_directory = select_folder()

    magi.get_panels_for_chapter(input_directory, output_directory)
