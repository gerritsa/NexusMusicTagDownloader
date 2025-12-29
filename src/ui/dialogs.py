import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
                                 QComboBox, QPushButton, QSpacerItem, QSizePolicy, QFrame, QMessageBox)
from PySide6.QtCore import Qt, Signal

class ConvertDialog(QDialog):
    def __init__(self, mode="tag_to_filename", initial_track_info=None, parent=None):
        super().__init__(parent)
        self.mode = mode # "tag_to_filename" or "filename_to_tag"
        self.track_info = initial_track_info or {}
        
        self.setWindowTitle("Tag - Filename" if mode == "tag_to_filename" else "Filename - Tag")
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header
        header_lbl = QLabel("Select format string")
        font = header_lbl.font()
        font.setBold(True)
        header_lbl.setFont(font)
        layout.addWidget(header_lbl)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # Format Input Row
        fmt_layout = QVBoxLayout()
        fmt_layout.addWidget(QLabel("Format string:"))
        
        self.fmt_combo = QComboBox()
        self.fmt_combo.setEditable(True)
        # Default formats
        defaults = ["%artist% - %title%", "%track% - %title%", "%artist% - %album% - %track% - %title%"]
        self.fmt_combo.addItems(defaults)
        
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(self.fmt_combo)
        
        fmt_layout.addLayout(fmt_row)
        layout.addLayout(fmt_layout)
        
        # Preview
        self.preview_lbl = QLabel("Preview:")
        layout.addWidget(self.preview_lbl)
        
        layout.addSpacing(10)
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("OK")
        self.btn_ok.setDefault(True)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_help = QPushButton("Help")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_help)
        layout.addLayout(btn_layout)
        
        # Connections
        self.fmt_combo.editTextChanged.connect(self._update_preview)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_help.clicked.connect(self._show_help)
        
        self._update_preview()

    def get_format(self):
        return self.fmt_combo.currentText()

    def _update_preview(self):
        from ..core.metadata_manager import MetadataManager
        fmt = self.fmt_combo.currentText()
        
        if self.mode == "tag_to_filename":
            preview = MetadataManager.resolve_format(fmt, self.track_info)
            # Add extension from original file if available
            orig = self.track_info.get('filepath', '')
            ext = os.path.splitext(orig)[1]
            self.preview_lbl.setText(f"{preview}{ext}")
        else:
            # Filename to Tag
            fname = os.path.basename(self.track_info.get('filepath', 'Unknown.mp3'))
            extracted = MetadataManager.parse_filename(fmt, fname)
            if extracted:
                lines = ["Extracted data:"]
                for k, v in extracted.items():
                    # Capitalize key for display (e.g. 'artist' -> 'Artist')
                    display_key = k.capitalize()
                    lines.append(f"{display_key}: {v}")
                self.preview_lbl.setText("\n".join(lines))
            else:
                self.preview_lbl.setText("No match found for this format.")

    def _show_help(self):
        help_text = (
            "Available Placeholders:\n"
            "%artist% - Artist Name\n"
            "%title% - Song Title\n"
            "%album% - Album Name\n"
            "%year% - Year\n"
            "%track% - Track Number\n"
            "%genre% - Genre"
        )
        QMessageBox.information(self, "Placeholders Help", help_text)

from PySide6.QtWidgets import QGroupBox, QFormLayout, QFileDialog

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        from ..core.settings_manager import SettingsManager
        self.settings = SettingsManager()
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Downloader Group
        dl_group = QGroupBox("Downloader")
        dl_layout = QFormLayout(dl_group)
        
        self.path_input = QLineEdit(self.settings.save_path)
        path_btn = QPushButton("Browse...")
        path_btn.clicked.connect(self._on_browse_path)
        
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_input)
        path_row.addWidget(path_btn)
        dl_layout.addRow("Save Location:", path_row)
        
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["128", "192", "256", "320"])
        self.bitrate_combo.setCurrentText(self.settings.bitrate)
        dl_layout.addRow("Bitrate (kbps):", self.bitrate_combo)
        
        layout.addWidget(dl_group)
        
        # Discogs Group
        discogs_group = QGroupBox("Discogs")
        discogs_layout = QFormLayout(discogs_group)
        
        self.discogs_token_input = QLineEdit(self.settings.discogs_token)
        self.discogs_token_input.setPlaceholderText("Paste your Discogs API token here")
        self.discogs_token_input.setEchoMode(QLineEdit.Password)
        
        token_btn = QPushButton("Get Token")
        token_btn.clicked.connect(self._on_get_discogs_token)
        
        token_row = QHBoxLayout()
        token_row.addWidget(self.discogs_token_input)
        token_row.addWidget(token_btn)
        discogs_layout.addRow("API Token:", token_row)
        
        layout.addWidget(discogs_group)
        
        layout.addStretch()
        
        # Buttons
        btns = QHBoxLayout()
        ok_btn = QPushButton("Save")
        ok_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def _on_browse_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Save Location", self.path_input.text())
        if directory:
            self.path_input.setText(directory)

    def _on_save(self):
        self.settings.save_path = self.path_input.text()
        self.settings.bitrate = self.bitrate_combo.currentText()
        self.settings.discogs_token = self.discogs_token_input.text()
        self.accept()
    
    def _on_get_discogs_token(self):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl("https://www.discogs.com/settings/developers"))

from PySide6.QtWidgets import QListWidget, QListWidgetItem

class ColumnDialog(QDialog):
    def __init__(self, title, all_columns, visible_columns, parent=None):
        from PySide6.QtWidgets import QAbstractItemView
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select columns to display:"))
        
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        
        for col in all_columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled)
            check_state = Qt.Checked if col in visible_columns else Qt.Unchecked
            item.setCheckState(check_state)
            self.list_widget.addItem(item)
            
        layout.addWidget(self.list_widget)

        tip = QLabel("<i>Tip: Drag to reorder columns</i>")
        tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip)
        
        btns = QHBoxLayout()
        ok_btn = QPushButton("Apply")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    def get_column_state(self):
        """Returns ordered list of {'name', 'visible'} dicts."""
        state = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            state.append({
                'name': item.text(),
                'visible': item.checkState() == Qt.Checked
            })
        return state
