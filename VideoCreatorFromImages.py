import json
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from moviepy import (
    AudioClip,
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
)
import os

from TextToSpeech import TextToSpeech
from SpeechTextParser import SpeechTextParser
from DrawBoxCoords import DrawBoxCoords
from gui_classes.ProgressPanel import report_progress
from utils import (
    PANEL_TEXT_FILE_NAME,
    READING_DIRECTION_FILE_NAME,
    list_images,
)

# What Magi found in a folder of images is saved here, next to the transcript. Reading the text is the slowest part of making a video (minutes), so it's never done twice for the same images.
MAGI_DATA_FILE_NAME = "magi-data.json"
MAGI_DATA_FILE_VERSION = 1

# If this many voice-over lines in a row fail, something is wrong (like no internet), so the video stops instead of going on without a voice.
MAX_CONSECUTIVE_VOICE_OVER_FAILURES = 3

# Each voice-over line mostly waits on the internet, so a few are made at the same time.
VOICE_OVERS_AT_ONCE = 4

# Which codecs to use for each video format. MoviePy can't figure these out by itself for formats like ".mov".
VIDEO_CODECS_BY_EXTENSION = {
    "mp4": {"codec": "libx264", "audio_codec": "aac"},
    "mov": {"codec": "libx264", "audio_codec": "aac"},
}

# Video shapes as (width, height) ratios.
VIDEO_ASPECT_RATIOS = {
    "16:9": (16, 9),  # Landscape (YouTube)
    "9:16": (9, 16),  # Vertical (TikTok, YouTube Shorts, Instagram Reels)
    "1:1": (1, 1),  # Square
}


def get_json_value(value):
    """
    For saving Magi's results as JSON: they're lists and numbers, but some of the numbers can be NumPy or PyTorch ones.
    """
    if hasattr(value, "tolist"):
        return value.tolist()

    raise TypeError(f"Can't save {type(value).__name__} as JSON")


def get_audio_duration(audio_file_path):
    audio_clip = AudioFileClip(audio_file_path)
    duration = audio_clip.duration
    audio_clip.close()

    return duration


def get_number_setting(flet_page_client_storage, setting_key, default_value):
    """
    Settings are saved as strings (or can be empty), so convert them to a number safely.
    """
    try:
        return float(flet_page_client_storage.get(setting_key))
    except (TypeError, ValueError):
        return default_value


class VideoCreatorFromImages:
    def __init__(self, flet_page_client_storage=None):
        self.flet_page_client_storage = flet_page_client_storage
        self.speech_text_parser = SpeechTextParser()
        self.tts = TextToSpeech(self.flet_page_client_storage)
        self.draw_box_coords = DrawBoxCoords(self.flet_page_client_storage)

        self.consecutive_voice_over_failures = 0
        self.voice_over_lock = threading.Lock()

        self.video_height = 1080
        self.video_aspect_ratio = "16:9"
        self.image_displayed_duration = 3

        self.use_reading_speed_wpm = True
        self.reading_speed_wpm = 150

        self.use_minimum_image_duration = True
        self.minimum_image_duration = 3

        self.use_text_to_speech_azure = False
        self.image_pre_tts_audio_delay = 0
        self.image_post_tts_audio_delay = 0

        self.highlight_text_boxes_in_images = False

        self.clean_up_images_with_highlighted_text_boxes_folder = False
        self.clean_up_tts_audio_files_folder = False

        self.initialize_flet_client_storage_values()

    def initialize_flet_client_storage_values(self, flet_page_client_storage=None):
        if flet_page_client_storage:
            self.flet_page_client_storage = flet_page_client_storage
            self.draw_box_coords.initialize_flet_client_storage_values(
                self.flet_page_client_storage
            )

        if self.flet_page_client_storage:
            storage = self.flet_page_client_storage

            self.video_height = int(get_number_setting(storage, "video_height", 1080))
            self.video_aspect_ratio = storage.get("video_aspect_ratio") or "16:9"
            self.speech_text_parser.reading_direction = (
                storage.get("reading_direction") or "auto"
            )
            self.image_displayed_duration = get_number_setting(
                storage, "image_displayed_duration", 3
            )
            self.use_reading_speed_wpm = self.flet_page_client_storage.get(
                "use_reading_speed_wpm"
            )
            self.reading_speed_wpm = get_number_setting(
                storage, "reading_speed_wpm", 150
            )

            self.use_minimum_image_duration = self.flet_page_client_storage.get(
                "use_minimum_image_duration"
            )
            self.minimum_image_duration = get_number_setting(
                storage, "minimum_image_duration", 0
            )

            self.use_text_to_speech_azure = self.flet_page_client_storage.get(
                "use_text_to_speech_azure"
            )
            self.image_pre_tts_audio_delay = get_number_setting(
                storage, "image_pre_tts_audio_delay", 0
            )
            self.image_post_tts_audio_delay = get_number_setting(
                storage, "image_post_tts_audio_delay", 0
            )

            self.highlight_text_boxes_in_images = self.flet_page_client_storage.get(
                "highlight_text_boxes_in_images"
            )

            self.clean_up_images_with_highlighted_text_boxes_folder = (
                self.flet_page_client_storage.get(
                    "clean_up_images_with_highlighted_text_boxes_folder"
                )
            )
            self.clean_up_tts_audio_files_folder = self.flet_page_client_storage.get(
                "clean_up_tts_audio_files_folder"
            )

    def create_video_from_images(
        self,
        image_folder,
        output_file,
        full_output_directory=None,
    ):
        images_duration_based_on_wpm = []
        images_duration_based_on_tts = []
        images_with_highlighted_text_boxes_folder = os.path.join(
            full_output_directory, "images-with-highlighted-text-boxes"
        )
        full_audio_files_output_directory = f"{full_output_directory}/audio-files"

        images = list_images(image_folder)

        report_progress(detail="Reading the text in the images...")
        (essential_text_in_images_matrix, magi_output_data) = (
            self.get_essential_text_and_magi_data(
                image_folder, full_output_directory, image_count=len(images)
            )
        )

        if images_with_highlighted_text_boxes_folder and os.path.exists(
            images_with_highlighted_text_boxes_folder
        ):
            # Remove the directory and all its contents
            shutil.rmtree(images_with_highlighted_text_boxes_folder)
            print('Removed "images-with-highlighted-text-boxes" folders')

        if full_audio_files_output_directory and os.path.exists(
            full_audio_files_output_directory
        ):
            # Remove the directory and all its contents
            shutil.rmtree(full_audio_files_output_directory)
            print('Removed TTS "audio-files" folders')

        if self.use_text_to_speech_azure:
            images_duration_based_on_tts = self.get_images_duration_based_on_tts(
                images,
                images_with_highlighted_text_boxes_folder,
                full_audio_files_output_directory,
                essential_text_in_images_matrix,
                magi_output_data,
            )
        elif self.use_reading_speed_wpm:
            self.draw_boxes_with_text_and_magi_data(
                images,
                images_with_highlighted_text_boxes_folder,
                magi_output_data,
                one_box_per_image=True,
            )

            images_duration_based_on_wpm = (
                self.speech_text_parser.get_images_duration_based_on_wpm(
                    image_folder,
                    self.reading_speed_wpm,
                    one_text_str_at_a_time=self.highlight_text_boxes_in_images,
                    essential_text_in_images_matrix=essential_text_in_images_matrix,
                )
            )
        else:
            # For "Use Image Displayed Duration (sec.)"
            self.draw_boxes_with_text_and_magi_data(
                images,
                images_with_highlighted_text_boxes_folder,
                magi_output_data,
                one_box_per_image=False,
            )

        # Ensure the output directory exists
        output_directory = os.path.dirname(output_file)
        os.makedirs(output_directory, exist_ok=True)

        # Create a list of ImageClips, resizing them to fit the video height
        clips = self.get_clips(
            images,
            images_with_highlighted_text_boxes_folder,
            images_duration_based_on_wpm,
            images_duration_based_on_tts,
            full_output_directory,
        )

        # Concatenate all ImageClips into a single video. Every clip is already the full video frame size, so they can simply be played one after another ("chain"), which is much faster than "compose".
        video = concatenate_videoclips(clips, method="chain")

        fps = 1

        if self.highlight_text_boxes_in_images or self.use_text_to_speech_azure:
            fps = 5

        # "fps" is set to 1 as the images being saved are typically going to be Manga Panels and will have no smooth transitions between panels so no need to create extra frames for nothing. Just show the same frame for the specified duration.
        video_extension = os.path.splitext(output_file)[1].lstrip(".").lower()
        codecs = VIDEO_CODECS_BY_EXTENSION.get(
            video_extension, VIDEO_CODECS_BY_EXTENSION["mp4"]
        )
        report_progress(
            pages_done=None, pages_total=None, detail="Writing the video file..."
        )
        video.write_videofile(output_file, fps=fps, **codecs)

        if (
            self.highlight_text_boxes_in_images
            and self.clean_up_images_with_highlighted_text_boxes_folder
            and images_with_highlighted_text_boxes_folder
            and os.path.exists(images_with_highlighted_text_boxes_folder)
        ):
            # Remove the directory and all its contents
            shutil.rmtree(images_with_highlighted_text_boxes_folder)
            print('Removed "images-with-highlighted-text-boxes" folders')

        if (
            self.use_text_to_speech_azure
            and self.clean_up_tts_audio_files_folder
            and full_audio_files_output_directory
            and os.path.exists(full_audio_files_output_directory)
        ):
            # Remove the directory and all its contents
            shutil.rmtree(full_audio_files_output_directory)
            print('Removed TTS "audio-files" folders')

    def get_images_duration_based_on_tts(
        self,
        images,
        images_with_highlighted_text_boxes_folder,
        full_audio_files_output_directory,
        essential_text_in_images_matrix,
        magi_output_data,
    ):
        self.consecutive_voice_over_failures = 0
        self.draw_boxes_with_text_and_magi_data(
            images,
            images_with_highlighted_text_boxes_folder,
            magi_output_data,
            one_box_per_image=True,
        )
        os.makedirs(full_audio_files_output_directory, exist_ok=True)

        # Every voice-over file to make, as (text lines, audio file), in the order they're shown: one for each line when highlighting, otherwise one for each image. "None" is an image without text.
        voice_overs = []
        for image_path, panel_text_arr in zip(images, essential_text_in_images_matrix):
            base_name, _ = os.path.splitext(os.path.basename(image_path))

            if not panel_text_arr:
                voice_overs.append(None)
            elif self.highlight_text_boxes_in_images:
                for line_number, text_str in enumerate(panel_text_arr, start=1):
                    voice_overs.append(
                        ([text_str], f"{full_audio_files_output_directory}/{base_name}-{line_number}.mp3")
                    )
            else:
                voice_overs.append(
                    (panel_text_arr, f"{full_audio_files_output_directory}/{base_name}.mp3")
                )

        voice_overs_to_make = [voice_over for voice_over in voice_overs if voice_over]
        voice_overs_made = 0
        report_progress(
            pages_done=0, pages_total=len(voice_overs_to_make), detail="Making the voice-over"
        )

        voice_over_stopped = threading.Event()

        def make_voice_over(voice_over):
            nonlocal voice_overs_made
            # If the voice-over stopped (e.g. no internet), don't try the lines that are still waiting.
            if voice_over_stopped.is_set():
                return

            try:
                self.generate_voice_over(*voice_over)
            except Exception:
                voice_over_stopped.set()
                raise

            with self.voice_over_lock:
                voice_overs_made += 1
                report_progress(pages_done=voice_overs_made)

        with ThreadPoolExecutor(max_workers=VOICE_OVERS_AT_ONCE) as executor:
            list(executor.map(make_voice_over, voice_overs_to_make))

        # No audio file is made for an image without text, or for text that can't be said out loud, so it's shown for 1 second.
        return [
            get_audio_duration(voice_over[1])
            if voice_over and os.path.exists(voice_over[1])
            else 1
            for voice_over in voice_overs
        ]

    def draw_boxes_with_text_and_magi_data(
        self,
        images,
        images_with_highlighted_text_boxes_folder,
        magi_output_data,
        one_box_per_image=True,
    ):
        if self.highlight_text_boxes_in_images:
            for index, image_file in enumerate(images):
                magi_image_data = magi_output_data[index]
                text_matrix_boxes_coords = magi_image_data["texts"]
                essential_text_arr = magi_image_data["is_essential_text"]

                essential_text_matrix_boxes_coords = [
                    box_coords
                    for index, box_coords in enumerate(text_matrix_boxes_coords)
                    if essential_text_arr[index]
                ]

                self.draw_box_coords.draw_box_coords_box_list(
                    essential_text_matrix_boxes_coords,
                    image_file,
                    images_with_highlighted_text_boxes_folder,
                    one_box_per_image=one_box_per_image,
                )

    def get_img_duration(
        self, images_duration_based_on_wpm, images_duration_based_on_tts, index
    ):
        final_image_duration = self.image_displayed_duration

        if self.use_text_to_speech_azure:
            final_image_duration = float(images_duration_based_on_tts[index])
        elif self.use_reading_speed_wpm:
            final_image_duration = float(images_duration_based_on_wpm[index])

        if self.use_minimum_image_duration:
            # This is necessary because not every image will have text. So, for an image without text, "image_duration_based_on_wpm" would be 0 so the image would almost be skipped over in the video but obviously, we need to give the reader/viewer a chance to look at the image, so there should be a minimum duration (in this case it's 5 seconds).
            return max(final_image_duration, self.minimum_image_duration)

        return final_image_duration

    def get_video_frame_size(self):
        """
        The "video_height" setting is the video's resolution, like "1080p": it's the length of the shorter side. So 1080 gives 1920x1080 for 16:9, 1080x1920 for 9:16 and 1080x1080 for 1:1. The width and height must be even numbers for most video codecs.
        """
        ratio_width, ratio_height = VIDEO_ASPECT_RATIOS.get(
            self.video_aspect_ratio, VIDEO_ASPECT_RATIOS["16:9"]
        )
        shorter_side = int(self.video_height)
        if shorter_side < 2:
            shorter_side = 1080
        scale = shorter_side / min(ratio_width, ratio_height)

        video_width = round(ratio_width * scale) // 2 * 2
        video_height = round(ratio_height * scale) // 2 * 2

        return (video_width, video_height)

    def get_image_clip_fit_to_video_frame(self, image_path):
        """
        Scale the image so that it fits inside the video frame and center it on a black background. Without this, one very wide or very tall panel would change the size of the whole video.
        """
        video_width, video_height = self.get_video_frame_size()
        image_clip = ImageClip(image_path)

        scale = min(video_width / image_clip.w, video_height / image_clip.h)
        image_clip = image_clip.resized(scale)

        return CompositeVideoClip(
            [image_clip.with_position("center")],
            size=(video_width, video_height),
            bg_color=(0, 0, 0),
        )

    def get_essential_text_and_magi_data(
        self, image_folder, full_output_directory, image_count=None
    ):
        # A fixed duration per image without text-to-speech or highlighting doesn't use the text at all, so don't spend time loading and running Magi.
        text_is_needed = (
            self.use_text_to_speech_azure
            or self.use_reading_speed_wpm
            or self.highlight_text_boxes_in_images
        )
        if not text_is_needed:
            return ([[] for _ in range(image_count or 0)], None)

        magi_output_data = None
        magi_data_signature = self.get_magi_data_signature(image_folder)
        essential_text_from_transcript = self.get_essential_text_from_transcript(
            full_output_directory
        )

        # Only reuse a saved transcript if it still matches the images. If the number of images changed, the text would end up on the wrong images (or crash).
        # When highlighting text boxes, each line of text has to match one of Magi's text boxes exactly, so a hand-edited transcript can't be used there either.
        transcript_does_not_match_images = (
            essential_text_from_transcript is not None
            and image_count is not None
            and len(essential_text_from_transcript) != image_count
        )

        if transcript_does_not_match_images or (
            essential_text_from_transcript and self.highlight_text_boxes_in_images
        ):
            if transcript_does_not_match_images:
                print(
                    "The saved transcript doesn't match the number of images. Reading the text with Magi instead."
                )

            essential_text_from_transcript = None

        if essential_text_from_transcript:
            essential_text_in_images_matrix = essential_text_from_transcript
        else:
            # What Magi found last time for these same images, if anything.
            magi_output_data = self.load_saved_magi_data(
                full_output_directory, magi_data_signature
            )

            # The text Panel-By-Panel already read on the pages. Highlighting needs where the text is on each panel, which that doesn't have.
            panel_text = (
                None
                if self.highlight_text_boxes_in_images
                else self.get_panel_text(image_folder, image_count)
            )

            if magi_output_data is not None:
                essential_text_in_images_matrix = (
                    self.speech_text_parser.get_essential_text_list_from_magi_data(
                        magi_output_data
                    )
                )
            elif panel_text is not None:
                essential_text_in_images_matrix = panel_text
            else:
                essential_text_in_images_matrix = (
                    self.speech_text_parser.get_essential_text_list_in_images(
                        image_folder
                    )
                )
                magi_output_data = self.speech_text_parser.last_magi_data
                self.save_magi_data(
                    full_output_directory, magi_data_signature, magi_output_data
                )

        # The text was read from an existing transcript so Magi didn't run. Highlighting the text boxes needs the box positions from Magi though.
        if self.highlight_text_boxes_in_images and magi_output_data is None:
            magi_output_data = self.load_saved_magi_data(
                full_output_directory, magi_data_signature
            )

        if self.highlight_text_boxes_in_images and magi_output_data is None:
            magi_output_data = self.speech_text_parser.magi.get_data_from_images(
                image_folder, self.speech_text_parser.reading_direction
            )
            self.save_magi_data(
                full_output_directory, magi_data_signature, magi_output_data
            )

        self.save_essential_text_to_transcript(
            essential_text_in_images_matrix, full_output_directory
        )

        return (essential_text_in_images_matrix, magi_output_data)

    def get_panel_text(self, image_folder, image_count):
        """
        The dialogue on each image that Panel-By-Panel read on the pages ("PANEL_TEXT_FILE_NAME"), or None if there isn't any or it doesn't match these images.
        """
        try:
            with open(os.path.join(image_folder, PANEL_TEXT_FILE_NAME), encoding="utf-8") as file:
                panel_text = json.load(file)
        except (OSError, ValueError):
            return None

        # E.g. an image failed to upscale, so the lines would end up on the wrong images.
        if not isinstance(panel_text, list) or len(panel_text) != image_count:
            print("The text Panel-By-Panel read doesn't match these images. Reading the text with Magi instead.")
            return None

        print("Using the text Panel-By-Panel read on the pages (no need to run Magi again).")
        return panel_text

    def get_magi_data_signature(self, image_folder):
        """
        What the saved Magi results were made from. If the images or the reading direction change, they can't be used. That includes the direction saved next to the images, which "Automatic" uses.
        """
        saved_reading_direction_file = os.path.join(image_folder, READING_DIRECTION_FILE_NAME)
        saved_reading_direction = None
        if os.path.isfile(saved_reading_direction_file):
            with open(saved_reading_direction_file, encoding="utf-8") as file:
                saved_reading_direction = file.read().strip()

        return {
            "version": MAGI_DATA_FILE_VERSION,
            "reading_direction": self.speech_text_parser.reading_direction,
            "saved_reading_direction": saved_reading_direction,
            "images": [
                [os.path.basename(image_path), os.path.getsize(image_path)]
                for image_path in list_images(image_folder)
            ],
        }

    def load_saved_magi_data(self, full_output_directory, signature):
        """
        The results Magi saved for these same images, or None if there aren't any (or they're from other images).
        """
        try:
            with open(
                os.path.join(full_output_directory, MAGI_DATA_FILE_NAME), encoding="utf-8"
            ) as file:
                saved = json.load(file)
        except (OSError, ValueError):
            return None

        if not isinstance(saved, dict) or saved.get("signature") != signature:
            return None

        print("Using the results Magi saved for these images (no need to run it again).")
        return saved.get("magi_data")

    def save_magi_data(self, full_output_directory, signature, magi_data):
        # Saving is only a shortcut for next time, so it must never stop the video.
        try:
            os.makedirs(full_output_directory, exist_ok=True)
            file_path = os.path.join(full_output_directory, MAGI_DATA_FILE_NAME)
            temporary_file_path = f"{file_path}.tmp"

            with open(temporary_file_path, "w", encoding="utf-8") as file:
                json.dump(
                    {"signature": signature, "magi_data": magi_data},
                    file,
                    default=get_json_value,
                )

            # Replaced in one step, so a half-written file can never be left behind.
            os.replace(temporary_file_path, file_path)
        except Exception as error:
            print(f"Couldn't save Magi's results ({error}). It will be run again next time.")

    def generate_voice_over(self, text_list, output_file):
        """
        One line that can't be turned into speech shouldn't throw away a whole video (the text takes minutes to read), so it's skipped and has no voice. But if several in a row fail, something is wrong (like no internet), so that stops the video.
        """
        try:
            self.tts.generate_audio(text_list, output_file)

            with self.voice_over_lock:
                self.consecutive_voice_over_failures = 0
        except Exception as error:
            # A few voice-overs are made at the same time, so only one at a time may change the count.
            with self.voice_over_lock:
                self.consecutive_voice_over_failures += 1
                too_many_failures = (
                    self.consecutive_voice_over_failures
                    >= MAX_CONSECUTIVE_VOICE_OVER_FAILURES
                )

            if too_many_failures:
                raise

            print(f"WARNING: Couldn't make the voice-over for {text_list}: {error}. It's skipped.")

            # A failed attempt can leave a partial file behind.
            if os.path.exists(output_file):
                os.remove(output_file)

    def save_essential_text_to_transcript(
        self, essential_text_in_images_matrix, full_output_directory
    ):
        # Ensure the directory exists
        os.makedirs(full_output_directory, exist_ok=True)

        # Save each sentence on a new line with a separator between arrays
        with open(f"{full_output_directory}/transcript.txt", "w") as file:
            for image_text_arr in essential_text_in_images_matrix:
                if image_text_arr:  # Non-empty array
                    for sentence in image_text_arr:
                        file.write(sentence + "\n")
                # Add the separator for the next array
                file.write("------ new image ------\n")

        print("Transcript saved with separators.")

    def get_essential_text_from_transcript(self, full_output_directory):
        # Check if the directory exists
        if not os.path.isdir(full_output_directory):
            print(
                f"Directory '{full_output_directory}' does not exist. Skipping operation."
            )
            return None

        transcript_path = f"{full_output_directory}/transcript.txt"

        # Check if the transcript file exists
        if not os.path.exists(transcript_path):
            print(
                f"Transcript file '{transcript_path}' does not exist. Skipping operation."
            )
            return None

        # Read the transcript file
        with open(transcript_path, "r") as file:
            lines = file.readlines()

        loaded_arrays = []  # List to store all arrays
        current_array = []  # Temporary list for the current array

        for line in lines:
            line = line.strip()
            if line == "------ new image ------":  # Separator marks the end of an array
                loaded_arrays.append(current_array)  # Append the current array
                current_array = []  # Reset for the next array
            else:
                if line:  # Skip blank lines (there's nothing to read out loud)
                    current_array.append(line)  # Add line to the current array

        # Add the last array if the file doesn't end with the separator
        if current_array:
            loaded_arrays.append(current_array)

        return loaded_arrays

    def get_clips(
        self,
        images,
        images_with_highlighted_text_boxes_folder,
        images_duration_based_on_wpm,
        images_duration_based_on_tts,
        full_output_directory,
    ):
        clips = []

        image_paths_to_use = images

        if self.highlight_text_boxes_in_images:
            image_paths_to_use = list_images(images_with_highlighted_text_boxes_folder)

        for index, img in enumerate(image_paths_to_use):
            # Extract base name of the image (e.g., panel_1.png -> panel_1)
            base_name, _ = os.path.splitext(os.path.basename(img))
            audio_path = os.path.join(
                full_output_directory, f"audio-files/{base_name}.mp3"
            )

            img_duration = self.get_img_duration(
                images_duration_based_on_wpm=images_duration_based_on_wpm,
                images_duration_based_on_tts=images_duration_based_on_tts,
                index=index,
            )

            image_clip = self.get_image_clip_fit_to_video_frame(img).with_duration(
                img_duration
            )

            # Check if the corresponding audio file exists
            if os.path.exists(audio_path):
                # Get the actual duration of the audio file
                audio_clip = AudioFileClip(audio_path)
                audio_duration = audio_clip.duration

                # When each line of text gets its own highlighted image, the image should only last as long as its line of audio. Otherwise, keep the full image duration (which includes the minimum image duration).
                if self.highlight_text_boxes_in_images:
                    adjusted_duration = audio_duration
                else:
                    adjusted_duration = max(img_duration, audio_duration)

                # Make sure the audio never runs longer than the image.
                audio_clip = audio_clip.subclipped(
                    0, min(audio_duration, adjusted_duration)
                )

                combined_audio_clips = audio_clip

                use_image_pre_tts_audio_delay = True

                # Check if the image can use "Pre-TTS"
                if self.highlight_text_boxes_in_images:
                    current_panel_num = int(base_name.rsplit("-", 1)[1])
                    is_first_base_panel_image = current_panel_num == 1

                    if not is_first_base_panel_image:
                        use_image_pre_tts_audio_delay = False

                if self.image_pre_tts_audio_delay > 0 and use_image_pre_tts_audio_delay:
                    adjusted_duration += self.image_pre_tts_audio_delay

                    # Add padding before the audio starts
                    padding_before_audio_file_clip = AudioClip(
                        lambda t: 0, duration=self.image_pre_tts_audio_delay
                    )

                    # Combine the silent audio and actual audio
                    combined_audio_clips = CompositeAudioClip(
                        [
                            padding_before_audio_file_clip.with_start(0),
                            audio_clip.with_start(self.image_pre_tts_audio_delay),
                        ]
                    )

                use_image_post_tts_audio_delay = True

                # If the image is the last image in the directory or the next image after this one has a different starting base_name, then add the post_tts_delay. Else, do not add it.
                if self.highlight_text_boxes_in_images:
                    is_last_image_in_dir = index == len(image_paths_to_use) - 1

                    if not is_last_image_in_dir:
                        next_image_path = image_paths_to_use[index + 1]
                        next_panel_base_name, _ = os.path.splitext(
                            os.path.basename(next_image_path)
                        )

                        # Highlighted images are named "<original name>-<line number>". Use "rsplit" in case the original name has a "-" in it too.
                        current_panel_starting_base_name = base_name.rsplit("-", 1)[0]
                        next_panel_starting_base_name = next_panel_base_name.rsplit(
                            "-", 1
                        )[0]

                        last_highlighted_text_image_for_panel = (
                            current_panel_starting_base_name
                            != next_panel_starting_base_name
                        )

                        if not last_highlighted_text_image_for_panel:
                            use_image_post_tts_audio_delay = False

                if use_image_post_tts_audio_delay:
                    adjusted_duration += self.image_post_tts_audio_delay

                # Update the image clip's duration and add the audio
                image_clip = image_clip.with_duration(adjusted_duration).with_audio(
                    combined_audio_clips
                )

            # Add the clip to the list
            clips.append(image_clip)

        return clips
