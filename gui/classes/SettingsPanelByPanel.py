import flet as ft

# from classes.SettingsBase import SettingsBase


class SettingsPanelByPanel(ft.NavigationDrawer):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.bgcolor = "#3b4252"
        self.position = ft.NavigationDrawerPosition.END

        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Text(
                                        "Settings - Panel-by-Panel",
                                        size=14,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                ],
                            ),
                            expand=True,
                            padding=ft.padding.only(bottom=5),
                        ),
                        # ft.Checkbox(
                        #     # Replace existing manga, chapter, or list.
                        #     label="Replace Existing Manga/Chapter",
                        #     value=self.page.client_storage.get(
                        #         "replace_existing_manga"
                        #     ),
                        #     on_change=lambda e: self.change_mangadex_downloader_setting(
                        #         "replace_existing_manga", e.data
                        #     ),
                        # ),
                    ],
                    expand=True,
                ),
                padding=15,
                expand=True,
            )
        ]

    # def change_panel_by_panel_setting(self, setting_key, setting_value):
    #     final_setting_value = setting_value

    #     if setting_value == "true" or setting_value == "false":
    #         final_setting_value = {"true": True, "false": False}.get(
    #             setting_value.lower(), False
    #         )

    #     if setting_key in self.page_num_textfield_dict:
    #         page_num_textfield = self.page_num_textfield_dict[setting_key]

    #         if setting_value and not setting_value.isdigit():
    #             page_num_textfield.error_text = "Please enter a valid page number."
    #         else:
    #             page_num_textfield.error_text = ""
    #             self.page.client_storage.set(setting_key, final_setting_value)

    #         page_num_textfield.update()
    #     else:
    #         self.page.client_storage.set(setting_key, final_setting_value)
