import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
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
                preview_parts = [f"{k}: {v}" for k, v in extracted.items()]
                self.preview_lbl.setText("Extracted: " + ", ".join(preview_parts))
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
