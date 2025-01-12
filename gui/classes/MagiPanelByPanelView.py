import flet as ft
from classes.PickInputAndOutputDirectories import PickInputAndOutputDirectories
from utils import (
    open_directory,
    remove_last_directory,
)
import os
from magi import Magi


class MagiPanelByPanelView(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.bgcolor = "#3b4252"
        self.expand = True
        self.magi = None

        self.pick_input_output_directories_container = PickInputAndOutputDirectories(
            on_submit=self.handle_convert_to_panel_by_panel, parent_gui=parent_gui
        )

        self.content = self.pick_input_output_directories_container

    def handle_convert_to_panel_by_panel(self, e):
        input_directory = self.pick_input_output_directories_container.input_directory
        output_directory = self.pick_input_output_directories_container.output_directory

        if not input_directory and not output_directory:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: Please enter valid input and output directories."
            )
            return
        elif not input_directory:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: Please enter a valid input directory."
            )
            return
        elif not output_directory:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                "ERROR: Please enter a valid output directory."
            )
            return

        if not self.magi:
            self.magi = Magi()

        files_directory_structure = (
            self.pick_input_output_directories_container.files_directory_structure
        )

        self.process_images_in_structure(
            files_directory_structure, remove_last_directory(input_directory)
        )
        open_directory(output_directory)

    def process_images_in_structure(self, structure, base_path=""):
        output_directory = self.pick_input_output_directories_container.output_directory

        def traverse_and_process(level, current_path):
            for key, value in level.items():
                if key == "__images__":
                    # Current path is a directory containing images
                    input_directory = os.path.join(base_path, current_path)

                    # Call the processing function
                    self.magi.get_panels_for_chapter(input_directory, output_directory)
                else:
                    # Traverse nested directories
                    next_path = os.path.join(current_path, key) if current_path else key
                    traverse_and_process(value, next_path)

        # Start the traversal from the root of the structure
        traverse_and_process(structure, base_path)
