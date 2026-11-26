import weakref

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


# Every Reading Direction dropdown and its page, so a choice in one tab shows in the other too (only in the same window: in web mode, each browser tab has its own page and settings).
_reading_direction_dropdowns = weakref.WeakKeyDictionary()


def save_reading_direction(page, changed_dropdown, reading_direction):
    page.client_storage.set("reading_direction", reading_direction)
    for dropdown, dropdown_page in list(_reading_direction_dropdowns.items()):
        if dropdown is not changed_dropdown and dropdown_page is page:
            dropdown.value = reading_direction
            dropdown.helper_text = READING_DIRECTION_DESCRIPTIONS.get(
                reading_direction, ""
            )
            # A tab that isn't on screen can't be updated. It shows the new value when it's opened.
            try:
                dropdown.update()
            except Exception:
                pass


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
        on_change=lambda e: save_reading_direction(page, dropdown, e.data),
        descriptions=READING_DIRECTION_DESCRIPTIONS,
    )
    # Fit the choices to the box. Otherwise they're as wide as the longest one, which pushes the arrow out of the box.
    dropdown.options_fill_horizontally = True
    _reading_direction_dropdowns[dropdown] = page
    return dropdown
