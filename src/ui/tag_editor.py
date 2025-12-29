from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QLineEdit, QComboBox, QCheckBox, QFrame, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap

class DropZone(QLabel):
    file_dropped = Signal(str)
    cover_removed = Signal()
    cover_pasted = Signal(str) # Emits temporary file path

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText("\n\nDrag Cover Art Here\n\n")
        self.setAcceptDrops(True)
        # Force a perfect square (280 sidebar width - 20 margins = 260)
        self.setFixedSize(260, 260)
        # Mp3Tag style: Inset-like border, white/gray background
        self.setStyleSheet("""
            QLabel {
                border: 1px solid #a0a0a0;
                background-color: #f0f0f0;
                color: #888;
            }
        """)
        self.setScaledContents(False) # We handle scaling manually
        
        # Store original pixmap to rescale on resize
        self._original_pixmap = None

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu, QApplication
        menu = QMenu(self)
        copy_action = menu.addAction("Copy cover")
        paste_action = menu.addAction("Paste cover")
        menu.addSeparator()
        remove_action = menu.addAction("Remove cover")
        
        # Enable/Disable based on state
        copy_action.setEnabled(self._original_pixmap is not None)
        clipboard = QApplication.clipboard()
        paste_action.setEnabled(clipboard.mimeData().hasImage())
        
        action = menu.exec(event.globalPos())
        if action == remove_action:
            self.set_image(None)
            self.cover_removed.emit()
        elif action == copy_action:
            if self._original_pixmap:
                clipboard.setPixmap(self._original_pixmap)
        elif action == paste_action:
            pixmap = clipboard.pixmap()
            if not pixmap.isNull():
                import tempfile
                import os
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, "nexus_pasted_cover.png")
                pixmap.save(temp_path, "PNG")
                self.current_cover_path = temp_path # Will be set in set_image too
                self.set_image(temp_path)
                self.cover_pasted.emit(temp_path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(('.jpg', '.jpeg', '.png')):
                self.file_dropped.emit(path)
                event.acceptProposedAction()

    def set_image(self, path_or_pixmap):
        if not path_or_pixmap:
            self._original_pixmap = None
            self.setPixmap(QPixmap())
            self.setText("\n\nDrag Cover Art Here\n\n")
            self.setStyleSheet("""
                QLabel {
                    border: 1px solid #a0a0a0;
                    background-color: #f0f0f0;
                    color: #888;
                }
            """)
        else:
            if isinstance(path_or_pixmap, str):
                self._original_pixmap = QPixmap(path_or_pixmap)
            else:
                self._original_pixmap = path_or_pixmap
            
            self._update_pixmap()
            self.setStyleSheet("border: 1px solid #a0a0a0; background-color: #fff;")
            
    def resizeEvent(self, event):
        if self._original_pixmap:
            self._update_pixmap()
        super().resizeEvent(event)
        
    def _update_pixmap(self):
        if not self._original_pixmap: return
        
        # Scale to FILL the widget
        # KeepAspectRatioByExpanding ensures it fills the dimension but might overflow
        scaled = self._original_pixmap.scaled(
            self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        
        # Create a new pixmap of the widget size (clipping area)
        result = QPixmap(self.size())
        result.fill(Qt.transparent)
        
        # Draw the scaled pixmap centered
        from PySide6.QtGui import QPainter
        painter = QPainter(result)
        # Calculate offset to center
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()
        
        self.setPixmap(result)

class TagEditor(QWidget):
    save_clicked = Signal(dict)

    def __init__(self):
        super().__init__()
        
        # Main VBox
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Helper to add Label-above-Field
        def add_v_field(label_text, widget, parent_layout=layout):
            vbox = QVBoxLayout()
            vbox.setSpacing(2)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 11px; color: #555;") # Subtle labels
            vbox.addWidget(lbl)
            vbox.addWidget(widget)
            parent_layout.addLayout(vbox)
            return vbox

        # Title
        self.title_edit = QComboBox()
        self.title_edit.setEditable(True)
        add_v_field("Title:", self.title_edit)

        # Artist
        self.artist_edit = QComboBox()
        self.artist_edit.setEditable(True)
        add_v_field("Artist:", self.artist_edit)

        # Album
        self.album_edit = QComboBox()
        self.album_edit.setEditable(True)
        add_v_field("Album:", self.album_edit)

        # Row: Year | Track
        row_yt = QHBoxLayout()
        row_yt.setSpacing(10)
        
        self.year_edit = QComboBox()
        self.year_edit.setEditable(True)
        self.year_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        add_v_field("Year:", self.year_edit, row_yt)
        
        self.track_edit = QComboBox()
        self.track_edit.setEditable(True)
        self.track_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        add_v_field("Track:", self.track_edit, row_yt)
        
        layout.addLayout(row_yt)

        # Comment
        self.comment_edit = QComboBox()
        self.comment_edit.setEditable(True)
        add_v_field("Comment:", self.comment_edit)

        # Album Artist
        self.album_artist_edit = QComboBox()
        self.album_artist_edit.setEditable(True)
        add_v_field("Album Artist:", self.album_artist_edit)

        # Composer
        self.composer_edit = QComboBox()
        self.composer_edit.setEditable(True)
        add_v_field("Composer:", self.composer_edit)

        # Row: Disc | Genre
        row_dg = QHBoxLayout()
        row_dg.setSpacing(10)

        self.disc_edit = QComboBox()
        self.disc_edit.setEditable(True)
        self.disc_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        add_v_field("Disc:", self.disc_edit, row_dg)
        
        self.genre_edit = QComboBox()
        self.genre_edit.setEditable(True)
        self.genre_edit.addItems(["Techno", "Melodic Techno", "Dark Techno"])
        self.genre_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        add_v_field("Genre:", self.genre_edit, row_dg)
        
        layout.addLayout(row_dg)
        
        # Row: Label | Catalog #
        row_lc = QHBoxLayout()
        row_lc.setSpacing(10)
        
        self.label_edit = QComboBox()
        self.label_edit.setEditable(True)
        self.label_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        add_v_field("Label:", self.label_edit, row_lc)
        
        self.catalog_edit = QComboBox()
        self.catalog_edit.setEditable(True)
        self.catalog_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        add_v_field("Catalog #:", self.catalog_edit, row_lc)
        
        layout.addLayout(row_lc)

        # Compilation Row
        row_comp = QHBoxLayout()
        self.compilation_check = QCheckBox("Compilation")
        row_comp.addWidget(self.compilation_check)
        row_comp.addStretch()
        layout.addLayout(row_comp)
        
        layout.addSpacing(10)
        
        # Cover Art
        self.drop_zone = DropZone()
        self.drop_zone.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Grow to fill remaining vertical
        layout.addWidget(self.drop_zone)
        
        # Current Cover Path (internal)
        self.current_cover_path = None
        self.drop_zone.file_dropped.connect(self._on_cover_dropped)
        self.drop_zone.cover_removed.connect(self._emit_save)
        self.drop_zone.cover_pasted.connect(self._on_cover_pasted)
        
        # Connect signals for Auto-Save
        self.combos = [self.title_edit, self.artist_edit, self.album_edit, self.year_edit, 
                      self.track_edit, self.genre_edit, self.comment_edit, 
                      self.album_artist_edit, self.composer_edit, self.disc_edit,
                      self.label_edit, self.catalog_edit]
        
        for combo in self.combos:
            combo.lineEdit().editingFinished.connect(self._emit_save)
            combo.activated.connect(self._emit_save)
            
        self.compilation_check.toggled.connect(self._emit_save)

    def _update_combo_arrows(self):
        """No-op: Using native OS styling, arrows are always visible."""
        pass

    def set_data(self, data: dict, variants: dict = {}):
        self.blockSignals(True)
        
        mapping = {
            'title': self.title_edit,
            'artist': self.artist_edit,
            'album': self.album_edit,
            'year': self.year_edit,
            'track': self.track_edit,
            'genre': self.genre_edit,
            'comment': self.comment_edit,
            'album_artist': self.album_artist_edit,
            'composer': self.composer_edit,
            'disc_number': self.disc_edit,
            'label': self.label_edit,
            'catalog_number': self.catalog_edit
        }

        for key, combo in mapping.items():
            # 1. Update items based on variants
            v_list = variants.get(key, [])
            combo.clear()
            if combo == self.genre_edit:
                combo.addItems(["Techno", "Melodic Techno", "Dark Techno"])
            else:
                if v_list:
                    combo.addItems(v_list)
            
            # 2. Set current text
            val = str(data.get(key, ''))
            combo.setCurrentText(val)
        
        self.compilation_check.setChecked(bool(data.get('compilation', False)))
        self._update_combo_arrows()
        
        # Cover Art
        if 'cover_path' in data and data['cover_path']:
             self.drop_zone.set_image(data['cover_path'])
             self.current_cover_path = data['cover_path']
        else:
             self.drop_zone.set_image(None) 
             self.current_cover_path = None

        self.blockSignals(False)

    def _on_cover_dropped(self, path):
        self.current_cover_path = path
        self.drop_zone.set_image(path)
        self._emit_save()

    def _on_cover_pasted(self, path):
        self.current_cover_path = path
        self._emit_save()

    def _emit_save(self):
        data = {
            'title': self.title_edit.currentText(),
            'artist': self.artist_edit.currentText(),
            'album': self.album_edit.currentText(),
            'year': self.year_edit.currentText(),
            'track': self.track_edit.currentText(),
            'genre': self.genre_edit.currentText(),
            'comment': self.comment_edit.currentText(),
            'album_artist': self.album_artist_edit.currentText(),
            'composer': self.composer_edit.currentText(),
            'disc_number': self.disc_edit.currentText(),
            'label': self.label_edit.currentText(),
            'catalog_number': self.catalog_edit.currentText(),
            'compilation': "1" if self.compilation_check.isChecked() else "0",
        }
        if self.current_cover_path:
            data['cover_path'] = self.current_cover_path
            
        self.save_clicked.emit(data)
