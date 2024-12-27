import subprocess
import os
import sys
import select
from rename_folders_to_chapter_format import rename_folders_to_chapter_format
from group_panels import select_folder

def download_from_mangadex(url_to_download_from = 'https://mangadex.org/chapter/03c8f635-f361-45fe-84c6-f6c1da7ba3ff', output_directory = ''):
    # Running the command
    command = ["python3", "-m", "mangadex_downloader", url_to_download_from, "-d", output_directory, "--use-chapter-title", "--no-group-name"]

    # Ensure output is not buffered
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=env) as process:
        try:
            # Use `select` to monitor stdout and stderr
            while True:
                reads = [process.stdout.fileno(), process.stderr.fileno()]
                ret = select.select(reads, [], [])
                for fd in ret[0]:
                    if fd == process.stdout.fileno():
                        line = process.stdout.readline()
                        if line:
                            sys.stdout.write(line)
                            sys.stdout.flush()
                    elif fd == process.stderr.fileno():
                        line = process.stderr.readline()
                        if line:
                            sys.stderr.write(line)
                            sys.stderr.flush()
                
                if process.poll() is not None:
                    break  # Exit loop when process finishes
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if process.returncode == 0:
                print("Command executed successfully!")
            else:
                print(f"Command failed with return code {process.returncode}")

def start():
    manga_dex_url = input('\nEnter a Manga Dex URL: ')
    
    print('\nSelect an output directory: ')
    output_directory = select_folder()
    download_from_mangadex(manga_dex_url, output_directory)
    # rename_folders_to_chapter_format("One Piece (Official Colored)")

start()