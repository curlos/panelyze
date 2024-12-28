import tkinter as tk
from tkinter import filedialog


def select_folder():
    # Create a root window
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    root.attributes(
        "-topmost", True
    )  # Ensure the dialog is on top of all other windows

    # Force focus to the root window to ensure the dialog appears in front
    root.deiconify()
    root.lift()
    root.focus_force()

    # Open the folder selection dialog
    folder_path = filedialog.askdirectory(title="Select a Folder", parent=root)

    # Check if a folder was selected
    if folder_path:
        print(f"Selected folder: {folder_path}")
    else:
        print("No folder selected.")

    # Clean up the root window
    root.destroy()

    return folder_path
