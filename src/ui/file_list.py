from typing import List, Any
from PySide6.QtWidgets import QTableView, QAbstractItemView, QHeaderView
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from ..core.track import Track

class TrackModel(QAbstractTableModel):
    """
    Model for displaying Track objects in a table.
    """
    COLUMNS = ["Filename", "Title", "Artist", "Album", "Year", "Track", "Genre", "Album Artist", "Composer", "Disc", "Compilation"]
    
    def __init__(self, tracks: List[Track] = None):
        super().__init__()
        self._tracks = tracks or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._tracks)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        track = self._tracks[index.row()]
        col = index.column()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 0:
                return track.filename
            
            # Map columns to metadata keys
            key = self._get_key_for_col(col)
            if key:
                val = track.metadata.get(key, "")
                if key == 'compilation':
                    return "1" if val in [True, 1, "1"] else "0"
                return str(val)

        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        default = super().flags(index)
        if index.column() == 0:
            return default | Qt.ItemIsEditable
        return default

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole and index.column() == 0:
            track = self._tracks[index.row()]
            import os
            old_path = track.file_path
            new_name = value.strip()
            if not new_name:
                return False
                
            dir_name = os.path.dirname(old_path)
            new_path = os.path.join(dir_name, new_name)
            
            if old_path == new_path:
                return False
            
            if os.path.exists(new_path):
                return False
            
            try:
                os.rename(old_path, new_path)
                track.file_path = new_path
                self.dataChanged.emit(index, index)
                # Also notify that metadata columns might need refresh? 
                # (Though they shouldn't change, just the filename)
                return True
            except Exception as e:
                print(f"Rename failed: {e}")
                return False
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.COLUMNS[section]
        return None

    def _get_key_for_col(self, col):
        # Maps column index to internal metadata key
        mapping = {
            1: 'title',
            2: 'artist',
            3: 'album',
            4: 'year',
            5: 'track',
            6: 'genre',
            7: 'album_artist',
            8: 'composer',
            9: 'disc_number',
            10: 'compilation'
        }
        return mapping.get(col)

    def set_tracks(self, tracks: List[Track]):
        self.beginResetModel()
        self._tracks = tracks
        self.endResetModel()

    def add_tracks(self, tracks: List[Track]):
        if not tracks:
            return
        self.beginInsertRows(QModelIndex(), len(self._tracks), len(self._tracks) + len(tracks) - 1)
        self._tracks.extend(tracks)
        self.endInsertRows()

    def remove_tracks(self, rows: List[int]):
        """Remove tracks at given row indices."""
        if not rows:
            return
        
        # Sort in reverse to avoid index shifts
        for row in sorted(rows, reverse=True):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._tracks.pop(row)
            self.endRemoveRows()
        
    def sort(self, column, order=Qt.AscendingOrder):
        """Sort model by a specific column."""
        self.layoutAboutToBeChanged.emit()
        
        reverse = (order == Qt.DescendingOrder)
        
        def sort_key(track):
            if column == 0: # Filename
                return track.filename.lower()
            
            key = self._get_key_for_col(column)
            val = track.metadata.get(key, "")
            
            # Special handling for numerical columns
            if key == 'track':
                # Handle "1/10" or "01" or empty
                try:
                    s = str(val).split('/')[0]
                    return int(s) if s else 0
                except:
                    return 0
            if key == 'year':
                try:
                    return int(val) if val else 0
                except:
                    return 0
                    
            return str(val).lower()

        self._tracks.sort(key=sort_key, reverse=reverse)
        self.layoutChanged.emit()

    def get_track(self, index: int) -> Track:
        if 0 <= index < len(self._tracks):
            return self._tracks[index]
        return None

    def update_track(self, row: int):
        """Notify views that a track has changed."""
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))


class FileList(QTableView):
    """
    Table view for displaying the file list.
    Supports Drag & Drop.
    """
    files_dropped = Signal(list) # Emits list of local file paths (URLs)

    def __init__(self):
        super().__init__()
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSortingEnabled(True)
        self.setFrameShape(QTableView.NoFrame)  # Remove redundant border for cleaner tab integration
        
        # Style
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setStyleSheet("QHeaderView::section { font-weight: normal; text-align: left; font-size: 13px; padding: 4px; }")
        self.verticalHeader().setVisible(False)
        
        # Drag & Drop
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace or event.key() == Qt.Key_Delete:
            indexes = self.selectionModel().selectedRows()
            if indexes:
                rows = [idx.row() for idx in indexes]
                self.model().remove_tracks(rows)
            event.accept()
        else:
            super().keyPressEvent(event)
