import os
import shutil
from utils import select_folder


def copy_panels_to_one_level_directory(
    input_directory: str, output_directory: str
) -> None:
    """
    After analyzing manga pages with the MagiV2 AI Model and putting in the individual panels in "page_x" folders for a chapter, this function will help us grab the individual "panel_x" files from those folders and place them in a one-level directory where they will all exist for the manga chapter.
    """

    output_directory_exists = os.path.exists(output_directory)

    # If the output directory does not exist, then make the directory first.
    if not output_directory_exists:
        os.makedirs(output_directory)

    panel_counter = 1
    page_x_directories = [
        directory
        for directory in os.listdir(input_directory)
        if directory.startswith("page_")
    ]

    # Get all page_x directories sorted numerically
    sorted_page_x_directories = sorted(
        page_x_directories,
        key=extract_page_num,  # Sort by the numerical part of "page_x"
    )

    # Go through each page directory in order
    for page_dir in sorted_page_x_directories:
        page_path = os.path.join(input_directory, page_dir)
        page_dir_exists = os.path.isdir(page_path)
        panel_image_files = [f for f in os.listdir(page_path) if f.startswith("panel_")]

        if page_dir_exists:
            # Get all panel_x files sorted numerically
            sorted_panel_image_files = sorted(panel_image_files, key=extract_panel_num)

            for panel_file in sorted_panel_image_files:
                # Construct full file path
                input_file_path = os.path.join(page_path, panel_file)

                # Construct new file name and path
                output_file_name = f"panel_{panel_counter}.png"

                # TODO: "output_directory" should contain the Manga Series name and the Chapter name before it. For example, "One Piece (Official Colored)/0427_Chapter.427/panel_3.png" instead of the current "output_directory" which is just "panel_3.png". This needs to be done so that everything is grouped in order.
                output_file_path = os.path.join(output_directory, output_file_name)

                # Copy file to the new directory with the new name
                shutil.copy(input_file_path, output_file_path)
                print(f"Copied: {input_file_path} to {output_file_path}")

                # Increment panel counter
                panel_counter += 1


def extract_page_num(page_str: str) -> int:
    """
    Extract the numerical part from a string in the format 'page_x'. For example, 'page_2' will return '2'.
    """
    page_num = int(page_str.split("_")[1])
    return page_num


def extract_panel_num(panel_str: str) -> int:
    """
    Extract the numerical part from a string in the format 'panel_x.[extension]'. For example, 'panel_2.png' will return '2'.
    """
    panel_num = panel_str.split("_")[1].split(".")[0]
    return panel_num


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    print("Select a directory to group panels from:")
    input_directory = select_folder()

    print("Select a directory save the grouped panels to:")
    output_directory = select_folder()

    copy_panels_to_one_level_directory(input_directory, output_directory)
