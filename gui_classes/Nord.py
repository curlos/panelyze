import re

import flet as ft

# The app's colors, from the Nord theme (like the Nord theme in VS Code): https://www.nordtheme.com/docs/colors-and-palettes

# Backgrounds (Nord's "Polar Night"). The main area is the darkest. Bars, panels and boxes are a little lighter, so they stand out from it.
BACKGROUND = "#2e3440"
SURFACE = "#3b4252"
SURFACE_HIGH = "#434c5e"

# Text (Nord's "Snow Storm").
TEXT = "#d8dee9"
TEXT_BRIGHT = "#eceff4"
# Lighter than Nord's own grays, which are too dark to read as text (this one is easy to read on every background above).
TEXT_MUTED = "#a9afba"

# Accents (Nord's "Frost"). ACCENT is the app's main color: the main buttons, the selected tab, checkboxes and anything focused with the keyboard.
TEAL = "#8fbcbb"
ACCENT = "#88c0d0"
BLUE = "#5e81ac"

# Status colors (Nord's "Aurora").
RED = "#bf616a"
# Nord's red is too dark to read as text, so error messages use a lighter red.
RED_TEXT = "#d4a2a9"
# Red buttons are a little darker than Nord's red, with white text, so the text is easy to read (4.5 to 1, the accessibility standard).
RED_BUTTON = "#b25d66"
YELLOW = "#ebcb8b"
GREEN = "#a3be8c"
PURPLE = "#b48ead"
# Nord's purple is too dark to read as small text on the Status view's background (3.6 to 1), so names use a lighter purple (4.8 to 1 there, 5.9 to 1 on the page's background).
PURPLE_TEXT = "#c7aac2"

# Folder and file paths ("Save to: /Users/..."), everywhere in the app, so where things go stands out from the text around them.
PATH = TEAL
# The names of the computer's GPUs (or CPU) in Settings and the Status view, the one the AI models run on and the ones they don't, so they stand out like a path does.
DEVICE = PURPLE_TEXT


def get_highlighted_spans(text, parts, color):
    """
    "text" as spans for a "ft.Text", with each of "parts" in "color" (e.g. the GPUs' names in "The AI models run on the ... Not used: the ...").
    """
    parts = [part for part in parts if part]
    if not parts:
        return [ft.TextSpan(text)]
    # Longest first, so a name that's part of a longer one doesn't split it.
    pattern = "|".join(re.escape(part) for part in sorted(parts, key=len, reverse=True))
    return [
        ft.TextSpan(piece, style=ft.TextStyle(color=color) if piece in parts else None)
        for piece in re.split(f"({pattern})", text)
        if piece
    ]


# Buttons have square corners, like the panels in a manga page.
SQUARE = ft.RoundedRectangleBorder(radius=0)

BUTTON_COLORS = {
    # The button that starts the tab's job (Split Into Panels, Upscale, Create Video, Download, Run Pipeline).
    "primary": (ACCENT, BACKGROUND),
    "secondary": (SURFACE_HIGH, TEXT),
    # Buttons that stop or undo something (Cancel, Reset All Settings).
    "danger": (RED_BUTTON, "#ffffff"),
}


def get_focus_border():
    """
    A light border around a button while it's focused with the keyboard (Tab key), so it's easy to see which button Enter or Space will press.
    """
    return {
        ft.ControlState.FOCUSED: ft.BorderSide(2, TEXT_BRIGHT),
        ft.ControlState.DEFAULT: ft.BorderSide(0, ft.Colors.TRANSPARENT),
    }


def button_style(kind="secondary"):
    """
    The style of a filled button: "primary", "secondary" or "danger". Each button needs its own new style: Flet puts a button's colors into its style, so a shared one would give every button the same colors.
    """
    bgcolor, color = BUTTON_COLORS[kind]
    return ft.ButtonStyle(
        bgcolor=bgcolor,
        color=color,
        shape=SQUARE,
        side=get_focus_border(),
        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD)
        if kind == "danger"
        else None,
    )


def icon_button_style():
    """
    The style of a button that's only an icon (like the folder button). Square, with the focus border.
    """
    return ft.ButtonStyle(shape=SQUARE, side=get_focus_border())


def get_theme():
    """
    The colors Flet uses for anything that doesn't set its own (checkboxes, text boxes, sliders, ...). Without this, Flet makes up its own colors, which aren't Nord.
    """
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ACCENT,
            on_primary=BACKGROUND,
            secondary=BLUE,
            on_secondary=TEXT_BRIGHT,
            error=RED_TEXT,
            on_error=BACKGROUND,
            surface=SURFACE,
            on_surface=TEXT,
            on_surface_variant=TEXT,
            surface_container_low=SURFACE_HIGH,
            surface_container_high=SURFACE_HIGH,
            outline=BLUE,
        ),
        # The background of open dropdown menus (otherwise Flet's near-black).
        canvas_color=SURFACE_HIGH,
        # No lighter box behind a dropdown (and the grey line under it) while it has the focus after a choice is picked. Dropdowns ignore their own "focus_color".
        focus_color=ft.Colors.TRANSPARENT,
        checkbox_theme=ft.CheckboxTheme(
            shape=SQUARE,
            # Its own focus color, since the theme's is turned off above (for the dropdowns).
            overlay_color={
                ft.ControlState.FOCUSED: ft.Colors.with_opacity(0.24, ACCENT)
            },
        ),
        # Dialogs (e.g. "Delete Pipeline?") a shade lighter than the page, like the cards, so they stand out over the darkened page (otherwise Flet's near-black).
        dialog_theme=ft.DialogTheme(
            bgcolor=SURFACE_HIGH, shape=ft.RoundedRectangleBorder(radius=6)
        ),
    )


def tooltip(message):
    """
    A tooltip that looks like it's on top of the page: a box with a border and a shadow, just under what it's about. Use it for every tooltip. (The theme's plain lighter box was almost the page's color, so tooltips looked like text floating over the page.) Flutter's tooltips can't have an arrow pointing at the control.
    """
    return ft.Tooltip(
        message=message,
        bgcolor=SURFACE_HIGH,
        border=ft.border.all(1, ACCENT),
        border_radius=4,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
        shadow=[
            ft.BoxShadow(
                blur_radius=10,
                spread_radius=1,
                color=ft.Colors.with_opacity(0.6, ft.Colors.BLACK),
            )
        ],
        text_style=ft.TextStyle(color=TEXT_BRIGHT, size=13),
        prefer_below=True,
        vertical_offset=18,
    )
