import flet as ft
from gui_classes.SettingsBase import SettingsBase
from gui_classes.DropdownTextOptions import DropdownTextOptions


class HighlightTextBoxesInImages(SettingsBase):
    def __init__(self, page):
        super().__init__()
        self.page = page

        self.colors = {
            "transparent": "none",
            "#ef4444": "red",
            "#f97316": "orange",
            "#f59e0b": "amber",
            "#eab308": "yellow",
            "#84cc16": "lime",
            "#22c55e": "green",
            "#10b981": "emerald",
            "#14b8a6": "teal",
            "#06b6d4": "cyan",
            "#0ea5e9": "sky",
            "#3b82f6": "blue",
            "#6366f1": "indigo",
            "#8b5cf6": "violet",
            "#a855f7": "purple",
            "#d946ef": "fuchsia",
            "#ec4899": "pink",
            "#f43f5e": "rose",
        }

        self.border_style_list = ["solid", "dotted", "dashed", "dashdot"]

        default_images_to_video_text_box_border_width = int(
            float(self.get_setting_value("images_to_video_text_box_border_width", 1))
        )
        default_images_to_video_text_box_padding = int(
            float(self.get_setting_value("images_to_video_text_box_padding", 15))
        )
        default_images_to_video_text_box_background_color_opacity = float(
            self.get_setting_value(
                "images_to_video_text_box_background_color_opacity", 1
            )
        )
        default_images_to_video_text_box_border_color_opacity = float(
            self.get_setting_value("images_to_video_text_box_border_color_opacity", 1)
        )
        default_images_to_video_text_box_border_style = self.get_setting_value(
            "images_to_video_text_box_border_style", "solid"
        )
        default_images_to_video_text_box_border_color = self.get_setting_value(
            "images_to_video_text_box_border_color", "#ef4444"
        )
        default_images_to_video_text_box_background_color = self.get_setting_value(
            "images_to_video_text_box_background_color",
            "#eab308",  # Yellow is the default color.
        )

        self.text_box_border_color_dropdown = DropdownTextOptions(
            label="Border Color",
            options=[
                ft.dropdown.Option(
                    key=hex_code,
                    content=ft.Row(
                        controls=[
                            ft.Icon(name=ft.Icons.CIRCLE, color=hex_code),
                            ft.Text(
                                value=name,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.VerticalAlignment.CENTER,
                        spacing=5,
                    ),
                )
                for hex_code, name in self.colors.items()
            ],
            value=default_images_to_video_text_box_border_color,
            on_change=lambda e: self.change_setting(
                "images_to_video_text_box_border_color", e.data
            ),
        )

        self.text_box_border_style_dropdown = DropdownTextOptions(
            label="Border Style",
            options=[
                ft.dropdown.Option(border_style)
                for border_style in self.border_style_list
            ],
            value=default_images_to_video_text_box_border_style,
            on_change=lambda e: self.change_setting(
                "images_to_video_text_box_border_style", e.data
            ),
        )

        self.text_box_background_color_dropdown = DropdownTextOptions(
            label="Background Color",
            options=[
                ft.dropdown.Option(
                    key=hex_code,
                    content=ft.Row(
                        controls=[
                            ft.Icon(name=ft.Icons.CIRCLE, color=hex_code),
                            ft.Text(
                                value=name,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.VerticalAlignment.CENTER,
                        spacing=5,
                    ),
                )
                for hex_code, name in self.colors.items()
            ],
            value=default_images_to_video_text_box_background_color,
            on_change=lambda e: self.change_setting(
                "images_to_video_text_box_background_color", e.data
            ),
        )

        self.highlight_text_boxes_in_images_col = ft.Container(
            content=ft.Column(
                controls=[
                    self.text_box_border_color_dropdown,
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Border Color Opacity:"),
                                ft.Slider(
                                    value=default_images_to_video_text_box_border_color_opacity,
                                    min=0,
                                    max=1,
                                    divisions=10,
                                    round=1,
                                    label="{value}",
                                    on_change_end=lambda e: self.change_setting(
                                        "images_to_video_text_box_border_color_opacity",
                                        e.data,
                                    ),
                                    height=20,
                                ),
                                ft.Text("Border Width:"),
                                ft.Container(
                                    content=ft.Slider(
                                        value=default_images_to_video_text_box_border_width,
                                        min=0,
                                        max=5,
                                        divisions=5,
                                        round=0,
                                        label="{value}",
                                        on_change_end=lambda e: self.change_setting(
                                            "images_to_video_text_box_border_width",
                                            e.data,
                                        ),
                                        height=20,
                                    ),
                                    padding=ft.padding.only(bottom=10),
                                ),
                                self.text_box_border_style_dropdown,
                            ]
                        ),
                        padding=ft.padding.only(left=20, bottom=15),
                    ),
                    self.text_box_background_color_dropdown,
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Text("Background Color Opacity:"),
                                ft.Slider(
                                    value=default_images_to_video_text_box_background_color_opacity,
                                    min=0,
                                    max=1,
                                    divisions=10,
                                    round=1,
                                    label="{value}",
                                    on_change_end=lambda e: self.change_setting(
                                        "images_to_video_text_box_background_color_opacity",
                                        e.data,
                                    ),
                                    height=20,
                                ),
                            ]
                        ),
                        padding=ft.padding.only(left=20),
                    ),
                    ft.Text("Padding:"),
                    ft.Slider(
                        value=default_images_to_video_text_box_padding,
                        min=0,
                        max=30,
                        divisions=6,
                        round=0,
                        label="{value}",
                        on_change_end=lambda e: self.change_setting(
                            "images_to_video_text_box_padding", e.data
                        ),
                        height=20,
                    ),
                    ft.Checkbox(
                        label='Clean up "images-with-highlighted-text-boxes" folder',
                        label_style=ft.TextStyle(size=10),
                        value=self.page.client_storage.get(
                            "clean_up_images_with_highlighted_text_boxes_folder"
                        ),
                        on_change=lambda e: self.change_setting(
                            "clean_up_images_with_highlighted_text_boxes_folder", e.data
                        ),
                    ),
                ],
            ),
            padding=ft.padding.only(left=30),
            visible=bool(
                self.page.client_storage.get("highlight_text_boxes_in_images")
            ),
        )

        self.content = ft.Column(
            controls=[
                ft.ExpansionTile(
                    title=ft.Checkbox(
                        label="Highlight Text Boxes In Images",
                        label_style=ft.TextStyle(size=14),
                        value=self.page.client_storage.get(
                            "highlight_text_boxes_in_images"
                        ),
                        on_change=lambda e: self.toggle_setting_element_visibility(
                            e,
                            self.highlight_text_boxes_in_images_col,
                            "highlight_text_boxes_in_images",
                        ),
                    ),
                    maintain_state=True,
                    text_color="white",
                    controls=[self.highlight_text_boxes_in_images_col],
                    tile_padding=0,
                    controls_padding=ft.padding.only(top=5, bottom=10),
                ),
            ]
        )
