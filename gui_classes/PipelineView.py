import os
import shutil
import time
import flet as ft
from gui_classes import Nord
from gui_classes.AppBar import TAB_ICONS
from gui_classes.ReadingDirectionSetting import READING_DIRECTIONS
from gui_classes.WrappingCheckbox import WrappingCheckbox
from default_settings import can_pick_output_folders, get_output_directory
from gui_classes.MangaDexDownloaderView import get_downloader
from download_pages_from_url import get_min_image_side
from gui_classes.PickInputAndOutputDirectories import (
    COMIC_FILES_HELP_TEXT,
    save_input_to_temporary_folder,
)
from gui_classes.ProgressPanel import (
    format_duration,
    report_output_folder,
    report_progress,
)
from utils import (
    get_error_text,
    COMIC_FILE_EXTENSIONS,
    IMAGE_EXTENSIONS,
    DownloadCancelled,
    reset_cancel_button,
    set_cancel_click,
    add_line_to_terminal_output_list_view,
    get_image_folders,
    get_last_directory,
    is_comic_file,
    is_image_file,
    open_directory,
    is_same_or_inside,
    paths_overlap,
)


class StepFailed(RuntimeError):
    """
    A step's tab stopped with an error it already showed.
    """


# The steps always run in this order, so a later step can never come before an earlier one. Any combination of one or more steps can be picked.
PIPELINE_STEPS = [
    "Download",
    "Panel-By-Panel",
    "Upscale Images",
    "Images To Video",
]

# Each step saves to its own numbered folder inside the picked output directory, e.g. "<output>/2-panel-by-panel".
PIPELINE_STEP_FOLDER_NAMES = {
    "Download": "1-download",
    "Panel-By-Panel": "2-panel-by-panel",
    "Upscale Images": "3-upscale-images",
    "Images To Video": "4-images-to-video",
}


# What the last step of the pipeline makes, for the "Final result" part of the review.
FINAL_RESULT_DESCRIPTIONS = {
    "Download": "The downloaded chapters",
    "Panel-By-Panel": "The panels",
    "Upscale Images": "The upscaled images",
    "Images To Video": "The videos",
}

LABEL_COLOR = Nord.TEAL
DETAIL_COLOR = Nord.TEXT
MUTED_COLOR = Nord.TEXT_MUTED
PATH_COLOR = Nord.PATH


def get_section(label, controls):
    """
    A part of the review: a small label in capitals and then what belongs under it.
    """
    return ft.Column(
        controls=[
            ft.Text(
                label.upper(), size=12, weight=ft.FontWeight.BOLD, color=LABEL_COLOR
            ),
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
    if step == "Download":
        # The downloaders save to "<output>/<series>/<chapter>/..." (a web page or an Internet Archive item to "<output>/<title>/..."). The next steps start from that one folder, so their folders are named after it ("2-panel-by-panel/One Piece"), not after "1-download". Several series (a MangaDex list) keep the whole folder.
        series_folders = [
            os.path.join(step_output_directory, name)
            for name in os.listdir(step_output_directory)
            if os.path.isdir(os.path.join(step_output_directory, name))
        ]
        return series_folders[0] if len(series_folders) == 1 else step_output_directory

    # Panel-By-Panel (whose panels are never grouped by page in a Pipeline) and Upscale Images.
    return os.path.join(step_output_directory, get_last_directory(step_input_directory))


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
    if "Download" in selected_steps:
        return "reading direction Automatic (from MangaDex or comix.to)"
    return "reading direction Automatic (from the images, unless the folder was downloaded from MangaDex or comix.to)"


def get_download_review(storage, url):
    """
    The Download step's settings. Only the ones the link's site uses: MangaDex uses all of them, comix.to only the chapters, a web page only "Only keep bigger images", the Internet Archive none. Before a link is entered, the MangaDex ones are shown, marked as such.
    """
    get = storage.get
    try:
        source = get_downloader(url)[0] if (url or "").strip() else None
    except ValueError:
        source = None

    details = []
    if source in (None, "MangaDex"):
        language = get("language") or {}
        details.append(
            f"language {language.get('name', 'English')}"
            + (" (MangaDex only)" if source is None else "")
        )
    if source in (None, "MangaDex", "comix.to") and get("use_start_and_end_chapters"):
        details.append(
            f"chapters {get('start_chapter') or 'first'} to {get('end_chapter') or 'last'}"
        )
    if source in (None, "MangaDex"):
        if get("use_start_and_end_pages"):
            details.append(
                f"pages {get('start_page') or 'first'} to {get('end_page') or 'last'}"
            )
        if get("upload_choice") == "first":
            details.append("first upload of each chapter")
        elif get("upload_choice") == "group" and (get("preferred_group") or "").strip():
            details.append("the preferred group's uploads")
    if source == "the web page" and get_min_image_side(storage):
        details.append(
            f"only images at least {get_min_image_side(storage)}px on the shorter side"
        )
    if source:
        details.insert(0, f"from {source}")
    return ", ".join(details)


def get_settings_review(storage, selected_steps, url=""):
    """
    A short summary of the settings (from each step's own tab) that the pipeline will use, as (step, details) pairs. "url" is the Download step's link.
    """
    get = storage.get
    review = []

    if "Download" in selected_steps:
        review.append(("Download", get_download_review(storage, url)))

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
        if get("limit_upscale_to_4k"):
            details += ", at most 4K (3840px)"
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
    Runs several steps in a row (e.g. Download -> Panel-By-Panel -> Images To Video). Each step uses the settings saved in its own tab and reads the folder the step before it saved to.
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
        # Set when comic files (.cbz, .pdf, ...) were picked instead of a folder.
        self.input_comic_paths = []
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
            label="Enter a MangaDex, comix.to, Internet Archive or web page URL",
            border_color=Nord.BLUE,
            visible=False,
            # The Download settings shown depend on the link's site.
            on_change=self.handle_url_change,
        )

        self.input_directory_picker = ft.FilePicker(
            on_result=lambda e: self.handle_directory_picked(e, "input")
        )
        self.output_directory_picker = ft.FilePicker(
            on_result=lambda e: self.handle_directory_picked(e, "output")
        )
        self.input_images_picker = ft.FilePicker(on_result=self.handle_images_picked)
        self.input_comic_files_picker = ft.FilePicker(
            on_result=self.handle_comic_files_picked
        )
        self.parent_gui.page.overlay.append(self.input_images_picker)
        self.parent_gui.page.overlay.append(self.input_comic_files_picker)
        self.parent_gui.page.overlay.append(self.input_directory_picker)
        self.parent_gui.page.overlay.append(self.output_directory_picker)

        self.input_directory_text = ft.Text(
            "No input directory picked", color=Nord.TEXT
        )

        self.output_directory_text = ft.Text(self.output_directory, color=Nord.PATH)

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
                        allowed_extensions=[
                            extension.lstrip(".") for extension in IMAGE_EXTENSIONS
                        ],
                    ),
                ),
                ft.ElevatedButton(
                    "Pick Comic File(s)",
                    style=Nord.button_style("secondary"),
                    icon=ft.Icons.MENU_BOOK,
                    on_click=lambda e: self.input_comic_files_picker.pick_files(
                        allow_multiple=True,
                        file_type=ft.FilePickerFileType.CUSTOM,
                        allowed_extensions=[
                            extension.lstrip(".") for extension in COMIC_FILE_EXTENSIONS
                        ],
                    ),
                ),
                self.input_directory_text,
            ],
        )
        # Links are downloaded with the Download step instead.
        self.input_column = ft.Column(
            controls=[
                self.input_directory_row,
                ft.Text(COMIC_FILES_HELP_TEXT, color=Nord.TEXT_MUTED, size=12),
            ],
            spacing=6,
        )

        # Filled in by "refresh_review".
        self.review_column = ft.Column(spacing=14)

        self.run_button = ft.FilledTonalButton(
            style=Nord.button_style("primary"),
            text="Run Pipeline",
            on_click=self.handle_run_pipeline,
        )

        # Where the results are saved.
        self.output_row = ft.Row(
            wrap=True,
            controls=[
                # Running from source, everything goes to the repo's own folder (see "can_pick_output_folders").
                ft.ElevatedButton(
                    "Change Output Folder",
                    style=Nord.button_style("secondary"),
                    icon=ft.Icons.FOLDER_OPEN,
                    on_click=lambda e: (
                        self.output_directory_picker.get_directory_path()
                    ),
                    visible=can_pick_output_folders(),
                ),
                ft.IconButton(
                    ft.Icons.RESTART_ALT,
                    icon_color=Nord.TEXT,
                    style=Nord.icon_button_style(),
                    tooltip=Nord.tooltip("Use the default output folder"),
                    on_click=lambda e: self.set_output_directory(""),
                    visible=can_pick_output_folders(),
                ),
                self.output_directory_text,
            ],
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
                self.input_column,
                self.output_row,
                ft.Text("Review", size=18, weight=ft.FontWeight.BOLD),
                self.review_column,
            ],
            spacing=15,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        # Shown next to Run while the Pipeline runs. Each step sets what it stops (see "run_step").
        self.cancel_button = ft.FilledTonalButton(
            style=Nord.button_style("danger"), text="Cancel", visible=False
        )
        # Set when Cancel is clicked, so no step after the current one starts.
        self.cancelled = False
        # How far a run is: each selected step and whether it's done, running, waiting, failed or cancelled (see "show_step_statuses").
        self.step_status_column = ft.Column(spacing=4, visible=False)
        # The Run button stays under the part that scrolls, so it's always on screen.
        self.content = ft.Column(
            controls=[
                self.content,
                ft.Row(controls=[self.run_button, self.cancel_button]),
                self.step_status_column,
            ],
            spacing=15,
        )

        self.refresh_review()

    def get_selected_steps(self):
        return [step for step in PIPELINE_STEPS if self.step_checkboxes[step].value]

    def refresh_review(self):
        """
        Called whenever this view is shown, since settings may have changed in the other tabs. It shows the steps, the settings each of them will use, and where the final result will be saved.
        """
        selected_steps = self.get_selected_steps()

        if not selected_steps:
            self.review_column.controls = [
                ft.Text("Pick at least one step.", color=MUTED_COLOR)
            ]
            return

        self.review_column.controls = [
            get_section("Steps", [self.get_steps_flow(selected_steps)]),
            get_section(
                "Settings each step will use",
                [
                    *self.get_settings_rows(selected_steps),
                    ft.Text(
                        "Change them in each step's own tab.",
                        size=12,
                        color=MUTED_COLOR,
                    ),
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
                        ft.Text(
                            f"{step_number}.",
                            weight=ft.FontWeight.BOLD,
                            color=Nord.TEXT,
                        ),
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
                            ft.Text(
                                step,
                                weight=ft.FontWeight.BOLD,
                                color=Nord.TEXT,
                                expand=True,
                            ),
                        ],
                        spacing=6,
                        width=230,
                    ),
                    ft.Text(details, color=DETAIL_COLOR, expand=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            for step, details in get_settings_review(
                self.parent_gui.page.client_storage,
                selected_steps,
                self.mangadex_url_text_field.value or "",
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
        # The Download step is where the images come from, so it replaces the input directory.
        uses_mangadex = bool(self.step_checkboxes["Download"].value)
        self.mangadex_url_text_field.visible = uses_mangadex
        self.input_column.visible = not uses_mangadex

        self.refresh_review()
        self.update()

    def handle_url_change(self, e):
        self.refresh_review()
        self.update()

    def handle_directory_picked(self, e, input_or_output):
        # The user cancelled the dialog.
        if not e.path:
            return

        if input_or_output == "input":
            self.clear_input()
            self.input_directory = e.path
            self.input_directory_text.value = e.path
            self.input_directory_text.color = PATH_COLOR
        else:
            self.set_output_directory(e.path)
            return

        self.refresh_review()
        self.update()

    def set_output_directory(self, output_directory):
        # An empty one means the default folder.
        storage = self.parent_gui.page.client_storage
        storage.set("output_directory_pipeline", output_directory)
        self.output_directory = get_output_directory(
            storage, "output_directory_pipeline"
        )
        self.output_directory_text.value = self.output_directory

        self.refresh_review()
        self.update()

    def handle_images_picked(self, e):
        # The user cancelled the dialog.
        if not e.files:
            return

        self.clear_input()
        self.input_image_paths = [file.path for file in e.files]
        self.input_directory = os.path.dirname(self.input_image_paths[0])
        self.input_directory_text.value = (
            f"{len(self.input_image_paths)} image(s) from {self.input_directory}"
        )
        self.input_directory_text.color = PATH_COLOR

        self.refresh_review()
        self.update()

    def handle_comic_files_picked(self, e):
        # The user cancelled the dialog.
        if not e.files:
            return

        # The Mac file picker can let other files through, so check again.
        comic_paths = [file.path for file in e.files if is_comic_file(file.path)]
        if not comic_paths:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                f"ERROR: Please pick comic files ({', '.join(COMIC_FILE_EXTENSIONS)})."
            )
            return

        self.clear_input()
        self.input_comic_paths = comic_paths
        self.input_directory = os.path.dirname(comic_paths[0])
        self.input_directory_text.value = (
            f"{len(comic_paths)} comic file(s) from {self.input_directory}"
        )
        self.input_directory_text.color = PATH_COLOR

        self.refresh_review()
        self.update()

    def clear_input(self):
        # Only one input is used at a time, so picking one clears the others.
        self.input_directory = ""
        self.input_image_paths = []
        self.input_comic_paths = []

    def get_error_before_running(self, selected_steps):
        if not selected_steps:
            return "ERROR: Pick at least one step."
        if not self.output_directory:
            return "ERROR: Please pick an output directory."
        if "Download" in selected_steps:
            if not self.mangadex_url_text_field.value:
                return "ERROR: The URL to download must not be empty."
            try:
                get_downloader(self.mangadex_url_text_field.value)
            except ValueError as error:
                return f"ERROR: {error}"
        elif not self.input_directory or not os.path.isdir(self.input_directory):
            return "ERROR: Please pick an input directory."
        elif not (self.input_image_paths or self.input_comic_paths):
            # Each step's numbered folder is cleared before it runs, so an input inside one would be deleted. (Picked images and comic files are copied to a temporary folder first.)
            for step in selected_steps:
                step_folder = get_step_output_directory(self.output_directory, step)
                if is_same_or_inside(self.input_directory, step_folder):
                    return f'ERROR: The input is inside "{os.path.basename(step_folder)}", a folder the Pipeline clears before the "{step}" step. Please move it out, or pick a different output directory.'

        return None

    def set_locked(self, locked):
        """
        While the Pipeline runs, nothing here can be changed: the steps, the link, the input, the output folder and the Run button. What's on screen then says what it's working on.
        """
        for control in (
            *self.step_checkboxes.values(),
            self.mangadex_url_text_field,
            self.input_column,
            self.output_row,
            self.run_button,
        ):
            control.disabled = locked
        # The button styles don't change for a disabled button, so it's faded like the other tabs.
        self.run_button.opacity = 0.5 if locked else 1

        # E.g. the page has closed.
        try:
            self.update()
        except Exception:
            pass

    def handle_run_pipeline(self, e):
        # Flet runs click handlers in separate threads, so without this a double-click would start two runs.
        if self.run_button.disabled:
            return

        terminal_output = self.parent_gui.terminal_output
        selected_steps = self.get_selected_steps()

        error = self.get_error_before_running(selected_steps)
        if error:
            terminal_output.update_terminal_with_error_message(error)
            return

        # Only one job can run at a time.
        if not self.parent_gui.try_to_start_job("Pipeline"):
            return

        input_directory = self.input_directory
        temporary_input_folder = None

        # Everything after the job is started is in the "try", so whatever fails, "finally" ends the job and the app is never left locked.
        try:
            # The steps use the settings of the other tabs, which can't be opened while it runs (see "set_job_running").
            self.set_locked(True)
            self.cancelled = False
            reset_cancel_button(self.cancel_button)
            # Until the first step sets what it stops (e.g. while picked comic files are opened).
            set_cancel_click(self.cancel_button, self.cancel)
            self.show_cancel_button(True)
            # The last run's list isn't about this one (it's shown again when the first step starts).
            self.step_status_column.visible = False

            # Picked comic files or picked images are saved into their own temporary folder, so they're processed exactly like a picked folder.
            if "Download" not in selected_steps:
                temporary_input_folder = save_input_to_temporary_folder(
                    self.input_comic_paths, self.input_image_paths
                )
            if temporary_input_folder:
                input_directory = temporary_input_folder

            self.run_pipeline(selected_steps, input_directory)
        except Exception as error:
            terminal_output.update_terminal_with_error_message(
                f"ERROR: Pipeline stopped: {get_error_text(error)}"
            )
        finally:
            # First, so nothing below can leave the app locked.
            self.parent_gui.set_job_running(False)
            # Only ever delete the temporary folder made just above.
            if temporary_input_folder:
                shutil.rmtree(
                    os.path.dirname(temporary_input_folder), ignore_errors=True
                )

            report_progress(prefix="", total_started_at=None)
            reset_cancel_button(self.cancel_button)
            self.show_cancel_button(False)
            self.set_locked(False)

    def show_cancel_button(self, visible):
        self.cancel_button.visible = visible
        # This tab might not be on screen.
        try:
            self.cancel_button.update()
        except Exception:
            pass

    def cancel(self):
        # Until a step sets what Cancel stops, it only stops the steps that haven't started.
        self.cancelled = True

    def run_pipeline(self, selected_steps, input_directory):
        terminal_output = self.parent_gui.terminal_output
        step_input_directory = input_directory
        self.read_text_for_video = video_will_use_text_read_by_panel_by_panel(
            self.parent_gui.page.client_storage, selected_steps
        )

        pipeline_started_at = time.monotonic()
        report_progress(total_started_at=pipeline_started_at)
        step_durations = []
        # Each step's status under the Run button: "waiting", "running", "done" (with how long it took), "failed" or "cancelled".
        step_statuses = {step: ("waiting", "") for step in selected_steps}
        self.show_step_statuses(step_statuses)

        # Set by the loop below (there's always at least one step).
        step = step_output_directory = None
        for step_number, step in enumerate(selected_steps, start=1):
            if self.cancelled:
                self.show_pipeline_cancelled(step_statuses, step)
                return
            step_started_at = time.monotonic()
            step_statuses[step] = ("running", "")
            self.show_step_statuses(step_statuses)
            self.show_progress_message(
                f"Pipeline: Step {step_number}/{len(selected_steps)}: {step}"
            )
            # Without the stages of the step before (e.g. Panel-By-Panel's), which a model download in this step would be added to.
            report_progress(
                prefix=f"Step {step_number} of {len(selected_steps)}",
                stages=(),
                stage=None,
                upcoming_stages=(),
            )
            step_output_directory = get_step_output_directory(
                self.output_directory, step
            )
            try:
                # Clear this step's folder from any previous pipeline run. Otherwise, if this step fails without raising an error (e.g. waifu2x not installed), the next step would use the old images. Never delete a folder that holds this step's input images.
                if os.path.exists(step_output_directory) and not (
                    step_input_directory
                    and paths_overlap(step_output_directory, step_input_directory)
                ):
                    shutil.rmtree(step_output_directory)
                os.makedirs(step_output_directory, exist_ok=True)

                self.run_step(step, step_input_directory, step_output_directory)
                step_time = format_duration(time.monotonic() - step_started_at)
                step_durations.append(f"{step} {step_time}")
            except Exception as error:
                if self.cancelled or isinstance(error, DownloadCancelled):
                    self.show_pipeline_cancelled(step_statuses, step)
                    return
                step_statuses[step] = ("failed", "")
                self.show_step_statuses(step_statuses)
                message = (
                    f'ERROR: Pipeline stopped. "{step}" failed: {get_error_text(error)}'
                )
                if isinstance(error, StepFailed):
                    # The Status view keeps the step's own error (e.g. "waifu2x was not found"), which says what to fix.
                    add_line_to_terminal_output_list_view(
                        terminal_output.terminal_output_list_view,
                        message,
                        color=Nord.RED_TEXT,
                    )
                else:
                    terminal_output.update_terminal_with_error_message(message)
                return

            step_statuses[step] = ("done", step_time)
            self.show_step_statuses(step_statuses)

            if step == "Images To Video":
                break

            # A step can finish without saving anything (e.g. a MangaDex download that found no pages), so check before running the next step.
            step_input_directory = get_next_step_input_directory(
                step, step_input_directory, step_output_directory
            )
            if not folder_has_images(step_input_directory):
                step_statuses[step] = ("failed", "no images saved")
                self.show_step_statuses(step_statuses)
                terminal_output.update_terminal_with_error_message(
                    f'ERROR: Pipeline stopped. "{step}" didn\'t save any images to {step_input_directory}'
                )
                return

        total_time = format_duration(time.monotonic() - pipeline_started_at)
        self.show_progress_message(
            f"Time: {' · '.join(step_durations)} · total {total_time}"
        )
        self.show_progress_message(
            f"Pipeline finished in {total_time}! Everything was saved to {self.output_directory}"
        )
        open_directory(self.output_directory)
        # Opened last, so it's the window in front.
        open_directory(
            get_final_step_folder(step, step_input_directory, step_output_directory)
        )

    def show_pipeline_cancelled(self, step_statuses, step):
        """
        After Cancel: "step" was stopped (or never started), and so were the ones after it. The folders of the steps that finished are kept.
        """
        step_statuses[step] = ("cancelled", "")
        self.show_step_statuses(step_statuses)
        message = f'Pipeline cancelled at "{step}". The steps that finished are kept in {self.output_directory}'
        # Shown as cancelled, like a tab's own Cancel, not as an error.
        add_line_to_terminal_output_list_view(
            self.parent_gui.terminal_output.terminal_output_list_view,
            message,
            color=Nord.YELLOW,
        )
        self.parent_gui.terminal_output.hide_loading_text(
            message, success=False, cancelled=True
        )

    def show_step_statuses(self, step_statuses):
        """
        The list under the Run button: each selected step, with ✓ and its time when done, an hourglass while it runs, an empty circle while it waits, and ✗ if it failed.
        """
        icons = {
            "waiting": (ft.Icons.RADIO_BUTTON_UNCHECKED, Nord.TEXT_MUTED),
            "running": (ft.Icons.HOURGLASS_TOP, Nord.ACCENT),
            "done": (ft.Icons.CHECK_CIRCLE, Nord.GREEN),
            "failed": (ft.Icons.CANCEL, Nord.RED),
            "cancelled": (ft.Icons.DO_NOT_DISTURB_ON, Nord.YELLOW),
        }
        rows = []
        for step, (status, note) in step_statuses.items():
            icon, color = icons[status]
            rows.append(
                ft.Row(
                    controls=[
                        ft.Icon(icon, size=16, color=color),
                        ft.Text(
                            step,
                            color=Nord.TEXT if status != "waiting" else Nord.TEXT_MUTED,
                        ),
                        *(
                            [ft.Text(note, size=12, color=Nord.TEXT_MUTED)]
                            if note
                            else []
                        ),
                    ],
                    spacing=8,
                )
            )
        self.step_status_column.controls = rows
        self.step_status_column.visible = True
        # This tab might not be on screen.
        try:
            self.step_status_column.update()
        except Exception:
            pass

    def show_progress_message(self, message):
        add_line_to_terminal_output_list_view(
            self.parent_gui.terminal_output.terminal_output_list_view,
            message,
            color=Nord.GREEN,
        )

    def run_step(self, step, step_input_directory, step_output_directory):
        if step == "Download":
            terminal_output = self.parent_gui.terminal_output
            # A link pasted with a space before or after it is the same link.
            url = (self.mangadex_url_text_field.value or "").strip()
            # From MangaDex, comix.to, the Internet Archive or any web page (see "get_downloader").
            source, download = get_downloader(url)
            terminal_output.show_loading_text(f"Downloading from {source}...")
            # The downloader sets what Cancel stops once it has started (like in the Download tab).
            set_cancel_click(
                self.cancel_button, self.cancel, "Cancelling the download..."
            )
            try:
                report_output_folder(step_output_directory)
                summary = download(
                    url,
                    step_output_directory,
                    terminal_output.terminal_output_list_view,
                    self.parent_gui.page.client_storage,
                    self.cancel_button,
                )
            except DownloadCancelled as cancelled:
                terminal_output.hide_loading_text(
                    str(cancelled) or f"Download from {source} cancelled.",
                    success=False,
                    cancelled=True,
                )
                raise
            except Exception:
                terminal_output.hide_loading_text(
                    f"Download from {source} failed.", success=False
                )
                raise
            report_progress(
                chapter=None,
                chapters=None,
                pages_done=None,
                pages_total=None,
                detail=None,
            )
            terminal_output.hide_loading_text(
                summary or f"Download from {source} ended."
            )
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

        # A Cancel clicked in that tab after its own last job ended mustn't stop the Pipeline.
        step_view.cancel_event.clear()

        def stop_step():
            self.cancelled = True
            step_view.cancel_event.set()
            # E.g. waifu2x is stopped right away.
            step_view.cancel_job()

        # Like the step's own Cancel: e.g. "Cancelling after the chapter being split into panels...".
        set_cancel_click(self.cancel_button, stop_step, step_view.get_cancel_message)
        try:
            finished = step_view.start_job(step_input_directory, step_output_directory)
        finally:
            if step == "Panel-By-Panel":
                step_view.ignore_group_by_page = False
                step_view.read_text_for_video = False

        if not finished:
            raise StepFailed("see the error above")
