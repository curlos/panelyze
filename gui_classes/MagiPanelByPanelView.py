import json
import os
import flet as ft
from gui_classes.WrappingCheckbox import WrappingCheckbox
from gui_classes.JobView import JobView
from gui_classes.ProgressPanel import report_progress
from gui_classes import Nord
from gui_classes.ReadingDirectionSetting import get_reading_direction_dropdown
from utils import (
    PANELS_INFO_FILE_NAME,
    get_image_folders,
    get_last_directory,
    get_panels_folder,
    get_relative_output_path,
    is_image_file,
    pluralize,
    read_saved_reading_direction,
    save_folder_as_cbz,
)


class MagiPanelByPanelView(JobView):
    submit_text = "Split Into Panels"
    loading_text = "Converting to Panel-By-Panel..."
    finished_text = "Panel-By-Panel conversion finished!"
    failed_text = "Panel-By-Panel conversion failed."
    cancel_message = "Cancelling after the chapter being split into panels..."
    open_output_directory_when_finished = True
    next_view_name = "UpscaleImagesView"

    def __init__(self, parent_gui):
        storage = parent_gui.page.client_storage
        # The Pipeline's next steps need all of the panels together, so it turns this off for its Panel-By-Panel step.
        self.ignore_group_by_page = False
        # The Pipeline turns this on when it will also make a video, so the text is read from the pages here.
        self.read_text_for_video = False
        # The chapters that were already split into panels (and kept) in this run (see "before_job").
        self.kept_chapters = []

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
                        WrappingCheckbox(
                            label="Show full characters (can include parts of nearby panels)",
                            value=storage.get("show_full_characters"),
                            on_change=lambda e: storage.set(
                                "show_full_characters", e.data == "true"
                            ),
                        ),
                        WrappingCheckbox(
                            label="Split very tall panels for phones (never through text)",
                            value=storage.get("split_tall_panels"),
                            on_change=lambda e: storage.set(
                                "split_tall_panels", e.data == "true"
                            ),
                        ),
                        WrappingCheckbox(
                            label="Split into panels again even if already split",
                            value=storage.get("split_panels_again"),
                            on_change=lambda e: storage.set(
                                "split_panels_again", e.data == "true"
                            ),
                        ),
                        # Panels ignores the comic file's "one image at a time" marking (see "get_comic_info").
                        ft.Text(
                            'Reading the panels\' comic files in the Panels app? Set "Presets > Configure Reader > Number of Pages" to "1". On "2" or "Automatic", it shows two narrow panels side by side when there\'s room (e.g. a phone held sideways), which can show them in the wrong order.',
                            size=12,
                            color=Nord.TEXT_MUTED,
                        ),
                    ]
                ),
                width=350,
                padding=ft.padding.only(left=10, top=5, right=10),
            ),
            output_setting_key="output_directory_panel_by_panel",
        )
        directories = self.pick_input_output_directories_container
        directories.get_extra_input_summary = self.get_already_split_summary
        # The settings that change the panels change which chapters are already split.
        for control in directories.settings_container.content.controls:
            if isinstance(control, WrappingCheckbox):
                # Its box and its label each call the same handler.
                control.on_checkbox_change = control.checkbox.on_change = refresh_after(
                    control.on_checkbox_change, directories.refresh_input_summary
                )
            elif getattr(control, "on_change", None):
                control.on_change = refresh_after(control.on_change, directories.refresh_input_summary)

    def get_already_split_summary(self, input_directory, output_directory):
        """
        What will really be split, for the line under the picked folder: "only 1 new chapter to split" when the others are already split (and kept, see "process_image_folder"). "" when none are.
        """
        storage = self.parent_gui.page.client_storage
        if storage.get("split_panels_again") or not output_directory or not os.path.isdir(input_directory):
            return ""
        group_by_page = bool(storage.get("group_panels_by_page"))
        try:
            image_folders = list(get_image_folders(input_directory))
            kept = sum(
                1
                for image_folder, images in image_folders
                if read_panels_info(get_panels_folder(output_directory, get_relative_output_path(image_folder, input_directory), group_by_page))
                == get_panels_info(image_folder, images, storage, group_by_page, self.read_text_for_video)
            )
        except OSError:
            # E.g. a page was deleted meanwhile. It's only a hint, so it's left out.
            return ""
        if not kept:
            return ""
        if kept == len(image_folders):
            return "already split, nothing new to split"
        return f"only {pluralize(len(image_folders) - kept, 'new chapter')} to split"

    def before_job(self):
        self.kept_chapters = []

    def get_finished_text(self, chapter_count):
        # Like the Download tab's "Already downloaded".
        if not self.kept_chapters:
            return self.finished_text
        if len(self.kept_chapters) == chapter_count:
            if chapter_count == 1:
                return f"Already split into panels (kept): {self.kept_chapters[0]}"
            return f"Already split into panels (kept): {pluralize(chapter_count, 'chapter')}"
        verb = "was" if len(self.kept_chapters) == 1 else "were"
        return f"{self.finished_text} {len(self.kept_chapters)} of {pluralize(chapter_count, 'chapter')} {verb} already split (kept)."

    def get_folder_to_open(self, input_directory, output_directory):
        group_by_page = bool(self.parent_gui.page.client_storage.get("group_panels_by_page"))
        folder = get_panels_folder(output_directory, get_last_directory(input_directory), group_by_page)
        return folder if os.path.isdir(folder) else output_directory

    def get_next_tab_input_directory(self, input_directory, output_directory):
        # Panels grouped by page have a folder for each page, which is not what the next tab expects.
        if self.parent_gui.page.client_storage.get("group_panels_by_page"):
            return None

        return get_panels_folder(output_directory, get_last_directory(input_directory))

    def process_image_folder(self, image_folder, images, input_directory, output_directory):
        # Imported here so that torch and transformers only load when Magi is actually used, not when the app starts.
        from magi import get_magi

        storage = self.parent_gui.page.client_storage
        group_by_page = bool(
            storage.get("group_panels_by_page") and not self.ignore_group_by_page
        )
        panels_folder = get_panels_folder(
            output_directory, get_relative_output_path(image_folder, input_directory), group_by_page
        )
        panels_info = get_panels_info(image_folder, images, storage, group_by_page, self.read_text_for_video)
        is_already_split = not storage.get("split_panels_again") and read_panels_info(panels_folder) == panels_info
        if is_already_split:
            print(f"Already split into panels (kept): {panels_folder}")
            self.kept_chapters.append(os.path.basename(image_folder))
            report_progress(detail="Already split into panels (kept)")
        else:
            magi = get_magi()
            magi.show_full_characters = bool(storage.get("show_full_characters"))
            magi.split_tall_panels = bool(storage.get("split_tall_panels"))
            magi.get_panels_for_chapter(
                image_folder,
                output_directory,
                selected_input_directory=input_directory,
                reading_direction=storage.get("reading_direction"),
                group_by_page=group_by_page,
                read_text=self.read_text_for_video,
            )
            # A chapter where nothing was saved is still tried again next time ("read_panels_info" needs panels).
            if os.path.isdir(panels_folder):
                with open(os.path.join(panels_folder, PANELS_INFO_FILE_NAME), "w", encoding="utf-8") as file:
                    json.dump(panels_info, file)

        if storage.get("save_as_cbz"):
            reading_direction = storage.get("reading_direction")
            if reading_direction in (None, "", "auto"):
                # On "Automatic", Magi uses the direction saved next to the panels, or manga order if there isn't one.
                reading_direction = read_saved_reading_direction(panels_folder) or "rtl"
            save_folder_as_cbz(
                panels_folder,
                size=storage.get("save_as_cbz"),
                reading_direction=reading_direction,
                one_image_at_a_time=True,
            )


def get_panels_info(image_folder, images, storage, group_by_page, read_text):
    """
    What a chapter's panels are made from: its pages (names and sizes) and every setting that changes the panels. Saved next to the panels ("panels-info.json"), so the next run can tell they're still up to date. Not when the pages changed: imported comic files and picked images are copied to a new temporary folder on every run.
    """
    return {
        "pages": [[image["name"], os.path.getsize(os.path.join(image_folder, image["name"]))] for image in images],
        "reading_direction": storage.get("reading_direction"),
        # On "Automatic", the direction a download saved next to the pages decides the order.
        "saved_reading_direction": read_saved_reading_direction(image_folder),
        "show_full_characters": bool(storage.get("show_full_characters")),
        "split_tall_panels": bool(storage.get("split_tall_panels")),
        "group_by_page": group_by_page,
        "read_text": bool(read_text),
    }


def read_panels_info(panels_folder):
    """
    The "panels-info.json" of a chapter's panels, or None if it's missing, unreadable, or its panels are gone.
    """
    if not os.path.isdir(panels_folder) or not any(
        (name.startswith("panel_") and is_image_file(name)) or name.startswith("page_") for name in os.listdir(panels_folder)
    ):
        return None
    try:
        with open(os.path.join(panels_folder, PANELS_INFO_FILE_NAME), encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return None


def refresh_after(on_change, refresh):
    """
    "on_change", then "refresh" (the settings are saved first).
    """
    def handle_change(e):
        on_change(e)
        refresh()

    return handle_change
