from moviepy import ImageClip, concatenate_videoclips
import os
import re

from utils import select_folder


def natural_sort_key(filename):
    """
    Extracts numbers from filenames for natural sorting.
    For example, 'panel_10.jpg' -> [10], so it can be sorted correctly.
    """
    return [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", filename)]


def create_video_from_images(image_folder, output_file, duration=3, video_height=1080):
    # Get all image file paths from the folder and sort them naturally
    images = [
        os.path.join(image_folder, img)
        for img in sorted(os.listdir(image_folder), key=natural_sort_key)
        if img.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif"))
    ]

    # Create a list of ImageClips, resizing them to fit the video height
    clips = [
        ImageClip(img)
        .resized(height=video_height)  # Resize to fit the height of the video
        .with_duration(duration)  # Set duration for each image
        for img in images
    ]

    # Concatenate all ImageClips into a single video
    video = concatenate_videoclips(clips, method="compose")

    # Write the video to the output file
    video.write_videofile(output_file, fps=1)


# Example usage
image_folder = select_folder()
output_file = f"485_fps_1.mp4"
create_video_from_images(image_folder, output_file)
