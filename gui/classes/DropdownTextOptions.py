import flet as ft


class DropdownTextOptions(ft.Dropdown):
    def __init__(self, label, options, value, on_change):
        super().__init__()
        self.label = label
        self.options = options
        self.value = value
        self.on_change = on_change

        self.text_style = ft.TextStyle(
            color="white",  # Text color of the selected item
            size=14,  # Font size
        )
        self.fill_color = "#3b4252"  # Background color of the dropdown
        self.border_color = "#5e81ac"
        self.max_menu_height = 300
