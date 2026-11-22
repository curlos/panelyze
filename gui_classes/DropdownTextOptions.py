import flet as ft
from gui_classes import Nord


def add_descriptions(dropdown, descriptions):
    """
    Shows a short grey line under the dropdown that explains the selected choice ("descriptions" has one for each choice's key), so the choices themselves can have short names that fit in the box.
    """
    change_setting = dropdown.on_change

    def show_description(e=None):
        dropdown.helper_text = descriptions.get(dropdown.value, "")
        dropdown.helper_max_lines = 3
        dropdown.helper_style = ft.TextStyle(size=12, color=Nord.TEXT_MUTED)
        if dropdown.page:
            dropdown.update()

    def handle_change(e):
        show_description()
        if change_setting:
            change_setting(e)

    dropdown.on_change = handle_change
    show_description()
    return dropdown


class DropdownTextOptions(ft.Dropdown):
    def __init__(self, label, options, value, on_change, descriptions=None):
        super().__init__()
        self.label = label
        self.options = options
        self.value = value
        self.on_change = on_change

        self.text_style = ft.TextStyle(
            color=Nord.TEXT,  # Text color of the selected item
            size=14,  # Font size
        )
        self.fill_color = Nord.SURFACE  # Background color of the dropdown
        # No other color when the mouse is over it (Flutter paints one over the box and the grey line under it otherwise).
        self.hover_color = ft.Colors.TRANSPARENT
        self.border_color = Nord.BLUE
        self.border_radius = 0
        self.max_menu_height = 300
        if descriptions:
            add_descriptions(self, descriptions)
