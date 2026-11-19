import flet as ft


class AppBarButton(ft.TextButton):
    def __init__(self, text, current_view, change_view):
        super().__init__()
        self.text = text
        self.on_click = lambda e: change_view(text)
        self.style = self.get_button_style_by_view(current_view)

    def get_button_style_by_view(self, current_view):
        return ft.ButtonStyle(
            bgcolor=("#5e81ac" if current_view == self.text else "#3b4252"),
            color="white",
            shape={
                ft.ControlState.HOVERED: ft.RoundedRectangleBorder(radius=0),
                ft.ControlState.DEFAULT: ft.RoundedRectangleBorder(radius=0),
            },
        )


TAB_NAMES = [
    "MangaDex Downloader",
    "Panel-By-Panel",
    "Upscale Images",
    "Images To Video",
    "Pipeline",
]


class AppBar(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui

        self.bgcolor = "#3b4252"
        self.padding = 0
        self.margin = 0

        self.content = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        AppBarButton(
                            text=tab_name,
                            current_view=self.parent_gui.current_view,
                            change_view=self.change_view,
                        )
                        for tab_name in TAB_NAMES
                    ]
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    icon_color="white",
                    tooltip="Settings",
                    # Square corners to match the tab buttons.
                    style=ft.ButtonStyle(
                        bgcolor=(
                            "#5e81ac"
                            if self.parent_gui.current_view == "Settings"
                            else "#3b4252"
                        ),
                        shape=ft.RoundedRectangleBorder(radius=0),
                    ),
                    on_click=lambda e: self.change_view("Settings"),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=True,
        )

    def change_view(self, view_name):
        if view_name == self.parent_gui.current_view:
            return

        self.parent_gui.current_view = view_name

        # Re-rendering the page also builds a new app bar with the right button highlighted.
        self.parent_gui.render_page_based_on_current_view()
        self.parent_gui.page.update()
