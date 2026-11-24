import os
import sys
import threading
import time

import flet as ft
from gui_classes import Nord

# The "ProgressPanel" that's currently shown, if any. Jobs report to it with "report_progress", so the code that does the work doesn't need to know about the GUI.
current_progress_panel = None

PROGRESS_FIELDS = (
    "prefix",
    "chapter",
    "chapters",
    "group_label",
    "pages_done",
    "pages_total",
    "unit",
    "detail",
    # A job made of stages (Images To Video: reading the text, the voice-over, writing the video): their names, and the one it's on (see "get_stages_text").
    "stages",
    "stage",
    # Where the AI model of the job runs ("AMD Radeon RX 6700 XT", "Apple M1", "CPU"; see "magi.get_device_name").
    "device",
    # When a Pipeline started (time.monotonic()), so its total time can be shown next to each step's. It's not cleared between steps.
    "total_started_at",
)

IDLE_TEXT = "Ready. Pick your input, then press the button."
ERROR_TITLE = "Something went wrong"
ERROR_HINT = "Full details are in Raw Output."
MUTED_COLOR = Nord.TEXT_MUTED

# What the panel is showing. "idle" is before anything runs, then "running", and then "finished", "failed" or "cancelled" (the user stopped it).
IDLE, RUNNING, FINISHED, FAILED, CANCELLED = "idle", "running", "finished", "failed", "cancelled"


def get_singular(unit):
    # "1 of 1 text box", not "text boxe".
    return unit[: -len("es")] if unit.endswith("xes") else unit.rstrip("s")


def format_duration(seconds):
    """
    How long something took, from the largest unit that's needed down to seconds: "42s", "3m5s", "1h2m3s", "1d2h3m4s".
    """
    seconds = int(seconds)
    parts = []
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        amount, seconds = divmod(seconds, size)
        if amount or parts:
            parts.append(f"{amount}{unit}")
    parts.append(f"{seconds}s")
    return "".join(parts)


# Sizes are shown the way the computer's own file manager shows them. Windows' File Explorer counts 1 KB as 1024 bytes and has its own rounding, so on Windows they're written by Windows itself (see "format_size_like_file_explorer").
USE_FILE_EXPLORER_SIZES = sys.platform == "win32"


def format_size_like_file_explorer(size):
    """
    A number of bytes exactly as File Explorer shows it ("67.1 MB", "5.17 KB", "512 bytes"), written by the Windows function it uses. Windows only.
    """
    import ctypes

    text = ctypes.create_unicode_buffer(64)
    ctypes.windll.shlwapi.StrFormatByteSizeW(ctypes.c_longlong(int(size)), text, len(text))
    return text.value


def format_size(size):
    """
    A number of bytes the way the file manager shows it: on the Mac like Finder (1 KB = 1000 bytes), "512 B", "5.3 KB", "412 MB", "1.2 GB"; on Windows like File Explorer.
    """
    if USE_FILE_EXPLORER_SIZES:
        return format_size_like_file_explorer(size)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1000:
            break
        size /= 1000
    else:
        unit = "TB"
    if unit == "B" or size >= 100:
        return f"{size:.0f} {unit}"
    return f"{size:.1f} {unit}"


# The kinds of files the size is split into, in the order they're shown ("85 MB (40 MB video + 38 MB audio + 7 MB other)"), by their file extensions.
SIZE_KINDS = {
    "images": (".png", ".jpg", ".jpeg", ".webp", ".gif"),
    ".cbz files": (".cbz",),
    "video": (".mp4", ".mov", ".webm", ".mkv", ".avi"),
    "audio": (".mp3", ".wav", ".m4a", ".aac"),
}


def get_size_kind(file_name):
    extension = os.path.splitext(file_name)[1].lower()
    return next((kind for kind, extensions in SIZE_KINDS.items() if extension in extensions), "other")


def get_folder_size(folder):
    """
    The size of everything in "folder", and how much of it is each kind of file (see "SIZE_KINDS", plus "other"), as (total, {kind: size}).
    """
    total = 0
    size_by_kind = {}
    for directory, _, file_names in os.walk(folder):
        for file_name in file_names:
            try:
                size = os.path.getsize(os.path.join(directory, file_name))
            except OSError:
                # E.g. a temporary file that was just deleted.
                continue
            total += size
            kind = get_size_kind(file_name)
            size_by_kind[kind] = size_by_kind.get(kind, 0) + size
    return total, size_by_kind


def report_output_folder(folder):
    """
    The folder the running job saves into, so the Status view can show how much it has saved so far (see "ProgressPanel.measure_output").
    """
    if current_progress_panel:
        current_progress_panel.watch_output_folder(folder)


def report_cancelling(message):
    """
    Shown as soon as Cancel is clicked (e.g. "Cancelling after the image being upscaled..."), until the job really stops. Also printed, so it's in the Raw Output and the log.
    """
    print(message)
    if current_progress_panel:
        current_progress_panel.show_cancelling(message)


def report_progress(**fields):
    """
    Update the progress panel. Pass only the fields that changed: "chapter" and "chapters" (e.g. 2 of 5, called "Chapter" unless "group_label" says otherwise), "pages_done" and "pages_total" (called "pages" unless "unit" says otherwise, e.g. "images"), "detail" (any extra text) and "prefix" (e.g. "Step 2 of 4" in the Pipeline). Passing "None" clears a field.
    """
    if current_progress_panel:
        current_progress_panel.update_progress(**fields)


class ProgressPanel(ft.Container):
    """
    The "Status" view: a friendly view of how far the current job is (an icon and a title, a short status line and a progress bar), and of any error. It's shown in place of the raw terminal output, which has every detail.
    """

    def __init__(self):
        super().__init__()
        global current_progress_panel
        current_progress_panel = self

        self.prefix = ""
        self.total_started_at = None
        # When the job that's running (or ran last) started and ended, for its timer.
        self.started_at = None
        self.ended_at = None
        self.stop_watching_output_folder()
        self.clear_progress()
        self.title = IDLE_TEXT
        self.state = IDLE
        # Whether the failure being shown already has its error message (see "show_error").
        self.error_message_shown = False

        self.status_icon = ft.Icon(size=22)
        self.title_text = ft.Text(size=15, expand=True)
        self.timer_text = ft.Text(color=MUTED_COLOR, size=13)
        self.status_text = ft.Text(color=Nord.TEXT)
        self.stages_text = ft.Text(color=MUTED_COLOR, size=12, visible=False)
        self.device_text = ft.Text(color=MUTED_COLOR, size=12, visible=False)
        self.error_hint_text = ft.Text(ERROR_HINT, color=MUTED_COLOR, size=12, visible=False)
        self.progress_bar = ft.ProgressBar(
            color=Nord.BLUE, bgcolor=Nord.SURFACE_HIGH, visible=False
        )

        self.bgcolor = Nord.SURFACE
        self.padding = ft.padding.only(left=10, right=10, top=10)
        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[self.status_icon, self.title_text, self.timer_text],
                    spacing=10,
                ),
                self.stages_text,
                self.status_text,
                self.device_text,
                self.error_hint_text,
                self.progress_bar,
            ],
            spacing=8,
            # When the terminal is dragged so small that the status doesn't fit, it scrolls (the scroll bar only shows then, like the Settings page's).
            scroll=ft.ScrollMode.ALWAYS,
        )
        self.render()

    def clear_progress(self):
        self.chapter = None
        self.chapters = None
        self.group_label = "Chapter"
        self.pages_done = None
        self.pages_total = None
        self.unit = "pages"
        self.detail = None
        self.stages = ()
        self.stage = None
        self.device = None

    def start(self, title):
        self.clear_progress()
        self.title = title
        self.state = RUNNING
        self.error_message_shown = False
        self.started_at = time.monotonic()
        self.ended_at = None
        self.stop_watching_output_folder()
        self.render()
        threading.Thread(target=self.tick, args=(self.started_at,), daemon=True).start()

    def finish(self, title, success=True, cancelled=False):
        self.title = title
        self.state = CANCELLED if cancelled else (FINISHED if success else FAILED)
        self.detail = None
        self.error_message_shown = False
        if self.started_at is not None and self.ended_at is None:
            self.ended_at = time.monotonic()
            self.measure_output()
            print(self.get_timer_text())
        self.render()

    def stop_watching_output_folder(self):
        self.output_folder = None
        self.output_size_at_start = (0, {})
        self.bytes_saved = None
        # How much of "bytes_saved" is each kind of file (see "get_folder_size").
        self.bytes_saved_by_kind = {}
        self.output_changed = False

    def watch_output_folder(self, folder):
        self.output_folder = folder
        self.output_size_at_start = get_folder_size(folder)
        self.bytes_saved = 0
        self.bytes_saved_by_kind = {}
        self.render()

    def measure_output_if_changed(self):
        """
        Called by the timer every second: measures again only if the job reported progress since the last time (a page, an image, a panel or a voice line done). It runs on the timer's thread, so the job never waits for a big folder to be measured.
        """
        if self.output_changed:
            self.output_changed = False
            self.measure_output()

    def measure_output(self):
        """
        How much the job has saved so far: how much bigger its output folder is than when it started (files it replaced can make that less than what it wrote).
        """
        if not self.output_folder:
            return
        total, size_by_kind = get_folder_size(self.output_folder)
        self.bytes_saved = max(0, total - self.output_size_at_start[0])
        self.bytes_saved_by_kind = {
            kind: max(0, size - self.output_size_at_start[1].get(kind, 0)) for kind, size in size_by_kind.items()
        }

    def show_cancelling(self, message):
        if self.state == RUNNING:
            self.title = message
            self.render()

    def tick(self, started_at):
        """
        Keeps the timer counting every second while the job that started at "started_at" runs.
        """
        while self.state == RUNNING and self.started_at == started_at:
            time.sleep(1)
            # It may have ended during the second, and then "Took ..." must stay.
            if self.state != RUNNING or self.started_at != started_at:
                return
            self.measure_output_if_changed()
            self.timer_text.value = self.get_timer_text()
            try:
                self.timer_text.update()
            except Exception:
                pass

    def get_timer_text(self):
        """
        "3m5s · 412 MB" while running (how long, and how much was saved, see "measure_output"; with the Pipeline's total after it, "3m5s · 412 MB · total 10m2s"), and "Took 3m5s · 412 MB" when it's over. Nothing before anything ran.
        """
        if self.started_at is None:
            return ""

        size = ""
        if self.bytes_saved is not None:
            size = f" · {format_size(self.bytes_saved)}"
            # With more than one kind of file, how much each is: "85 MB (40 MB video + 38 MB audio + 7 MB other)". A kind that's under 1% of it (e.g. a small "download.db") would only clutter it.
            parts = [
                f"{format_size(self.bytes_saved_by_kind[kind])} {kind}"
                for kind in [*SIZE_KINDS, "other"]
                if self.bytes_saved_by_kind.get(kind, 0) >= self.bytes_saved / 100
                and self.bytes_saved_by_kind.get(kind, 0) > 0
            ]
            if len(parts) > 1:
                size += f" ({' + '.join(parts)})"
        if self.ended_at is not None:
            return f"Took {format_duration(self.ended_at - self.started_at)}{size}"

        now = time.monotonic()
        text = format_duration(now - self.started_at) + size
        if self.total_started_at is not None:
            text += f" · total {format_duration(now - self.total_started_at)}"
        return text

    def show_error(self, message):
        """
        Show an error (until the next job starts). A job that just failed already has a title saying what failed (e.g. "Download from comix.to failed."), so the message goes under it. Any other error (e.g. a link that isn't valid, before anything ran) gets a title of its own.
        """
        message = message.removeprefix("ERROR:").strip()

        if self.state == RUNNING:
            # The job stops here, so its timer does too.
            self.ended_at = time.monotonic()
        elif not (self.state == FAILED and not self.error_message_shown):
            # An error of its own (e.g. no input picked), so no timer from an earlier job next to it.
            self.started_at = self.ended_at = None

        if not (self.state == FAILED and not self.error_message_shown):
            self.clear_progress()
            self.title = ERROR_TITLE
            self.state = FAILED

        # What was counted on the way ("1 of 1 image") means nothing once it failed.
        self.chapter = self.chapters = self.pages_done = self.pages_total = None
        self.detail = message
        self.error_message_shown = True
        self.render()

    def update_progress(self, **fields):
        for field_name, value in fields.items():
            if field_name in PROGRESS_FIELDS:
                setattr(self, field_name, value)

        self.output_changed = True
        self.render()

    def get_stages_text(self):
        """
        "✓ Reading the text   ● Making the voice-over   ○ Writing the video": the stages done, the one it's on (its progress is the bar), and the ones still to come. All ✓ when the job finished.
        """
        # A single stage (a video without text) says nothing the title doesn't.
        if len(self.stages) < 2 or self.state not in (RUNNING, FINISHED):
            return ""
        current = list(self.stages).index(self.stage) if self.stage in self.stages else 0
        if self.state == FINISHED:
            current = len(self.stages)
        marks = ["✓" if index < current else "●" if index == current else "○" for index in range(len(self.stages))]
        return "   ".join(f"{mark} {name}" for mark, name in zip(marks, self.stages))

    def get_device_text(self):
        """
        "Running on the AMD Radeon RX 6700 XT" while a job that uses an AI model runs ("Ran on ..." after it). Nothing for the other jobs.
        """
        if not self.device or self.state not in (RUNNING, FINISHED):
            return ""
        return f"{'Running' if self.state == RUNNING else 'Ran'} on the {self.device}"

    def get_status_text(self):
        parts = []

        # A single folder of images isn't worth calling "chapter 1 of 1".
        if self.chapters and self.chapters > 1:
            parts.append(f"{self.group_label} {self.chapter} of {self.chapters}")

        if self.pages_total:
            unit = self.unit if self.pages_total != 1 else get_singular(self.unit)
            parts.append(f"{self.pages_done or 0} of {self.pages_total} {unit}")

        if self.detail:
            parts.append(self.detail)

        return " · ".join(parts)

    def get_bar_value(self):
        """
        How far along it is from 0 to 1, or None when that isn't known (the bar then just keeps moving).
        """
        if self.state == FINISHED:
            return 1

        if not (self.chapters and self.chapter):
            return None

        chapters_done = self.chapter - 1

        if self.pages_total:
            chapters_done += (self.pages_done or 0) / self.pages_total

        return min(chapters_done / self.chapters, 1)

    def render(self):
        self.title_text.value = f"{self.prefix} · {self.title}" if self.prefix else self.title
        self.title_text.color = MUTED_COLOR if self.state == IDLE else Nord.TEXT
        self.status_text.value = self.get_status_text()
        self.stages_text.value = self.get_stages_text()
        self.stages_text.visible = bool(self.stages_text.value)
        device_text = self.get_device_text()
        self.device_text.spans = Nord.get_highlighted_spans(device_text, [self.device], Nord.DEVICE)
        self.device_text.visible = bool(device_text)
        self.timer_text.value = self.get_timer_text()
        self.progress_bar.value = self.get_bar_value()
        self.progress_bar.visible = self.state in (RUNNING, FINISHED)
        self.error_hint_text.visible = self.state == FAILED

        # An icon for the state. While running it doesn't spin: the terminal's title bar already has a spinning ring (the one that's seen when the terminal is closed or shows the Raw Output), and the timer and the bar show it's working.
        self.status_icon.name, self.status_icon.color = {
            IDLE: (ft.Icons.PLAY_CIRCLE_OUTLINE, MUTED_COLOR),
            RUNNING: (ft.Icons.HOURGLASS_TOP, Nord.ACCENT),
            FINISHED: (ft.Icons.CHECK_CIRCLE, Nord.GREEN),
            FAILED: (ft.Icons.ERROR, Nord.RED_TEXT),
            CANCELLED: (ft.Icons.CANCEL_OUTLINED, MUTED_COLOR),
        }.get(self.state, (ft.Icons.PLAY_CIRCLE_OUTLINE, MUTED_COLOR))

        # Never let a GUI problem break the job that's reporting.
        try:
            if self.page:
                self.update()
        except Exception:
            pass
