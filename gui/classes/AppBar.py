import flet as ft


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
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.current_view = "MangaDex Downloader"

        # Define the buttons
        self.mangadex_button = AppBarButton(
            text="MangaDex Downloader",
            current_view=self.current_view,
            change_view=self.change_view,
        )

        self.panel_button = AppBarButton(
            text="Panel-By-Panel",
            current_view=self.current_view,
            change_view=self.change_view,
        )

        self.bgcolor = "#3b4252"
        self.padding = 0
        self.margin = 0

        print(
            f'use_chapter_title value: {self.page.client_storage.get("use_chapter_title")}'
        )

        print(
            f'self.page.client_storage value: {self.page.client_storage.get_keys("key-prefix.")}'
        )

        drawer = ft.NavigationDrawer(
            bgcolor="#3b4252",
            position=ft.NavigationDrawerPosition.END,
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                "Settings - MangaDex Downloader",
                                size=14,
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Checkbox(
                                label="Use Chapter Title",
                                value=self.page.client_storage.get("use_chapter_title"),
                                on_change=lambda e: self.change_mangadex_downloader_setting(
                                    "use_chapter_title", e.data
                                ),
                            ),
                            ft.Checkbox(
                                label="No Group Name",
                                value=self.page.client_storage.get("no_group_name"),
                                on_change=lambda e: self.change_mangadex_downloader_setting(
                                    "no_group_name", e.data
                                ),
                            ),
                            ft.Dropdown(
                                options=[
                                    ft.dropdown.Option("Red"),
                                    ft.dropdown.Option("Green"),
                                    ft.dropdown.Option("Blue"),
                                ],
                                value="Red",
                                text_style=ft.TextStyle(
                                    color="white",  # Text color of the selected item
                                    size=14,  # Font size
                                ),
                                fill_color="#3b4252",  # Background color of the dropdown
                                border_color="#5e81ac",
                            ),
                        ]
                    ),
                    padding=15,
                )
            ],
        )

        self.content = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        self.mangadex_button,
                        # TODO: Bring back after I start working on the "Panel-By-Panel" view.
                        # self.panel_button,
                    ]
                ),
                ft.IconButton(
                    ft.icons.MENU,
                    on_click=lambda e: self.page.open(drawer),
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
        self.current_view = view_name

        # Update button styles dynamically
        self.mangadex_button.style = self.mangadex_button.get_button_style_by_view(
            self.current_view
        )

        self.panel_button.style = self.panel_button.get_button_style_by_view(
            self.current_view
        )

        self.page.update()  # Refresh the UI

    def change_mangadex_downloader_setting(self, setting_key, setting_value):
        print(setting_key)
        print(setting_value)

        boolean_setting_value = {"true": True, "false": False}.get(
            setting_value.lower(), False
        )

        print(boolean_setting_value)

        self.page.client_storage.set(setting_key, boolean_setting_value)
