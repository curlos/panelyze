import flet as ft
from classes.NavDrawerMangaDexDownloader import NavDrawerMangaDexDownloader


class AppBarButton(ft.TextButton):
    def __init__(self, text, current_view, change_view):
        super().__init__()
        self.text = text
        self.on_click = lambda e: change_view(text)
        self.style = self.get_button_style_by_view(current_view)

    def get_button_style_by_view(self, current_view):
        return ft.ButtonStyle(
            bgcolor=(
                "#5e81ac" if current_view == self.text else ft.Colors.BLUE_GREY_800
            ),
            color="white",
            shape={
                ft.ControlState.HOVERED: ft.RoundedRectangleBorder(radius=0),
                ft.ControlState.DEFAULT: ft.RoundedRectangleBorder(radius=0),
            },
        )


class AppBar(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui
        self.page = self.parent_gui.page

        # Define the buttons
        self.mangadex_button = AppBarButton(
            text="MangaDex Downloader",
            current_view=self.parent_gui.current_view,
            change_view=self.change_view,
        )

        self.panel_button = AppBarButton(
            text="Panel-By-Panel",
            current_view=self.parent_gui.current_view,
            change_view=self.change_view,
        )

        self.bgcolor = "#3b4252"
        self.padding = 0
        self.margin = 0

        self.create()

    def create(self):
        mangadex_drawer = NavDrawerMangaDexDownloader(
            self.page, self.parent_gui.all_mangadex_languages
        )

        self.content = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        self.mangadex_button,
                        self.panel_button,
                    ]
                ),
                ft.IconButton(
                    ft.Icons.SETTINGS,
                    on_click=lambda e: self.page.open(mangadex_drawer),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=4), padding=1
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=True,
        )

    # Function to change the view and update the button styles
    def change_view(self, view_name):
        if view_name == self.parent_gui.current_view:
            return

        self.parent_gui.current_view = view_name

        # Update button styles dynamically
        self.mangadex_button.style = self.mangadex_button.get_button_style_by_view(
            self.parent_gui.current_view
        )

        self.panel_button.style = self.panel_button.get_button_style_by_view(
            self.parent_gui.current_view
        )

        self.parent_gui.render_page_based_on_current_view()
        self.parent_gui.page.update()
