import os
import subprocess
from utils import get_waifu2x_path


def upscale_with_waifu2x(
    input_image,
    output_image,
    upscale_ratio=4,
    noise_level=1,
    image_format="ext/png",
    terminal_output_list_view=None,
    process_manager=None,
):

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
        os.path.join(os.path.dirname(waifu2x_path), "models-cunet"),
    ]

    if process_manager and terminal_output_list_view:
        process_manager.monitor_terminal_output(
            terminal_command, terminal_output_list_view
        )
    else:
        subprocess.run(terminal_command, check=True)
    print(f"Upscaled image saved to: {output_image}")
