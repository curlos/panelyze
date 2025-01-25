import os
import flet as ft
from classes.PickInputAndOutputDirectories import PickInputAndOutputDirectories
from classes.SettingsImagesToVideo import SettingsImagesToVideo
from VideoCreatorFromImages import VideoCreatorFromImages
from utils import (
    get_last_two_directories_obj,
    input_and_output_dirs_are_valid,
    open_directory,
    remove_last_directory,
)


class ImagesToVideoView(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui
        self.page = self.parent_gui.page
        self.bgcolor = "#3b4252"
        self.expand = True
        self.speech_text_parser = None
        self.tts = None

        self.pick_input_output_directories_container = PickInputAndOutputDirectories(
            on_submit=self.handle_create_videos,
            parent_gui=parent_gui,
            settings_container=SettingsImagesToVideo(self.parent_gui.page),
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
                    directory_base_name = os.path.basename(current_path)

                    if directory_base_name != "images-with-highlighted-text-boxes":
                        self.process_list_of_images_video_creator(
                            base_path, current_path, output_directory
                        )
                else:
                    # Traverse nested directories
                    next_path = os.path.join(current_path, key) if current_path else key
                    traverse_and_process(value, next_path)

        # Start the traversal from the root of the structure
        traverse_and_process(files_directory_structure, base_path)

        open_directory(output_directory)

    def process_list_of_images_video_creator(
        self, base_path, current_path, output_directory
    ):
        # Current path is a directory containing images
        input_directory = os.path.join(base_path, current_path)
        series_name, chapter_name = get_last_two_directories_obj(input_directory)
        full_output_directory = f"{output_directory}/{series_name}"
        output_file = f"{output_directory}/{series_name}/{chapter_name}.mp4"

        video_height = self.page.client_storage.get("video_height")
        image_displayed_duration = self.page.client_storage.get(
            "image_displayed_duration"
        )

        print(f'Creating video "{series_name}/{chapter_name}.mp4"')

        video_creator_from_images = VideoCreatorFromImages(
            flet_page_client_storage=self.page.client_storage,
        )

        video_creator_from_images.create_video_from_images(
            input_directory,
            output_file,
            image_displayed_duration,
            video_height,
            full_output_directory=full_output_directory,
        )

        print(f"Images To Video: Finished creating video to {output_file}")
