import os
import shutil
import flet as ft
from gui_classes import Nord
from gui_classes.AppBar import TAB_ICONS
from gui_classes.ReadingDirectionSetting import READING_DIRECTIONS
from gui_classes.WrappingCheckbox import WrappingCheckbox
from default_settings import get_output_directory
from download_from_mangadex import download_from_mangadex
from gui_classes.ProgressPanel import report_progress
from utils import (
    IMAGE_EXTENSIONS,
    add_line_to_terminal_output_list_view,
    copy_picked_images_to_folder,
    get_image_folders,
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


# What the last step of the pipeline makes, for the "Final result" part of the review.
FINAL_RESULT_DESCRIPTIONS = {
    "MangaDex Downloader": "The downloaded chapters",
    "Panel-By-Panel": "The panels",
    "Upscale Images": "The upscaled images",
    "Images To Video": "The videos",
}

LABEL_COLOR = Nord.TEAL
DETAIL_COLOR = Nord.TEXT
MUTED_COLOR = Nord.TEXT_MUTED
PATH_COLOR = Nord.GREEN


def get_section(label, controls):
    """
    A part of the review: a small label in capitals and then what belongs under it.
    """
    return ft.Column(
        controls=[
            ft.Text(label.upper(), size=12, weight=ft.FontWeight.BOLD, color=LABEL_COLOR),
            *controls,
        ],
        spacing=6,
    )


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
            step_output_directory, "panel-by-panel", "not-grouped-by-page", input_folder_name
        )

    # Upscale Images
    return os.path.join(step_output_directory, input_folder_name)


def folder_has_images(directory):
    return any(
        is_image_file(file_name)
        for _, _, file_names in os.walk(directory)
        for file_name in file_names
    )


def get_final_step_folder(step, step_input_directory, step_output_directory):
    """
    The folder opened when the pipeline finishes, next to the pipeline folder: the chapter's own folder when the last step made just one (so it doesn't have to be clicked through to), or else the last step's folder. "step_input_directory" is where the last step saved its images (see "get_next_step_input_directory").
    """
    if step == "Images To Video":
        return step_output_directory

    image_folders = list(get_image_folders(step_input_directory))
    return image_folders[0][0] if len(image_folders) == 1 else step_output_directory


def video_will_use_text_read_by_panel_by_panel(storage, selected_steps):
    """
    When the Pipeline makes panels and then a video that needs the text, Panel-By-Panel reads it from the pages (much faster than Images To Video reading every panel). Highlighting text boxes needs where the text is on each panel, so it still reads the panels.
    """
    get = storage.get
    return (
        "Panel-By-Panel" in selected_steps
        and "Images To Video" in selected_steps
        and bool(get("use_text_to_speech_azure") or get("use_reading_speed_wpm"))
        and not get("highlight_text_boxes_in_images")
    )


def get_reading_direction_review(storage, selected_steps):
    """
    The Reading Direction, and for "Automatic", where it will come from.
    """
    reading_direction = storage.get("reading_direction") or "auto"
    if reading_direction != "auto":
        return f"reading direction {READING_DIRECTIONS.get(reading_direction, reading_direction)}"
    if "MangaDex Downloader" in selected_steps:
        return "reading direction Automatic (from MangaDex)"
    return "reading direction Automatic (from the images, unless the folder was downloaded from MangaDex)"


def get_settings_review(storage, selected_steps):
    """
    A short summary of the settings (from each step's own tab) that the pipeline will use, as (step, details) pairs.
    """
    get = storage.get
    review = []

    if "MangaDex Downloader" in selected_steps:
        language = get("language") or {}
        details = f"language {language.get('name', 'English')}"
        if get("use_start_and_end_chapters"):
            details += f", chapters {get('start_chapter') or 'first'} to {get('end_chapter') or 'last'}"
        if get("use_start_and_end_pages"):
            details += f", pages {get('start_page') or 'first'} to {get('end_page') or 'last'}"
        review.append(("MangaDex Downloader", details))

    if "Panel-By-Panel" in selected_steps:
        details = f"Magi AI Model, {get_reading_direction_review(storage, selected_steps)}, panels saved together (not grouped by page)"
        if get("show_full_characters"):
            details += ", shows full characters"
        if get("split_tall_panels"):
            details += ", splits very tall panels"
        if video_will_use_text_read_by_panel_by_panel(storage, selected_steps):
            details += ", also reads the text for the video"
        review.append(("Panel-By-Panel", details))

    if "Upscale Images" in selected_steps:
        details = f"{get('upscale_ratio')}x, noise level {get('noise_level')}, {get('image_format')}, {get('upscale_model') or 'fast'} model"
        if get("use_custom_panel_image_height"):
            details += f", height {get('custom_panel_image_height')}px"
        if get("use_max_image_width"):
            details += f", max width {get('max_image_width')}px"
        review.append(("Upscale Images", details))

    if "Images To Video" in selected_steps:
        if get("use_text_to_speech_azure"):
            timing = f"Text-To-Speech ({get('tts_engine') or 'edge'}, {get('azure_voice_name')})"
        elif get("use_image_displayed_duration"):
            timing = f"{get('image_displayed_duration')}s per image"
        else:
            timing = f"reading speed {get('reading_speed_wpm')} WPM"

        details = f"{get('video_aspect_ratio') or '16:9'}, {get('video_height')}p, {get('video_extension')}, {timing}"
        if get("highlight_text_boxes_in_images"):
            details += ", highlight text boxes"
        review.append(("Images To Video", details))

    return review


class PipelineView(ft.Container):
    """
    Runs several steps in a row (e.g. MangaDex Downloader -> Panel-By-Panel -> Images To Video). Each step uses the settings saved in its own tab and reads the folder the step before it saved to.
    """

    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui
        # Use "self.parent_gui.page", not "self.page": Flet sets "self.page" to None when this view is not on screen.
        self.bgcolor = Nord.BACKGROUND
        self.expand = True
        self.padding = 20

        self.input_directory = ""
        # Set for each run (see "video_will_use_text_read_by_panel_by_panel").
        self.read_text_for_video = False
        # Set when individual images were picked instead of a folder.
        self.input_image_paths = []
        # Starts as the default folder. Picking a different one is remembered.
        self.output_directory = get_output_directory(
            self.parent_gui.page.client_storage, "output_directory_pipeline"
        )

        self.step_checkboxes = {
            step: WrappingCheckbox(
                label=step, on_change=self.handle_steps_change, icon=TAB_ICONS[step]
            )
            for step in PIPELINE_STEPS
        }

        self.mangadex_url_text_field = ft.TextField(
            border_radius=0,
            label="Enter a MangaDex Page URL",
            border_color=Nord.BLUE,
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

        self.input_directory_text = ft.Text("No input directory picked", color=Nord.TEXT)
        self.output_directory_text = ft.Text(self.output_directory, color=Nord.TEXT)

        self.input_directory_row = ft.Row(
            wrap=True,
            controls=[
                ft.ElevatedButton(
                    "Pick Input Folder",
                    style=Nord.button_style("secondary"),
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda e: self.input_directory_picker.get_directory_path(),
                ),
                ft.ElevatedButton(
                    "Pick Input Image(s)",
                    style=Nord.button_style("secondary"),
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

        # Filled in by "refresh_review".
        self.review_column = ft.Column(spacing=14)

        self.run_button = ft.FilledTonalButton(
            style=Nord.button_style("primary"),
            text="Run Pipeline",
            on_click=self.handle_run_pipeline,
        )

        self.content = ft.Column(
            controls=[
                ft.Text("Pipeline", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Pick the steps to run. They always run in this order, and each step uses the settings saved in its own tab.",
                    color=Nord.TEXT,
                ),
                ft.Column(controls=list(self.step_checkboxes.values()), spacing=0),
                self.mangadex_url_text_field,
                self.input_directory_row,
                ft.Row(
                    wrap=True,
                    controls=[
                        ft.ElevatedButton(
                            "Change Output Folder",
                            style=Nord.button_style("secondary"),
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=lambda e: self.output_directory_picker.get_directory_path(),
                        ),
                        ft.IconButton(
                            ft.Icons.RESTART_ALT,
                            icon_color=Nord.TEXT,
                            style=Nord.icon_button_style(),
                            tooltip="Use the default output folder",
                            on_click=lambda e: self.set_output_directory(""),
                        ),
                        self.output_directory_text,
                    ]
                ),
                ft.Text("Review", size=18, weight=ft.FontWeight.BOLD),
                self.review_column,
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        # The Run button stays under the part that scrolls, so it's always on screen.
        self.content = ft.Column(controls=[self.content, self.run_button], spacing=15)

        self.refresh_review()

    def get_selected_steps(self):
        return [step for step in PIPELINE_STEPS if self.step_checkboxes[step].value]

    def refresh_review(self):
        """
        Called whenever this view is shown, since settings may have changed in the other tabs. It shows the steps, the settings each of them will use, and where the final result will be saved.
        """
        selected_steps = self.get_selected_steps()

        if not selected_steps:
            self.review_column.controls = [ft.Text("Pick at least one step.", color=MUTED_COLOR)]
            return

        self.review_column.controls = [
            get_section("Steps", [self.get_steps_flow(selected_steps)]),
            get_section(
                "Settings each step will use",
                [
                    *self.get_settings_rows(selected_steps),
                    ft.Text("Change them in each step's own tab.", size=12, color=MUTED_COLOR),
                ],
            ),
            get_section("Final result", [self.get_final_result_card(selected_steps)]),
        ]

    def get_steps_flow(self, selected_steps):
        # A numbered list, one step on each line (the numbers show the order).
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(f"{step_number}.", weight=ft.FontWeight.BOLD, color=Nord.TEXT),
                        ft.Icon(TAB_ICONS[step], size=18, color=Nord.TEXT),
                        ft.Text(step, weight=ft.FontWeight.BOLD, color=Nord.TEXT),
                    ],
                    spacing=6,
                )
                for step_number, step in enumerate(selected_steps, start=1)
            ],
            spacing=4,
        )

    def get_settings_rows(self, selected_steps):
        return [
            ft.Row(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(TAB_ICONS[step], size=18, color=Nord.TEXT),
                            ft.Text(step, weight=ft.FontWeight.BOLD, color=Nord.TEXT, expand=True),
                        ],
                        spacing=6,
                        width=230,
                    ),
                    ft.Text(details, color=DETAIL_COLOR, expand=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            for step, details in get_settings_review(
                self.parent_gui.page.client_storage, selected_steps
            )
        ]

    def get_final_result_card(self, selected_steps):
        last_step = selected_steps[-1]

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"{FINAL_RESULT_DESCRIPTIONS[last_step]} will be saved in:",
                        color=Nord.TEXT,
                    ),
                    ft.Text(
                        get_step_output_directory(self.output_directory, last_step),
                        color=PATH_COLOR,
                        selectable=True,
                    ),
                    ft.Text(
                        f"Each step's results are also kept in numbered folders (1-…, 2-…) inside {self.output_directory}",
                        size=12,
                        color=MUTED_COLOR,
                    ),
                ],
                spacing=4,
            ),
            border=ft.border.all(1, Nord.BLUE),
            padding=10,
        )

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
            self.set_output_directory(e.path)
            return

        self.refresh_review()
        self.update()

    def set_output_directory(self, output_directory):
        # An empty one means the default folder.
        storage = self.parent_gui.page.client_storage
        storage.set("output_directory_pipeline", output_directory)
        self.output_directory = get_output_directory(storage, "output_directory_pipeline")
        self.output_directory_text.value = self.output_directory

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

            report_progress(prefix="")
            self.parent_gui.is_job_running = False
            self.run_button.disabled = False

            # If the user switched to another tab while the pipeline was running, this button isn't on the page right now and can't be updated.
            if self.run_button.page:
                self.run_button.update()

    def run_pipeline(self, selected_steps, input_directory):
        terminal_output = self.parent_gui.terminal_output
        step_input_directory = input_directory
        self.read_text_for_video = video_will_use_text_read_by_panel_by_panel(
            self.parent_gui.page.client_storage, selected_steps
        )

        for step_number, step in enumerate(selected_steps, start=1):
            self.show_progress_message(
                f"Pipeline: Step {step_number}/{len(selected_steps)}: {step}"
            )
            report_progress(prefix=f"Step {step_number} of {len(selected_steps)}")
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
        # Opened last, so it's the window in front.
        open_directory(get_final_step_folder(step, step_input_directory, step_output_directory))

    def show_progress_message(self, message):
        add_line_to_terminal_output_list_view(
            self.parent_gui.terminal_output.terminal_output_list_view,
            message,
            color=Nord.GREEN,
        )

    def run_step(self, step, step_input_directory, step_output_directory):
        if step == "MangaDex Downloader":
            terminal_output = self.parent_gui.terminal_output
            terminal_output.show_loading_text("Downloading from MangaDex...")
            try:
                download_from_mangadex(
                    self.mangadex_url_text_field.value,
                    step_output_directory,
                    terminal_output.terminal_output_list_view,
                    self.parent_gui.page.client_storage,
                )
            except Exception:
                terminal_output.hide_loading_text("MangaDex download failed.", success=False)
                raise
            terminal_output.hide_loading_text("MangaDex download ended.")
            return

        # The other steps run exactly like they do in their own tabs.
        step_views = {
            "Panel-By-Panel": self.parent_gui.MagiPanelByPanelView,
            "Upscale Images": self.parent_gui.UpscaleImagesView,
            "Images To Video": self.parent_gui.ImagesToVideoView,
        }

        step_view = step_views[step]
        if step == "Panel-By-Panel":
            step_view.ignore_group_by_page = True
            step_view.read_text_for_video = self.read_text_for_video

        try:
            finished = step_view.start_job(step_input_directory, step_output_directory)
        finally:
            if step == "Panel-By-Panel":
                step_view.ignore_group_by_page = False
                step_view.read_text_for_video = False

        if not finished:
            raise RuntimeError("see the error above")
