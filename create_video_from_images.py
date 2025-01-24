import shutil
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
from draw_box_coords import draw_box_coords_box_list
from magi_ch_55_frieren_essential_text import magi_ch_55_frieren_essential_text
from magi_frieren_ch_55_panel_6_output import magi_frieren_ch_55_panel_6_output
from magi_ch_55_frieren_panel_1_to_7_output import (
    magi_ch_55_frieren_panel_1_to_7_output,
)
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

    highlight_text_boxes_in_images = False
    clean_up_tts_audio_files_folder = False

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
        highlight_text_boxes_in_images = flet_page_client_storage.get(
            "highlight_text_boxes_in_images"
        )
        clean_up_tts_audio_files_folder = flet_page_client_storage.get(
            "clean_up_tts_audio_files_folder"
        )

    if speech_text_parser:
        if use_text_to_speech_azure:
            # TODO: Bring this back after testing is done.
            # essential_text_in_images_matrix = (
            #     speech_text_parser.get_essential_text_list_in_images(image_folder)
            # )

            # essential_text_in_images_matrix = [
            #     [
            #         "Red Line: Holy Land of Mariejoa",
            #         "vanished...?",
            #         "Yeah. That's what happened.",
            #         "I don't mean just like a figure of speech, either. He literally vanished into thin air!!",
            #         "Fuffuffu... it sure took me by surprise, I'll tell you that. Does the Kage Kage no mi have that kind of power?",
            #         "This is no joking matter!!!",
            #     ],
            #     [
            #         "Ahh, don't worry... He was half-dead already. There was no saving him, no matter where he went.",
            #         "Well... unless he managed to resurrect himself as a zombie, of course... Fuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffuffu! Hey, it serves him right.",
            #         "And you call this doing your job, do you...?!!!",
            #     ],
            # ]

            essential_text_in_images_matrix = [
                [
                    "A battle between mages is akin to a rock-paper-scissors match, after all.",
                    "Albeit a rock-paper-scissors match",
                    "that is extremely complex, difficult to read and involves a myriad of moves.",
                ],
            ]

            # essential_text_in_images_matrix = [
            #     [],
            #     [],
            #     [
            #         "I more or less get the picture now.",
            #         'You people are buying time for Friedman to defeat this "Spiegel", the "Reflective Water Demon".',
            #         "Well, for the clones, we've already dealt with three of them.",
            #         "It seems this discussion will be quick then.",
            #         "In that case-",
            #     ],
            #     [
            #         "..... Oh my.",
            #         "It seems Sense-san's clone got crushed just now.",
            #         "...This mama. The one who took it down must be libel, the third- class mage.",
            #     ],
            #     [
            #         "What a surprising outcome.",
            #         "You think? That match-up's pretty off.",
            #     ],
            #     [
            #         "A battle between images is akin to a rock- paper-scissors match, after all.",
            #         "Albert a rock-paper- scissors match",
            #         "that is extremely complex, difficult to read and involves a myriad of moves.",
            #     ],
            #     [
            #         "So you would like to increase the number of available moves we have, by how- ever little it may be.",
            #         "Very well. I'll help you hold back the clones.",
            #     ],
            # ]

            # TODO: Will need the full Magi output for the highlight text boxes feature.
            # TODO: Move this up to the top later - this is a separate feature from TTS that should be able to be used with other options "Image Duration" and "Reading WPM (Seconds)".

            magi_output_data = magi_frieren_ch_55_panel_6_output

            if highlight_text_boxes_in_images:
                images_with_highlighted_text_boxes_folder = os.path.join(
                    full_output_directory, "images-with-highlighted-text-boxes"
                )

                for index, image_file in enumerate(images):
                    magi_image_data = magi_output_data[index]
                    text_matrix_boxes_coords = magi_image_data["texts"]
                    essential_text_arr = magi_image_data["is_essential_text"]

                    essential_text_matrix_boxes_coords = [
                        box_coords
                        for index, box_coords in enumerate(text_matrix_boxes_coords)
                        if essential_text_arr[index]
                    ]

                    draw_box_coords_box_list(
                        essential_text_matrix_boxes_coords,
                        image_file,
                        images_with_highlighted_text_boxes_folder,
                        flet_page_client_storage,
                    )

            for index, panel_text_arr in enumerate(essential_text_in_images_matrix):
                image_path = images[index]
                base_name, _ = os.path.splitext(os.path.basename(image_path))

                full_audio_files_output_directory = (
                    f"{full_output_directory}/audio-files"
                )

                audio_output_file = (
                    f"{full_audio_files_output_directory}/{base_name}.wav"
                )
                panel_audio_file_duration = 1

                os.makedirs(full_audio_files_output_directory, exist_ok=True)

                if panel_text_arr and len(panel_text_arr) > 0:
                    if highlight_text_boxes_in_images:
                        for index, text_str in enumerate(panel_text_arr):
                            highlight_text_audio_output_file = f"{full_audio_files_output_directory}/{base_name}-{index + 1}.wav"
                            tts.generate_azure_audio(
                                [text_str], highlight_text_audio_output_file
                            )

                            panel_audio_file_duration = get_audio_file_duration(
                                highlight_text_audio_output_file
                            )

                            images_duration_based_on_tts.append(
                                panel_audio_file_duration
                            )
                    else:
                        tts.generate_azure_audio(panel_text_arr, audio_output_file)

                        panel_audio_file_duration = get_audio_file_duration(
                            audio_output_file
                        )

                        images_duration_based_on_tts.append(panel_audio_file_duration)
                else:
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

        image_paths_to_use = images

        if highlight_text_boxes_in_images:
            sorted_images_from_highlighted_text = sorted(
                os.listdir(images_with_highlighted_text_boxes_folder),
                key=natural_sort_key,
            )
            files_that_are_images = [
                file
                for file in sorted_images_from_highlighted_text
                if file.lower().endswith((".png", ".jpg", ".jpeg"))
            ]
            image_paths_to_use = [
                os.path.join(images_with_highlighted_text_boxes_folder, file)
                for file in files_that_are_images
            ]

        for index, img in enumerate(image_paths_to_use):
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
                highlight_text_boxes_in_images=highlight_text_boxes_in_images,
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

                use_image_pre_tts_audio_delay = True

                # Check if the image can use "Pre-TTS"
                if highlight_text_boxes_in_images:
                    current_panel_num = int(base_name.split("-")[1])
                    is_first_base_panel_image = current_panel_num == 1

                    if not is_first_base_panel_image:
                        use_image_pre_tts_audio_delay = False

                if image_pre_tts_audio_delay > 0 and use_image_pre_tts_audio_delay:
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

                use_image_post_tts_audio_delay = True

                # If the image is the last image in the directory or the next image after this one has a different starting base_name, then add the post_tts_delay. Else, do not add it.
                if highlight_text_boxes_in_images:
                    is_last_image_in_dir = index == len(image_paths_to_use) - 1

                    if not is_last_image_in_dir:
                        next_image_path = image_paths_to_use[index + 1]
                        next_panel_base_name, _ = os.path.splitext(
                            os.path.basename(next_image_path)
                        )

                        current_panel_starting_base_name = base_name.split("-")[0]
                        next_panel_starting_base_name = next_panel_base_name.split("-")[
                            0
                        ]

                        last_highlighted_text_image_for_panel = (
                            current_panel_starting_base_name
                            != next_panel_starting_base_name
                        )

                        if not last_highlighted_text_image_for_panel:
                            use_image_post_tts_audio_delay = False

                if use_image_post_tts_audio_delay:
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

    fps = 1

    if highlight_text_boxes_in_images or use_text_to_speech_azure:
        fps = 2

    # "fps" is set to 1 as the images being saved are typically going to be Manga Panels and will have no smooth transitions between panels so no need to create extra frames for nothing. Just show the same frame for the specified duration.
    video.write_videofile(output_file, fps=fps)

    if (
        clean_up_tts_audio_files_folder
        and full_audio_files_output_directory
        and os.path.exists(full_audio_files_output_directory)
    ):
        # Remove the directory and all its contents
        shutil.rmtree(full_audio_files_output_directory)
        print('Removed TTS "audio-files" folders')


def get_img_duration(
    image_displayed_duration,
    images_duration_based_on_wpm,
    images_duration_based_on_tts,
    index,
    use_reading_speed_wpm,
    use_minimum_image_duration,
    minimum_image_duration,
    use_text_to_speech_azure,
    highlight_text_boxes_in_images,
):
    final_image_duration = image_displayed_duration

    if use_text_to_speech_azure:
        if highlight_text_boxes_in_images:
            final_image_duration = float(images_duration_based_on_tts[index])
        else:
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
