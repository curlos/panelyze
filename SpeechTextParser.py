import pytesseract
from PIL import Image

from magi import Magi
from utils import time_it


class SpeechTextParser:
    def __init__(self):
        self.magi = Magi()

    def analyze_wpm(self):
        print("Hello World")


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    speech_text_parser = SpeechTextParser()

    @time_it()
    def extract_text_with_pytesseract():
        # Load the image
        image = Image.open("wpm-test/panel_40.png")

        # Extract text
        extracted_text = pytesseract.image_to_string(image)
        print(extracted_text)

    @time_it()
    def extract_text_with_magi():
        magi_data_from_images = speech_text_parser.magi.get_data_from_images("wpm-test")

        for magi_image_data in magi_data_from_images:
            print(magi_image_data)

            breakpoint()

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

    # extract_text_with_pytesseract()

    # extract_text_with_magi()

    essential_text = [
        "Ahh, don't worry... he was half-dead already. There was no saving him, no matter where he went.",
        "Well... unless he managed to resurrect himself as a zombie, of course... Fuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffu! Hey, it serves him right.",
        "And you call this doing your job, do you...?!!!",
    ]
