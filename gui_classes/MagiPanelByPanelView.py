import flet as ft
from gui_classes.JobView import JobView
from gui_classes.ReadingDirectionSetting import get_reading_direction_dropdown


class MagiPanelByPanelView(JobView):
    loading_text = "Converting to Panel-By-Panel..."
    finished_text = "Panel-By-Panel conversion finished!"
    failed_text = "Panel-By-Panel conversion failed."
    open_output_directory_when_finished = True

    def __init__(self, parent_gui):
        super().__init__(
            parent_gui,
            settings_container=ft.Container(
                content=get_reading_direction_dropdown(parent_gui.page),
                width=350,
                padding=ft.padding.only(left=10, top=5, right=10),
            ),
        )

    def process_image_folder(self, image_folder, images, input_directory, output_directory):
        # Imported here so that torch and transformers only load when Magi is actually used, not when the app starts.
        from magi import get_magi

        get_magi().get_panels_for_chapter(
            image_folder,
            output_directory,
            selected_input_directory=input_directory,
            reading_direction=self.parent_gui.page.client_storage.get("reading_direction"),
        )
