import flet as ft
from gui_classes import Nord
from gui_classes.WrappingCheckbox import WrappingCheckbox
from gui_classes.SettingsBase import SettingsBase


def get_settings_group_label(text):
    return ft.Text(text.upper(), size=12, weight=ft.FontWeight.BOLD, color=Nord.TEAL)


def get_help_text(text):
    return ft.Text(text, size=12, color=Nord.TEXT_MUTED)


# What can be pasted in the Download tab, shown before a link is pasted. Each site's name opens the site, to find something to paste.
SOURCES = [
    ("MangaDex", "a series or a chapter", "https://mangadex.org"),
    ("comix.to", "a series or a chapter", "https://comix.to"),
    ("Internet Archive", "a public-domain comic", "https://archive.org/details/comics"),
    ("Any web page", "its images", None),
]


def get_source_name(source, url):
    if not url:
        return ft.Text(source, weight=ft.FontWeight.BOLD, color=Nord.TEXT, width=120)
    # Underlined and light blue, like a link on a web page (Nord's darker blue is hard to read on the background).
    link_style = ft.TextStyle(weight=ft.FontWeight.BOLD, color=Nord.ACCENT, decoration=ft.TextDecoration.UNDERLINE)
    return ft.Text(spans=[ft.TextSpan(source, style=link_style, url=url)], width=120, tooltip=Nord.tooltip(url))

# The sidebar's title for each source (see "get_downloader" for the sources).
SOURCE_TITLES = {
    "MangaDex": "MangaDex",
    "comix.to": "comix.to",
    "the Internet Archive": "Internet Archive",
    "the web page": "Web page",
}


class SettingsMangaDexDownloader(SettingsBase):
    """
    The Download tab's settings. Only the settings for the site of the pasted link are shown (see "show_settings_for"); before a link is pasted, it lists what can be pasted.
    """

    def __init__(self, page, all_mangadex_languages):
        super().__init__()

        self.page = page

        mangadex_languages = all_mangadex_languages["mangadex_languages"]
        mangadex_languages_by_name = all_mangadex_languages[
            "mangadex_languages_by_name"
        ]

        default_language = self.page.client_storage.get("language")

        self.title_text = get_settings_group_label("Paste a link from")

        self.sources_list = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        get_source_name(source, url),
                        ft.Text(what, color=Nord.TEXT, expand=True),
                    ]
                )
                for source, what, url in SOURCES
            ]
            + [get_help_text("Click a site's name to open it and find something to paste. Settings for that site show up here once you paste a link.")],
            spacing=6,
        )

        # Languages only works for a whole manga - not individual chapters. If I pass in the URL for the One Piece Manga with all of the chapters, it will download it in the specified language. But if I pass in a specific URL of Chapter. 567 in English, it will download in English and not the passed in language.
        self.language_dropdown = ft.Dropdown(
            border_radius=0,
            label="Language",
            options=[
                ft.dropdown.Option(language["name"])
                for language in mangadex_languages
            ],
            value=default_language["name"],
            text_style=ft.TextStyle(
                color=Nord.TEXT,  # Text color of the selected item
                size=14,  # Font size
            ),
            fill_color=Nord.SURFACE,  # Background color of the dropdown
            border_color=Nord.BLUE,
            max_menu_height=300,
            on_change=lambda e: self.handle_language_dropdown_change(
                e.data, mangadex_languages_by_name
            ),
            padding=ft.padding.only(top=5),
        )

        # The chapter range is used by MangaDex and comix.to.
        self.start_and_end_chapter_row = self.get_start_and_end_row(
            "Start Chapter", "start_chapter", "End Chapter", "end_chapter", "use_start_and_end_chapters"
        )
        self.chapter_range = ft.Column(
            controls=[
                WrappingCheckbox(
                    label="Only some chapters",
                    value=self.page.client_storage.get("use_start_and_end_chapters"),
                    on_change=lambda e: self.toggle_setting_element_visibility(
                        e, self.start_and_end_chapter_row, "use_start_and_end_chapters"
                    ),
                ),
                self.start_and_end_chapter_row,
            ]
        )

        self.comix_help = get_help_text(
            "Takes the official upload of each chapter when there is one (a checkmark on comix.to), otherwise the most liked one."
        )

        self.preferred_group_textfield = ft.TextField(
            border_radius=0,
            border_color=Nord.BLUE,
            dense=True,
            hint_text="https://mangadex.org/group/...",
            value=self.page.client_storage.get("preferred_group"),
            on_change=lambda e: self.change_setting("preferred_group", e.data),
            visible=self.page.client_storage.get("upload_choice") == "group",
        )
        self.which_upload = ft.Column(
            controls=[
                get_settings_group_label("Which upload"),
                get_help_text("When a chapter was uploaded by several groups."),
                ft.RadioGroup(
                    value=self.page.client_storage.get("upload_choice") or "newest",
                    on_change=self.handle_upload_choice_change,
                    content=ft.Column(
                        controls=[
                            ft.Radio(value="newest", label="The newest"),
                            ft.Radio(value="first", label="The first (often the original group)"),
                            ft.Radio(value="group", label="This group's (or the newest if it skipped one):"),
                        ],
                        spacing=0,
                    ),
                ),
                self.preferred_group_textfield,
            ],
            spacing=4,
        )

        self.start_and_end_page_row = self.get_start_and_end_row(
            "Start Page", "start_page", "End Page", "end_page", "use_start_and_end_pages"
        )
        # Options that are rarely changed are folded away.
        self.more_options = ft.ExpansionTile(
            title=ft.Text("More options", color=Nord.TEXT, size=14),
            tile_padding=ft.padding.all(0),
            controls_padding=ft.padding.only(left=0),
            collapsed_icon_color=Nord.TEXT,
            icon_color=Nord.TEXT,
            controls=[
                WrappingCheckbox(
                    label="Only some pages",
                    value=self.page.client_storage.get("use_start_and_end_pages"),
                    on_change=lambda e: self.toggle_setting_element_visibility(
                        e, self.start_and_end_page_row, "use_start_and_end_pages"
                    ),
                ),
                self.start_and_end_page_row,
                self.get_checkbox("Include Chapter Title in Folder Names", "use_chapter_title"),
                self.get_checkbox("No Group Name", "no_group_name"),
                self.get_checkbox("No Oneshot Chapters", "no_oneshot_chapters"),
                self.get_checkbox("Use Chapter Cover", "use_chapter_cover"),
                self.get_checkbox("Use Volume Cover", "use_volume_cover"),
            ],
        )

        # Every image on the page is saved, unless the user only wants the bigger ones (to leave out icons, avatars and ads).
        self.web_page_min_size_textfield = self.get_number_textfield("Shorter side at least (px)", "web_page_min_size")
        self.web_page_min_size_textfield.visible = bool(self.page.client_storage.get("use_web_page_min_size"))
        self.web_page_options = ft.Column(
            controls=[
                WrappingCheckbox(
                    label="Only keep bigger images",
                    value=self.page.client_storage.get("use_web_page_min_size"),
                    on_change=lambda e: self.toggle_setting_element_visibility(
                        e, self.web_page_min_size_textfield, "use_web_page_min_size"
                    ),
                ),
                self.web_page_min_size_textfield,
            ]
        )
        self.web_page_help = get_help_text(
            "Saves every image on the page, in order. Pages that load their images with JavaScript give none."
        )
        self.internet_archive_help = get_help_text(
            "Downloads the comic, for items marked as public domain only. No settings."
        )

        # Something that's already downloaded (and still has all its pages) isn't downloaded again. This downloads it again. One checkbox for every site, so it always shows the setting as it is.
        self.replace_checkbox = self.get_checkbox("Download again even if already downloaded", "replace_existing_manga")

        # Which controls each site shows ("None" is before a link is pasted).
        self.controls_for_source = {
            None: [self.sources_list],
            "MangaDex": [self.language_dropdown, self.chapter_range, self.which_upload, self.replace_checkbox, self.more_options],
            "comix.to": [self.chapter_range, self.comix_help, self.replace_checkbox],
            "the web page": [self.web_page_help, self.web_page_options, self.replace_checkbox],
            "the Internet Archive": [self.internet_archive_help, self.replace_checkbox],
        }
        # The order of everything in the sidebar. (A control that isn't in this list can't be shown.)
        controls_in_order = [
            self.sources_list, self.language_dropdown, self.chapter_range, self.comix_help, self.web_page_help,
            self.web_page_options, self.internet_archive_help, self.which_upload, self.replace_checkbox, self.more_options,
        ]
        all_controls = sorted(
            {control for controls in self.controls_for_source.values() for control in controls},
            key=controls_in_order.index,
        )

        self.inner_content = [self.title_text, *all_controls]
        self.content = self.get_full_content()
        self.show_settings_for(None)

    def show_settings_for(self, source):
        """
        Show only the settings of "source" (as returned by "get_downloader", or None before a link is pasted).
        """
        shown_controls = self.controls_for_source.get(source, self.controls_for_source[None])
        self.title_text.value = SOURCE_TITLES.get(source, "Paste a link from").upper()

        for control in self.inner_content[1:]:
            control.visible = control in shown_controls

    def get_checkbox(self, label, setting_key):
        return WrappingCheckbox(
            label=label,
            value=self.page.client_storage.get(setting_key),
            on_change=lambda e: self.change_setting(setting_key, e.data),
        )

    def get_start_and_end_row(self, start_label, start_key, end_label, end_key, use_key):
        start_textfield = self.get_number_textfield(start_label, start_key)
        end_textfield = self.get_number_textfield(end_label, end_key)
        start_textfield.expand = True
        end_textfield.expand = True
        return ft.Row(
            controls=[start_textfield, end_textfield],
            visible=bool(self.page.client_storage.get(use_key)),
        )

    def handle_upload_choice_change(self, e):
        self.change_setting("upload_choice", e.control.value)
        self.preferred_group_textfield.visible = e.control.value == "group"
        self.preferred_group_textfield.update()

    def handle_language_dropdown_change(
        self, chosen_language_name, mangadex_languages_by_name
    ):
        language_obj = mangadex_languages_by_name[chosen_language_name]
        self.page.client_storage.set("language", language_obj)
