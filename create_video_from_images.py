from moviepy import (
    AudioClip,
    ImageClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
)
import os

from TextToSpeech import TextToSpeech
from SpeechTextParser import SpeechTextParser
from utils import (
    get_last_two_directories_obj,
    natural_sort_key,
    select_folder,
    get_audio_file_duration,
)


def create_video_from_images(
    image_folder,
    output_file,
    image_displayed_duration=3,
    video_height=1080,
    speech_text_parser=None,
    flet_page_client_storage=None,
    tts=None,
    full_output_directory=None,
):
    sorted_chapter_directory = sorted(os.listdir(image_folder), key=natural_sort_key)
    files_that_are_images = [
        file
        for file in sorted_chapter_directory
        if file.lower().endswith((".png", ".jpg", ".jpeg"))
    ]
    images = [os.path.join(image_folder, file) for file in files_that_are_images]

    use_reading_speed_wpm = True
    reading_speed_wpm = 150
    images_duration_based_on_wpm = []

    use_minimum_image_duration = True
    minimum_image_duration = 5

    use_text_to_speech_azure = False
    images_duration_based_on_tts = []

    image_pre_tts_audio_delay = 0
    image_post_tts_audio_delay = 0

    if flet_page_client_storage:
        use_reading_speed_wpm = flet_page_client_storage.get("use_reading_speed_wpm")
        reading_speed_wpm = int(flet_page_client_storage.get("reading_speed_wpm"))
        image_displayed_duration = int(
            flet_page_client_storage.get("image_displayed_duration") or 0
        )
        use_minimum_image_duration = flet_page_client_storage.get(
            "use_minimum_image_duration"
        )
        minimum_image_duration = int(
            flet_page_client_storage.get("minimum_image_duration") or 0
        )

        use_text_to_speech_azure = flet_page_client_storage.get(
            "use_text_to_speech_azure"
        )

        image_pre_tts_audio_delay = int(
            flet_page_client_storage.get("image_pre_tts_audio_delay") or 0
        )
        image_post_tts_audio_delay = int(
            flet_page_client_storage.get("image_post_tts_audio_delay") or 0
        )

    if speech_text_parser:
        if use_text_to_speech_azure:
            essential_text_in_images_matrix = (
                speech_text_parser.get_essential_text_list_in_images(image_folder)
            )

            for index, panel_text_arr in enumerate(essential_text_in_images_matrix):
                image_path = images[index]
                base_name, _ = os.path.splitext(os.path.basename(image_path))

                all_panel_text_str = " ".join(panel_text_arr)

                full_audio_files_output_directory = (
                    f"{full_output_directory}/audio-files"
                )

                audio_output_file = (
                    f"{full_audio_files_output_directory}/{base_name}.wav"
                )
                panel_audio_file_duration = 0

                os.makedirs(full_audio_files_output_directory, exist_ok=True)

                if all_panel_text_str:
                    print(all_panel_text_str)
                    tts.generate_azure_audio(all_panel_text_str, audio_output_file)

                    panel_audio_file_duration = get_audio_file_duration(
                        audio_output_file
                    )

                images_duration_based_on_tts.append(panel_audio_file_duration)
        elif use_reading_speed_wpm:
            images_duration_based_on_wpm = (
                speech_text_parser.get_images_duration_based_on_wpm(
                    image_folder, reading_speed_wpm
                )
            )

    # Ensure the output directory exists
    output_directory = os.path.dirname(output_file)
    os.makedirs(output_directory, exist_ok=True)

    def get_clips():
        clips = []

        for index, img in enumerate(images):
            # Extract base name of the image (e.g., panel_1.png -> panel_1)
            base_name, _ = os.path.splitext(os.path.basename(img))
            wav_path = os.path.join(
                full_output_directory, f"audio-files/{base_name}.wav"
            )

            img_duration = get_img_duration(
                image_displayed_duration=float(image_displayed_duration),
                images_duration_based_on_wpm=images_duration_based_on_wpm,
                images_duration_based_on_tts=images_duration_based_on_tts,
                index=index,
                use_reading_speed_wpm=use_reading_speed_wpm,
                use_minimum_image_duration=use_minimum_image_duration,
                minimum_image_duration=minimum_image_duration,
                use_text_to_speech_azure=use_text_to_speech_azure,
            )

            image_clip = (
                ImageClip(img)
                .resized(height=int(video_height))
                .with_duration(img_duration)
            )

            # Check if the corresponding .wav file exists
            if os.path.exists(wav_path):
                # Get the actual duration of the audio file
                audio_clip = AudioFileClip(wav_path)
                audio_duration = audio_clip.duration

                # Adjust the duration to avoid exceeding the audio duration
                adjusted_duration = min(img_duration, audio_duration)

                # Subclip the audio to match the adjusted duration
                audio_clip = audio_clip.subclipped(0, adjusted_duration)

                combined_audio_clips = audio_clip

                if image_pre_tts_audio_delay > 0:
                    adjusted_duration += image_pre_tts_audio_delay

                    # Add padding before the audio starts
                    padding_before_audio_file_clip = AudioClip(
                        lambda t: 0, duration=image_pre_tts_audio_delay
                    )

                    # Combine the silent audio and actual audio
                    combined_audio_clips = CompositeAudioClip(
                        [
                            padding_before_audio_file_clip.with_start(0),
                            audio_clip.with_start(image_pre_tts_audio_delay),
                        ]
                    )

                adjusted_duration += image_post_tts_audio_delay

                # Update the image clip's duration and add the audio
                image_clip = image_clip.with_duration(adjusted_duration).with_audio(
                    combined_audio_clips
                )

            # Add the clip to the list
            clips.append(image_clip)

        return clips

    # Create a list of ImageClips, resizing them to fit the video height
    clips = get_clips()

    # Concatenate all ImageClips into a single video
    video = concatenate_videoclips(clips, method="compose")

    # "fps" is set to 1 as the images being saved are typically going to be Manga Panels and will have no smooth transitions between panels so no need to create extra frames for nothing. Just show the same frame for the specified duration.
    video.write_videofile(output_file, fps=1)


def get_img_duration(
    image_displayed_duration,
    images_duration_based_on_wpm,
    images_duration_based_on_tts,
    index,
    use_reading_speed_wpm,
    use_minimum_image_duration,
    minimum_image_duration,
    use_text_to_speech_azure,
):
    final_image_duration = image_displayed_duration

    if use_text_to_speech_azure:
        final_image_duration = float(images_duration_based_on_tts[index])
    elif use_reading_speed_wpm:
        final_image_duration = float(images_duration_based_on_wpm[index])

    if use_minimum_image_duration:
        # This is necessary because not every image will have text. So, for an image without text, "image_duration_based_on_wpm" would be 0 so the image would almost be skipped over in the video but obviously, we need to give the reader/viewer a chance to look at the image, so there should be a minimum duration (in this case it's 5 seconds).
        return max(final_image_duration, minimum_image_duration)

    return final_image_duration


is_running_as_main_program = __name__ == "__main__"


if is_running_as_main_program:
    tts = TextToSpeech()
    speech_text_parser = SpeechTextParser()

    print("Select Input Directory:")
    input_directory = select_folder()

    print("Select Output Directory:")
    output_directory = select_folder()

    series_name, chapter_name = get_last_two_directories_obj(input_directory)
    full_output_directory = f"{output_directory}/{series_name}"
    output_file = f"{full_output_directory}/{chapter_name}.mp4"

    print(f'Creating video "{series_name}/{chapter_name}.mp4"')
    create_video_from_images(
        image_folder=input_directory,
        output_file=output_file,
        speech_text_parser=speech_text_parser,
        tts=tts,
        full_output_directory=full_output_directory,
    )
