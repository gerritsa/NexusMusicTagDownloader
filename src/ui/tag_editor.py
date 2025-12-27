from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QLineEdit, QComboBox, QCheckBox, QFrame, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap

class DropZone(QLabel):
    file_dropped = Signal(str)
    cover_removed = Signal()

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
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        remove_action = menu.addAction("Remove cover")
        
        action = menu.exec(event.globalPos())
        if action == remove_action:
            self.set_image(None)
            self.cover_removed.emit()

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

    def set_image(self, path):
        if path:
            self._original_pixmap = QPixmap(path)
            self._update_pixmap()
            self.setStyleSheet("border: 1px solid #a0a0a0; background-color: #fff;") 
        else:
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
            # lbl.setStyleSheet("font-weight: bold;") # Removed bold per user request
            vbox.addWidget(lbl)
            vbox.addWidget(widget)
            parent_layout.addLayout(vbox)

        # Title
        self.title_edit = QLineEdit()
        add_v_field("Title:", self.title_edit)

        # Artist
        self.artist_edit = QComboBox()
        self.artist_edit.setEditable(True)
        add_v_field("Artist:", self.artist_edit)

        # Album
        self.album_edit = QComboBox()
        self.album_edit.setEditable(True)
        add_v_field("Album:", self.album_edit)

        # Row: Year | Track | Genre
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)
        
        self.year_edit = QComboBox()
        self.year_edit.setEditable(True)
        self.year_edit.setFixedWidth(80) # Sized for 4 chars
        add_v_field("Year:", self.year_edit, row_layout)
        
        self.track_edit = QComboBox() # ComboBox for track often allows "1" or "1/12"
        self.track_edit.setEditable(True)
        self.track_edit.setFixedWidth(60)
        add_v_field("Track:", self.track_edit, row_layout)
        
        self.genre_edit = QComboBox()
        self.genre_edit.setEditable(True)
        self.genre_edit.addItems(["Pop", "Rock", "Electronic", "Classical", "Jazz", "Hip Hop"])
        add_v_field("Genre:", self.genre_edit, row_layout)
        
        layout.addLayout(row_layout)

        # Comment
        self.comment_edit = QComboBox() # Mp3Tag uses combo for history
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

        # Disc Number + Compilation
        disc_row = QHBoxLayout()
        self.disc_edit = QComboBox()
        self.disc_edit.setEditable(True)
        self.disc_edit.setFixedWidth(60)
        add_v_field("Disc:", self.disc_edit, disc_row)
        
        disc_row.addStretch()
        
        self.compilation_check = QCheckBox("Compilation")
        # Align checkbox with bottom to match text fields visually
        wrapper = QVBoxLayout()
        wrapper.addStretch()
        wrapper.addWidget(self.compilation_check)
        disc_row.addLayout(wrapper)
        
        layout.addLayout(disc_row)
        
        # Spacer to push Cover Art to bottom?
        # Mp3Tag has cover art below fields.
        
        layout.addSpacing(10)
        
        # Cover Art
        self.drop_zone = DropZone()
        self.drop_zone.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Grow to fill remaining vertical
        layout.addWidget(self.drop_zone)
        
        # Current Cover Path (internal)
        self.current_cover_path = None
        self.drop_zone.file_dropped.connect(self._on_cover_dropped)
        
        # Connect signals for Auto-Save
        self.title_edit.editingFinished.connect(self._emit_save)
        
        # For QComboBox (Editable): editingFinished covers the text part, 
        # but activated(int) covers selecting from the dropdown.
        for combo in [self.artist_edit, self.album_edit, self.year_edit, 
                      self.track_edit, self.genre_edit, self.comment_edit, 
                      self.album_artist_edit, self.composer_edit, self.disc_edit]:
            combo.lineEdit().editingFinished.connect(self._emit_save)
            combo.activated.connect(self._emit_save)
            
        self.compilation_check.toggled.connect(self._emit_save)

    def set_data(self, data: dict):
        self.blockSignals(True)
        
        self.title_edit.setText(data.get('title', ''))
        self.artist_edit.setCurrentText(data.get('artist', ''))
        self.album_edit.setCurrentText(data.get('album', ''))
        self.year_edit.setCurrentText(str(data.get('year', '')))
        self.track_edit.setCurrentText(str(data.get('track', '')))
        self.genre_edit.setCurrentText(data.get('genre', ''))
        self.comment_edit.setCurrentText(data.get('comment', ''))
        self.album_artist_edit.setCurrentText(data.get('album_artist', ''))
        self.composer_edit.setCurrentText(data.get('composer', ''))
        self.disc_edit.setCurrentText(str(data.get('disc_number', '')))
        self.compilation_check.setChecked(bool(data.get('compilation', False)))
        
        # Cover Art
        if 'cover_path' in data and data['cover_path']:
             self.drop_zone.set_image(data['cover_path'])
             self.current_cover_path = data['cover_path']
        else:
             self.drop_zone.set_image(None) # Use set_image(None) to clear the image and reset text/style
             self.current_cover_path = None

        self.blockSignals(False)

    def _on_cover_dropped(self, path):
        self.current_cover_path = path
        self.drop_zone.set_image(path)
        self._emit_save()

    def _emit_save(self):
        data = {
            'title': self.title_edit.text(),
            'artist': self.artist_edit.currentText(),
            'album': self.album_edit.currentText(),
            'year': self.year_edit.currentText(),
            'track': self.track_edit.currentText(),
            'genre': self.genre_edit.currentText(),
            'comment': self.comment_edit.currentText(),
            'album_artist': self.album_artist_edit.currentText(),
            'composer': self.composer_edit.currentText(),
            'disc_number': self.disc_edit.currentText(),
            'compilation': self.compilation_check.isChecked(),
        }
        if self.current_cover_path:
            data['cover_path'] = self.current_cover_path
            
        self.save_clicked.emit(data)
