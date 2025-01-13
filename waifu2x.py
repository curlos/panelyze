import subprocess


def upscale_with_waifu2x(
    input_image,
    output_image,
    upscale_ratio=4,
    noise_level=1,
    image_format="ext/png",
    terminal_output_list_view=None,
    process_manager=None,
):

    terminal_command = [
        "waifu2x-ncnn-vulkan",  # Path to the binary
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
    ]

    if process_manager and terminal_output_list_view:
        process_manager.monitor_terminal_output(
            terminal_command, terminal_output_list_view
        )
    else:
        subprocess.run(terminal_command, check=True)
    print(f"Upscaled image saved to: {output_image}")
