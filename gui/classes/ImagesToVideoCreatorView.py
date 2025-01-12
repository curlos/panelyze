import flet as ft
from classes.PickInputAndOutputDirectories import PickInputAndOutputDirectories


class ImagesToVideoCreatorView(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.bgcolor = "#3b4252"
        self.expand = True

        self.pick_input_output_directories_container = PickInputAndOutputDirectories(
            on_submit=self.create_video, parent_gui=parent_gui
        )

        self.content = self.pick_input_output_directories_container

    def create_video(self):
        print("Creating video...")
