import os
from gui_classes.JobView import JobView
from gui_classes.SettingsImagesToVideo import SettingsImagesToVideo
from VideoCreatorFromImages import VideoCreatorFromImages, VIDEO_CODECS_BY_EXTENSION
from utils import get_relative_output_path, is_image_file


class ImagesToVideoView(JobView):
    submit_text = "Create Video"
    loading_text = "Creating Video..."
    finished_text = "Video has been created!"
    failed_text = "Video creation failed."
    cancel_message = "Cancelling after the video being made..."
    open_output_directory_when_finished = True

    def __init__(self, parent_gui):
        super().__init__(
            parent_gui,
            settings_container=SettingsImagesToVideo(parent_gui.page),
            output_setting_key="output_directory_images_to_video",
        )
        self.video_creator_from_images = VideoCreatorFromImages(
            flet_page_client_storage=self.parent_gui.page.client_storage,
        )

    def get_folder_to_open(self, input_directory, output_directory):
        # One chapter (its images are right in the input folder) is saved as "<output>/Ch 1.mp4". The "Ch 1" folder next to it only has its transcript and audio.
        if os.path.isdir(input_directory) and any(
            is_image_file(name) for name in os.listdir(input_directory)
        ):
            return output_directory
        return super().get_folder_to_open(input_directory, output_directory)

    def before_job(self):
        # Use the latest settings.
        self.video_creator_from_images.initialize_flet_client_storage_values(
            self.parent_gui.page.client_storage
        )

    def process_image_folder(
        self, image_folder, images, input_directory, output_directory
    ):
        # Highlighted images made by an earlier video run aren't panels.
        if os.path.basename(image_folder) == "images-with-highlighted-text-boxes":
            return

        # For example, "One Piece/Chapter 1". Keeps videos from different series (that both have a "Chapter 1") from overwriting each other.
        relative_output_path = get_relative_output_path(image_folder, input_directory)
        video_extension = self.parent_gui.page.client_storage.get("video_extension")

        # Fall back to mp4 for anything unsupported (e.g. "webm" or "avi" saved by an older version of the app).
        if video_extension not in VIDEO_CODECS_BY_EXTENSION:
            video_extension = "mp4"

        # Each chapter gets its own folder for its transcript, TTS audio files and highlighted images. The video goes right next to that folder.
        full_output_directory = os.path.join(output_directory, relative_output_path)
        output_file = f"{full_output_directory}.{video_extension}"

        print(f'Creating video "{relative_output_path}.{video_extension}"')

        self.video_creator_from_images.create_video_from_images(
            image_folder,
            output_file,
            full_output_directory=full_output_directory,
        )

        print(f"Images To Video: Finished creating video to {output_file}")
