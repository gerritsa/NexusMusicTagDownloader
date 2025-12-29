from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                                 QTableWidgetItem, QPushButton, QLabel, QHeaderView)
from PySide6.QtCore import Qt

class DiscogsMatchDialog(QDialog):
    """Dialog for manually selecting a Discogs release when multiple matches are found"""
    
    def __init__(self, matches: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Discogs Match")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self.matches = matches
        self.selected_id = None
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Multiple matches found. Select the correct release:")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Artist", "Title", "Year", "Label"])
        self.table.setRowCount(len(matches))
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Populate table
        for row, match in enumerate(matches):
            self.table.setItem(row, 0, QTableWidgetItem(match.get('artists', '')))
            self.table.setItem(row, 1, QTableWidgetItem(match.get('title', '')))
            self.table.setItem(row, 2, QTableWidgetItem(str(match.get('year', ''))))
            self.table.setItem(row, 3, QTableWidgetItem(match.get('label', '')))
            
            # Store release ID in row data
            self.table.item(row, 0).setData(Qt.UserRole, match.get('id'))
        
        # Auto-select first row
        if matches:
            self.table.selectRow(0)
        
        # Resize columns
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
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
        self.setMinimumHeight(350)
        
        self.approved = False
        
        layout = QVBoxLayout(self)
        
        # Header
        header_text = f"Review changes for: {track_name}" if track_name else "Review metadata changes"
        header = QLabel(header_text)
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Field", "Current", "New"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        
        # Populate table with fields that have changes
        rows_with_changes = []
        for key, label in self.FIELDS:
            current_val = str(current_metadata.get(key, '') or '')
            new_val = str(new_metadata.get(key, '') or '')
            
            # Only show if new value exists OR current differs from new
            if new_val or current_val != new_val:
                has_change = current_val != new_val and new_val
                rows_with_changes.append((label, current_val, new_val, has_change))
        
        self.table.setRowCount(len(rows_with_changes))
        
        for row, (label, current_val, new_val, has_change) in enumerate(rows_with_changes):
            self.table.setItem(row, 0, QTableWidgetItem(label))
            self.table.setItem(row, 1, QTableWidgetItem(current_val))
            
            new_item = QTableWidgetItem(new_val)
            if has_change:
                new_item.setForeground(Qt.green)  # Highlight changes
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
        skip_btn = QPushButton("Skip")
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
