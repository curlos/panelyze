"""
The default value of every setting, in one place. Used when the app first opens, by "Reset All Settings", and by the settings forms.
"""

import os
import sys

# Shown in Settings → About. The first release is 1.0.0 (spec 40).
APP_VERSION = "1.0.0"

# Where each system keeps apps' logs: "~/Library/Logs" on a Mac, "AppData\Local" on Windows. (Here, not in "AppOutput", so "self_test.py" can use it without importing flet.)
if sys.platform == "win32":
    LOG_FOLDER = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local"),
        "Panelyze",
        "Logs",
    )
else:
    LOG_FOLDER = os.path.expanduser("~/Library/Logs/Panelyze")

# matplotlib's font cache in the packaged app (see the top of gui.py), in the folder each system keeps apps' caches in.
if sys.platform == "win32":
    MATPLOTLIB_CACHE_FOLDER = os.path.join(os.path.dirname(LOG_FOLDER), "matplotlib")
else:
    MATPLOTLIB_CACHE_FOLDER = os.path.expanduser("~/Library/Caches/Panelyze/matplotlib")

# Everything the app makes is saved here unless a different folder is picked (in the app's Settings, or for just one tool). Each tool gets its own folder inside it, so one tool's files never mix with another's.
PANELYZE_FOLDER = os.path.join(os.path.expanduser("~"), "Documents", "Panelyze")


# The folder this code is in.
CODE_FOLDER = os.path.dirname(os.path.abspath(__file__))


def get_dev_output_folder(code_folder=CODE_FOLDER):
    """
    When the app runs from source (the main repo or a spec's git worktree), everything is saved in "~/Documents/Panelyze/<repo folder>" (e.g. ".../Panelyze/panelyze-main" or ".../Panelyze/17-second-downloader"), so development and testing never mix with the normal folders. Source has a ".git" (a folder in the main repo, a file in a worktree); the packaged app has none, so it returns None and saves in "~/Documents/Panelyze".
    """
    if os.path.exists(os.path.join(code_folder, ".git")):
        return os.path.join(PANELYZE_FOLDER, os.path.basename(code_folder))
    return None


DEV_OUTPUT_FOLDER = get_dev_output_folder()


def can_pick_output_folders():
    """
    Output folders can only be picked in the packaged app. A picked folder is saved in the settings, which every run shares (the packaged app, the main repo and every worktree), so one picked while developing would send other runs' files to the wrong place.
    """
    return not DEV_OUTPUT_FOLDER


# The folder of each tool inside the Panelyze folder, by the setting that holds the output folder picked for that tool.
OUTPUT_SUBFOLDERS = {
    "output_directory_mangadex": "Downloads",
    "output_directory_panel_by_panel": "Panel-By-Panel",
    "output_directory_upscale_images": "Upscaled Images",
    "output_directory_images_to_video": "Videos",
    "output_directory_pipeline": "Pipeline",
}


def get_output_directory(storage, output_setting_key):
    """
    Where a tool saves its results: the folder picked for that tool, or else its folder inside the Panelyze folder (the repo's own folder when running from source, see "get_dev_output_folder").
    """
    picked_directory = storage.get(output_setting_key)

    # From source, a folder picked earlier (maybe in the packaged app) is ignored (see "can_pick_output_folders").
    if picked_directory and can_pick_output_folders():
        return picked_directory

    # The Panelyze folder saved in the settings is shared by the main repo, every worktree and the packaged app, so the repo's own folder comes first.
    panelyze_folder = (
        DEV_OUTPUT_FOLDER or storage.get("panelyze_folder") or PANELYZE_FOLDER
    )
    return os.path.join(panelyze_folder, OUTPUT_SUBFOLDERS[output_setting_key])


def get_panelyze_folder_inside(picked_directory):
    """
    The Panelyze folder to use when "picked_directory" is chosen as the place to save things. A "Panelyze" folder is made inside it so the tools' folders don't end up scattered among the other files in it (e.g. in Downloads), unless it already is the "Panelyze" folder.
    """
    if os.path.basename(os.path.normpath(picked_directory)) == "Panelyze":
        return picked_directory

    return os.path.join(picked_directory, "Panelyze")


DEFAULT_SETTINGS = {
    # Output folders. The folder of each tool is empty (use the Panelyze folder) until one is picked for that tool.
    "panelyze_folder": PANELYZE_FOLDER,
    "output_directory_mangadex": "",
    "output_directory_panel_by_panel": "",
    "output_directory_upscale_images": "",
    "output_directory_images_to_video": "",
    "output_directory_pipeline": "",
    # Also save the downloaded chapters (Download tab), panels (Panel-By-Panel) and upscaled images (Upscale) of each chapter as a comic file to read in comic reader apps: "" (don't), "small" (for phones and tablets) or "full".
    "save_as_cbz": "",
    # The tab that's open when Panelyze starts (one of the tabs at the top, picked in Settings). Download, since a new user has nothing to split into panels yet.
    "start_tab": "Download",
    # MangaDex Downloader
    "language": {"name": "English", "code": "en"},
    "use_start_and_end_pages": False,
    "use_start_and_end_chapters": False,
    "use_chapter_title": True,
    "no_group_name": False,
    "replace_existing_manga": False,
    "no_oneshot_chapters": False,
    "use_chapter_cover": False,
    "use_volume_cover": False,
    "start_page": "",
    "end_page": "",
    "start_chapter": "",
    "end_chapter": "",
    # Which upload to take when a chapter was uploaded by several groups: "newest", "first", or "group" (the "preferred_group" link's, or the newest when that group skipped the chapter).
    "upload_choice": "newest",
    "preferred_group": "",
    # A web page: every image is saved, or only the ones whose shorter side is at least this many pixels.
    "use_web_page_min_size": True,
    "web_page_min_size": "600",
    # Panel-By-Panel and Images To Video
    "reading_direction": "auto",
    # Panel-By-Panel
    "group_panels_by_page": False,
    "show_full_characters": False,
    "split_tall_panels": True,
    # A chapter whose panels are already up to date (same pages and settings, see "panels-info.json") is skipped, unless this is on.
    "split_panels_again": False,
    # Upscale Images
    "use_custom_panel_image_height": False,
    "custom_panel_image_height": "",
    "use_max_image_width": False,
    "max_image_width": "",
    "upscale_ratio": 2,
    "noise_level": 0,
    "image_format": "webp",
    "limit_upscale_to_4k": True,
    # "fast", "better" or "best" (see "UPSCALE_MODELS" in "SettingsUpscaleImages.py").
    "upscale_model": "fast",
    # Images To Video
    "video_height": 1080,
    "video_aspect_ratio": "16:9",
    # How long each panel shows: by reading speed, a fixed time, or the voice ("use_text_to_speech_azure"). Only one of the three is on (they're one choice in the tab).
    "use_reading_speed_wpm": False,
    "reading_speed_wpm": 150,
    "use_image_displayed_duration": False,
    "image_displayed_duration": 5,
    "use_minimum_image_duration": True,
    "minimum_image_duration": 3,
    # A voice reads the text (the free Edge voice by default: people expect a video to have sound). The name is old: it's for every voice, not only Azure.
    "use_text_to_speech_azure": True,
    "image_pre_tts_audio_delay": 0,
    # A short breath after each panel's voice, so the next panel doesn't start the moment the last word ends.
    "image_post_tts_audio_delay": 0.5,
    "video_extension": "mp4",
    "clean_up_tts_audio_files_folder": True,
    # Images To Video - Text-To-Speech ("edge" is free and the default. "azure" needs your own key. The "azure_" voice settings are used by both engines.)
    "tts_engine": "edge",
    "azure_voice_style": "none",
    "azure_voice_style_degree": 1,
    "azure_voice_locale": "en-US",
    "azure_voice_name": "en-US-AriaNeural",
    "azure_voice_volume": "x-loud",
    "azure_voice_rate": "medium",
    "azure_voice_pitch": "medium",
    "azure_break_time_between_text": 0,
    # Images To Video - Highlight Text Boxes In Images
    "highlight_text_boxes_in_images": False,
    "clean_up_images_with_highlighted_text_boxes_folder": True,
    "images_to_video_text_box_border_width": 1,
    "images_to_video_text_box_padding": 15,
    "images_to_video_text_box_border_style": "solid",
    "images_to_video_text_box_border_color": "#ef4444",
    "images_to_video_text_box_border_color_opacity": 1,
    "images_to_video_text_box_background_color": "#eab308",
    "images_to_video_text_box_background_color_opacity": 0.25,
}
