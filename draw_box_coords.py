import os
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
from utils import time_it

matplotlib.use("Agg")

from utils import modify_filename
from magi_frieren_ch_55_panel_6_output import magi_frieren_ch_55_panel_6_output
from magi_ch_55_frieren_panel_1_to_7_output import (
    magi_ch_55_frieren_panel_1_to_7_output,
)


def draw_box_coords_box(
    box_coords,
    base_pil_image,
    input_file_path,
    index,
    output_image_folder,
    flet_page_client_storage,
):
    images_to_video_text_box_color = "red"
    images_to_video_line_width = 1

    if flet_page_client_storage:
        images_to_video_text_box_color = flet_page_client_storage.get(
            "images_to_video_text_box_color"
        )
        images_to_video_line_width = int(
            float(flet_page_client_storage.get("images_to_video_line_width"))
        )

    figure, subplot = plt.subplots(1, 1, figsize=(10, 10))
    subplot.imshow(base_pil_image)
    plt.axis("off")

    width = box_coords[2] - box_coords[0]
    height = box_coords[3] - box_coords[1]

    top_left_box_coords = box_coords[:2]

    # Add padding to the box coordinates
    padding = 15  # Adjust this value as needed

    rect = patches.Rectangle(
        (
            top_left_box_coords[0] - padding,  # Move left by padding
            top_left_box_coords[1] - padding,  # Move up by padding
        ),
        width + 2 * padding,  # Add padding to width on both sides
        height + 2 * padding,  # Add padding to height on top and bottom
        linewidth=images_to_video_line_width,
        edgecolor=images_to_video_text_box_color,
        facecolor="none",
        linestyle="solid",
    )

    subplot.add_patch(rect)

    output_file_name = get_output_file_name(input_file_path, index, output_image_folder)

    figure.savefig(output_file_name, bbox_inches="tight", pad_inches=0)

    plt.close()


@time_it()
def draw_box_coords_box_list(
    text_matrix_boxes_coords,
    input_file_path,
    output_image_folder,
    flet_page_client_storage,
):
    if len(text_matrix_boxes_coords) == 0:
        output_file_name = get_output_file_name(input_file_path, 1, output_image_folder)
        image_copy = Image.open(input_file_path)

        image_copy.save(output_file_name)
        return

    # Load the base image once as a PIL image
    with Image.open(input_file_path) as base_pil_image:
        base_pil_image.load()  # Ensure the image is fully loaded into memory

    for index, box_coords in enumerate(text_matrix_boxes_coords):
        draw_box_coords_box(
            box_coords,
            base_pil_image,
            input_file_path,
            index + 1,
            output_image_folder,
            flet_page_client_storage,
        )


def get_output_file_name(input_file_path, index, output_image_folder):
    output_file_name = modify_filename(input_file_path, index)
    base_name = os.path.basename(output_file_name)
    output_file_name = os.path.join(output_image_folder, base_name)
    os.makedirs(output_image_folder, exist_ok=True)

    return output_file_name


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    text_matrix_boxes_coords = magi_ch_55_frieren_panel_1_to_7_output[0]["texts"]
    draw_box_coords_box_list(
        text_matrix_boxes_coords,
        "z-tts-test-output-2/panel_1.png",
        "/Volumes/Macintosh HD/Users/curlos/Desktop/Github Repos/manga-panel-splitter/z-tts-test-output-2/TESTING/images-with-highlighted-text-boxes",
    )
