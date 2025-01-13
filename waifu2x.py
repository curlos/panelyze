import subprocess


def upscale_with_waifu2x(input_image, output_image, upscale_ratio=4, noise_level=1):
    print(f"\nupscale_ratio: {upscale_ratio}")
    print(f"noise_level: {noise_level}\n")

    command = [
        "waifu2x-ncnn-vulkan",  # Path to the binary
        "-i",
        input_image,
        "-o",
        output_image,
        "-s",
        str(upscale_ratio),
        "-n",
        str(noise_level),
    ]
    subprocess.run(command, check=True)
    print(f"Upscaled image saved to: {output_image}")
