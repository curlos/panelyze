import os
import re

def rename_folders_to_chapter_format(directory):
    for folder_name in os.listdir(directory):
        folder_path = os.path.join(directory, folder_name)
        if os.path.isdir(folder_path):
            # Extract "Ch. xxx" using regex
            match = re.search(r"Ch\. (\d+)", folder_name, re.IGNORECASE)
            if match:
                chapter_number = int(match.group(1))
                new_folder_name = f"{chapter_number:04d}_Chapter.{chapter_number}"
                new_folder_path = os.path.join(directory, new_folder_name)
                os.rename(folder_path, new_folder_path)
                print(f'Renamed: "{folder_name}" -> "{new_folder_name}"')
            else:
                print(f'Skipped: "{folder_name}" (no chapter found)')

# rename_folders_to_chapter_format("Dragon Ball (Official Colored)")