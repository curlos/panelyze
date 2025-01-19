from moviepy import ImageClip, concatenate_videoclips
import os

from utils import (
    get_last_two_directories_obj,
    natural_sort_key,
    select_folder,
)


def create_video_from_images(
    image_folder,
    output_file,
    image_displayed_duration=3,
    video_height=1080,
    speech_text_parser=None,
    flet_page_client_storage=None,
):
    use_reading_speed_wpm = True
    reading_speed_wpm = 150
    images_duration_based_on_wpm = []

    use_minimum_image_duration = True
    minimum_image_duration = 5

    if flet_page_client_storage:
        use_reading_speed_wpm = flet_page_client_storage.get("use_reading_speed_wpm")
        reading_speed_wpm = int(flet_page_client_storage.get("reading_speed_wpm"))
        image_displayed_duration = int(
            flet_page_client_storage.get("image_displayed_duration") or 0
        )
        use_minimum_image_duration = flet_page_client_storage.get(
            "use_minimum_image_duration"
        )
        minimum_image_duration = int(
            flet_page_client_storage.get("minimum_image_duration") or 0
        )

    if speech_text_parser and use_reading_speed_wpm:
        images_duration_based_on_wpm = (
            speech_text_parser.get_images_duration_based_on_wpm(
                image_folder, reading_speed_wpm
            )
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
            get_img_duration(
                image_displayed_duration=float(image_displayed_duration),
                images_duration_based_on_wpm=images_duration_based_on_wpm,
                index=index,
                use_reading_speed_wpm=use_reading_speed_wpm,
                use_minimum_image_duration=use_minimum_image_duration,
                minimum_image_duration=minimum_image_duration,
            )
        )  # Set duration for each image
        for index, img in enumerate(images)
    ]

    # Concatenate all ImageClips into a single video
    video = concatenate_videoclips(clips, method="compose")

    # "fps" is set to 1 as the images being saved are typically going to be Manga Panels and will have no smooth transitions between panels so no need to create extra frames for nothing. Just show the same frame for the specified duration.
    video.write_videofile(output_file, fps=1)


def get_img_duration(
    image_displayed_duration,
    images_duration_based_on_wpm,
    index,
    use_reading_speed_wpm,
    use_minimum_image_duration,
    minimum_image_duration,
):
    final_image_duration = image_displayed_duration

    if use_reading_speed_wpm:
        final_image_duration = float(images_duration_based_on_wpm[index])

    if use_minimum_image_duration:
        # This is necessary because not every image will have text. So, for an image without text, "image_duration_based_on_wpm" would be 0 so the image would almost be skipped over in the video but obviously, we need to give the reader/viewer a chance to look at the image, so there should be a minimum duration (in this case it's 5 seconds).
        return max(final_image_duration, minimum_image_duration)

    return final_image_duration


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
