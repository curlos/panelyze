import flet as ft


class ResponsiveColumns(ft.Container):
    """
    A tab's main part with its settings on the right. When the window is narrow (like a phone, or a window shrunk to half the screen), the settings go under the main part instead, like on a web page.
    """

    def __init__(self, main, settings, main_fills_height=True):
        super().__init__()
        self.expand = True
        # The space between the tab's content and the edges (the tabs above, the terminal below and the window's sides).
        self.padding = 16
        self.main = main
        self.settings = settings
        # When stacked, a main part that doesn't fill the height (like the MangaDex tab's short form) only takes the space it needs, and the settings get the rest.
        self.main_fills_height = main_fills_height
        # The settings' width when they're on the right. Stacked, they're as wide as the window.
        self.settings_width = settings.width
        self.set_narrow(False)

    def set_narrow(self, is_narrow):
        """
        Doesn't update the page. The caller does that once, after every view is changed.
        """
        if is_narrow:
            # The main part gets 3/5 of the height and the settings 2/5. The settings scroll if they don't fit.
            self.main.expand = 3 if self.main_fills_height else None
            self.settings.expand = 2 if self.main_fills_height else True
            self.settings.width = None
            self.content = ft.Column(
                controls=[self.main, self.settings],
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                expand=True,
            )
        else:
            self.main.expand = True
            self.settings.expand = True
            self.settings.width = self.settings_width
            # In a row, the settings are put in a column so they keep their width and still fill the height.
            self.content = ft.Row(
                controls=[self.main, ft.Column(controls=[self.settings])],
                expand=True,
                # A main part that's shorter than the window stays at the top instead of being centered.
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
