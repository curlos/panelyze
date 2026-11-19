import os
import traceback
import flet as ft
from gui_classes.AppOutput import write_to_log_file_only
from gui_classes.ProgressPanel import report_progress
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
    # What each folder of images is called in the progress panel (e.g. "Chapter 2 of 5").
    group_label = "Chapter"
    # The tab that works on this tab's results next. When this tab finishes, that tab's input folder is filled in with the results (see "get_next_tab_input_directory").
    next_view_name = None

    def __init__(self, parent_gui, settings_container, output_setting_key=None):
        super().__init__()
        self.parent_gui = parent_gui
        self.bgcolor = "#3b4252"
        self.expand = True

        self.pick_input_output_directories_container = PickInputAndOutputDirectories(
            on_submit=self.handle_submit,
            parent_gui=parent_gui,
            settings_container=settings_container,
            output_setting_key=output_setting_key,
        )
        self.content = self.pick_input_output_directories_container

    def handle_submit(self, input_directory, output_directory):
        if not self.start_job(input_directory, output_directory):
            return

        self.fill_in_next_tab_input(input_directory, output_directory)

        if self.open_output_directory_when_finished:
            open_directory(output_directory)

    def get_next_tab_input_directory(self, input_directory, output_directory):
        """
        Where this tab saved its results, which is what the next tab should work on. None if there's nothing to pass on.
        """
        return None

    def fill_in_next_tab_input(self, input_directory, output_directory):
        next_input_directory = self.get_next_tab_input_directory(
            input_directory, output_directory
        )
        if not (self.next_view_name and next_input_directory and os.path.isdir(next_input_directory)):
            return

        next_directories = getattr(
            self.parent_gui, self.next_view_name
        ).pick_input_output_directories_container

        # A folder the user picked in that tab themselves is never replaced.
        if next_directories.input_directory and not next_directories.input_was_filled_in_by_app:
            return

        next_directories.set_input_directory(next_input_directory, filled_in_by_app=True)

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
            image_folders = list(get_image_folders(input_directory))

            for chapter_number, (image_folder, images) in enumerate(image_folders, start=1):
                report_progress(
                    chapter=chapter_number,
                    chapters=len(image_folders),
                    group_label=self.group_label,
                    pages_done=None,
                    pages_total=None,
                    detail=None,
                )
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
