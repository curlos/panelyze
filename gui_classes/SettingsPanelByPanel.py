import flet as ft
from gui_classes.SettingsBase import SettingsBase


class SettingsPanelByPanel(SettingsBase):
    def __init__(self, page):
        super().__init__()
        self.page = page

        # TODO: Need to figure out if I even need this anymore. Check if there's any settings that I can use for panel-by-panel.
