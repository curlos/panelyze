import pytesseract
from PIL import Image

from magi import Magi
from utils import time_it


class SpeechTextParser:
    def __init__(self):
        self.magi = Magi()

    def get_images_duration_based_on_wpm(self, images_directory, wpm):
        images_duration_based_on_wpm = []

        essential_text_list_in_image_list = self.get_essential_text_list_in_images(
            images_directory
        )

        for essential_text_list_in_image in essential_text_list_in_image_list:
            duration_based_on_wpm = self.calculate_reading_time(
                essential_text_list_in_image, wpm
            )
            print(f"Estimated reading time: {duration_based_on_wpm:.2f} seconds")

            images_duration_based_on_wpm.append(duration_based_on_wpm)

        return images_duration_based_on_wpm

    @time_it()
    def get_essential_text_list_in_images(self, images_directory):
        magi_data_from_images = self.magi.get_data_from_images(images_directory)

        essential_text_list_in_images = []

        for magi_image_data in magi_data_from_images:
            # "is_essential_text" from what I've seen so far with one panel will tell you what the "essential" text on the page is. For example, in "panel_40.png", the essential text are the text bubbles with the conversation between Doflamingo and the World Govt. official. However, on the page, there is a "World Govt" label in the background NOT in a speech bubble. This was deemed as NOT essential by Magi. This is very useful as I only want to take into account speech or thought bubbles - not background text for both the WPM and Text-To-Speech calculations.
            # "is_essential_text" will return an array of boolean values (such as [True, True, False, False, True])
            is_essential_text_arr = magi_image_data["is_essential_text"]

            # "ocr" will return an array of strings with all of the text on the page - including non-essential text.
            # Example = ["Ahh, don't worry... he was half-dead already. There was no saving him, no matter where he went.", 'Well... unless he managed to resurrect himself as a zombie, of course... Fuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffu! Hey, it serves him right.', "How'd", 'World', 'And you call this doing your job, do you...?!!!']
            ocr_text_arr = magi_image_data["ocr"]
            ocr_essential_text_arr = ocr_text_arr

            # Not sure if the lengths are ever not equal (seems unlikely) but just in case, filter out all of the non-essential text from the OCR array and only get what is essential and take that into account for WPM and Text-To-Speech calculations.
            if len(is_essential_text_arr) == len(ocr_text_arr):
                ocr_essential_text_arr = [
                    ocr_text_arr[i]
                    for i in range(len(ocr_text_arr))
                    if is_essential_text_arr[i]
                ]

            essential_text_list_in_images.append(ocr_essential_text_arr)

        return essential_text_list_in_images

    def calculate_reading_time(self, text_list, wpm=250):
        """Calculate the time required to read the text based on WPM."""
        # Join the list of strings into a single text
        full_text = " ".join(text_list)

        # Count the total number of words
        word_count = len(full_text.split())

        # Calculate reading time in seconds (WPM -> Words Per Second)
        reading_time_seconds = word_count / (wpm / 60)

        return reading_time_seconds


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    speech_text_parser = SpeechTextParser()

    essential_text = [
        "Ahh, don't worry... he was half-dead already. There was no saving him, no matter where he went.",
        "Well... unless he managed to resurrect himself as a zombie, of course... Fuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffu! Hey, it serves him right.",
        "And you call this doing your job, do you...?!!!",
    ]

    wpm = 250  # Adjust WPM as needed
    time_required = speech_text_parser.calculate_reading_time(essential_text, wpm)
    print(f"Estimated reading time: {time_required:.2f} seconds")
