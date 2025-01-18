import flet as ft
import pdb


class SettingsBase(ft.Container):
    def __init__(self):
        super().__init__()
        self.bgcolor = "#3b4252"
        self.expand = True
        self.width = 300

    def change_setting(self, setting_key, setting_value):
        final_setting_value = setting_value

        if setting_value == "true" or setting_value == "false":
            final_setting_value = {"true": True, "false": False}.get(
                setting_value.lower(), False
            )

        if (
            hasattr(self, "page_num_textfield_dict")
            and setting_key in self.page_num_textfield_dict
        ):
            page_num_textfield = self.page_num_textfield_dict[setting_key]

            if setting_value and not setting_value.isdigit():
                page_num_textfield.error_text = "Please enter a valid number."
            else:
                page_num_textfield.error_text = ""
                self.page.client_storage.set(setting_key, final_setting_value)

            page_num_textfield.update()
        else:
            self.page.client_storage.set(setting_key, final_setting_value)

    def get_number_textfield(self, label, client_storage_key):
        return ft.TextField(
            label=label,
            border_color="#5e81ac",
            keyboard_type=ft.KeyboardType.NUMBER,
            value=self.page.client_storage.get(client_storage_key),
            on_change=lambda e: self.change_setting(client_storage_key, e.data),
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
                    padding=ft.padding.only(left=10, top=5, right=10),
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
