import sys
from rename_folders_to_chapter_format import rename_folders_to_chapter_format
from utils import (
    select_folder,
    is_tool_installed,
    pip_install_or_uninstall_tool,
    ProcessManager,
)
import flet as ft
import pdb

all_options_with_terminal_command = {
    "use_chapter_title": "--use-chapter-title",
    "no_group_name": "--no-group-name",
    "language": ["--language", "en"],
    "start_page": 1,
    "end_page": 9999,  # Random max value just to show what the values could look like.
    "start_chapter": 1,
    "end_chapter": 9999,
}


def get_additional_terminal_options(flet_page_client_storage):
    if not flet_page_client_storage:
        return ["--use-chapter-title", "--no-group-name", ""]

    additional_terminal_options = []

    use_start_and_end_pages = flet_page_client_storage.get("use_start_and_end_pages")
    use_start_and_end_chapters = flet_page_client_storage.get(
        "use_start_and_end_chapters"
    )

    for key, terminal_command in all_options_with_terminal_command.items():
        storage_value = flet_page_client_storage.get(key)

        print(f"{key}: {storage_value}")

        # pdb.set_trace()

        if key == "language":
            additional_terminal_options.extend(["--language", storage_value["code"]])
        elif key == "start_page" and storage_value:
            if use_start_and_end_pages:
                additional_terminal_options.extend(["--start-page", storage_value])
        elif key == "end_page" and storage_value:
            if use_start_and_end_pages:
                additional_terminal_options.extend(["--end-page", storage_value])
        elif key == "start_chapter" and storage_value:
            if use_start_and_end_chapters:
                additional_terminal_options.extend(["--start-chapter", storage_value])
        elif key == "end_chapter" and storage_value:
            if use_start_and_end_chapters:
                additional_terminal_options.extend(["--end-chapter", storage_value])
        elif storage_value:
            additional_terminal_options.append(terminal_command)

    print(additional_terminal_options)

    return additional_terminal_options


def download_from_mangadex(
    mangadex_url_to_download_from: str = "",
    output_directory: str = "",
    terminal_output_list_view: ft.ListView = None,
    flet_page_client_storage=None,
    cancel_process_button=None,
) -> None:
    """
    @description Use the third-party "mangadex_downloader" command line tool to download manga from the given URL. URL must be a valid MangaDex URL.
    @IMPORTANT "mangadex_downloader" MUST be installed on your system to use this.
    """

    additional_terminal_options = get_additional_terminal_options(
        flet_page_client_storage
    )

    terminal_command = [
        sys.executable,
        "-m",
        "mangadex_downloader",
        mangadex_url_to_download_from,
        "-d",
        output_directory,
    ]

    terminal_command.extend(additional_terminal_options)

    process_manager = ProcessManager()

    if cancel_process_button:
        cancel_process_button.on_click = lambda _: process_manager.cancel_process()

    process_manager.monitor_terminal_output(
        terminal_command, terminal_output_list_view, output_directory
    )


is_running_as_main_program = __name__ == "__main__"

if is_running_as_main_program:
    mangadex_downloader_module_name = "mangadex_downloader"

    if not is_tool_installed(mangadex_downloader_module_name):
        print(f"Error: {mangadex_downloader_module_name} is not installed.")
        pip_install_or_uninstall_tool(mangadex_downloader_module_name, "install")

    mangadex_url_to_download_from = input("\nEnter a Manga Dex URL: ")

    print("\nSelect an output directory: ")
    output_directory = select_folder()

    download_from_mangadex(mangadex_url_to_download_from, output_directory)
