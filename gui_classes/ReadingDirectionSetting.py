import flet as ft
from gui_classes.DropdownTextOptions import DropdownTextOptions

READING_DIRECTIONS = {
    "auto": "Automatic",
    "rtl": "Right to left (Manga)",
    "ltr": "Left to right (Comics)",
    "webtoon": "Webtoon (Vertical scroll)",
    "4koma": "4-koma (Strips)",
}
READING_DIRECTION_DESCRIPTIONS = {
    "4koma": "Strips are read top to bottom, right strip first.",
}


def get_reading_direction_dropdown(page):
    """
    The order panels (and text) are read in. Shared by the Panel-By-Panel and Images To Video settings.
    """
    dropdown = DropdownTextOptions(
        label="Reading Direction",
        options=[
            ft.dropdown.Option(key=direction, text=label)
            for direction, label in READING_DIRECTIONS.items()
        ],
        value=page.client_storage.get("reading_direction") or "auto",
        on_change=lambda e: page.client_storage.set("reading_direction", e.data),
        descriptions=READING_DIRECTION_DESCRIPTIONS,
    )
    # Fit the choices to the box. Otherwise they're as wide as the longest one, which pushes the arrow out of the box.
    dropdown.options_fill_horizontally = True
    return dropdown
