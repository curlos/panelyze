import tkinter as tk
from tkinter import filedialog
import subprocess
import sys
import os
import platform
import flet as ft


def select_folder():
    """
    Create a "tk" window that will allow the user to select a folder and return the folder's path.
    The "tk" window shows up on the top-left and above all other windows.
    """

    root = tk.Tk()
    root.attributes("-topmost", True)

    root.lift()
    root.focus_force()

    folder_path = filedialog.askdirectory(title="Select a Folder", parent=root)

    if folder_path:
        print(f"Selected folder: {folder_path}")
    else:
        print("No folder selected.")

    # Clean Up
    root.destroy()

    return folder_path


def pip_install_or_uninstall_tool(module_name: str, action: str):
    """
    Install or uninstall a Python module using pip.

    Args:
        module_name (str): The name of the module to manage.
        action (str): The action to perform ('install' or 'uninstall').

    Raises:
        ValueError: If an invalid action is provided.
    """
    if action not in {"install", "uninstall"}:
        raise ValueError("Invalid action. Use 'install' or 'uninstall'.")

    try:
        # Construct the pip command in a single list
        pip_command = [
            sys.executable,  # The python executable (like the venv/bin/python folder)
            "-m",
            "pip",
            action,
            (
                "-y" if action == "uninstall" else ""
            ),  # Automatically say "Yes" to any uninstall prompts instead of having to wait for manual user input.
            module_name.replace("_", "-"),
        ]

        # Remove any empty strings from the command list
        pip_command = [cmd for cmd in pip_command if cmd]

        print(f"Attempting to {action} '{module_name}'...")

        result = subprocess.run(
            pip_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode == 0:
            print(f"'{module_name}' {action}ed successfully!")
        else:
            print(f"Failed to {action} '{module_name}'. Please try manually.")
            print(result.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"An error occurred while trying to {action} '{module_name}': {e}")
        sys.exit(1)


def is_tool_installed(module_name: str) -> bool:
    """
    Check if a Python module is executable using `python3 -m`.

    Args:
        module_name (str): The name of the module to check.

    Returns:
        bool: True if the module can be executed, False otherwise.
    """
    try:
        # Test invoking the module with `python3 -m module_name --help`
        result = subprocess.run(
            [sys.executable, "-m", module_name, "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Check if the error message indicates the module is not installed
        if "No module named" in result.stderr:
            return False

        # Return True if no errors related to missing modules are found
        return result.returncode == 0
    except FileNotFoundError:
        return False  # Python executable or module not found
    except Exception as e:
        print(f"An unexpected error occurred while checking {module_name}: {e}")
        return False


def convert_size(size_in_bytes, unit="KB"):
    """
    Convert a size in bytes to the specified unit.

    Args:
        size_in_bytes (int): The size in bytes.
        unit (str): The desired unit for conversion ("B", "KB", "MB", "GB").

    Returns:
        float: The size converted to the specified unit, rounded to 2 decimal places.
    """

    unit = unit.upper()
    if unit == "B":
        return size_in_bytes
    elif unit == "KB":
        return round(size_in_bytes / 1024, 2)
    elif unit == "MB":
        return round(size_in_bytes / (1024**2), 2)
    elif unit == "GB":
        return round(size_in_bytes / (1024**3), 3)
    else:
        raise ValueError(f"Invalid unit '{unit}'. Use 'B', 'KB', 'MB', or 'GB'.")


def get_dir_total_image_size(
    directory: str = "./outputs/One Piece (Official Colored)/0427_Chapter.427",
    unit: str = "KB",
) -> int:
    """
    Calculate the total size of image files in a directory and return it in the specified unit.

    Args:
        directory (str): The path to the directory to analyze.
        unit (str): The desired unit for the total size ("B", "KB", "MB", "GB").

    Returns:
        int: The total size of the images files in the specified unit.
    """

    total_size = 0

    if not os.path.exists(directory):
        print("Directory does not exist.")
        return total_size

    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)

        file_is_an_image = file_name.lower().endswith(
            (".png", ".jpg", ".jpeg", ".gif", ".bmp")
        )

        if file_is_an_image:
            total_size += os.path.getsize(file_path)

    total_size_in_unit = convert_size(total_size, unit)

    print(f"{total_size_in_unit} {unit}")

    return total_size_in_unit


def get_last_two_directories(path):
    """
    Extracts and returns the last two directories from a given path string.

    Args:
        path (str): The directory path string.

    Returns:
        str: A string containing the last two directories.
    """
    # Normalize the path to handle different OS path separators
    normalized_path = os.path.normpath(path)

    # Split the path into components
    path_parts = normalized_path.split(os.sep)

    # Extract the last two directories
    last_two = path_parts[-2:]

    # Join them back into a string
    return os.path.join(*last_two)


def open_directory(path):
    if platform.system() == "Darwin":  # macOS
        subprocess.run(["open", path])
    elif platform.system() == "Windows":  # Windows
        os.startfile(path)
    elif platform.system() == "Linux":  # Linux
        subprocess.run(["xdg-open", path])
    else:
        raise OSError(f"Unsupported operating system: {platform.system()}")


def add_line_to_terminal_output_list_view(
    terminal_output_list_view, text, color="white"
):
    if terminal_output_list_view:
        # Add the line to the Flet ListView
        terminal_output_list_view.controls.append(ft.Text(text, color=color))
        terminal_output_list_view.update()  # Update the Flet UI
