import os
import flet as ft
from classes.PickInputAndOutputDirectories import PickInputAndOutputDirectories
from create_video_from_images import create_video_from_images
from utils import (
    get_last_two_directories_obj,
    input_and_output_dirs_are_valid,
    remove_last_directory,
)


class ImagesToVideoView(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui
        self.bgcolor = "#3b4252"
        self.expand = True

        self.pick_input_output_directories_container = PickInputAndOutputDirectories(
            on_submit=self.handle_create_videos, parent_gui=parent_gui
        )

        self.content = self.pick_input_output_directories_container

    def handle_create_videos(self, e):
        if not input_and_output_dirs_are_valid(self):
            return

        input_directory = self.pick_input_output_directories_container.input_directory
        output_directory = self.pick_input_output_directories_container.output_directory

        files_directory_structure = (
            self.pick_input_output_directories_container.files_directory_structure
        )
        base_path = remove_last_directory(input_directory)

        def traverse_and_process(level, current_path):
            for key, value in level.items():
                if key == "__images__":
                    img_obj_list = value
                    self.process_list_of_images_video_creator(
                        base_path, current_path, output_directory, img_obj_list
                    )
                else:
                    # Traverse nested directories
                    next_path = os.path.join(current_path, key) if current_path else key
                    traverse_and_process(value, next_path)

        # Start the traversal from the root of the structure
        traverse_and_process(files_directory_structure, base_path)

    def process_list_of_images_video_creator(
        self, base_path, current_path, output_directory, img_obj_list
    ):
        # Current path is a directory containing images
        input_directory = os.path.join(base_path, current_path)
        series_name, chapter_name = get_last_two_directories_obj(input_directory)
        output_file = f"{output_directory}/{series_name}/{chapter_name}.mp4"

        print(f'Creating video "{series_name}/{chapter_name}.mp4"')
        create_video_from_images(input_directory, output_file)

        print(f"Images To Video: Finished creating video to {output_file}")
