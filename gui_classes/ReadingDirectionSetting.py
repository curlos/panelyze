import flet as ft
from gui_classes.DropdownTextOptions import DropdownTextOptions

READING_DIRECTIONS = {
    "rtl": "Right to left (Manga)",
    "ltr": "Left to right (Comics)",
}


def get_reading_direction_dropdown(page):
    """
    The order panels (and text) are read in. Shared by the Panel-By-Panel and Images To Video settings.
    """
    return DropdownTextOptions(
        label="Reading Direction",
        options=[
            ft.dropdown.Option(key=direction, text=label)
            for direction, label in READING_DIRECTIONS.items()
        ],
        value=page.client_storage.get("reading_direction") or "rtl",
        on_change=lambda e: page.client_storage.set("reading_direction", e.data),
    )
