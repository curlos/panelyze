import flet as ft
from classes.SettingsBase import SettingsBase


class SettingsMangaDexDownloader(ft.NavigationDrawer):
    def __init__(self, page, all_mangadex_languages):
        super().__init__()

        self.page = page

        mangadex_languages = all_mangadex_languages["mangadex_languages"]
        mangadex_languages_by_name = all_mangadex_languages[
            "mangadex_languages_by_name"
        ]

        if not self.page.client_storage.get("language"):
            self.page.client_storage.set("language", {"name": "English", "code": "en"})

        default_language = self.page.client_storage.get("language")

        self.start_page_textfield = self.get_number_textfield(
            "Start Page", "start_page"
        )
        self.end_page_textfield = self.get_number_textfield("End Page", "end_page")
        self.start_and_end_page_col = ft.Column(
            controls=[
                self.start_page_textfield,
                self.end_page_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_start_and_end_pages")),
        )

        self.start_chapter_textfield = self.get_number_textfield(
            "Start Chapter", "start_chapter"
        )
        self.end_chapter_textfield = self.get_number_textfield(
            "End Chapter", "end_chapter"
        )
        self.start_and_end_chapter_col = ft.Column(
            controls=[
                self.start_chapter_textfield,
                self.end_chapter_textfield,
            ],
            visible=bool(self.page.client_storage.get("use_start_and_end_chapters")),
        )

        self.page_num_textfield_dict = {
            "start_page": self.start_page_textfield,
            "end_page": self.end_page_textfield,
            "start_chapter": self.start_chapter_textfield,
            "end_chapter": self.end_chapter_textfield,
        }

        self.settings_base = SettingsBase(self.page, self.page_num_textfield_dict)
        self.change_setting = self.settings_base.change_setting

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
                                        "Settings - MangaDex Downloader",
                                        size=14,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                ],
                            ),
                            expand=True,
                            padding=ft.padding.only(bottom=5),
                        ),
                        # Languages only works for a whole manga - not individual chapters. If I pass in the URL for the One Piece Manga with all of the chapters, it will download it in the specified language. But if I pass in a specific URL of Chapter. 567 in English, it will download in English and not the passed in language.
                        ft.Dropdown(
                            label="Language",
                            options=[
                                ft.dropdown.Option(language["name"])
                                for language in mangadex_languages
                            ],
                            value=default_language["name"],
                            text_style=ft.TextStyle(
                                color="white",  # Text color of the selected item
                                size=14,  # Font size
                            ),
                            fill_color="#3b4252",  # Background color of the dropdown
                            border_color="#5e81ac",
                            max_menu_height=300,
                            on_change=lambda e: self.handle_language_dropdown_change(
                                e.data, mangadex_languages_by_name
                            ),
                        ),
                        ft.Checkbox(
                            label="Use Start and End Pages",
                            value=self.page.client_storage.get(
                                "use_start_and_end_pages"
                            ),
                            on_change=lambda e: self.toggle_start_and_end_page_col_visibility(
                                e
                            ),
                        ),
                        self.start_and_end_page_col,
                        ft.Checkbox(
                            label="Use Start and End Chapters",
                            value=self.page.client_storage.get(
                                "use_start_and_end_chapters"
                            ),
                            on_change=lambda e: self.toggle_start_and_end_chapter_col_visibility(
                                e
                            ),
                        ),
                        self.start_and_end_chapter_col,
                        ft.Checkbox(
                            label="Use Chapter Title",
                            value=self.page.client_storage.get("use_chapter_title"),
                            on_change=lambda e: self.change_setting(
                                "use_chapter_title", e.data
                            ),
                        ),
                        ft.Checkbox(
                            label="No Group Name",
                            value=self.page.client_storage.get("no_group_name"),
                            on_change=lambda e: self.change_setting(
                                "no_group_name", e.data
                            ),
                        ),
                        ft.Checkbox(
                            # Replace existing manga, chapter, or list.
                            label="Replace Existing Manga/Chapter",
                            value=self.page.client_storage.get(
                                "replace_existing_manga"
                            ),
                            on_change=lambda e: self.change_setting(
                                "replace_existing_manga", e.data
                            ),
                        ),
                        ft.Checkbox(
                            # Replace existing manga, chapter, or list.
                            label="No Oneshot Chapters",
                            value=self.page.client_storage.get("no_oneshot_chapters"),
                            on_change=lambda e: self.change_setting(
                                "no_oneshot_chapters", e.data
                            ),
                        ),
                        ft.Checkbox(
                            label="Use Chapter Cover",
                            value=self.page.client_storage.get("use_chapter_cover"),
                            on_change=lambda e: self.change_setting(
                                "use_chapter_cover", e.data
                            ),
                        ),
                        ft.Checkbox(
                            label="Use Volume Cover",
                            value=self.page.client_storage.get("use_volume_cover"),
                            on_change=lambda e: self.change_setting(
                                "use_volume_cover", e.data
                            ),
                        ),
                    ],
                    expand=True,
                ),
                padding=15,
                expand=True,
            )
        ]

    def handle_language_dropdown_change(
        self, chosen_language_name, mangadex_languages_by_name
    ):
        language_obj = mangadex_languages_by_name[chosen_language_name]
        self.page.client_storage.set("language", language_obj)

    def toggle_start_and_end_page_col_visibility(self, e):
        self.start_and_end_page_col.visible = not self.start_and_end_page_col.visible
        self.change_setting("use_start_and_end_pages", e.data)
        self.page.update()

    def toggle_start_and_end_chapter_col_visibility(self, e):
        self.start_and_end_chapter_col.visible = (
            not self.start_and_end_chapter_col.visible
        )
        self.change_setting("use_start_and_end_chapters", e.data)
        self.page.update()

    def get_number_textfield(self, label, client_storage_key):
        return ft.TextField(
            label=label,
            expand=True,
            border_color="#5e81ac",
            keyboard_type=ft.KeyboardType.NUMBER,
            value=self.page.client_storage.get(client_storage_key),
            on_change=lambda e: self.change_setting(client_storage_key, e.data),
        )
