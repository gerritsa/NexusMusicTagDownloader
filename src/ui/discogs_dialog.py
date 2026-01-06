from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                                 QTableWidgetItem, QPushButton, QLabel, QHeaderView, QCheckBox, QSplitter, QStyledItemDelegate)
from PySide6.QtCore import Qt

class ElideLeftDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option.textElideMode = Qt.ElideLeft
        super().paint(painter, option, index)

class DiscogsMatchDialog(QDialog):
    """Dialog for manually selecting a Discogs release when multiple matches are found"""
    
    def __init__(self, matches: list, parent=None, query_info: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Select Discogs Match")
        self.setMinimumWidth(800)
        self.setMinimumHeight(400)
        
        self.matches = matches
        self.selected_id = None
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Multiple matches found. Select the correct release:")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)
        
        if query_info:
            sub = QLabel(f"Search Query: {query_info}")
            sub.setStyleSheet("color: #666; margin-bottom: 5px;")
            layout.addWidget(sub)
        
        from difflib import SequenceMatcher
        
        # Pre-calculate scores and sort
        for match in self.matches:
            artist = match.get('artists', '')
            title = match.get('title', '')
            score = 0
            if query_info:
                target = f"{artist} - {title}"
                score = SequenceMatcher(None, query_info.lower(), target.lower()).ratio() * 100
            match['_calculated_score'] = score

        # Sort: is_cd (True first), then score (descending)
        self.matches.sort(key=lambda m: (m.get('is_cd', False), m.get('_calculated_score', 0)), reverse=True)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Artist", "Title", "Format", "Score", "Year", "Label"])
        self.table.setRowCount(len(self.matches))
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Populate table
        for row, match in enumerate(self.matches):
            artist = match.get('artists', '')
            title = match.get('title', '')
            score = match.get('_calculated_score', 0)
            
            self.table.setItem(row, 0, QTableWidgetItem(artist))
            self.table.setItem(row, 1, QTableWidgetItem(title))
            self.table.setItem(row, 2, QTableWidgetItem(match.get('format', '')))
            
            score_item = QTableWidgetItem(f"{int(score)}%")
            if score > 80:
                score_item.setForeground(Qt.darkGreen)
                font = score_item.font()
                font.setBold(True)
                score_item.setFont(font)
            elif score < 50:
                score_item.setForeground(Qt.red)
            
            self.table.setItem(row, 3, score_item)
            self.table.setItem(row, 4, QTableWidgetItem(str(match.get('year', ''))))
            self.table.setItem(row, 5, QTableWidgetItem(match.get('label', '')))
            
            # Store release ID in row data
            self.table.item(row, 0).setData(Qt.UserRole, match.get('id'))
        
        # Auto-select first row (or best score?)
        if matches:
            self.table.selectRow(0)
        
        # Resize columns
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Select")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_select)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # Double-click to select
        self.table.doubleClicked.connect(self._on_select)
    
    def _on_select(self):
        """User confirmed their selection"""
        selected_rows = self.table.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            self.selected_id = self.table.item(row, 0).data(Qt.UserRole)
            self.accept()
    
    def get_selected_id(self):
        """Return the selected release ID"""
        return self.selected_id


class MetadataPreviewDialog(QDialog):
    """Dialog showing before/after comparison of metadata changes"""
    
    FIELDS = [
        ('artist', 'Artist'),
        ('album', 'Album'),
        ('title', 'Title'),
        ('track', 'Track #'),
        ('year', 'Year'),
        ('genre', 'Genre'),
        ('label', 'Label'),
        ('catalog_number', 'Catalog #'),
        ('compilation', 'Compilation'),
    ]
    
    def __init__(self, current_metadata: dict, new_metadata: dict, track_name: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preview Metadata Changes")
        self.setMinimumWidth(650)
        self.setMinimumHeight(400)
        
        self.approved = False
        
        layout = QVBoxLayout(self)
        
        # Header
        header_text = f"Review changes for: {track_name}" if track_name else "Review metadata changes"
        header = QLabel(header_text)
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        # Instruction
        layout.addWidget(QLabel("Green indicates new or changed values."))
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Field", "Current Value", "New Value"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        
        # Populate table with fields that have changes
        rows_with_changes = []
        for key, label in self.FIELDS:
            current_val = str(current_metadata.get(key, '') or '')
            new_val = str(new_metadata.get(key, '') or '')
            
            # Always show Title and Artist for context, even if unchanged
            is_key_field = key in ['title', 'artist']
            
            # Only show if new value exists OR current differs from new OR it's a key field
            if new_val or current_val != new_val or is_key_field:
                has_change = current_val != new_val and new_val
                rows_with_changes.append((label, current_val, new_val, has_change))
        
        self.table.setRowCount(len(rows_with_changes))
        
        for row, (label, current_val, new_val, has_change) in enumerate(rows_with_changes):
            self.table.setItem(row, 0, QTableWidgetItem(label))
            self.table.setItem(row, 1, QTableWidgetItem(current_val))
            
            new_item = QTableWidgetItem(new_val)
            if has_change:
                new_item.setForeground(Qt.darkGreen)
                font = new_item.font()
                font.setBold(True)
                new_item.setFont(font)
            self.table.setItem(row, 2, new_item)
        
        # Resize columns
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply Changes")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply)
        skip_btn = QPushButton("Skip Track")
        skip_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(skip_btn)
        layout.addLayout(btn_layout)
    
    def _on_apply(self):
        self.approved = True
        self.accept()
    
    def was_approved(self):
        return self.approved

class AlbumMappingDialog(QDialog):
    """
    Dialog to review and adjust mapping between Local Files and Discogs Tracks.
    """
    def __init__(self, mapping: list, discogs_tracks: list, release_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Album Match: {release_title}")
        self.setMinimumWidth(900)
        self.setMinimumHeight(500)
        
        self.mapping = mapping # List of {'file_name': str, 'track': TrackObj, 'discogs_track': DiscogsTrackObj, 'score': float}
        self.discogs_tracks = discogs_tracks
        self.approved_mapping = []
        
        layout = QVBoxLayout(self)
        
        header = QLabel(f"Review track mapping for album: {release_title}")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        layout.addWidget(QLabel("Uncheck rows to skip incorrect matches."))
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Apply", "File", "L.#", "L.Title", "Discogs Track Match", "Score"])
        self.table.setRowCount(len(mapping))
        
        # Set Item Delegate for Filename column to elide left
        self.table.setItemDelegateForColumn(1, ElideLeftDelegate(self.table))
        
        for row, item in enumerate(mapping):
            # Checkbox
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if item['discogs_track'] else Qt.Unchecked)
            self.table.setItem(row, 0, chk)
            
            # Local File
            local_name = item['file_name']
            file_item = QTableWidgetItem(local_name)
            file_item.setToolTip(local_name) # Show full name on hover
            self.table.setItem(row, 1, file_item)
            
            # Local Track Metadata
            track_obj = item.get('track')
            l_num = track_obj.metadata.get('track', '') if track_obj else ''
            l_title = track_obj.metadata.get('title', '') if track_obj else ''
            
            self.table.setItem(row, 2, QTableWidgetItem(l_num))
            self.table.setItem(row, 3, QTableWidgetItem(l_title))
            
            # Discogs Track
            d_track = item['discogs_track']
            d_title = "No Match"
            if d_track:
                pos = d_track.get('position', '')
                title = d_track.get('title', '')
                d_title = f"{pos} - {title}" if pos else title
            
            d_item = QTableWidgetItem(d_title)
            if not d_track:
                d_item.setForeground(Qt.red)
            self.table.setItem(row, 4, d_item)
            
            # Score
            score = item['score']
            s_item = QTableWidgetItem(f"{int(score*100)}%")
            if score < 0.6:
                s_item.setForeground(Qt.red)
            elif score > 0.9:
                s_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 5, s_item)
            
        # Resize Modes
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Apply
        header.setSectionResizeMode(1, QHeaderView.Interactive)      # File (User Resizable)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # L.#
        header.setSectionResizeMode(3, QHeaderView.Interactive)      # L.Title (User Resizable)
        header.setSectionResizeMode(4, QHeaderView.Interactive)      # Discogs Match (User Resizable)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # Score
        
        # Set initial widths for interactive columns
        self.table.setColumnWidth(1, 150) # File
        self.table.setColumnWidth(3, 200) # L.Title
        self.table.setColumnWidth(4, 250) # Discogs Match
        
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Apply Selected Matches")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_apply)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def _on_apply(self):
        self.approved_mapping = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                self.approved_mapping.append(self.mapping[row])
        self.accept()
    
    def get_mapping(self):
        return self.approved_mapping