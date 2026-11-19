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
)

IDLE_TEXT = "Ready. Pick your folders and press Submit."
MUTED_COLOR = Nord.TEXT_MUTED

# What the panel is showing. "idle" is before anything runs, then "running", and then "finished" or "failed".
IDLE, RUNNING, FINISHED, FAILED = "idle", "running", "finished", "failed"


def report_progress(**fields):
    """
    Update the progress panel. Pass only the fields that changed: "chapter" and "chapters" (e.g. 2 of 5, called "Chapter" unless "group_label" says otherwise), "pages_done" and "pages_total" (called "pages" unless "unit" says otherwise, e.g. "images"), "detail" (any extra text) and "prefix" (e.g. "Step 2 of 4" in the Pipeline). Passing "None" clears a field.
    """
    if current_progress_panel:
        current_progress_panel.update_progress(**fields)


class ProgressPanel(ft.Container):
    """
    A friendly view of how far the current job is: an icon and a title, a short status line and a progress bar. It's shown next to the raw terminal output.
    """

    def __init__(self):
        super().__init__()
        global current_progress_panel
        current_progress_panel = self

        self.prefix = ""
        self.clear_progress()
        self.title = IDLE_TEXT
        self.state = IDLE

        self.status_icon = ft.Icon(size=22)
        self.running_ring = ft.ProgressRing(width=20, height=20, stroke_width=2.5)
        self.title_text = ft.Text(size=15)
        self.status_text = ft.Text(color=Nord.TEXT)
        self.progress_bar = ft.ProgressBar(
            color=Nord.BLUE, bgcolor=Nord.SURFACE_HIGH, visible=False
        )

        self.bgcolor = Nord.SURFACE
        self.padding = ft.padding.only(left=10, right=10, top=10)
        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[self.status_icon, self.running_ring, self.title_text],
                    spacing=10,
                ),
                self.status_text,
                self.progress_bar,
            ],
            spacing=8,
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

    def start(self, title):
        self.clear_progress()
        self.title = title
        self.state = RUNNING
        self.render()

    def finish(self, title, success=True):
        self.title = title
        self.state = FINISHED if success else FAILED
        self.detail = None
        self.render()

    def update_progress(self, **fields):
        for field_name, value in fields.items():
            if field_name in PROGRESS_FIELDS:
                setattr(self, field_name, value)

        self.render()

    def get_status_text(self):
        parts = []

        # A single folder of images isn't worth calling "chapter 1 of 1".
        if self.chapters and self.chapters > 1:
            parts.append(f"{self.group_label} {self.chapter} of {self.chapters}")

        if self.pages_total:
            unit = self.unit if self.pages_total != 1 else self.unit.rstrip("s")
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
        self.progress_bar.value = self.get_bar_value()
        self.progress_bar.visible = self.state in (RUNNING, FINISHED)

        # A spinning ring while running. Otherwise an icon for the state.
        self.running_ring.visible = self.state == RUNNING
        self.status_icon.visible = self.state != RUNNING
        self.status_icon.name, self.status_icon.color = {
            IDLE: (ft.Icons.PLAY_CIRCLE_OUTLINE, MUTED_COLOR),
            FINISHED: (ft.Icons.CHECK_CIRCLE, Nord.GREEN),
            FAILED: (ft.Icons.ERROR, Nord.RED_TEXT),
        }.get(self.state, (ft.Icons.PLAY_CIRCLE_OUTLINE, MUTED_COLOR))

        # Never let a GUI problem break the job that's reporting.
        try:
            if self.page:
                self.update()
        except Exception:
            pass
