import threading
import flet as ft
from utils import add_line_to_terminal_output_list_view


MIN_TERMINAL_HEIGHT = 60
DEFAULT_TERMINAL_HEIGHT = 200


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
                border=ft.border.only(top=ft.border.BorderSide(2, "#5e81ac")),
            ),
            mouse_cursor=ft.MouseCursor.RESIZE_UP_DOWN,
            on_vertical_drag_update=self.handle_resize_drag,
            drag_interval=20,
        )

        self.terminal_output_list_view = ft.ListView(expand=True, auto_scroll=True)
        self.terminal_arrow_icon = ft.IconButton(
            ft.Icons.KEYBOARD_ARROW_DOWN,
            on_click=self.toggle_terminal_visibility,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4), padding=1),
        )

        self.title_text = ft.Text(value="Terminal Output", color="#8fbcbb")
        self.command_text = ft.Text(value="", color="gray", visible=False)
        self.progress_ring = ft.ProgressRing(width=14, height=14, visible=False)
        self.success_icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color="green", visible=False)

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
        self.bgcolor = "#3b4252"
        self.height = DEFAULT_TERMINAL_HEIGHT

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
                        self.terminal_arrow_icon,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.terminal_output_list_view,
            ],
        )

    def handle_resize_drag(self, e):
        # Dragging up (negative "delta_y") makes the terminal taller. Keep some room for the view above it.
        max_height = max(DEFAULT_TERMINAL_HEIGHT, (self.page.height or 800) - 150)
        new_height = min(max(self.height - e.delta_y, MIN_TERMINAL_HEIGHT), max_height)

        self.height = new_height
        self.terminal_output_list_view.visible = new_height > MIN_TERMINAL_HEIGHT
        self.terminal_arrow_icon.icon = (
            ft.Icons.KEYBOARD_ARROW_DOWN
            if self.terminal_output_list_view.visible
            else ft.Icons.KEYBOARD_ARROW_UP
        )
        if self.terminal_output_list_view.visible:
            self.expanded_height = new_height

        self.update()

    def show_loading_text(self, new_command_text="Command Is Running..."):
        self.loading_text_count += 1
        self.title_text.value = "Terminal Output:"
        self.command_text.value = new_command_text

        self.command_text.visible = True
        self.progress_ring.visible = True

        self.title_text.update()
        self.command_text.update()
        self.progress_ring.update()

    def hide_loading_text(
        self, result_text="Command has finished running!", success=True
    ):
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
        self.terminal_output_list_view.visible = (
            not self.terminal_output_list_view.visible
        )

        if self.terminal_output_list_view.visible:
            # Expand back to the last size it was dragged to.
            self.height = self.expanded_height
            self.terminal_arrow_icon.icon = ft.Icons.KEYBOARD_ARROW_DOWN
        else:
            self.height = MIN_TERMINAL_HEIGHT
            self.terminal_arrow_icon.icon = ft.Icons.KEYBOARD_ARROW_UP

        self.page.update()  # Refresh the UI to reflect changes

    def update_terminal_with_error_message(self, error_message):
        add_line_to_terminal_output_list_view(
            self.terminal_output_list_view, error_message, color=ft.Colors.RED
        )
