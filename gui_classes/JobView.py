import os
import traceback
import flet as ft
from gui_classes import Nord
from gui_classes.AppOutput import write_to_log_file_only
from gui_classes.ProgressPanel import report_output_folder, report_progress
from gui_classes.PickInputAndOutputDirectories import PickInputAndOutputDirectories
from utils import (
    get_error_text,
    DownloadCancelled,
    get_image_folders,
    get_input_and_output_error,
    get_last_directory,
    open_directory,
)


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
    # The text of the button that starts the job: what it does, e.g. "Upscale".
    submit_text = "Submit"
    # The tab that works on this tab's results next. When this tab finishes, that tab's input folder is filled in with the results (see "get_next_tab_input_directory").
    next_view_name = None
    # Shown as soon as Cancel is clicked: when the job will really stop.
    cancel_message = "Cancelling after the chapter being worked on..."

    def __init__(self, parent_gui, settings_container, output_setting_key=None):
        super().__init__()
        self.parent_gui = parent_gui
        self.bgcolor = Nord.BACKGROUND
        self.expand = True

        self.pick_input_output_directories_container = PickInputAndOutputDirectories(
            on_submit=self.handle_submit,
            parent_gui=parent_gui,
            settings_container=settings_container,
            output_setting_key=output_setting_key,
            submit_text=self.submit_text,
        )
        self.content = self.pick_input_output_directories_container
        # Clicking Cancel sets this, and the job stops at its next check ("raise_if_cancelled"). A tab with something running that can be stopped right away overrides "cancel_job".
        self.cancel_event = self.pick_input_output_directories_container.cancel_event
        self.pick_input_output_directories_container.on_cancel = self.cancel_job
        self.pick_input_output_directories_container.get_cancel_message = (
            self.get_cancel_message
        )

    def get_cancel_message(self):
        return self.cancel_message

    def cancel_job(self):
        """
        Called when Cancel is clicked, to stop anything running that doesn't check "cancel_event" itself.
        """

    def raise_if_cancelled(self):
        if self.cancel_event.is_set():
            raise DownloadCancelled("Cancelled. The chapters that finished are kept.")

    def set_locked(self, locked):
        self.pick_input_output_directories_container.set_locked(locked)

    def set_narrow(self, is_narrow):
        self.pick_input_output_directories_container.set_narrow(is_narrow)

    def handle_submit(self, input_directory, output_directory):
        if not self.start_job(input_directory, output_directory):
            return

        self.fill_in_next_tab_input(input_directory, output_directory)

        if self.open_output_directory_when_finished:
            open_directory(self.get_folder_to_open(input_directory, output_directory))

    def get_folder_to_open(self, input_directory, output_directory):
        """
        The folder with what this job made, to open when it's done: "<output>/<series>" (or "<output>/<chapter>" for one chapter), like the input. The whole output folder if it isn't there.
        """
        folder = os.path.join(output_directory, get_last_directory(input_directory))
        return folder if os.path.isdir(folder) else output_directory

    def get_next_tab_input_directory(
        self, input_directory, output_directory
    ) -> str | None:
        """
        Where this tab saved its results, which is what the next tab should work on. None if there's nothing to pass on.
        """
        return None

    def fill_in_next_tab_input(self, input_directory, output_directory):
        next_input_directory = self.get_next_tab_input_directory(
            input_directory, output_directory
        )
        if not (
            self.next_view_name
            and next_input_directory
            and os.path.isdir(next_input_directory)
        ):
            return

        next_directories = getattr(
            self.parent_gui, self.next_view_name
        ).pick_input_output_directories_container

        # A folder the user picked in that tab themselves is never replaced.
        if (
            next_directories.input_directory
            and not next_directories.input_was_filled_in_by_app
        ):
            return

        next_directories.set_input_directory(
            next_input_directory, filled_in_by_app=True
        )

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
            report_output_folder(output_directory)
            self.before_job()
            image_folders = list(get_image_folders(input_directory))

            for chapter_number, (image_folder, images) in enumerate(
                image_folders, start=1
            ):
                self.raise_if_cancelled()
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
        except DownloadCancelled as cancelled:
            terminal_output.hide_loading_text(
                str(cancelled), success=False, cancelled=True
            )
            return False
        except Exception as error:
            # The full details go in the log file. The app shows a short message.
            write_to_log_file_only(traceback.format_exc())
            # After the "failed" title, so the error stays under it in the Status view.
            terminal_output.hide_loading_text(self.failed_text, success=False)
            terminal_output.update_terminal_with_error_message(
                f"ERROR: {get_error_text(error)}"
            )
            return False

        terminal_output.hide_loading_text(self.get_finished_text(len(image_folders)))
        return True

    def get_finished_text(self, chapter_count):
        """
        The result line when the job finished, for "chapter_count" folders of images.
        """
        return self.finished_text

    def before_job(self):
        """
        Anything to check or set up once before the image folders are processed. Raise an error to stop the job.
        """

    def process_image_folder(
        self, image_folder, images, input_directory, output_directory
    ):
        raise NotImplementedError
