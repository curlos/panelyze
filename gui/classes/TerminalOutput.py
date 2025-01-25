import time
import flet as ft


class TerminalOutput(ft.Container):
    def __init__(self, page):
        super().__init__()
        self.page = page

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
        self.bgcolor = "#3b4252"
        self.padding = 10
        self.height = 200
        self.border = ft.border.only(top=ft.border.BorderSide(1, "#5e81ac"))

    def show_loading_text(self, new_command_text="Command Is Running..."):
        self.title_text.value = "Terminal Output:"
        self.command_text.value = new_command_text

        self.command_text.visible = True
        self.progress_ring.visible = True

        self.title_text.update()
        self.command_text.update()
        self.progress_ring.update()

    def hide_loading_text(self, result_text="Command has finished running!"):
        self.command_text.value = result_text
        self.progress_ring.visible = False
        self.success_icon.visible = True

        self.command_text.update()
        self.progress_ring.update()
        self.success_icon.update()

        time.sleep(3)

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

        # Check if height is currently fixed (200)
        if self.height == 200:
            # Set to auto height by removing fixed height
            self.height = 60
            self.terminal_arrow_icon.icon = ft.Icons.KEYBOARD_ARROW_UP
        else:
            # Reset to fixed height
            self.height = 200
            self.terminal_arrow_icon.icon = ft.Icons.KEYBOARD_ARROW_DOWN

        self.page.update()  # Refresh the UI to reflect changes

    def update_terminal_with_error_message(self, error_message):
        self.terminal_output_list_view.controls.append(
            ft.Text(error_message, color=ft.Colors.RED)
        )
        self.terminal_output_list_view.update()
