import os
import shutil
from gui_classes.JobView import JobView
from gui_classes.ProgressPanel import report_progress
from gui_classes.SettingsTranslate import SettingsTranslate
from default_settings import DEFAULT_SETTINGS
from translate import OLLAMA_MODELS, check_engine_ready, download_ollama_model, get_api_key, get_default_model, list_installed_ollama_models, reading_models_are_downloaded, translate_chapter
from utils import DownloadCancelled, get_last_directory, get_relative_output_path, save_folder_as_cbz

# Hayai OCR and LaMa download about 800 MB the first time, so there must be room for them.
MIN_FREE_DISK_GB = 2


def get_translate_settings(storage):
    """
    What "translate_chapter" needs, from the Translate tab's saved settings.
    """
    def get(key):
        value = storage.get(key)
        return DEFAULT_SETTINGS[key] if value is None or value == "" else value

    engine = get("translate_engine")
    return {
        "engine": engine,
        "model": (get("translate_models") or {}).get(engine) or get_default_model(engine, get("translate_from"), get("translate_to")),
        "api_key": get_api_key(engine, (get("translate_api_keys") or {}).get(engine)),
        "source_language": get("translate_from"),
        "target_language": get("translate_to"),
        "keep_honorifics": get("translate_keep_honorifics"),
        "font": get("translate_font"),
        "send_page_image": get("translate_send_page_image"),
    }


class TranslateView(JobView):
    submit_text = "Translate"
    loading_text = "Translating..."
    finished_text = "Translation finished!"
    failed_text = "Translation failed."
    next_view_name = "MagiPanelByPanelView"
    open_output_directory_when_finished = True
    cancel_message = "Cancelling after the page being translated..."

    def __init__(self, parent_gui):
        # While the model is downloaded before translating (see "download_model_if_needed").
        self.is_downloading_model = False
        super().__init__(
            parent_gui,
            settings_container=SettingsTranslate(parent_gui.page, parent_gui),
            output_setting_key="output_directory_translate",
        )

    def get_next_tab_input_directory(self, input_directory, output_directory):
        return os.path.join(output_directory, get_last_directory(input_directory))

    def get_cancel_message(self):
        # A model download stops at once; translating stops between pages.
        return "Cancelling the download..." if self.is_downloading_model else self.cancel_message

    def before_job(self):
        self.settings = get_translate_settings(self.parent_gui.page.client_storage)
        self.download_model_if_needed()
        check_engine_ready(self.settings)
        if not reading_models_are_downloaded() and shutil.disk_usage(os.path.expanduser("~")).free < MIN_FREE_DISK_GB * 1024**3:
            raise RuntimeError(f"Translate needs at least {MIN_FREE_DISK_GB} GB of free disk space for its reading and erasing models.")

    def download_model_if_needed(self):
        """
        An Ollama model that isn't downloaded yet is downloaded first, as part of the job (with its progress, and Cancel stops it at once), so Translate works without visiting "Manage Ollama models". Ollama keeps what's downloaded, so a cancelled download carries on next time.
        """
        model = self.settings["model"]
        installed = list_installed_ollama_models()
        # Not running: "check_engine_ready" says so.
        if self.settings["engine"] != "ollama" or installed is None or model in installed or f"{model}:latest" in installed:
            return
        name, size = OLLAMA_MODELS.get(model, {}).get("name", model), OLLAMA_MODELS.get(model, {}).get("size", "")
        print(f"{name} isn't downloaded yet, so it's downloaded first ({size}). Cancel stops the download; what's downloaded is kept for next time.")
        report_progress(chapter=1, chapters=1, group_label="Model", pages_done=0, pages_total=None, unit="GB", detail=f"Downloading {name} before translating")
        self.is_downloading_model = True
        try:
            finished = download_ollama_model(
                model,
                report=lambda done_gb, total_gb: report_progress(pages_done=round(done_gb, 1), pages_total=round(total_gb, 1)),
                is_cancelled=self.cancel_event.is_set,
            )
        finally:
            self.is_downloading_model = False
            report_progress(chapter=None, chapters=None, pages_done=None, pages_total=None, unit=None, detail=None)
        if not finished:
            raise DownloadCancelled(f"Cancelled the download of {name}. What was downloaded is kept, so translating again carries on.")
        print(f"Downloaded {name}.")

    def process_image_folder(self, image_folder, images, input_directory, output_directory):
        output_folder = os.path.join(output_directory, get_relative_output_path(image_folder, input_directory))
        # The glossary goes in the series folder, or next to the chapter when a single chapter was picked (so two series never share one).
        series_folder = os.path.dirname(os.path.normpath(output_folder))
        is_series_folder = os.path.normpath(series_folder) != os.path.normpath(output_directory)
        translate_chapter(
            image_folder,
            [image_info["name"] for image_info in images],
            output_folder,
            self.settings,
            glossary_folder=series_folder if is_series_folder else output_folder,
            report_progress=report_progress,
            raise_if_cancelled=self.raise_if_cancelled,
        )

        comic_file_size = self.parent_gui.page.client_storage.get("save_as_cbz")
        if comic_file_size:
            save_folder_as_cbz(
                output_folder,
                size=comic_file_size,
                reading_direction=self.parent_gui.page.client_storage.get("reading_direction"),
            )
