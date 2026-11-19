import os
import flet as ft
from gui_classes.WrappingCheckbox import WrappingCheckbox
from gui_classes.JobView import JobView
from gui_classes.ReadingDirectionSetting import get_reading_direction_dropdown
from utils import get_last_directory, get_relative_output_path, save_folder_as_cbz


class MagiPanelByPanelView(JobView):
    loading_text = "Converting to Panel-By-Panel..."
    finished_text = "Panel-By-Panel conversion finished!"
    failed_text = "Panel-By-Panel conversion failed."
    open_output_directory_when_finished = True
    next_view_name = "UpscaleImagesView"

    def __init__(self, parent_gui):
        storage = parent_gui.page.client_storage
        # The Pipeline's next steps need all of the panels together, so it turns this off for its Panel-By-Panel step.
        self.ignore_group_by_page = False
        # The Pipeline turns this on when it will also make a video, so the text is read from the pages here.
        self.read_text_for_video = False

        super().__init__(
            parent_gui,
            settings_container=ft.Container(
                content=ft.Column(
                    controls=[
                        get_reading_direction_dropdown(parent_gui.page),
                        WrappingCheckbox(
                            label="Group panels by page (one folder for each page)",
                            value=storage.get("group_panels_by_page"),
                            on_change=lambda e: storage.set(
                                "group_panels_by_page", e.data == "true"
                            ),
                        ),
                    ]
                ),
                width=350,
                padding=ft.padding.only(left=10, top=5, right=10),
            ),
            output_setting_key="output_directory_panel_by_panel",
        )

    def get_next_tab_input_directory(self, input_directory, output_directory):
        # Panels grouped by page have a folder for each page, which is not what the next tab expects.
        if self.parent_gui.page.client_storage.get("group_panels_by_page"):
            return None

        return os.path.join(
            output_directory,
            "panel-by-panel",
            "not-grouped-by-page",
            get_last_directory(input_directory),
        )

    def process_image_folder(self, image_folder, images, input_directory, output_directory):
        # Imported here so that torch and transformers only load when Magi is actually used, not when the app starts.
        from magi import get_magi

        storage = self.parent_gui.page.client_storage
        group_by_page = bool(
            storage.get("group_panels_by_page") and not self.ignore_group_by_page
        )
        get_magi().get_panels_for_chapter(
            image_folder,
            output_directory,
            selected_input_directory=input_directory,
            reading_direction=storage.get("reading_direction"),
            group_by_page=group_by_page,
            read_text=self.read_text_for_video,
        )

        if storage.get("save_as_cbz"):
            save_folder_as_cbz(
                os.path.join(
                    output_directory,
                    "panel-by-panel",
                    "grouped-by-page" if group_by_page else "not-grouped-by-page",
                    get_relative_output_path(image_folder, input_directory),
                ),
                size=storage.get("save_as_cbz"),
            )
