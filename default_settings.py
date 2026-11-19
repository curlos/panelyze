"""
The default value of every setting, in one place. Used when the app first opens, by "Reset All Settings", and by the settings forms.
"""
import os

# Everything the app makes is saved here unless a different folder is picked (in the app's Settings, or for just one tool). Each tool gets its own folder inside it, so one tool's files never mix with another's.
PANELYZE_FOLDER = os.path.join(os.path.expanduser("~"), "Documents", "Panelyze")

# The folder of each tool inside the Panelyze folder, by the setting that holds the output folder picked for that tool.
OUTPUT_SUBFOLDERS = {
    "output_directory_mangadex": "MangaDex Downloads",
    "output_directory_panel_by_panel": "Panel-By-Panel",
    "output_directory_upscale_images": "Upscaled Images",
    "output_directory_images_to_video": "Videos",
    "output_directory_pipeline": "Pipeline",
}


def get_output_directory(storage, output_setting_key):
    """
    Where a tool saves its results: the folder picked for that tool, or else its folder inside the Panelyze folder.
    """
    picked_directory = storage.get(output_setting_key)

    if picked_directory:
        return picked_directory

    panelyze_folder = storage.get("panelyze_folder") or PANELYZE_FOLDER
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
        # Also save the panels (Panel-By-Panel) and upscaled images (Upscale) of each chapter as a comic file to read in comic reader apps: "" (don't), "small" (for phones and tablets) or "full".
        "save_as_cbz": "",
        # The tab that's open when Panelyze starts (one of the tabs at the top, picked in Settings).
        "start_tab": "Panel-By-Panel",
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
        # Panel-By-Panel and Images To Video
        "reading_direction": "rtl",
        # Panel-By-Panel
        "group_panels_by_page": False,
        # Upscale Images
    "use_custom_panel_image_height": False,
    "custom_panel_image_height": "",
    "use_max_image_width": False,
    "max_image_width": "",
        "upscale_ratio": 2,
        "noise_level": 0,
        "image_format": "png",
        "limit_upscale_to_4k": True,
        # "fast", "better" or "best" (see "UPSCALE_MODELS" in "SettingsUpscaleImages.py").
        "upscale_model": "fast",
        # Images To Video
        "video_height": 1080,
        "video_aspect_ratio": "16:9",
        "use_reading_speed_wpm": True,
        "reading_speed_wpm": 150,
        "use_image_displayed_duration": False,
        "image_displayed_duration": 5,
        "use_minimum_image_duration": True,
        "minimum_image_duration": 3,
        "use_text_to_speech_azure": False,
        "image_pre_tts_audio_delay": 0,
        "image_post_tts_audio_delay": 0,
        "video_extension": "mp4",
        "clean_up_tts_audio_files_folder": False,
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
        "clean_up_images_with_highlighted_text_boxes_folder": False,
        "images_to_video_text_box_border_width": 1,
        "images_to_video_text_box_padding": 15,
        "images_to_video_text_box_border_style": "solid",
        "images_to_video_text_box_border_color": "#ef4444",
        "images_to_video_text_box_border_color_opacity": 1,
        "images_to_video_text_box_background_color": "#eab308",
        "images_to_video_text_box_background_color_opacity": 0.25,
    }
