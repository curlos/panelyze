import flet as ft
from gui_classes import Nord


class WrappingCheckbox(ft.Row):
    """
    A checkbox whose label goes onto more lines when it doesn't fit, instead of being cut off (the label of Flet's own checkbox can't wrap). Used like "ft.Checkbox": "label", "value", "on_change" and "label_style".
    """

    def __init__(self, label, value=False, on_change=None, label_style=None, icon=None):
        super().__init__(vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        self.on_checkbox_change = on_change
        self.checkbox = ft.Checkbox(value=value, on_change=on_change)

        self.controls = [
            self.checkbox,
            # An optional icon between the checkbox and the label.
            *([ft.Icon(icon, size=18, color=Nord.TEXT), ft.Container(width=6)] if icon else []),
            # Clicking the label toggles the checkbox, the same as with a normal one.
            ft.Container(
                content=ft.Text(label, style=label_style),
                expand=True,
                on_click=self.handle_label_click,
            ),
        ]

    @property
    def value(self):
        return self.checkbox.value

    @value.setter
    def value(self, value):
        self.checkbox.value = value

    def handle_label_click(self, e):
        self.checkbox.value = not self.checkbox.value

        try:
            self.checkbox.update()
        except Exception:
            pass

        if self.on_checkbox_change:
            # Checkboxes send "true" or "false" as text.
            self.on_checkbox_change(
                ft.ControlEvent(
                    target=self.checkbox.uid or "",
                    name="change",
                    data=str(self.checkbox.value).lower(),
                    control=self.checkbox,
                    page=self.checkbox.page,
                )
            )
