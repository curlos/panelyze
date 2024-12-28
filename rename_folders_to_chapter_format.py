import os
import re
from utils import select_folder


def rename_folders_to_chapter_format(directory):
    """
    Goes through a directory of manga chapter folders and renames the folder names to in the format "xxxx_Chapter.xxx" so that the chapter folders are in sorted order by default.
    """
    folder_name_list = os.listdir(directory)

    for folder_name in folder_name_list:
        folder_path = os.path.join(directory, folder_name)
        folder_exists = os.path.isdir(folder_path)

        if folder_exists:
            # Extract "Ch. xxx" using regex
            match = re.search(r"\bCh\. (\d+)\b", folder_name, re.IGNORECASE)

            # If we find the Chapter Number, then rename the folder in the format of "xxxx_Chapter.xxx" using the chapter number.
            if match:
                chapter_number = int(match.group(1))
                new_folder_name = f"{chapter_number:04d}_Chapter.{chapter_number}"
                new_folder_path = os.path.join(directory, new_folder_name)
                os.rename(folder_path, new_folder_path)
                print(f'Renamed: "{folder_name}" -> "{new_folder_name}"')
            else:
                print(f'Skipped: "{folder_name}" (no chapter found)')


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    print(
        "\nSelect a directory with chapter folders to rename in the format of 'xxxx_Chapter.xxx': "
    )
    chapter_folder_list_directory = select_folder()
    rename_folders_to_chapter_format(chapter_folder_list_directory)
