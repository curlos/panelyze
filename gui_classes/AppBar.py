import flet as ft
from gui_classes import Nord


class AppBarButton(ft.Container):
    """
    A tab at the top. The selected one has the main area's color and a line under it, like a tab in VS Code. When "show_text" is False, only the icon is shown (the name is in the tooltip).
    """

    def __init__(self, text, icon, shortcut, current_view, change_view, show_text, on_focus_change, running_job_name=""):
        super().__init__()
        is_selected = current_view == text
        # While a job runs, only its own tab can be open.
        is_waiting = bool(running_job_name) and not is_selected
        self.opacity = 0.5 if is_waiting else 1

        self.bgcolor = Nord.BACKGROUND if is_selected else None
        self.border = ft.border.only(
            bottom=ft.border.BorderSide(2, Nord.ACCENT if is_selected else ft.Colors.TRANSPARENT)
        )
        style = ft.ButtonStyle(
            color=Nord.TEXT_BRIGHT if is_selected else Nord.TEXT_MUTED,
            shape=Nord.SQUARE,
            side=Nord.get_focus_border(),
        )
        # An icon-only tab is an icon button, so the icon is centered (a text button with no text still leaves room on the right for it).
        button_class = ft.TextButton if show_text else ft.IconButton
        # A tooltip only when it says something the tab doesn't: why it can't be opened, or the name when only the icon shows.
        if is_waiting:
            tooltip = Nord.tooltip(f'Wait for "{running_job_name}" to finish (only one job runs at a time)')
        elif not show_text:
            tooltip = Nord.tooltip(f"{text} ({shortcut})")
        else:
            tooltip = None
        self.content = button_class(
            icon=icon,
            tooltip=tooltip,
            on_click=lambda e: change_view(text),
            # Lets the arrow keys know a tab is focused (see "AppBar.move_to_tab").
            on_focus=lambda e: on_focus_change(text, True),
            on_blur=lambda e: on_focus_change(text, False),
            style=style,
            **({"text": text} if show_text else {}),
        )


TAB_NAMES = [
    "Download",
    "Panel-By-Panel",
    "Upscale Images",
    "Images To Video",
    "Pipeline",
]


TAB_ICONS = {
    "Download": ft.Icons.DOWNLOAD,
    "Panel-By-Panel": ft.Icons.GRID_VIEW,
    "Upscale Images": ft.Icons.HIGH_QUALITY,
    "Images To Video": ft.Icons.MOVIE,
    "Pipeline": ft.Icons.ACCOUNT_TREE,
}

# Every tab in the app bar, in order (Settings is the gear on the right).
ALL_TABS = TAB_NAMES + ["Settings"]

# While a tab is focused with the keyboard, these keys open another tab (like the tabs on a web page): the one before or after it (going around at the ends), or the first or last one.
TAB_LIST_KEYS = ["Arrow Left", "Arrow Right", "Home", "End"]

# Ctrl (⌘ on a Mac) + one of these keys opens the tab: 1 to 5 for the tabs in order, and comma for Settings (like most Mac apps).
SHORTCUT_KEYS = {
    **{tab_name: str(number) for number, tab_name in enumerate(TAB_NAMES, start=1)},
    "Settings": ",",
}


def get_shortcut_label(page, view_name):
    is_mac = getattr(page, "platform", None) == ft.PagePlatform.MACOS
    return ("⌘" if is_mac else "Ctrl+") + SHORTCUT_KEYS[view_name]


class AppBar(ft.Container):
    def __init__(self, parent_gui):
        super().__init__()
        self.parent_gui = parent_gui

        self.bgcolor = Nord.SURFACE
        self.padding = 0
        self.margin = 0

        def get_button(text, icon, show_text):
            return AppBarButton(
                text=text,
                icon=icon,
                shortcut=get_shortcut_label(self.parent_gui.page, text),
                current_view=self.parent_gui.current_view,
                change_view=self.change_view,
                show_text=show_text,
                on_focus_change=self.handle_tab_focus_change,
                running_job_name=self.parent_gui.running_job_name if self.parent_gui.is_job_running else "",
            )

        self.buttons = {
            tab_name: get_button(tab_name, TAB_ICONS[tab_name], show_text=not self.parent_gui.is_narrow)
            for tab_name in TAB_NAMES
        }
        self.buttons["Settings"] = get_button("Settings", ft.Icons.SETTINGS, show_text=False)

        self.content = ft.Row(
            controls=[
                # The tabs go onto another line when the window is too narrow for all of them, like on a web page. When it's very narrow (like a phone), they only show their icons.
                ft.Row(
                    wrap=True,
                    run_spacing=0,
                    spacing=0,
                    expand=True,
                    controls=[self.buttons[tab_name] for tab_name in TAB_NAMES],
                ),
                self.buttons["Settings"],
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=True,
        )

    def handle_tab_focus_change(self, tab_name, is_focused):
        if is_focused:
            self.parent_gui.focused_tab = tab_name
        # Only cleared if it's still this tab (another tab may have been focused already).
        elif self.parent_gui.focused_tab == tab_name:
            self.parent_gui.focused_tab = None

    def move_to_tab(self, key):
        """
        Opens the tab before or after the open one (one of "TAB_LIST_KEYS"), and keeps the keyboard focus on it.
        """
        # The other tabs can't be opened while a job runs.
        if self.parent_gui.is_job_running:
            return

        index = ALL_TABS.index(self.parent_gui.current_view)
        view_name = {
            "Arrow Left": ALL_TABS[index - 1],
            "Arrow Right": ALL_TABS[(index + 1) % len(ALL_TABS)],
            "Home": ALL_TABS[0],
            "End": ALL_TABS[-1],
        }[key]

        self.change_view(view_name)
        # Changing the tab builds a new app bar, so its button for the tab is focused.
        self.parent_gui.app_bar.buttons[view_name].content.focus()

    def change_view(self, view_name):
        # While a job runs, the other tabs can't be opened (clicked, or with a shortcut or the arrow keys).
        if view_name == self.parent_gui.current_view or self.parent_gui.is_job_running:
            return

        self.parent_gui.current_view = view_name

        # Re-rendering the page also builds a new app bar with the right button highlighted.
        self.parent_gui.render_page_based_on_current_view()
        self.parent_gui.page.update()
