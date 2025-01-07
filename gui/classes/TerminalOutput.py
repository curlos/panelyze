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

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(value="Terminal Output", color="#8fbcbb"),
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
