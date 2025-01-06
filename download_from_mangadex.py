import sys
from rename_folders_to_chapter_format import rename_folders_to_chapter_format
from utils import (
    select_folder,
    is_tool_installed,
    pip_install_or_uninstall_tool,
    monitor_terminal_output,
)
import flet as ft

all_options_with_terminal_command = {
    "use_chapter_title": "--use-chapter-title",
    "no_group_name": "--no-group-name",
}


def get_additional_terminal_options(flet_page_client_storage):
    if not flet_page_client_storage:
        return [
            "--use-chapter-title",
            "--no-group-name",
        ]

    additional_terminal_options = []

    for key, terminal_command in all_options_with_terminal_command.items():
        is_checked = flet_page_client_storage.get(key)

        print(f"{key}: {is_checked}")

        if is_checked:
            additional_terminal_options.append(terminal_command)

    print(additional_terminal_options)

    return additional_terminal_options


def download_from_mangadex(
    mangadex_url_to_download_from: str = "",
    output_directory: str = "",
    terminal_output_list_view: ft.ListView = None,
    flet_page_client_storage=None,
) -> None:
    """
    @description Use the third-party "mangadex_downloader" command line tool to download manga from the given URL. URL must be a valid MangaDex URL.
    @IMPORTANT "mangadex_downloader" MUST be installed on your system to use this.
    """

    additional_terminal_options = get_additional_terminal_options(
        flet_page_client_storage
    )

    # TODO: I've added some default commands here that I personally like however, later on as I develop the GUI, I should make this more flexible and dynamic so that it corresponds to the options from the GUI.
    terminal_command = [
        sys.executable,
        "-m",
        "mangadex_downloader",
        mangadex_url_to_download_from,
        "-d",
        output_directory,
    ]

    terminal_command.extend(additional_terminal_options)
    monitor_terminal_output(
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
