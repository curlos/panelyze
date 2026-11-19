import os
import shutil
import flet as ft
from download_from_mangadex import download_from_mangadex
from utils import (
    IMAGE_EXTENSIONS,
    add_line_to_terminal_output_list_view,
    copy_picked_images_to_folder,
    get_last_directory,
    is_image_file,
    open_directory,
    paths_overlap,
)

# The steps always run in this order, so a later step can never come before an earlier one. Any combination of one or more steps can be picked.
PIPELINE_STEPS = [
    "MangaDex Downloader",
    "Panel-By-Panel",
    "Upscale Images",
    "Images To Video",
]

# Each step saves to its own numbered folder inside the picked output directory, e.g. "<output>/2-panel-by-panel".
PIPELINE_STEP_FOLDER_NAMES = {
    "MangaDex Downloader": "1-mangadex-download",
    "Panel-By-Panel": "2-panel-by-panel",
    "Upscale Images": "3-upscale-images",
    "Images To Video": "4-images-to-video",
}


def get_step_output_directory(pipeline_output_directory, step):
    return os.path.join(pipeline_output_directory, PIPELINE_STEP_FOLDER_NAMES[step])


def get_next_step_input_directory(step, step_input_directory, step_output_directory):
    """
    Where a step saved its images, which is the folder the next step reads from.
    """
    if step == "MangaDex Downloader":
        # mangadex-downloader saves to "<output>/<Manga Title>/<Chapter>/...".
        return step_output_directory

    input_folder_name = get_last_directory(step_input_directory)

    if step == "Panel-By-Panel":
        return os.path.join(
            step_output_directory, "panel-by-panel", "not-grouped", input_folder_name
        )

    # Upscale Images
    return os.path.join(step_output_directory, input_folder_name)


def folder_has_images(directory):
    return any(
        is_image_file(file_name)
        for _, _, file_names in os.walk(directory)
        for file_name in file_names
    )


def get_settings_review_lines(storage, selected_steps):
    """
    A short summary of the settings (from each step's own tab) that the pipeline will use.
    """
    get = storage.get
    review_lines = []

    if "MangaDex Downloader" in selected_steps:
        language = get("language") or {}
        line = f"MangaDex Downloader: language {language.get('name', 'English')}"
        if get("use_start_and_end_chapters"):
            line += f", chapters {get('start_chapter') or 'first'} to {get('end_chapter') or 'last'}"
        if get("use_start_and_end_pages"):
            line += f", pages {get('start_page') or 'first'} to {get('end_page') or 'last'}"
        review_lines.append(line)

    if "Panel-By-Panel" in selected_steps:
        review_lines.append("Panel-By-Panel: Magi AI Model (no settings)")

    if "Upscale Images" in selected_steps:
        line = f"Upscale Images: {get('upscale_ratio')}x, noise level {get('noise_level')}, {get('image_format')}"
        if get("use_custom_panel_image_height"):
            line += f", height {get('custom_panel_image_height')}px"
        if get("use_max_image_width"):
            line += f", max width {get('max_image_width')}px"
        review_lines.append(line)

    if "Images To Video" in selected_steps:
        if get("use_text_to_speech_azure"):
            timing = f"Text-To-Speech ({get('tts_engine') or 'edge'}, {get('azure_voice_name')})"
        elif get("use_image_displayed_duration"):
            timing = f"{get('image_displayed_duration')}s per image"
        else:
            timing = f"reading speed {get('reading_speed_wpm')} WPM"

        line = f"Images To Video: {get('video_aspect_ratio') or '16:9'}, {get('video_height')}p, {get('video_extension')}, {timing}"
        if get("highlight_text_boxes_in_images"):
            line += ", highlight text boxes"
        review_lines.append(line)

    return review_lines


class PipelineView(ft.Container):
    """
    Runs several steps in a row (e.g. MangaDex Downloader -> Panel-By-Panel -> Images To Video). Each step uses the settings saved in its own tab and reads the folder the step before it saved to.
    """

    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui
        # Use "self.parent_gui.page", not "self.page": Flet sets "self.page" to None when this view is not on screen.
        self.bgcolor = "#3b4252"
        self.expand = True
        self.padding = 20

        self.input_directory = ""
        # Set when individual images were picked instead of a folder.
        self.input_image_paths = []
        self.output_directory = ""

        self.step_checkboxes = {
            step: ft.Checkbox(label=step, on_change=self.handle_steps_change)
            for step in PIPELINE_STEPS
        }

        self.mangadex_url_text_field = ft.TextField(
            label="Enter a MangaDex Page URL",
            border_color="#5e81ac",
            visible=False,
        )

        self.input_directory_picker = ft.FilePicker(
            on_result=lambda e: self.handle_directory_picked(e, "input")
        )
        self.output_directory_picker = ft.FilePicker(
            on_result=lambda e: self.handle_directory_picked(e, "output")
        )
        self.input_images_picker = ft.FilePicker(on_result=self.handle_images_picked)
        self.parent_gui.page.overlay.append(self.input_images_picker)
        self.parent_gui.page.overlay.append(self.input_directory_picker)
        self.parent_gui.page.overlay.append(self.output_directory_picker)

        self.input_directory_text = ft.Text("No input directory picked", color="white")
        self.output_directory_text = ft.Text(
            "No output directory picked", color="white"
        )

        self.input_directory_row = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "Pick Input Folder",
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda e: self.input_directory_picker.get_directory_path(),
                ),
                ft.ElevatedButton(
                    "Pick Input Image(s)",
                    icon=ft.Icons.IMAGE,
                    on_click=lambda e: self.input_images_picker.pick_files(
                        allow_multiple=True,
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=[extension.lstrip(".") for extension in IMAGE_EXTENSIONS],
                    ),
                ),
                self.input_directory_text,
            ]
        )

        self.review_text = ft.Text(color="white", selectable=True)

        self.run_button = ft.FilledTonalButton(
            text="Run Pipeline",
            color="white",
            bgcolor="#5e81ac",
            on_click=self.handle_run_pipeline,
        )

        self.content = ft.Column(
            controls=[
                ft.Text("Pipeline", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Pick the steps to run. They always run in this order, and each step uses the settings saved in its own tab.",
                    color="white",
                ),
                ft.Column(controls=list(self.step_checkboxes.values()), spacing=0),
                self.mangadex_url_text_field,
                self.input_directory_row,
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Pick Output Directory",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda e: self.output_directory_picker.get_directory_path(),
                        ),
                        self.output_directory_text,
                    ]
                ),
                ft.Text("Review", size=18, weight=ft.FontWeight.BOLD),
                self.review_text,
                self.run_button,
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
        )

        self.refresh_review()

    def get_selected_steps(self):
        return [step for step in PIPELINE_STEPS if self.step_checkboxes[step].value]

    def refresh_review(self):
        """
        Called whenever this view is shown, since settings may have changed in the other tabs.
        """
        selected_steps = self.get_selected_steps()

        if not selected_steps:
            self.review_text.value = "Pick at least one step."
            return

        review_lines = [" -> ".join(selected_steps), ""]
        review_lines += get_settings_review_lines(
            self.parent_gui.page.client_storage, selected_steps
        )
        if self.output_directory:
            review_lines += [
                "",
                "Each step saves to its own numbered folder in the output directory, e.g. "
                + get_step_output_directory(self.output_directory, selected_steps[0]),
            ]

        self.review_text.value = "\n".join(review_lines)

    def handle_steps_change(self, e):
        # The MangaDex Downloader is where the images come from, so it replaces the input directory.
        uses_mangadex = bool(self.step_checkboxes["MangaDex Downloader"].value)
        self.mangadex_url_text_field.visible = uses_mangadex
        self.input_directory_row.visible = not uses_mangadex

        self.refresh_review()
        self.update()

    def handle_directory_picked(self, e, input_or_output):
        # The user cancelled the dialog.
        if not e.path:
            return

        if input_or_output == "input":
            self.input_directory = e.path
            self.input_image_paths = []
            self.input_directory_text.value = e.path
        else:
            self.output_directory = e.path
            self.output_directory_text.value = e.path

        self.refresh_review()
        self.update()

    def handle_images_picked(self, e):
        # The user cancelled the dialog.
        if not e.files:
            return

        self.input_image_paths = [file.path for file in e.files]
        self.input_directory = os.path.dirname(self.input_image_paths[0])
        self.input_directory_text.value = f"{len(self.input_image_paths)} image(s) from {self.input_directory}"

        self.refresh_review()
        self.update()

    def get_error_before_running(self, selected_steps):
        if not selected_steps:
            return "ERROR: Pick at least one step."
        if not self.output_directory:
            return "ERROR: Please pick an output directory."
        if "MangaDex Downloader" in selected_steps:
            if not self.mangadex_url_text_field.value:
                return "ERROR: MangaDex Page URL must not be empty."
        elif not self.input_directory or not os.path.isdir(self.input_directory):
            return "ERROR: Please pick an input directory."

        return None

    def handle_run_pipeline(self, e):
        # Flet runs click handlers in separate threads, so without this a double-click would start two runs.
        if self.run_button.disabled:
            return

        terminal_output = self.parent_gui.terminal_output
        selected_steps = self.get_selected_steps()

        # Only one job can run at a time (see "PickInputAndOutputDirectories.handle_submit").
        if self.parent_gui.is_job_running:
            terminal_output.update_terminal_with_error_message(
                "ERROR: Another job is still running. Please wait for it to finish."
            )
            return

        error = self.get_error_before_running(selected_steps)
        if error:
            terminal_output.update_terminal_with_error_message(error)
            return

        self.run_button.disabled = True
        self.run_button.update()
        self.parent_gui.is_job_running = True

        input_directory = self.input_directory
        picked_images_folder = None

        try:
            # Picked images are copied into their own temporary folder, so they're processed exactly like a picked folder.
            if self.input_image_paths and "MangaDex Downloader" not in selected_steps:
                picked_images_folder = copy_picked_images_to_folder(self.input_image_paths)
                input_directory = picked_images_folder

            self.run_pipeline(selected_steps, input_directory)
        except Exception as error:
            terminal_output.update_terminal_with_error_message(f"ERROR: Pipeline stopped: {error}")
        finally:
            # Only ever delete the temporary folder made just above.
            if picked_images_folder:
                shutil.rmtree(os.path.dirname(picked_images_folder), ignore_errors=True)

            self.parent_gui.is_job_running = False
            self.run_button.disabled = False

            # If the user switched to another tab while the pipeline was running, this button isn't on the page right now and can't be updated.
            if self.run_button.page:
                self.run_button.update()

    def run_pipeline(self, selected_steps, input_directory):
        terminal_output = self.parent_gui.terminal_output
        step_input_directory = input_directory

        for step_number, step in enumerate(selected_steps, start=1):
            self.show_progress_message(
                f"Pipeline: Step {step_number}/{len(selected_steps)}: {step}"
            )
            step_output_directory = get_step_output_directory(
                self.output_directory, step
            )
            # Clear this step's folder from any previous pipeline run. Otherwise, if this step fails without raising an error (e.g. waifu2x not installed), the next step would use the old images. Never delete a folder that holds this step's input images.
            if os.path.exists(step_output_directory) and not (
                step_input_directory
                and paths_overlap(step_output_directory, step_input_directory)
            ):
                shutil.rmtree(step_output_directory)
            os.makedirs(step_output_directory, exist_ok=True)

            try:
                self.run_step(step, step_input_directory, step_output_directory)
            except Exception as error:
                terminal_output.update_terminal_with_error_message(
                    f'ERROR: Pipeline stopped. "{step}" failed: {error}'
                )
                return

            if step == "Images To Video":
                break

            # A step can finish without saving anything (e.g. a MangaDex download that found no pages), so check before running the next step.
            step_input_directory = get_next_step_input_directory(
                step, step_input_directory, step_output_directory
            )
            if not folder_has_images(step_input_directory):
                terminal_output.update_terminal_with_error_message(
                    f'ERROR: Pipeline stopped. "{step}" didn\'t save any images to {step_input_directory}'
                )
                return

        self.show_progress_message(
            f"Pipeline finished! Everything was saved to {self.output_directory}"
        )
        open_directory(self.output_directory)

    def show_progress_message(self, message):
        add_line_to_terminal_output_list_view(
            self.parent_gui.terminal_output.terminal_output_list_view,
            message,
            color="#a3be8c",
        )

    def run_step(self, step, step_input_directory, step_output_directory):
        if step == "MangaDex Downloader":
            download_from_mangadex(
                self.mangadex_url_text_field.value,
                step_output_directory,
                self.parent_gui.terminal_output.terminal_output_list_view,
                self.parent_gui.page.client_storage,
            )
            return

        # The other steps run exactly like they do in their own tabs.
        step_views = {
            "Panel-By-Panel": self.parent_gui.MagiPanelByPanelView,
            "Upscale Images": self.parent_gui.UpscaleImagesView,
            "Images To Video": self.parent_gui.ImagesToVideoView,
        }

        if not step_views[step].start_job(step_input_directory, step_output_directory):
            raise RuntimeError("see the error above")
