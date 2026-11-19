"""
The default value of every setting, in one place. Used when the app first opens, by "Reset All Settings", and by the settings forms.
"""

DEFAULT_SETTINGS = {
        # MangaDex Downloader
        "language": {"name": "English", "code": "en"},
        "use_start_and_end_pages": False,
        "use_start_and_end_chapters": False,
        "use_chapter_title": False,
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
        # Images To Video
        "video_height": 1080,
        "video_aspect_ratio": "16:9",
        "use_reading_speed_wpm": True,
        "reading_speed_wpm": 150,
        "use_image_displayed_duration": False,
        "image_displayed_duration": 5,
        "use_minimum_image_duration": True,
        "minimum_image_duration": 5,
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
