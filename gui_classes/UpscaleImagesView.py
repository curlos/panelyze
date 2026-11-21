from gui_classes.JobView import JobView
from gui_classes.ProgressPanel import report_progress
import os
import shutil
import tempfile
from gui_classes.SettingsUpscaleImages import SettingsUpscaleImages
from utils import (
    MAX_UPSCALED_IMAGE_SIDE,
    PANEL_TEXT_FILE_NAME,
    READING_DIRECTION_FILE_NAME,
    ProcessManager,
    get_capped_upscale_ratio,
    get_last_directory,
    get_relative_output_path,
    get_waifu2x_path,
    is_valid_number,
    replace_extension,
    save_folder_as_cbz,
)
from waifu2x import get_waifu2x_model, upscale_with_waifu2x
from PIL import Image


class UpscaleImagesView(JobView):
    loading_text = "Upscaling images..."
    finished_text = "Upscaling finished!"
    failed_text = "Upscaling failed."
    next_view_name = "ImagesToVideoView"
    # Any images can be upscaled, not just manga pages.
    group_label = "Folder"

    def __init__(self, parent_gui):
        super().__init__(
            parent_gui,
            settings_container=SettingsUpscaleImages(parent_gui.page),
            output_setting_key="output_directory_upscale_images",
        )

    def get_next_tab_input_directory(self, input_directory, output_directory):
        return os.path.join(output_directory, get_last_directory(input_directory))

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

        full_image_output_directory = os.path.join(
            output_directory, series_and_chapter_name_directory
        )
        os.makedirs(full_image_output_directory, exist_ok=True)

        # How much to upscale each image. The 4K limit can make it less for big images.
        image_upscale_ratios = {}
        for image_info in images:
            file_name = image_info["name"]
            image_upscale_ratio = upscale_ratio
            if limit_upscale_to_4k:
                with Image.open(f"{image_folder}/{file_name}") as image:
                    image_upscale_ratio = get_capped_upscale_ratio(
                        image.width, image.height, upscale_ratio
                    )
                if image_upscale_ratio == 1:
                    print(f"{file_name} is already 4K or bigger, so it's not upscaled.")
                elif image_upscale_ratio != int(upscale_ratio):
                    print(
                        f"Upscaling {file_name} {image_upscale_ratio}x instead of {upscale_ratio}x so it doesn't go past 4K."
                    )
            image_upscale_ratios[file_name] = image_upscale_ratio

            # waifu2x exits with code 0 even when it fails, so "did the output image get created?" is the real check below. Remove any output image left over from a previous run so it can't be mistaken for a new one.
            output_image = os.path.join(
                full_image_output_directory, replace_extension(file_name, image_format)
            )
            if os.path.exists(output_image):
                os.remove(output_image)

        self.upscale_all_images(
            image_folder,
            image_upscale_ratios,
            full_image_output_directory,
            noise_level,
            image_format,
            upscale_model=self.parent_gui.page.client_storage.get("upscale_model") or "fast",
        )

        for image_info in images:
            file_name = image_info["name"]
            input_image = f"{image_folder}/{file_name}"
            output_image = os.path.join(
                full_image_output_directory, replace_extension(file_name, image_format)
            )
            image_upscale_ratio = image_upscale_ratios[file_name]

            # If upscaling failed on this image, there's no output image to resize so move on to the next one.
            if not os.path.exists(output_image):
                self.parent_gui.terminal_output.update_terminal_with_error_message(
                    f"Upscale: Failed to upscale {input_image}. Skipping it."
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

        # The text Panel-By-Panel read for these images, and their reading direction, go along with them, so Images To Video can still use them. An old one from an earlier run is removed so it can't be used for different images.
        for file_name in (PANEL_TEXT_FILE_NAME, READING_DIRECTION_FILE_NAME):
            input_file = os.path.join(image_folder, file_name)
            output_file = os.path.join(output_directory, series_and_chapter_name_directory, file_name)
            if os.path.exists(input_file):
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                shutil.copy(input_file, output_file)
            elif os.path.exists(output_file):
                os.remove(output_file)

        comic_file_size = self.parent_gui.page.client_storage.get("save_as_cbz")
        if comic_file_size:
            save_folder_as_cbz(full_image_output_directory, size=comic_file_size)

        print(
            f"Waifu2X: Finished upscaling all images to {output_directory}/{series_and_chapter_name_directory}"
        )
        print(
            f"PIL: Finished resizing images in {output_directory}/{series_and_chapter_name_directory}"
        )

    def upscale_all_images(
        self,
        image_folder,
        image_upscale_ratios,
        output_folder,
        noise_level,
        image_format,
        upscale_model="fast",
    ):
        """
        Upscale the images with the "Upscale Model" setting: "fast" or "better" (waifu2x), or "best" (MangaJaNai, or IllustrationJaNai for color images, see "janai.py").

        waifu2x runs as few times as possible: one for each upscale ratio (usually just one). That's about 2x faster than one run for each image, because waifu2x only starts up and loads its model once.
        """
        process_manager = ProcessManager()
        images_done = 0

        def count_finished_image(line=" done"):
            nonlocal images_done
            if line.rstrip().endswith(" done"):
                images_done += 1
                report_progress(pages_done=images_done)

        report_progress(pages_done=0, pages_total=len(image_upscale_ratios), unit="images")

        waifu2x_image_upscale_ratios = dict(image_upscale_ratios)
        if upscale_model == "best":
            from janai import upscale_image_with_janai

            for file_name, upscale_ratio in image_upscale_ratios.items():
                # Images that aren't made bigger (already 4K) are only cleaned up, by waifu2x.
                if upscale_ratio == 1:
                    continue

                del waifu2x_image_upscale_ratios[file_name]
                try:
                    upscale_image_with_janai(
                        os.path.join(image_folder, file_name),
                        os.path.join(output_folder, replace_extension(file_name, image_format)),
                        upscale_ratio,
                    )
                except OSError:
                    # E.g. no internet for downloading the model, or a full disk. That would happen for every image, so stop.
                    raise
                except Exception as error:
                    # The image is reported as failed afterwards, and the others still get upscaled.
                    print(f"Couldn't upscale {file_name}: {error}")
                count_finished_image()

        for upscale_ratio in sorted(set(waifu2x_image_upscale_ratios.values())):
            # waifu2x upscales a whole folder, so the images with this ratio go in a temporary folder of their own. Hard links take no time or space (waifu2x skips symlinks).
            group_folder = tempfile.mkdtemp(prefix="panelyze-upscale-", dir=output_folder)
            try:
                for file_name, image_upscale_ratio in waifu2x_image_upscale_ratios.items():
                    if image_upscale_ratio == upscale_ratio:
                        link_or_copy_file(
                            os.path.join(image_folder, file_name),
                            os.path.join(group_folder, file_name),
                        )

                upscale_with_waifu2x(
                    input_image=group_folder,
                    output_image=output_folder,
                    upscale_ratio=upscale_ratio,
                    noise_level=noise_level,
                    image_format=image_format,
                    terminal_output_list_view=self.parent_gui.terminal_output.terminal_output_list_view,
                    process_manager=process_manager,
                    model=get_waifu2x_model(upscale_model, upscale_ratio),
                    on_line=count_finished_image,
                )
            finally:
                shutil.rmtree(group_folder, ignore_errors=True)


def link_or_copy_file(source, destination):
    try:
        os.link(source, destination)
    except OSError:
        # E.g. the images are on a different drive, where hard links aren't possible.
        shutil.copy(source, destination)
