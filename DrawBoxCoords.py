import os
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
from utils import hex_to_rgb, time_it

matplotlib.use("Agg")

from utils import modify_filename
from magi_frieren_ch_55_panel_6_output import magi_frieren_ch_55_panel_6_output
from magi_ch_55_frieren_panel_1_to_7_output import (
    magi_ch_55_frieren_panel_1_to_7_output,
)


class DrawBoxCoords:
    def __init__(self, flet_page_client_storage=None):
        self.flet_page_client_storage = flet_page_client_storage

        self.images_to_video_text_box_border_color = "red"
        self.images_to_video_text_box_border_width = 1
        self.images_to_video_text_box_padding = 15
        self.images_to_video_text_box_background_color = (
            "#eab308"  # Yellow is the default color.
        )

        self.images_to_video_text_box_border_color_opacity = 0
        self.images_to_video_text_box_background_color_opacity = 0

        self.images_to_video_text_box_border_style = "solid"

        self.initialize_flet_client_storage_values()

    def initialize_flet_client_storage_values(self, flet_page_client_storage=None):
        if flet_page_client_storage:
            self.flet_page_client_storage = flet_page_client_storage

        if self.flet_page_client_storage:
            self.images_to_video_text_box_border_width = int(
                float(
                    self.flet_page_client_storage.get(
                        "images_to_video_text_box_border_width"
                    )
                )
            )
            self.images_to_video_text_box_padding = int(
                float(
                    self.flet_page_client_storage.get(
                        "images_to_video_text_box_padding"
                    )
                )
            )

            self.images_to_video_text_box_border_color = (
                self.flet_page_client_storage.get(
                    "images_to_video_text_box_border_color"
                )
            )

            self.images_to_video_text_box_border_color_opacity = float(
                self.flet_page_client_storage.get(
                    "images_to_video_text_box_border_color_opacity"
                )
            )

            self.images_to_video_text_box_background_color = (
                self.flet_page_client_storage.get(
                    "images_to_video_text_box_background_color"
                )
            )
            self.images_to_video_text_box_background_color_opacity = float(
                self.flet_page_client_storage.get(
                    "images_to_video_text_box_background_color_opacity"
                )
            )

            self.images_to_video_text_box_border_style = (
                self.flet_page_client_storage.get(
                    "images_to_video_text_box_border_style"
                )
            )

    def draw_box_coords_box(
        self,
        box_coords_matrix,
        base_pil_image,
        input_file_path,
        index,
        output_image_folder,
    ):

        figure, subplot = plt.subplots(1, 1, figsize=(10, 10))
        subplot.imshow(base_pil_image)
        plt.axis("off")

        for box_coords in box_coords_matrix:
            width = box_coords[2] - box_coords[0]
            height = box_coords[3] - box_coords[1]
            top_left_box_coords = box_coords[:2]

            border_color = (0, 0, 0, 0)
            background_color = (0, 0, 0, 0)

            if self.images_to_video_text_box_border_color != "transparent":
                border_color = hex_to_rgb(
                    self.images_to_video_text_box_border_color
                ) + (self.images_to_video_text_box_border_color_opacity,)

            if self.images_to_video_text_box_background_color != "transparent":
                background_color = hex_to_rgb(
                    self.images_to_video_text_box_background_color
                ) + (self.images_to_video_text_box_background_color_opacity,)

            rect = patches.Rectangle(
                (
                    top_left_box_coords[0]
                    - self.images_to_video_text_box_padding,  # Move left by padding
                    top_left_box_coords[1]
                    - self.images_to_video_text_box_padding,  # Move up by padding
                ),
                width
                + 2
                * self.images_to_video_text_box_padding,  # Add padding to width on both sides
                height
                + 2
                * self.images_to_video_text_box_padding,  # Add padding to height on top and bottom
                linewidth=self.images_to_video_text_box_border_width,
                edgecolor=border_color,
                facecolor=background_color,
                linestyle=self.images_to_video_text_box_border_style,
            )

            subplot.add_patch(rect)

        output_file_name = self.get_output_file_name(
            input_file_path, index, output_image_folder
        )
        figure.savefig(output_file_name, bbox_inches="tight", pad_inches=0)
        plt.close()

    @time_it()
    def draw_box_coords_box_list(
        self,
        text_matrix_boxes_coords,
        input_file_path,
        output_image_folder,
        one_box_per_image=False,
    ):
        if len(text_matrix_boxes_coords) == 0:
            output_file_name = self.get_output_file_name(
                input_file_path, 1, output_image_folder
            )
            image_copy = Image.open(input_file_path)

            image_copy.save(output_file_name)
            return

        # Load the base image once as a PIL image
        with Image.open(input_file_path) as base_pil_image:
            base_pil_image.load()  # Ensure the image is fully loaded into memory

        if one_box_per_image:
            for index, box_coords in enumerate(text_matrix_boxes_coords):
                box_coords_single_matrix = [box_coords]
                self.draw_box_coords_box(
                    box_coords_matrix=box_coords_single_matrix,
                    base_pil_image=base_pil_image,
                    input_file_path=input_file_path,
                    index=index + 1,
                    output_image_folder=output_image_folder,
                )

        else:
            self.draw_box_coords_box(
                box_coords_matrix=text_matrix_boxes_coords,
                base_pil_image=base_pil_image,
                input_file_path=input_file_path,
                index=1,
                output_image_folder=output_image_folder,
            )

    def get_output_file_name(self, input_file_path, index, output_image_folder):
        output_file_name = modify_filename(input_file_path, index)
        base_name = os.path.basename(output_file_name)
        output_file_name = os.path.join(output_image_folder, base_name)
        os.makedirs(output_image_folder, exist_ok=True)

        return output_file_name


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    draw_box_coords = DrawBoxCoords()

    text_matrix_boxes_coords = magi_ch_55_frieren_panel_1_to_7_output[0]["texts"]
    draw_box_coords.draw_box_coords_box_list(
        text_matrix_boxes_coords,
        "z-tts-test-output-2/panel_1.png",
        "/Volumes/Macintosh HD/Users/curlos/Desktop/Github Repos/manga-panel-splitter/z-tts-test-output-2/TESTING/images-with-highlighted-text-boxes",
    )
