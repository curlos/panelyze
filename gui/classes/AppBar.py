import flet as ft
import sys
from utils import ProcessManager
import pdb


class AppBarButton(ft.TextButton):
    def __init__(self, text, current_view, change_view):
        super().__init__()
        self.text = text
        self.on_click = lambda e: change_view(text)
        self.style = self.get_button_style_by_view(current_view)

    def get_button_style_by_view(self, current_view):
        return ft.ButtonStyle(
            bgcolor=(
                "#5e81ac" if current_view == self.text else ft.Colors.BLUE_GREY_800
            ),
            color="white",
            shape={
                ft.ControlState.HOVERED: ft.RoundedRectangleBorder(radius=0),
                ft.ControlState.DEFAULT: ft.RoundedRectangleBorder(radius=0),
            },
        )


class AppBar(ft.Container):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.current_view = "MangaDex Downloader"

        # Define the buttons
        self.mangadex_button = AppBarButton(
            text="MangaDex Downloader",
            current_view=self.current_view,
            change_view=self.change_view,
        )

        self.panel_button = AppBarButton(
            text="Panel-By-Panel",
            current_view=self.current_view,
            change_view=self.change_view,
        )

        self.bgcolor = "#3b4252"
        self.padding = 0
        self.margin = 0

        self.create()

    def create(self):
        all_mangadex_languages = self.get_all_mangadex_languages()
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

        drawer = ft.NavigationDrawer(
            bgcolor="#3b4252",
            position=ft.NavigationDrawerPosition.END,
            controls=[
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
                                border=ft.border.only(
                                    bottom=ft.border.BorderSide(1, "#5e81ac")
                                ),
                                expand=True,
                                padding=ft.padding.only(bottom=5),
                            ),
                            ft.Checkbox(
                                label="Use Chapter Title",
                                value=self.page.client_storage.get("use_chapter_title"),
                                on_change=lambda e: self.change_mangadex_downloader_setting(
                                    "use_chapter_title", e.data
                                ),
                            ),
                            ft.Checkbox(
                                label="No Group Name",
                                value=self.page.client_storage.get("no_group_name"),
                                on_change=lambda e: self.change_mangadex_downloader_setting(
                                    "no_group_name", e.data
                                ),
                            ),
                            ft.Checkbox(
                                # Replace existing manga, chapter, or list.
                                label="Replace Existing Manga/Chapter",
                                value=self.page.client_storage.get(
                                    "replace_existing_manga"
                                ),
                                on_change=lambda e: self.change_mangadex_downloader_setting(
                                    "replace_existing_manga", e.data
                                ),
                            ),
                            # Languages only works for a whole manga - not individual chapters. If I pass in the URL for the One Piece Manga with all of the chapters, it will download it in the specified language. But if I pass in a specific URL of Chapter. 567 in English, it will download in English and not the passed in language.
                            ft.Dropdown(
                                label="Languages",
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
                        ],
                        expand=True,
                    ),
                    padding=15,
                    expand=True,
                )
            ],
        )

        self.content = ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        self.mangadex_button,
                        # TODO: Bring back after I start working on the "Panel-By-Panel" view.
                        # self.panel_button,
                    ]
                ),
                ft.IconButton(
                    ft.Icons.SETTINGS,
                    on_click=lambda e: self.page.open(drawer),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=4), padding=1
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=True,
        )

    # Function to change the view and update the button styles
    def change_view(self, view_name):
        self.current_view = view_name

        # Update button styles dynamically
        self.mangadex_button.style = self.mangadex_button.get_button_style_by_view(
            self.current_view
        )

        self.panel_button.style = self.panel_button.get_button_style_by_view(
            self.current_view
        )

        self.page.update()  # Refresh the UI

    def change_mangadex_downloader_setting(self, setting_key, setting_value):
        final_setting_value = setting_value

        if setting_value == "true" or setting_value == "false":
            final_setting_value = {"true": True, "false": False}.get(
                setting_value.lower(), False
            )

        # pdb.set_trace()

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

    def get_all_mangadex_languages(self):
        terminal_command = [
            sys.executable,
            "-m",
            "mangadex_downloader",
            "--list-language",
            "-ll",
        ]

        process_manager = ProcessManager()
        all_lines = process_manager.monitor_terminal_output(terminal_command)

        # Filter languages based on the pattern "name / code"
        filtered_languages = [line.strip() for line in all_lines if " / " in line]

        # If "MangaDex Downloader" somehow can't fetch the languages the first time around, then keep trying until we get the languages
        while len(filtered_languages) == 0:
            process_manager = ProcessManager()
            all_lines = process_manager.monitor_terminal_output(terminal_command)
            filtered_languages = [line.strip() for line in all_lines if " / " in line]

        mangadex_languages = [
            {"name": lang.split(" / ")[0], "code": lang.split(" / ")[1]}
            for lang in filtered_languages
        ]

        mangadex_languages_by_name = {lang["name"]: lang for lang in mangadex_languages}

        return {
            "mangadex_languages": mangadex_languages,
            "mangadex_languages_by_name": mangadex_languages_by_name,
        }

    def handle_language_dropdown_change(
        self, chosen_language_name, mangadex_languages_by_name
    ):
        language_obj = mangadex_languages_by_name[chosen_language_name]
        self.page.client_storage.set("language", language_obj)

    def toggle_start_and_end_page_col_visibility(self, e):
        self.start_and_end_page_col.visible = not self.start_and_end_page_col.visible
        self.change_mangadex_downloader_setting("use_start_and_end_pages", e.data)
        self.page.update()

    def toggle_start_and_end_chapter_col_visibility(self, e):
        self.start_and_end_chapter_col.visible = (
            not self.start_and_end_chapter_col.visible
        )
        self.change_mangadex_downloader_setting("use_start_and_end_chapters", e.data)
        self.page.update()

    def get_number_textfield(self, label, client_storage_key):
        return ft.TextField(
            label=label,
            expand=True,
            border_color="#5e81ac",
            keyboard_type=ft.KeyboardType.NUMBER,
            value=self.page.client_storage.get(client_storage_key),
            on_change=lambda e: self.change_mangadex_downloader_setting(
                client_storage_key, e.data
            ),
        )
