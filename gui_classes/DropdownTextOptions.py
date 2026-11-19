import flet as ft
from gui_classes import Nord


class DropdownTextOptions(ft.Dropdown):
    def __init__(self, label, options, value, on_change):
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
        self.border_color = Nord.BLUE
        self.border_radius = 0
        self.max_menu_height = 300
