import subprocess
import os
import sys
import select
from rename_folders_to_chapter_format import rename_folders_to_chapter_format
from utils import (
    add_line_to_terminal_output_list_view,
    select_folder,
    is_tool_installed,
    pip_install_or_uninstall_tool,
    open_directory,
)
import flet as ft


def download_from_mangadex(
    mangadex_url_to_download_from: str = "",
    output_directory: str = "",
    terminal_output_list_view: ft.ListView = None,
) -> None:
    """
    @description Use the third-party "mangadex_downloader" command line tool to download manga from the given URL. URL must be a valid MangaDex URL.
    @IMPORTANT "mangadex_downloader" MUST be installed on your system to use this.
    """

    # TODO: I've added some default commands here that I personally like however, later on as I develop the GUI, I should make this more flexible and dynamic so that it corresponds to the options from the GUI.
    terminal_command = [
        sys.executable,
        "-m",
        "mangadex_downloader",
        mangadex_url_to_download_from,
        "-d",
        output_directory,
        "--use-chapter-title",
        "--no-group-name",
    ]

    # Make a shallow copy of the OS environment variables.
    env = os.environ.copy()

    # Ensures that the subprocess writes output immediately to stdout/stderr without buffering so we data can be processed line-by-line in real-time programatically.
    # We need to take of the two running process with BOTH "PYTHONUNBUFFERED" (parent process - the running "download_from_mangadex.py" file) and bufsize=1 (subprocess) below.
    env["PYTHONUNBUFFERED"] = "1"

    # Open a child "process" (it's a child because it's opened within the parent process, the process that executes the "download_from_mangadex.py" file)
    with subprocess.Popen(
        terminal_command,
        stdout=subprocess.PIPE,  # Redirected to a PIPE so that the parent process (this python file) can manipulate the output and error lines in the code below instead of in the terminal.
        stderr=subprocess.PIPE,
        text=True,  # Return the output and errors as strings (text mode) instead of in binary data (bytes). If this was not done, then I would have to decode the binary data myself below.
        bufsize=1,  # Ensures that Python itself reads the output line-by-line from the pipe rather than waiting for the entire buffer to fill up. Only works in text mode (text = True)
        env=env,  # Use the modified "env" variable so that it takes "PYTHONUNBUFFERED" which will give us access to each line output immediately instead of after the program is done executing.
    ) as process:
        try:
            # Use `select` to monitor stdout and stderr
            while True:
                stdout_stream_id = process.stdout.fileno()
                stderr_stream_id = process.stderr.fileno()

                reads = [stdout_stream_id, stderr_stream_id]

                # "select.select()" basically subscribes to the "reads" array and the operating system will let select know when any new data is available on one of the monitored file descriptors. While this
                # In this case, we are only interested in monitoring the rlist (read-list). The wlist and xlist are not needed, so they are empty.
                ready_to_read_stream_ids = select.select(reads, [], [])

                for stream_id in ready_to_read_stream_ids[0]:
                    if stream_id == stdout_stream_id:
                        line = process.stdout.readline()

                        if line:
                            # end="" - Removes the new line at the end of the print statement.
                            # flush=True - Ensures immediate output to the terminal.
                            print(line, end="", flush=True)

                            add_line_to_terminal_output_list_view(
                                terminal_output_list_view, line.strip()
                            )
                    elif stream_id == stderr_stream_id:
                        line = process.stderr.readline()

                        if line:
                            print(line, end="", flush=True)
                            add_line_to_terminal_output_list_view(
                                terminal_output_list_view, line.strip()
                            )

                subprocess_has_finished = process.poll() is not None

                if subprocess_has_finished:
                    break  # Exit loop when process finishes
        except Exception as e:
            exception_str = f"An error occurred: {e}"

            print(exception_str)
            add_line_to_terminal_output_list_view(
                terminal_output_list_view, exception_str
            )
        finally:
            if process.returncode == 0:
                print("Command executed successfully!")
                add_line_to_terminal_output_list_view(
                    terminal_output_list_view, "Command executed successfully!"
                )

                # Open the directory that contains the downloads.
                open_directory(output_directory)

            else:
                print(f"Command failed with return code {process.returncode}")
                add_line_to_terminal_output_list_view(
                    terminal_output_list_view,
                    f"Command failed with return code {process.returncode}",
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
