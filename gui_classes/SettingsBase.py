import flet as ft
from gui_classes import Nord

from default_settings import DEFAULT_SETTINGS
from utils import is_valid_number


class SettingsBase(ft.Container):
    def __init__(self):
        super().__init__()
        self.bgcolor = Nord.BACKGROUND
        self.expand = True
        self.width = 350

    def change_setting(self, setting_key, setting_value):
        # Checkboxes send "true"/"false" as text.
        if setting_value in ("true", "false"):
            setting_value = setting_value == "true"

        self.page.client_storage.set(setting_key, setting_value)

    def change_number_setting(self, textfield, setting_key, setting_value):
        # Only save valid numbers (or an empty box). Otherwise, show an error under the box.
        if setting_value and not is_valid_number(setting_value):
            textfield.error_text = "Please enter a valid number."
        else:
            textfield.error_text = ""
            self.page.client_storage.set(setting_key, setting_value)

        textfield.update()

    def get_number_textfield(self, label, client_storage_key):
        return ft.TextField(
            border_radius=0,
            label=label,
            border_color=Nord.BLUE,
            keyboard_type=ft.KeyboardType.NUMBER,
            value=self.page.client_storage.get(client_storage_key),
            on_change=lambda e: self.change_number_setting(
                e.control, client_storage_key, e.data
            ),
        )

    def toggle_setting_element_visibility(self, e, view_element, setting_key):
        view_element.visible = not view_element.visible
        self.change_setting(setting_key, e.data)
        view_element.update()
        self.page.update()

    def change_setting_element_visibility(
        self, view_element, elem_visible, setting_key
    ):
        view_element.visible = elem_visible
        self.change_setting(setting_key, elem_visible)
        view_element.update()

    def get_full_content(self):
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(controls=self.inner_content),
                    # More room on the right, so the scrollbar (drawn over this edge) doesn't touch the settings.
                    padding=ft.padding.only(left=10, top=5, right=20),
                )
            ],
            expand=True,
            scroll=ft.ScrollMode.ALWAYS,
        )

    def handle_radio_group_change(self, e, radio_group_dict):
        selected_setting_key = e.control.value

        for val in radio_group_dict.values():
            toggle_elem = val["toggle_elem"]
            setting_key = val["setting_key"]
            is_checked = False

            if setting_key == selected_setting_key:
                is_checked = True

            self.change_setting_element_visibility(toggle_elem, is_checked, setting_key)

    def get_radio_group_init_value(self, radio_group_dict):
        for setting_key in radio_group_dict:
            is_checked = self.page.client_storage.get(setting_key)

            if is_checked:
                return setting_key

    def get_setting_value(self, setting_key):
        """
        The saved value of a setting, or its default (from "default_settings.py") if it was never saved.
        """
        setting_value = self.page.client_storage.get(setting_key)

        if setting_value is None or setting_value == "":
            setting_value = DEFAULT_SETTINGS[setting_key]
            self.page.client_storage.set(setting_key, setting_value)

        return setting_value
