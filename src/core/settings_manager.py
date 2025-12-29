import os
from PySide6.QtCore import QSettings

class SettingsManager:
    """
    Handles persistent application settings using QSettings.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._settings = QSettings("Nexus", "MusicTagDownloader")
        return cls._instance

    @property
    def save_path(self) -> str:
        default = os.path.join(os.path.expanduser("~"), "Downloads")
        return self._settings.value("downloader/save_path", default)

    @save_path.setter
    def save_path(self, value: str):
        self._settings.setValue("downloader/save_path", value)

    @property
    def bitrate(self) -> str:
        return self._settings.value("downloader/bitrate", "320")

    @bitrate.setter
    def bitrate(self, value: str):
        self._settings.setValue("downloader/bitrate", value)

    @property
    def discogs_token(self) -> str:
        return self._settings.value("discogs/api_token", "")

    @discogs_token.setter
    def discogs_token(self, value: str):
        self._settings.setValue("discogs/api_token", value)

    @property
    def column_metadata_library(self) -> list:
        val = self._settings.value("ui/library_column_state", None)
        if val is not None: return val
        return [
            {'name': 'Filename', 'visible': True},
            {'name': 'Title', 'visible': True},
            {'name': 'Artist', 'visible': True},
            {'name': 'Album', 'visible': True},
            {'name': 'Year', 'visible': True},
            {'name': 'Track', 'visible': True},
            {'name': 'Genre', 'visible': True},
            {'name': 'Album Artist', 'visible': True},
            {'name': 'Composer', 'visible': True},
            {'name': 'Disc', 'visible': True},
            {'name': 'Compilation', 'visible': True},
        ]

    @column_metadata_library.setter
    def column_metadata_library(self, value: list):
        self._settings.setValue("ui/library_column_state", value)

    @property
    def column_metadata_downloads(self) -> list:
        val = self._settings.value("ui/downloads_column_state", None)
        if val is not None: return val
        return [
            {'name': 'Status', 'visible': True},
            {'name': 'Title', 'visible': True},
            {'name': 'Artist', 'visible': True},
            {'name': 'Album', 'visible': True},
            {'name': 'Year', 'visible': True},
            {'name': 'Track', 'visible': True},
            {'name': 'Genre', 'visible': True},
            {'name': 'Album Artist', 'visible': True},
            {'name': 'Composer', 'visible': True},
            {'name': 'Disc', 'visible': True},
            {'name': 'Compilation', 'visible': True},
        ]

    @column_metadata_downloads.setter
    def column_metadata_downloads(self, value: list):
        self._settings.setValue("ui/downloads_column_state", value)

    @property
    def visible_columns_library(self) -> list:
        return [c['name'] for c in self.column_metadata_library if c['visible']]

    @property
    def visible_columns_downloads(self) -> list:
        return [c['name'] for c in self.column_metadata_downloads if c['visible']]
