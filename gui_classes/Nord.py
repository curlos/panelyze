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

# Buttons have square corners, like the panels in a manga page.
SQUARE = ft.RoundedRectangleBorder(radius=0)

BUTTON_COLORS = {
    # The button that starts the tab's job (Submit, Download, Run Pipeline).
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
        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD) if kind == "danger" else None,
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
        checkbox_theme=ft.CheckboxTheme(shape=SQUARE),
        tooltip_theme=ft.TooltipTheme(
            decoration=ft.BoxDecoration(bgcolor=SURFACE_HIGH),
            text_style=ft.TextStyle(color=TEXT_BRIGHT),
        ),
    )
