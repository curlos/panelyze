import threading
import flet as ft
from gui_classes import Nord
from gui_classes.ProgressPanel import ProgressPanel
from utils import add_line_to_terminal_output_list_view


MIN_TERMINAL_HEIGHT = 60
DEFAULT_TERMINAL_HEIGHT = 200
RAW_OUTPUT_EMPTY_TEXT = "Nothing here yet. The details of what Panelyze and its tools are doing show up here."


class RawOutputListView(ft.ListView):
    """
    The lines of the Raw Output. While there are none, "empty_message" is shown instead (see "update").
    """

    def __init__(self, empty_message, **kwargs):
        super().__init__(**kwargs)
        self.empty_message = empty_message
        self.sync_empty_message()

    def sync_empty_message(self):
        self.empty_message.visible = not self.controls

    def update(self):
        # Every part of the app that adds lines calls this afterwards.
        self.sync_empty_message()
        try:
            self.empty_message.update()
        except Exception:
            # Not on the page yet.
            pass
        super().update()


class TerminalOutput(ft.Container):
    def __init__(self, page):
        super().__init__()
        self.page = page
        # Counts how many jobs have started, so an old "finished" message can't clear a newer job's loading text.
        self.loading_text_count = 0
        # The height to go back to when the terminal is expanded again. Changed by dragging the blue line at the top.
        self.expanded_height = DEFAULT_TERMINAL_HEIGHT

        # Drag the blue line at the top of the terminal up or down to resize it.
        self.resize_handle = ft.GestureDetector(
            content=ft.Container(
                height=6,
                border=ft.border.only(top=ft.border.BorderSide(2, Nord.BLUE)),
            ),
            mouse_cursor=ft.MouseCursor.RESIZE_UP_DOWN,
            on_vertical_drag_update=self.handle_resize_drag,
            drag_interval=20,
        )

        # The raw output and the progress panel are stacked on top of each other, and the progress panel is shown or hidden. The raw output always stays on the page, so switching tabs never resets its scroll position.
        self.raw_output_empty_text = ft.Text(RAW_OUTPUT_EMPTY_TEXT, color=Nord.TEXT_MUTED, left=0, top=0, right=0)
        self.terminal_output_list_view = RawOutputListView(
            self.raw_output_empty_text, auto_scroll=True, left=0, top=0, right=0, bottom=0
        )
        self.progress_panel = ProgressPanel()
        self.progress_panel.left = 0
        self.progress_panel.top = 0
        self.progress_panel.right = 0
        self.progress_panel.bottom = 0
        self.output_area = ft.Stack(
            controls=[self.terminal_output_list_view, self.raw_output_empty_text, self.progress_panel],
            expand=True,
        )
        self.progress_tab_button = ft.TextButton(
            "Status", on_click=lambda e: self.show_tab("progress")
        )
        self.raw_output_tab_button = ft.TextButton(
            "Raw Output", on_click=lambda e: self.show_tab("raw_output")
        )
        self.update_tab_buttons()
        self.terminal_arrow_icon = ft.IconButton(
            ft.Icons.KEYBOARD_ARROW_DOWN,
            on_click=self.toggle_terminal_visibility,
            tooltip=Nord.tooltip("Show or hide the terminal"),
            style=ft.ButtonStyle(shape=Nord.SQUARE, side=Nord.get_focus_border(), padding=1),
        )

        self.title_text = ft.Text(
            value="Terminal Output", color=Nord.TEAL, weight=ft.FontWeight.BOLD
        )
        self.command_text = ft.Text(value="", color=Nord.TEXT_MUTED, visible=False)
        self.progress_ring = ft.ProgressRing(width=14, height=14, visible=False)
        self.success_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=Nord.GREEN, visible=False)

        self.content = ft.Column(
            controls=[
                self.resize_handle,
                ft.Container(
                    content=self.get_header_and_output_column(),
                    padding=ft.padding.only(left=10, right=10, bottom=10),
                    expand=True,
                ),
            ],
            spacing=0,
        )
        self.bgcolor = Nord.SURFACE
        self.height = DEFAULT_TERMINAL_HEIGHT
        self.side_borders_shown = False

    def set_side_borders(self, shown):
        """
        Blue borders on the left and right, for when the window is wider than the content: the terminal is then a box with margin on both sides, like the input cards. In a narrower window it touches the window's edges, so it has none.
        """
        if shown == self.side_borders_shown:
            return

        self.side_borders_shown = shown
        border_side = ft.BorderSide(1, Nord.BLUE)
        self.border = ft.border.only(left=border_side, right=border_side) if shown else None
        self.update()

    def get_header_and_output_column(self):
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Row(
                            controls=[
                                self.title_text,
                                self.command_text,
                                self.progress_ring,
                                self.success_icon,
                            ]
                        ),
                        ft.Row(
                            controls=[
                                self.progress_tab_button,
                                self.raw_output_tab_button,
                                self.terminal_arrow_icon,
                            ],
                            spacing=0,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.output_area,
            ],
        )

    def show_tab(self, tab_name):
        self.progress_panel.visible = tab_name == "progress"
        self.update_tab_buttons()
        self.progress_panel.update()
        self.progress_tab_button.update()
        self.raw_output_tab_button.update()

    def update_tab_buttons(self):
        for button, is_selected in [
            (self.progress_tab_button, self.progress_panel.visible),
            (self.raw_output_tab_button, not self.progress_panel.visible),
        ]:
            # The selected tab is the bright one.
            button.style = ft.ButtonStyle(
                color=Nord.ACCENT if is_selected else Nord.TEXT_MUTED,
                text_style=ft.TextStyle(weight=ft.FontWeight.BOLD if is_selected else None),
                shape=Nord.SQUARE,
                side=Nord.get_focus_border(),
            )

    def handle_resize_drag(self, e):
        # Dragging up (negative "delta_y") makes the terminal taller. Keep some room for the view above it.
        max_height = max(DEFAULT_TERMINAL_HEIGHT, (self.page.height or 800) - 150)
        new_height = min(max(self.height - e.delta_y, MIN_TERMINAL_HEIGHT), max_height)

        self.height = new_height
        self.output_area.visible = new_height > MIN_TERMINAL_HEIGHT
        self.terminal_arrow_icon.icon = (
            ft.Icons.KEYBOARD_ARROW_DOWN
            if self.output_area.visible
            else ft.Icons.KEYBOARD_ARROW_UP
        )
        if self.output_area.visible:
            self.expanded_height = new_height

        self.update()

    def show_loading_text(self, new_command_text="Command Is Running..."):
        self.loading_text_count += 1
        self.progress_panel.start(new_command_text)
        self.title_text.value = "Terminal Output:"
        self.command_text.value = new_command_text

        self.command_text.visible = True
        self.progress_ring.visible = True
        # The checkmark was for the job (or Pipeline step) before this one.
        self.success_icon.visible = False

        self.title_text.update()
        self.command_text.update()
        self.progress_ring.update()
        self.success_icon.update()

    def hide_loading_text(
        self, result_text="Command has finished running!", success=True, cancelled=False
    ):
        self.progress_panel.finish(result_text, success, cancelled)
        self.command_text.value = result_text
        self.progress_ring.visible = False
        # Only show the green success icon if the command actually succeeded.
        self.success_icon.visible = success

        self.command_text.update()
        self.progress_ring.update()
        self.success_icon.update()

        # Clear the result message after 3 seconds, without making the job (or the next Pipeline step) wait for it.
        loading_text_count = self.loading_text_count
        threading.Timer(3, self.reset_title, args=[loading_text_count]).start()

    def reset_title(self, loading_text_count):
        # A newer job started in the meantime, so its loading text must stay.
        if loading_text_count != self.loading_text_count:
            return

        self.title_text.value = "Terminal Output"
        self.command_text.value = ""
        self.command_text.visible = False
        self.success_icon.visible = False

        self.title_text.update()
        self.command_text.update()
        self.success_icon.update()

    def toggle_terminal_visibility(self, e):
        self.output_area.visible = not self.output_area.visible

        if self.output_area.visible:
            # Expand back to the last size it was dragged to.
            self.height = self.expanded_height
            self.terminal_arrow_icon.icon = ft.Icons.KEYBOARD_ARROW_DOWN
        else:
            self.height = MIN_TERMINAL_HEIGHT
            self.terminal_arrow_icon.icon = ft.Icons.KEYBOARD_ARROW_UP

        self.page.update()  # Refresh the UI to reflect changes

    def update_terminal_with_error_message(self, error_message):
        """
        Every error goes in the Raw Output (all the details) and in the Status view (a friendly message). A collapsed terminal is opened and the Status view shown, so an error can never be missed.
        """
        add_line_to_terminal_output_list_view(
            self.terminal_output_list_view, error_message, color=Nord.RED_TEXT
        )
        self.progress_panel.show_error(error_message)
        # E.g. a Pipeline download that worked but saved nothing: its checkmark isn't next to this error.
        self.success_icon.visible = False
        try:
            self.success_icon.update()
        except Exception:
            pass

        if not self.output_area.visible:
            self.toggle_terminal_visibility(None)
        self.show_tab("progress")
