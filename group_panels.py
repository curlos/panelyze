import os
import shutil
from utils import select_folder


def group_panels(input_directory, output_directory):
    # Ensure the output directory exists
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Counter for unique panel filenames
    panel_counter = 1

    # Get all page_x directories sorted numerically
    page_dirs = sorted(
        [d for d in os.listdir(input_directory) if d.startswith("page_")],
        key=lambda x: int(x.split("_")[1]),  # Sort by the numerical part of "page_x"
    )

    # Traverse each page directory in order
    for page_dir in page_dirs:
        page_path = os.path.join(input_directory, page_dir)
        if os.path.isdir(page_path):  # Ensure it's a directory
            # Get all panel_x files sorted numerically
            panel_files = sorted(
                [f for f in os.listdir(page_path) if f.startswith("panel_")],
                key=lambda x: int(
                    x.split("_")[1].split(".")[0]
                ),  # Sort by numerical part of "panel_x"
            )

            for panel_file in panel_files:
                # Construct full file path
                input_file_path = os.path.join(page_path, panel_file)

                # Construct new file name and path
                output_file_name = f"panel_{panel_counter}.png"
                output_file_path = os.path.join(output_directory, output_file_name)

                # Copy file to the new directory with the new name
                shutil.copy(input_file_path, output_file_path)
                print(f"Copied: {input_file_path} to {output_file_path}")

                # Increment panel counter
                panel_counter += 1


def start():
    print("Select a directory to group panels from:")
    input_directory = select_folder()

    print("Select a directory save the grouped panels to:")
    output_directory = select_folder()

    group_panels(input_directory, output_directory)


start()
