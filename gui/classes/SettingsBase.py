import flet as ft


class SettingsBase:
    def change_setting(self, setting_key, setting_value):
        final_setting_value = setting_value

        if setting_value == "true" or setting_value == "false":
            final_setting_value = {"true": True, "false": False}.get(
                setting_value.lower(), False
            )

        if setting_key in self.page_num_textfield_dict:
            page_num_textfield = self.page_num_textfield_dict[setting_key]

            if setting_value and not setting_value.isdigit():
                page_num_textfield.error_text = "Please enter a valid page number."
            else:
                page_num_textfield.error_text = ""
                self.page.client_storage.set(setting_key, final_setting_value)

            page_num_textfield.update()
        else:
            self.page.client_storage.set(setting_key, final_setting_value)

    def get_number_textfield(self, label, client_storage_key):
        return ft.TextField(
            label=label,
            expand=True,
            border_color="#5e81ac",
            keyboard_type=ft.KeyboardType.NUMBER,
            value=self.page.client_storage.get(client_storage_key),
            on_change=lambda e: self.change_setting(client_storage_key, e.data),
        )
