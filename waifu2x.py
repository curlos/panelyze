import os
import subprocess
from utils import get_waifu2x_path

# The waifu2x models (in folders next to the program). "fast" is the default: on manga panels it looks nearly the same as "better" and is about 2x faster.
WAIFU2X_MODELS = {
    "fast": "models-upconv_7_anime_style_art_rgb",
    "better": "models-cunet",
}


def get_waifu2x_model(upscale_model, upscale_ratio):
    """
    The waifu2x model for the "Upscale Model" setting ("fast", "better" or "best"). "best" mostly uses MangaJaNai instead (see "janai.py"), and only uses waifu2x for images that aren't made bigger.
    """
    # The fast model can only make images bigger. Images that aren't made bigger (only cleaned up) need cunet.
    if upscale_model == "fast" and int(upscale_ratio) > 1:
        return "fast"

    return "better"


def upscale_with_waifu2x(
    input_image,
    output_image,
    upscale_ratio=4,
    noise_level=1,
    image_format="ext/png",
    terminal_output_list_view=None,
    process_manager=None,
    model="better",
    on_line=None,
):
    """
    Upscale one image, or every image in a folder ("input_image" and "output_image" are then folders). A whole folder in one go is about 2x faster than one image at a time, because waifu2x only starts up and loads its model once.
    """

    # The real file, even if the one on the PATH is a shortcut (symlink), so its models folder is found next to it.
    waifu2x_path = os.path.realpath(get_waifu2x_path())

    terminal_command = [
        waifu2x_path,
        "-i",
        input_image,
        "-o",
        output_image,
        "-s",
        str(upscale_ratio),
        "-n",
        str(noise_level),
        "-f",
        str(image_format),
        # The model that comes with waifu2x, next to the program (so it's found no matter which folder the app runs from).
        "-m",
        os.path.join(os.path.dirname(waifu2x_path), WAIFU2X_MODELS[model]),
        # Prints a "... done" line for each finished image, so the progress can be shown.
        "-v",
    ]

    if process_manager and terminal_output_list_view:
        process_manager.monitor_terminal_output(
            terminal_command, terminal_output_list_view, on_line=on_line
        )
    else:
        subprocess.run(terminal_command, check=True)
    print(f"Upscaled image saved to: {output_image}")
