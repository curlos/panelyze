import os
import re
import sys
import threading
import time
import flet as ft

LOG_FILE_PATH = os.path.expanduser("~/Library/Logs/Panelyze/panelyze.log")
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024
MAX_LINES_IN_APP = 2000
UPDATE_INTERVAL_SECONDS = 0.2
STREAM_COLORS = {"stdout": "white", "stderr": "#ebcb8b"}

# The "AppOutput" that's currently showing everything printed, if any.
current_app_output = None


class AppOutput:
    """
    Shows everything the app prints (normal output, errors, warnings, progress bars and the output of tools like waifu2x) in the app's "Terminal Output", and also saves it to a log file.

    This is needed because the app usually isn't opened from a terminal (e.g. double-clicking Panelyze.app), so there's nowhere else to see what's happening.
    """

    def __init__(self, terminal_output_list_view, log_file_path=LOG_FILE_PATH):
        self.list_view = terminal_output_list_view
        self.lock = threading.RLock()
        # Text after the last line break, for each stream ("stdout" or "stderr") and thread. It's shown as a live line until the line is finished. Keeping each thread separate stops two threads printing at the same time from mixing their text into one line.
        self.unfinished_text = {}
        # The line that's being redrawn for each stream and thread (e.g. a progress bar that redraws itself with "\r").
        self.live_line = {}
        self.needs_update = False
        # New lines and lines to remove wait here until the next GUI update. Only "update_gui" changes the terminal's list of lines, so it never changes while Flet is reading it to redraw the window.
        self.lines_to_add = []
        self.lines_to_remove = []
        self.log_file = open_log_file(log_file_path)
        # The real terminal, if the app was started from one (so app messages show up there too).
        self.original_stdout = sys.stdout

        # Updating the GUI for every printed piece of text is slow, so the GUI is updated at most every 0.2 seconds instead.
        threading.Thread(target=self.keep_updating_gui, daemon=True).start()

    def write(self, stream_name, text):
        with self.lock:
            key = (stream_name, threading.get_ident())
            unfinished = self.unfinished_text.get(key, "")

            for piece in re.split(r"(\r\n|\n|\r)", text):
                if piece in ("\n", "\r\n"):
                    self.show_line(key, unfinished, finished=True)
                    unfinished = ""
                elif piece == "\r":
                    # "\r" means "go back to the start of the line": the next text replaces this line (that's how progress bars redraw themselves).
                    if unfinished.strip():
                        self.show_line(key, unfinished, finished=False)
                    elif unfinished:
                        # Spaces then "\r" means the line was erased (e.g. a finished progress bar clearing itself).
                        self.remove_live_line(key)
                    unfinished = ""
                else:
                    unfinished += piece

            if unfinished:
                self.unfinished_text[key] = unfinished
            else:
                self.unfinished_text.pop(key, None)

            # Show text that doesn't end in a line break yet (e.g. a progress bar) right away.
            if unfinished.strip():
                self.show_line(key, unfinished, finished=False)

    def show_line(self, key, text, finished):
        stream_name, _ = key
        live_line = self.live_line.get(key)

        if live_line is not None:
            live_line.value = text
        elif text.strip() or finished:
            live_line = self.add_text_control(text, STREAM_COLORS.get(stream_name, "white"))

        if finished:
            self.live_line.pop(key, None)
            self.write_to_log_file(text)
        else:
            self.live_line[key] = live_line

        self.needs_update = True

    def remove_live_line(self, key):
        live_line = self.live_line.pop(key, None)

        if live_line in self.lines_to_add:
            self.lines_to_add.remove(live_line)
        elif live_line is not None:
            self.lines_to_remove.append(live_line)
        self.needs_update = True

    def add_line(self, text, color="white"):
        """
        Add a whole line (e.g. an error message from the app itself) to the app's terminal and the log file.
        """
        with self.lock:
            self.add_text_control(text, color)
            self.write_to_log_file(text)
            self.needs_update = True

        if self.original_stdout:
            try:
                self.original_stdout.write(text + "\n")
                self.original_stdout.flush()
            except Exception:
                pass

    def add_text_control(self, text, color):
        text_control = ft.Text(text, color=color, selectable=True)
        self.lines_to_add.append(text_control)
        return text_control

    def write_to_log_file(self, text):
        if not self.log_file:
            return

        try:
            self.log_file.write(text.rstrip() + "\n")
            self.log_file.flush()
        except Exception:
            pass

    def keep_updating_gui(self):
        while True:
            time.sleep(UPDATE_INTERVAL_SECONDS)
            self.update_gui()

    def update_gui(self):
        with self.lock:
            if not self.needs_update:
                return
            self.needs_update = False

            controls = self.list_view.controls
            for line in self.lines_to_remove:
                if line in controls:
                    controls.remove(line)
            controls.extend(self.lines_to_add)
            self.lines_to_add = []
            self.lines_to_remove = []

            # Keep the app's terminal fast. The log file keeps everything.
            extra_lines = len(controls) - MAX_LINES_IN_APP
            if extra_lines > 0:
                del controls[:extra_lines]

            # Never let a GUI problem break the job that's printing.
            try:
                if self.list_view.page:
                    self.list_view.update()
            except Exception:
                pass


class AppOutputStream:
    """
    Stands in for "sys.stdout" or "sys.stderr". Everything written to it goes to the real terminal (if there is one) and to "AppOutput".
    """

    encoding = "utf-8"
    errors = "replace"

    def __init__(self, app_output, stream_name, original_stream):
        self.app_output = app_output
        self.stream_name = stream_name
        # "None" when the app wasn't started from a terminal (e.g. a packaged app opened from Finder).
        self.original_stream = original_stream

    def write(self, text):
        if self.original_stream:
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except Exception:
                pass

        self.app_output.write(self.stream_name, text)
        return len(text)

    def flush(self):
        if self.original_stream:
            try:
                self.original_stream.flush()
            except Exception:
                pass

    def isatty(self):
        return False


def write_to_log_file_only(text):
    """
    For details (like a full error traceback) that are useful in the log but too noisy for the app's terminal.
    """
    if current_app_output:
        current_app_output.write_to_log_file(text)
    else:
        print(text, file=sys.stderr)


def show_all_output_in_app(terminal_output_list_view, log_file_path=LOG_FILE_PATH):
    """
    From now on, everything printed anywhere in the app (including errors, warnings and progress bars) shows up in the app's terminal and the log file.
    """
    global current_app_output

    current_app_output = AppOutput(terminal_output_list_view, log_file_path)
    sys.stdout = AppOutputStream(current_app_output, "stdout", sys.stdout)
    sys.stderr = AppOutputStream(current_app_output, "stderr", sys.stderr)

    return current_app_output


def open_log_file(log_file_path):
    try:
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        # Start over when the log gets big, so it can't fill up the disk.
        if (
            os.path.exists(log_file_path)
            and os.path.getsize(log_file_path) > MAX_LOG_FILE_SIZE
        ):
            os.remove(log_file_path)

        log_file = open(log_file_path, "a", encoding="utf-8")
        log_file.write(f"\n===== Panelyze started {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
        log_file.flush()
        return log_file
    except Exception:
        # Not being able to write a log must never stop the app from opening.
        return None
