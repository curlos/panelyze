from gui_classes.JobView import JobView
import os
from gui_classes.SettingsUpscaleImages import SettingsUpscaleImages
from utils import (
    MAX_UPSCALED_IMAGE_SIDE,
    ProcessManager,
    get_capped_upscale_ratio,
    get_relative_output_path,
    get_waifu2x_path,
    is_valid_number,
    replace_extension,
)
from waifu2x import upscale_with_waifu2x
from PIL import Image


class UpscaleImagesView(JobView):
    loading_text = "Upscaling images..."
    finished_text = "Upscaling finished!"
    failed_text = "Upscaling failed."

    def __init__(self, parent_gui):
        super().__init__(
            parent_gui, settings_container=SettingsUpscaleImages(parent_gui.page)
        )

    def before_job(self):
        # Without this check, a missing waifu2x binary would make the button silently do nothing.
        if not get_waifu2x_path():
            raise RuntimeError(
                '"waifu2x-ncnn-vulkan" was not found. Download it from https://github.com/nihui/waifu2x-ncnn-vulkan/releases and add its folder to your PATH (see the README).'
            )

    def process_image_folder(self, image_folder, images, input_directory, output_directory):
        series_and_chapter_name_directory = get_relative_output_path(
            image_folder, input_directory
        )
        upscale_ratio = self.parent_gui.page.client_storage.get("upscale_ratio")
        noise_level = self.parent_gui.page.client_storage.get("noise_level")
        image_format = self.parent_gui.page.client_storage.get("image_format")

        use_custom_panel_image_height = self.parent_gui.page.client_storage.get(
            "use_custom_panel_image_height"
        )
        custom_panel_image_height = self.parent_gui.page.client_storage.get(
            "custom_panel_image_height"
        )

        # Only resize if the checkbox is checked AND a valid height was actually entered.
        use_custom_panel_image_height = bool(
            use_custom_panel_image_height
            and is_valid_number(custom_panel_image_height)
            and float(custom_panel_image_height) >= 1
        )

        if use_custom_panel_image_height:
            custom_panel_image_height = int(float(custom_panel_image_height))

        max_image_width = self.parent_gui.page.client_storage.get("max_image_width")
        use_max_image_width = bool(
            self.parent_gui.page.client_storage.get("use_max_image_width")
            and is_valid_number(max_image_width)
            and float(max_image_width) >= 1
        )

        if use_max_image_width:
            max_image_width = int(float(max_image_width))

        limit_upscale_to_4k = self.parent_gui.page.client_storage.get(
            "limit_upscale_to_4k"
        )

        process_manager = ProcessManager()

        for image_info in images:
            file_name = image_info["name"]

            input_image = f"{image_folder}/{file_name}"

            file_name_with_new_extension = replace_extension(file_name, image_format)

            full_image_output_directory = (
                f"{output_directory}/{series_and_chapter_name_directory}"
            )
            os.makedirs(full_image_output_directory, exist_ok=True)
            output_image = f"{full_image_output_directory}/{file_name_with_new_extension}"

            # waifu2x exits with code 0 even when it fails, so "did the output image get created?" is the real check below. Remove any output image left over from a previous run so it can't be mistaken for a new one.
            if os.path.exists(output_image):
                os.remove(output_image)

            image_upscale_ratio = upscale_ratio
            if limit_upscale_to_4k:
                with Image.open(input_image) as image:
                    image_upscale_ratio = get_capped_upscale_ratio(
                        image.width, image.height, upscale_ratio
                    )
                if image_upscale_ratio == 1:
                    print(f"{file_name} is already 4K or bigger, so it's not upscaled.")
                elif image_upscale_ratio != int(upscale_ratio):
                    print(
                        f"Upscaling {file_name} {image_upscale_ratio}x instead of {upscale_ratio}x so it doesn't go past 4K."
                    )

            upscale_with_waifu2x(
                input_image=input_image,
                output_image=output_image,
                upscale_ratio=image_upscale_ratio,
                noise_level=noise_level,
                image_format=(f"ext/{image_format}"),
                terminal_output_list_view=self.parent_gui.terminal_output.terminal_output_list_view,
                process_manager=process_manager,
            )

            # If waifu2x failed on this image, there's no output image to resize so move on to the next one.
            if process_manager.process.returncode != 0 or not os.path.exists(
                output_image
            ):
                self.parent_gui.terminal_output.update_terminal_with_error_message(
                    f"Waifu2X: Failed to upscale {input_image}. Skipping it."
                )
                continue

            # The capped ratio can still go a bit past 4K (e.g. 1000px x 4 = 4000px), so shrink it to exactly 4K. Images that were already bigger than 4K keep their original size.
            if limit_upscale_to_4k and image_upscale_ratio > 1:
                pil_image = Image.open(output_image)
                if max(pil_image.size) > MAX_UPSCALED_IMAGE_SIDE:
                    pil_image.thumbnail(
                        (MAX_UPSCALED_IMAGE_SIDE, MAX_UPSCALED_IMAGE_SIDE), Image.LANCZOS
                    )
                    pil_image.save(output_image)

            # Resize to custom height if specified
            if use_custom_panel_image_height:
                pil_image = Image.open(output_image)
                # Calculate the new width to maintain aspect ratio
                original_width, original_height = pil_image.size
                aspect_ratio = original_width / original_height
                new_width = int(custom_panel_image_height * aspect_ratio)

                # Resize the image
                pil_image = pil_image.resize(
                    (new_width, custom_panel_image_height), Image.LANCZOS
                )

                pil_image.save(output_image)

            # Shrink the image if it's wider than the max width (keeps the aspect ratio).
            if use_max_image_width:
                pil_image = Image.open(output_image)
                original_width, original_height = pil_image.size

                if original_width > max_image_width:
                    new_height = int(original_height * max_image_width / original_width)
                    pil_image = pil_image.resize(
                        (max_image_width, new_height), Image.LANCZOS
                    )
                    pil_image.save(output_image)

        print(
            f"Waifu2X: Finished upscaling all images to {output_directory}/{series_and_chapter_name_directory}"
        )
        print(
            f"PIL: Finished resizing images in {output_directory}/{series_and_chapter_name_directory}"
        )
