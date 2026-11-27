import os
import threading
import traceback

import flet as ft

import storage
from gui_classes import Nord
from gui_classes.AppOutput import LOG_FILE_PATH, LOG_FOLDER, write_to_log_file_only
from gui_classes.ProgressPanel import format_size
from utils import get_error_text, open_directory, set_text_with_links

CALCULATING_TEXT = "Calculating..."
# How wide a saved files row's name is, so the sizes after it (and the total's) line up.
NAME_WIDTH = 130


def get_disk_row(name, free_size, total_size):
    """
    A disk's name, a bar of how full it is, and how much is free, e.g. "This computer [■■■■■■■■□] 50.4 GB free of 494 GB". Like File Explorer and macOS's Storage settings: the bar is what's used, and it's red when less than 10% is free.
    """
    used_share = 1 - free_size / total_size if total_size else 0
    return ft.Row(
        controls=[
            ft.Text(name, color=Nord.TEXT, width=NAME_WIDTH),
            ft.ProgressBar(
                value=used_share,
                width=200,
                bar_height=8,
                color=Nord.RED if used_share > 0.9 else Nord.ACCENT,
                bgcolor=Nord.SURFACE_HIGH,
                border_radius=4,
            ),
            # What's free is what matters for downloading, so it stands out.
            ft.Text(
                spans=[
                    ft.TextSpan(
                        f"{format_size(free_size)} free", ft.TextStyle(color=Nord.TEXT)
                    ),
                    ft.TextSpan(
                        f" of {format_size(total_size)}",
                        ft.TextStyle(color=Nord.TEXT_MUTED),
                    ),
                ]
            ),
        ],
        wrap=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def get_group(heading, rows, spacing=0, heading_spacing=4):
    """
    A heading and its list, close together (the space between the groups is the section's own). "heading_spacing" is the space under the heading: a bit more when the list starts with its own small label.
    """
    return ft.Column(
        controls=[
            # More space above a heading than under it, so each heading and its list read as one group.
            ft.Container(
                content=get_subheading(heading), padding=ft.padding.only(top=16)
            ),
            ft.Column(controls=rows, spacing=spacing),
        ],
        spacing=heading_spacing,
    )


# How tall a row's compact icon button is (see "get_icon_button").
BUTTON_HEIGHT = 32


def get_group_label(text):
    # Small, gray and in capitals, like the labels in the Download tab, but not teal: the "Downloaded models" heading above is.
    return ft.Text(
        text.upper(), size=11, weight=ft.FontWeight.BOLD, color=Nord.TEXT_MUTED
    )


def get_subheading(text):
    # Teal like the terminal's title, so it stands out from the rows' white names.
    # A bit bigger than the rows, and smaller than the section's title ("Storage", 16).
    return ft.Text(text, size=15, weight=ft.FontWeight.BOLD, color=Nord.TEAL)


# The colors of the rows' small buttons, so they don't outweigh the text they're next to. Delete is red, but not a big red block.
SMALL_BUTTON_COLORS = {
    "primary": Nord.ACCENT,
    "secondary": Nord.TEXT,
    "danger": Nord.RED_TEXT,
}


def get_icon_button(name, icon, on_click, kind="secondary", disabled=False):
    """
    A row's Open, Download or Delete button: only its icon, so it doesn't draw attention (they aren't clicked often), with its name in a tooltip.
    """
    return ft.IconButton(
        icon=icon,
        icon_size=18,
        icon_color=SMALL_BUTTON_COLORS[kind],
        tooltip=Nord.tooltip(name),
        on_click=on_click,
        disabled=disabled,
        opacity=0.5 if disabled else 1,
        style=Nord.icon_button_style(),
        # Compact, so a row is only about as tall as its text (an icon button keeps 40 px around it otherwise, which spread the rows apart).
        visual_density=ft.VisualDensity.COMPACT,
        padding=4,
    )


def get_button(text, icon, on_click, kind="secondary", disabled=False):
    return ft.ElevatedButton(
        style=Nord.button_style(kind),
        text=text,
        icon=icon,
        on_click=on_click,
        disabled=disabled,
        # The button styles don't change for a disabled button, so it's faded instead.
        opacity=0.5 if disabled else 1,
    )


class StorageSection(ft.Column):
    """
    Settings → Storage: everywhere Panelyze keeps files on this computer (what the tabs saved, and the models it downloaded), how much space each takes, and buttons to open, delete or download them. The sizes are worked out in the background ("refresh"), since a few GB of files take a second or more to add up.
    """

    def __init__(self, parent_gui):
        super().__init__(spacing=12)
        self.parent_gui = parent_gui
        # The sizes by path, once they're worked out (None while they're being worked out).
        self.sizes = None
        # Counts the refreshes, so the sizes of an older one that finished late aren't shown.
        self.refresh_count = 0
        self.saved_files_rows = []
        self.model_rows = []
        # Shown next to the section's title (see "AppSettingsView").
        self.refresh_button = get_icon_button(
            "Measure the sizes again (e.g. after deleting files yourself)",
            ft.Icons.REFRESH,
            lambda e: self.refresh(),
        )
        # Shown next to the log file buttons (see "AppSettingsView").
        self.log_size_text = ft.Text(CALCULATING_TEXT, color=Nord.TEXT_MUTED)

    def refresh(self):
        """
        Find what's there now, then work out the sizes in the background. Done each time Settings is opened, since jobs keep saving files.
        """
        self.refresh_count += 1
        self.saved_files_rows = storage.get_saved_files_rows(
            self.parent_gui.page.client_storage
        )
        self.model_rows = storage.get_model_rows()
        self.sizes = None
        self.render()
        threading.Thread(
            target=self.find_sizes, args=[self.refresh_count], daemon=True
        ).start()

    def find_sizes(self, refresh_count):
        sizes = {}
        for row in self.saved_files_rows + self.model_rows:
            sizes[row.name] = storage.get_size(row.paths)
        sizes["log file"] = storage.get_size([LOG_FILE_PATH])
        sizes["logs folder"] = storage.get_size([LOG_FOLDER])
        sizes["disks"] = storage.get_disks(
            [row.folder_to_open for row in self.saved_files_rows]
            + storage.get_model_folders()
        )
        # A newer refresh started while these were worked out.
        if refresh_count != self.refresh_count:
            return
        self.sizes = sizes
        self.render()

    def get_size_text(self, row):
        if self.sizes is None:
            return CALCULATING_TEXT
        return format_size(self.sizes[row.name])

    def render(self):
        # Nothing can be deleted or downloaded while a job runs (it could be using the files).
        is_locked = self.parent_gui.is_job_running
        panelyze_folder = storage.get_panelyze_folder(
            self.parent_gui.page.client_storage
        )
        self.controls = [
            # How much space is left, to see what can still be downloaded.
            *(
                [ft.Text(CALCULATING_TEXT, color=Nord.TEXT_MUTED)]
                if self.sizes is None
                else [get_disk_row(*disk) for disk in self.sizes["disks"]]
            ),
            get_group(
                "Saved files",
                [
                    *[
                        self.get_saved_files_row(row, is_locked)
                        for row in self.saved_files_rows
                    ],
                    # Its size lines up with the folders' sizes above it. A little apart from them, as their total.
                    ft.Container(
                        padding=ft.padding.only(top=6),
                        content=ft.Row(
                            controls=[
                                ft.Text(
                                    "All saved files",
                                    weight=ft.FontWeight.BOLD,
                                    color=Nord.TEXT,
                                    width=NAME_WIDTH,
                                ),
                                ft.Text(
                                    self.get_total_text(),
                                    weight=ft.FontWeight.BOLD,
                                    color=Nord.TEXT,
                                    width=80,
                                ),
                                # The whole Panelyze folder (every tool's folder is in it).
                                get_icon_button(
                                    "Open the Panelyze folder",
                                    ft.Icons.FOLDER_OPEN,
                                    lambda e: open_directory(panelyze_folder),
                                    disabled=not os.path.isdir(panelyze_folder),
                                ),
                                get_icon_button(
                                    "Delete all saved files",
                                    ft.Icons.DELETE,
                                    lambda e: self.confirm_delete_all(),
                                    kind="danger",
                                    disabled=is_locked
                                    or not self.get_deletable_saved_files_rows(),
                                ),
                            ]
                        ),
                    ),
                ],
            ),
            get_group(
                "Downloaded models",
                self.get_model_rows_by_group(is_locked),
                spacing=24,
                heading_spacing=10,
            ),
        ]
        if self.sizes is None:
            self.log_size_text.value = CALCULATING_TEXT
        else:
            self.log_size_text.value = f"Current log: {format_size(self.sizes['log file'])} · all logs: {format_size(self.sizes['logs folder'])}"
        if self.page:
            self.update()
            self.log_size_text.update()

    def get_model_rows_by_group(self, is_locked):
        """
        The models of each kind ("UPSCALING", ...) under a small label right above them. The kinds are further apart than the models in each (see where this is used).
        """
        groups = {}
        for row in self.model_rows:
            groups.setdefault(row.group, []).append(self.get_model_row(row, is_locked))
        return [
            ft.Column(
                controls=[
                    get_group_label(group),
                    # Close, but not touching: the bold names and the small labels already set them apart.
                    ft.Column(controls=model_rows, spacing=8),
                ],
                spacing=2,
            )
            for group, model_rows in groups.items()
        ]

    def get_total_text(self):
        if self.sizes is None:
            return CALCULATING_TEXT
        return format_size(sum(self.sizes[row.name] for row in self.saved_files_rows))

    def get_saved_files_row(self, row, is_locked):
        controls = [
            ft.Text(row.name, color=Nord.TEXT, width=NAME_WIDTH),
            ft.Text(self.get_size_text(row), color=Nord.TEXT, width=80),
            get_icon_button(
                "Open folder",
                ft.Icons.FOLDER_OPEN,
                lambda e: open_directory(row.folder_to_open),
                # Nothing has been saved there yet.
                disabled=not os.path.isdir(row.folder_to_open),
            ),
        ]
        if row.can_delete:
            controls.append(
                get_icon_button(
                    "Delete",
                    ft.Icons.DELETE,
                    lambda e: self.confirm_delete(row),
                    kind="danger",
                    disabled=is_locked or not os.path.isdir(row.folder_to_open),
                )
            )
        else:
            controls.append(
                ft.Text(
                    "A folder picked in its tab, so it isn't deleted here",
                    size=12,
                    color=Nord.TEXT_MUTED,
                )
            )
        return ft.Row(
            controls=controls,
            wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def get_status_text(self, row):
        if row.status == storage.DOWNLOADED:
            return f"Downloaded · {self.get_size_text(row)}"
        if row.status == storage.BUILT_IN:
            return "Built in"
        if not row.download:
            # The panels-only Magi model, when running from source before it's made.
            return "Made from the full Magi model the first time it's needed"
        # What it takes on disk once downloaded (the same number Storage shows then).
        return f"Not downloaded · {format_size(row.download_size)}"

    def get_model_row(self, row, is_locked):
        # Dimmer than the name: it's there to read when wanted, not to compete with it.
        description_text = ft.Text(color=Nord.TEXT_MUTED, size=12)
        set_text_with_links(description_text, f"{row.description} From {row.url}")
        # In the same order as the saved files' buttons: Open, then Delete.
        buttons = []
        if row.folder_to_open:
            buttons.append(
                get_icon_button(
                    "Open folder",
                    ft.Icons.FOLDER_OPEN,
                    lambda e: open_directory(row.folder_to_open),
                )
            )
        if row.download and row.status == storage.NOT_DOWNLOADED:
            buttons.append(
                get_icon_button(
                    "Download",
                    ft.Icons.DOWNLOAD,
                    lambda e: self.download(row),
                    kind="primary",
                    disabled=is_locked,
                )
            )
        if row.can_delete:
            buttons.append(
                get_icon_button(
                    "Delete",
                    ft.Icons.DELETE,
                    lambda e: self.confirm_delete(row),
                    kind="danger",
                    disabled=is_locked,
                )
            )
        # Each model's name, buttons and description, as one group.
        return ft.Container(
            content=ft.Column(
                spacing=2,
                controls=[
                    # The buttons go next to the name and status (or under them on a narrow window).
                    ft.Row(
                        wrap=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            # Bold, so each model stands out from its description.
                            ft.Text(
                                row.name,
                                weight=ft.FontWeight.BOLD,
                                color=Nord.TEXT_BRIGHT,
                            ),
                            ft.Text(
                                self.get_status_text(row),
                                color=Nord.GREEN
                                if row.status == storage.DOWNLOADED
                                else Nord.TEXT_MUTED,
                            ),
                            # A model without buttons (built in) keeps the same height as one with them, so the models stay evenly spaced.
                            *(buttons or [ft.Container(width=0, height=BUTTON_HEIGHT)]),
                        ],
                    ),
                    description_text,
                ],
            ),
        )

    def get_delete_message(self, row):
        """
        What Delete deletes, as text spans: what it is in bold, its size in gray.
        """
        bold = ft.TextStyle(weight=ft.FontWeight.BOLD, color=Nord.TEXT_BRIGHT)
        gray = ft.TextStyle(color=Nord.TEXT_MUTED)
        size = ft.TextSpan(f" ({self.get_size_text(row)})", gray)
        if row in self.model_rows:
            return [
                ft.TextSpan("This deletes "),
                ft.TextSpan(row.name, bold),
                size,
                ft.TextSpan(
                    " from this computer. It's downloaded again the next time it's needed (or with its Download button)."
                ),
            ]
        return [
            ft.TextSpan("This deletes everything in "),
            ft.TextSpan(row.folder_to_open, bold),
            size,
            ft.TextSpan(". This can't be undone."),
        ]

    def confirm_delete(self, row):
        self.ask_to_delete(
            [row],
            "Delete this model?" if row in self.model_rows else "Delete these files?",
            self.get_delete_message(row),
        )

    def confirm_delete_all(self):
        """
        Delete every tool's saved files at once, after saying which folders and how much. A folder picked in a tab is left alone, as on its own row.
        """
        rows = self.get_deletable_saved_files_rows()
        bold = ft.TextStyle(weight=ft.FontWeight.BOLD, color=Nord.TEXT_BRIGHT)
        gray = ft.TextStyle(color=Nord.TEXT_MUTED)
        message = [ft.TextSpan("This deletes everything in these folders:\n")]
        for row in rows:
            message += [
                ft.TextSpan("• "),
                ft.TextSpan(row.name, bold),
                ft.TextSpan(f" ({self.get_size_text(row)})\n", gray),
            ]
        message += [
            ft.TextSpan("All together: "),
            ft.TextSpan(
                format_size(sum(self.sizes[row.name] for row in rows))
                if self.sizes
                else CALCULATING_TEXT,
                bold,
            ),
            ft.TextSpan(". This can't be undone."),
        ]
        self.ask_to_delete(rows, "Delete all saved files?", message)

    def get_deletable_saved_files_rows(self):
        return [
            row
            for row in self.saved_files_rows
            if row.can_delete and os.path.isdir(row.folder_to_open)
        ]

    def ask_to_delete(self, rows, title, message):
        page = self.parent_gui.page
        dialog = ft.AlertDialog(
            modal=True,
            # The name is in the message, in bold, so the title doesn't repeat it in a big font.
            title=ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
            content=ft.Text(spans=message),
            actions=[
                # Plain text for the safe choice, and the filled red button for the one that deletes, as most dialogs do.
                ft.TextButton(
                    "Cancel",
                    on_click=lambda e: page.close(dialog),
                    style=ft.ButtonStyle(
                        color=Nord.TEXT_BRIGHT,
                        shape=Nord.SQUARE,
                        side=Nord.get_focus_border(),
                    ),
                ),
                get_button(
                    "Delete", None, lambda e: self.delete(rows, dialog), kind="danger"
                ),
            ],
        )
        page.open(dialog)

    def delete(self, rows, dialog):
        self.parent_gui.page.close(dialog)
        name = rows[0].name if len(rows) == 1 else "all saved files"
        # Deleting runs like a job, so no job can start in the middle of it (e.g. an upscale using the models being deleted). It also says so if a job started since the dialog was opened.
        if not self.parent_gui.try_to_start_job(f"Delete {name}"):
            return
        try:
            for row in rows:
                storage.delete_paths(row)
                print(f"Deleted {row.name}: {', '.join(row.paths)}")
        except OSError as error:
            self.parent_gui.terminal_output.update_terminal_with_error_message(
                f"ERROR: Couldn't delete all of {name} ({error})."
            )
        finally:
            self.parent_gui.set_job_running(False)
            self.refresh()

    def download(self, row):
        """
        Download a model now instead of the first time it's needed. It runs like any other job: one at a time, with its progress in the Status view.
        """
        if not row.download:
            return
        if not self.parent_gui.try_to_start_job(f"Download {row.name}"):
            return
        terminal_output = self.parent_gui.terminal_output
        try:
            # Turns the Download and Delete buttons off while it runs.
            self.render()
            terminal_output.show_loading_text(f"Downloading {row.name}...")
            # The download is this job itself, so it isn't shown again as a step of its own.
            terminal_output.progress_panel.shows_extra_stages = False
            row.download()
            terminal_output.hide_loading_text(f"Downloaded {row.name}.")
        except Exception as error:
            # The full details go in the log file. The app shows a short message.
            write_to_log_file_only(traceback.format_exc())
            terminal_output.hide_loading_text("Failed.", success=False)
            terminal_output.update_terminal_with_error_message(
                f"ERROR: {get_error_text(error)}"
            )
        finally:
            self.parent_gui.set_job_running(False)
            self.refresh()
