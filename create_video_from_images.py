from moviepy import ImageClip, concatenate_videoclips
import os
import re

from utils import get_last_two_directories_obj, select_folder


def natural_sort_key(filename):
    """
    Extracts numbers from filenames for natural sorting.
    For example, 'panel_10.jpg' -> [10], so it can be sorted correctly.
    """
    return [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", filename)]


def create_video_from_images(
    image_folder, output_file, duration=3, video_height=1080, speech_text_parser=None
):
    use_wpm = True
    wpm = 250
    images_duration_based_on_wpm = []

    if use_wpm and speech_text_parser:
        images_duration_based_on_wpm = (
            speech_text_parser.get_images_duration_based_on_wpm(image_folder, wpm)
        )

    # Ensure the output directory exists
    output_directory = os.path.dirname(output_file)
    os.makedirs(output_directory, exist_ok=True)

    # Get all image file paths from the folder and sort them naturally
    images = [
        os.path.join(image_folder, img)
        for img in sorted(os.listdir(image_folder), key=natural_sort_key)
        if img.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
    ]

    # Create a list of ImageClips, resizing them to fit the video height
    clips = [
        ImageClip(img)
        .resized(height=int(video_height))  # Resize to fit the height of the video
        .with_duration(
            get_img_duration(int(duration), images_duration_based_on_wpm, index)
        )  # Set duration for each image
        for index, img in enumerate(images)
    ]

    # Concatenate all ImageClips into a single video
    video = concatenate_videoclips(clips, method="compose")

    # "fps" is set to 1 as the images being saved are typically going to be Manga Panels and will have no smooth transitions between panels so no need to create extra frames for nothing. Just show the same frame for the specified duration.
    video.write_videofile(output_file, fps=1)


def get_img_duration(duration, images_duration_based_on_wpm, index):
    if images_duration_based_on_wpm and images_duration_based_on_wpm[index]:
        return int(images_duration_based_on_wpm[index])

    return duration


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    print("Select Input Directory:")
    input_directory = select_folder()

    print("Select Output Directory:")
    output_directory = select_folder()

    series_name, chapter_name = get_last_two_directories_obj(input_directory)
    output_file = f"{output_directory}/{series_name}/{chapter_name}.mp4"

    print(f'Creating video "{series_name}/{chapter_name}.mp4"')
    create_video_from_images(input_directory, output_file)
