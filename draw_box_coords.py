import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from PIL import Image

from magi_frieren_ch_55_panel_6_output import magi_frieren_ch_55_panel_6_output


def draw_box_coords(bbox, output_file_name):
    figure, subplot = plt.subplots(1, 1, figsize=(10, 10))

    with Image.open("z-tts-test-output/panel_6.png") as pil_image:
        subplot.imshow(pil_image)
        plt.axis("off")

        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        rect = patches.Rectangle(
            bbox[:2],
            w,
            h,
            linewidth=1,
            edgecolor="red",
            facecolor="none",
            linestyle="solid",
        )
        subplot.add_patch(rect)

    figure.savefig(output_file_name, bbox_inches="tight", pad_inches=0)
    plt.close()


texts_matrix = magi_frieren_ch_55_panel_6_output["texts"]

draw_box_coords(texts_matrix[0], "z-tts-test-output/panel_6-1.png")
draw_box_coords(texts_matrix[1], "z-tts-test-output/panel_6-2.png")
draw_box_coords(texts_matrix[2], "z-tts-test-output/panel_6-3.png")
