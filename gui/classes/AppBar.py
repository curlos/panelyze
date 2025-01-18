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
    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui
        self.current_view = self.parent_gui.current_view
        self.page = self.parent_gui.page

        # Buttons
        self.mangadex_downloader_button = AppBarButton(
            text="MangaDex Downloader",
            current_view=self.parent_gui.current_view,
            change_view=self.change_view,
        )

        self.panel_by_panel_button = AppBarButton(
            text="Panel-By-Panel",
            current_view=self.parent_gui.current_view,
            change_view=self.change_view,
        )

        self.upscale_images_button = AppBarButton(
            text="Upscale Images",
            current_view=self.parent_gui.current_view,
            change_view=self.change_view,
        )

        self.images_to_video_button = AppBarButton(
            text="Images To Video",
            current_view=self.parent_gui.current_view,
            change_view=self.change_view,
        )

        self.bgcolor = "#3b4252"
        self.padding = 0
        self.margin = 0

        self.content = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        self.mangadex_downloader_button,
                        self.panel_by_panel_button,
                        self.upscale_images_button,
                        self.images_to_video_button,
                    ]
                ),
                ft.IconButton(
                    ft.Icons.SETTINGS,
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
        self.mangadex_downloader_button.style = (
            self.mangadex_downloader_button.get_button_style_by_view(
                self.parent_gui.current_view
            )
        )

        self.panel_by_panel_button.style = (
            self.panel_by_panel_button.get_button_style_by_view(
                self.parent_gui.current_view
            )
        )

        self.parent_gui.render_page_based_on_current_view()
        self.parent_gui.page.update()
