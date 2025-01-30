import flet as ft
from gui_classes.PickInputAndOutputDirectories import PickInputAndOutputDirectories
from gui_classes.SettingsPanelByPanel import SettingsPanelByPanel
from utils import (
    input_and_output_dirs_are_valid,
    open_directory,
    remove_last_directory,
)
import os
from magi import Magi


class MagiPanelByPanelView(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui
        self.bgcolor = "#3b4252"
        self.expand = True
        self.magi = None

        self.pick_input_output_directories_container = PickInputAndOutputDirectories(
            on_submit=self.handle_convert_to_panel_by_panel,
            parent_gui=parent_gui,
            settings_container=SettingsPanelByPanel(self.parent_gui.page),
        )

        self.content = self.pick_input_output_directories_container

    def handle_convert_to_panel_by_panel(self, e):
        if not input_and_output_dirs_are_valid(self):
            return

        if not self.magi:
            self.magi = Magi()

        input_directory = self.pick_input_output_directories_container.input_directory
        output_directory = self.pick_input_output_directories_container.output_directory

        files_directory_structure = (
            self.pick_input_output_directories_container.files_directory_structure
        )
        base_path = remove_last_directory(input_directory)

        def traverse_and_process(level, current_path):
            for key, value in level.items():
                if key == "__images__":
                    # Current path is a directory containing images
                    input_directory = os.path.join(base_path, current_path)

                    # Call the processing function
                    self.magi.get_panels_for_chapter(
                        input_directory, output_directory, self.page.client_storage
                    )
                else:
                    # Traverse nested directories
                    next_path = os.path.join(current_path, key) if current_path else key
                    traverse_and_process(value, next_path)

        # Start the traversal from the root of the structure
        traverse_and_process(files_directory_structure, base_path)

        # After all pages have been converted to panel-by-panel format, open the output directory.
        open_directory(output_directory)
