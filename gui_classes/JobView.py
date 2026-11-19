import traceback
import flet as ft
from gui_classes.AppOutput import write_to_log_file_only
from gui_classes.PickInputAndOutputDirectories import PickInputAndOutputDirectories
from utils import get_image_folders, get_input_and_output_error, open_directory


class JobView(ft.Container):
    """
    A tab that runs a job on every folder of images in the picked input directory (Panel-By-Panel, Upscale Images and Images To Video). This class does everything they have in common: checking the directories, finding the image folders, the loading text and error handling. Each tab only says what to do with one folder of images ("process_image_folder").
    """

    loading_text = "Working..."
    finished_text = "Finished!"
    failed_text = "Failed."
    # Open the output directory in Finder when the job is started from this tab (not from the Pipeline).
    open_output_directory_when_finished = False

    def __init__(self, parent_gui, settings_container):
        super().__init__()
        self.parent_gui = parent_gui
        self.bgcolor = "#3b4252"
        self.expand = True

        self.pick_input_output_directories_container = PickInputAndOutputDirectories(
            on_submit=self.handle_submit,
            parent_gui=parent_gui,
            settings_container=settings_container,
        )
        self.content = self.pick_input_output_directories_container

    def handle_submit(self, input_directory, output_directory):
        if (
            self.start_job(input_directory, output_directory)
            and self.open_output_directory_when_finished
        ):
            open_directory(output_directory)

    def start_job(self, input_directory, output_directory):
        """
        Run this tab's job. Returns True if it finished, False if it couldn't start or failed (the reason is shown in the terminal).
        """
        terminal_output = self.parent_gui.terminal_output

        error = get_input_and_output_error(input_directory, output_directory)
        if error:
            terminal_output.update_terminal_with_error_message(error)
            return False

        terminal_output.show_loading_text(self.loading_text)

        try:
            self.before_job()
            for image_folder, images in get_image_folders(input_directory):
                self.process_image_folder(
                    image_folder, images, input_directory, output_directory
                )
        except Exception as error:
            # The full details go in the log file. The app shows a short message.
            write_to_log_file_only(traceback.format_exc())
            terminal_output.update_terminal_with_error_message(f"ERROR: {error}")
            terminal_output.hide_loading_text(self.failed_text, success=False)
            return False

        terminal_output.hide_loading_text(self.finished_text)
        return True

    def before_job(self):
        """
        Anything to check or set up once before the image folders are processed. Raise an error to stop the job.
        """

    def process_image_folder(self, image_folder, images, input_directory, output_directory):
        raise NotImplementedError
