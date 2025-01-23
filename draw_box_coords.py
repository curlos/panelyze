import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
from utils import time_it

from magi_frieren_ch_55_panel_6_output import magi_frieren_ch_55_panel_6_output
from utils import modify_filename


def draw_box_coords_box(box_coords, base_pil_image, input_file_path, index):
    figure, subplot = plt.subplots(1, 1, figsize=(10, 10))
    subplot.imshow(base_pil_image)
    plt.axis("off")

    w = box_coords[2] - box_coords[0]
    h = box_coords[3] - box_coords[1]
    rect = patches.Rectangle(
        box_coords[:2],
        w,
        h,
        linewidth=1,
        edgecolor="red",
        facecolor="none",
        linestyle="solid",
    )
    subplot.add_patch(rect)

    output_file_name = modify_filename(input_file_path, index)
    figure.savefig(output_file_name, bbox_inches="tight", pad_inches=0)

    plt.close()


@time_it()
def draw_box_coords_box_list(text_matrix_boxes_coords, input_file_path):
    # Load the base image once as a PIL image
    with Image.open(input_file_path) as base_pil_image:
        base_pil_image.load()  # Ensure the image is fully loaded into memory

    for index, box_coords in enumerate(text_matrix_boxes_coords):
        draw_box_coords_box(box_coords, base_pil_image, input_file_path, index + 1)


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    text_matrix_boxes_coords = magi_frieren_ch_55_panel_6_output["texts"]
    draw_box_coords_box_list(text_matrix_boxes_coords, "z-tts-test-output/panel_6.png")
