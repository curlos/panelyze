import subprocess


def upscale_with_waifu2x(input_image, output_image, scale=4, noise_level=1):
    command = [
        "waifu2x-ncnn-vulkan",  # Path to the binary
        "-i",
        input_image,
        "-o",
        output_image,
        "-s",
        str(scale),
        "-n",
        str(noise_level),
    ]
    subprocess.run(command, check=True)
    print(f"Upscaled image saved to: {output_image}")
