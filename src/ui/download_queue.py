from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                                 QPushButton, QTableView, QHeaderView, QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt, SLOT, QAbstractTableModel, QModelIndex, Signal

from ..core.download_manager import DownloadManager

class DownloadJobModel(QAbstractTableModel):
    COLUMNS = ["Status", "Title", "Artist", "Album", "Year", "Track", "Genre", "Album Artist", "Composer", "Disc", "Compilation"]
    
    def __init__(self, jobs=None):
        super().__init__()
        # Jobs list of dicts
        self.jobs = jobs or []

    def rowCount(self, parent=QModelIndex()):
        return len(self.jobs)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        job = self.jobs[index.row()]
        col = index.column()
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col == 0: 
                # Merged Status/Progress
                s = job.get('status', 'Pending')
                if s == 'Downloading':
                    p = job.get('progress', 0)
                    return f"{p:.1f}%"
                return s
            
            mapping = {
                1: 'title', 2: 'artist', 3: 'album', 4: 'year', 
                5: 'track', 6: 'genre', 7: 'album_artist', 
                8: 'composer', 9: 'disc_number', 10: 'compilation'
            }
            key = mapping.get(col)
            if key:
                val = job.get(key, '')
                if key == 'compilation':
                    return "1" if val in [True, 1, "1"] else "0"
                return str(val)
        
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            job = self.jobs[index.row()]
            col = index.column()
            # Allow editing metadata if Pending
            if job.get('status') == 'Pending':
                 key = None
                 if col == 1: key = 'title'
                 elif col == 2: key = 'artist'
                 elif col == 3: key = 'album'
                 elif col == 4: key = 'year'
                 elif col == 5: key = 'track'
                 elif col == 6: key = 'genre'
                 
                 if key:
                     job[key] = value
                     self.dataChanged.emit(index, index)
                     return True
        return False

    def flags(self, index):
        default = super().flags(index)
        job = self.jobs[index.row()]
        # Editable if Pending and not Status column (0)
        if job.get('status') == 'Pending' and index.column() > 0:
            return default | Qt.ItemIsEditable
        return default

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLUMNS[section]
        return None

    def add_jobs(self, new_jobs):
        self.beginInsertRows(QModelIndex(), len(self.jobs), len(self.jobs) + len(new_jobs) - 1)
        self.jobs.extend(new_jobs)
        self.endInsertRows()

    def remove_jobs(self, rows):
        # Rows should be sorted descending to avoid index shift issues
        rows = sorted(rows, reverse=True)
        for row in rows:
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.jobs[row]
            self.endRemoveRows()

    def update_job_progress(self, row, progress):
        self.jobs[row]['progress'] = progress
        self.jobs[row]['status'] = 'Downloading'
        if progress >= 100:
            self.jobs[row]['status'] = 'Done'
        # Emitting change for Status column (0)
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0))

    def update_job_status(self, row, status):
        self.jobs[row]['status'] = status
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0))

    def get_job(self, row):
        return self.jobs[row]

    def sort(self, column, order=Qt.AscendingOrder):
        """Sort model by a specific column."""
        self.layoutAboutToBeChanged.emit()
        
        reverse = (order == Qt.DescendingOrder)
        
        def sort_key(job):
            if column == 0: # Status
                return str(job.get('status', 'Pending')).lower()
            
            # Map columns to metadata keys
            mapping = {
                1: 'title', 2: 'artist', 3: 'album', 4: 'year', 
                5: 'track', 6: 'genre', 7: 'album_artist', 
                8: 'composer', 9: 'disc_number', 10: 'compilation'
            }
            key = mapping.get(column)
            if not key: return ""
            
            val = job.get(key, "")
            
            # Special handling for numerical columns
            if key in ['year', 'track', 'disc_number', 'compilation']:
                try:
                    s = str(val).split('/')[0]
                    if key == 'compilation':
                        return 1 if val in [True, 1, "1"] else 0
                    return int(s) if s else 0
                except:
                    return 0
                    
            return str(val).lower()

        self.jobs.sort(key=sort_key, reverse=reverse)
        self.layoutChanged.emit()


class DownloadTable(QTableView):
    backspace_pressed = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace or event.key() == Qt.Key_Delete:
            self.backspace_pressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)


class DownloadQueue(QWidget):
    def __init__(self, download_manager: DownloadManager):
        super().__init__()
        self.manager = download_manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Row 1: Input Area (Primary Action)
        input_layout = QHBoxLayout()
        self.edit_url = QLineEdit()
        self.edit_url.setPlaceholderText("Paste YouTube URL...")
        self.btn_preload = QPushButton("Preload Info")
        # Style Preload as a semi-primary action (standard width)
        self.btn_preload.setFixedWidth(100)
        
        input_layout.addWidget(self.edit_url)
        input_layout.addWidget(self.btn_preload)
        layout.addLayout(input_layout)
        
        # Row 2: Management Toolbar (Secondary Actions)
        tools_layout = QHBoxLayout()
        self.btn_download = QPushButton("Start Download")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_clear = QPushButton("Clear Completed")
        
        # Make "Start Download" stand out slightly if possible (Standard native)
        # We'll just group them together for 
        tools_layout.addWidget(self.btn_download)
        tools_layout.addWidget(self.btn_remove)
        tools_layout.addWidget(self.btn_clear)
        tools_layout.addStretch()
        layout.addLayout(tools_layout)
        
        # Table Area
        self.table = DownloadTable()
        self.table.setFrameShape(QTableView.NoFrame) # Cleaner integration with tabs
        self.table.backspace_pressed.connect(self._remove_selected)
        self.model = DownloadJobModel()
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionsMovable(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setStyleSheet("QHeaderView::section { font-weight: normal; text-align: left; font-size: 13px; padding: 4px; }")
        
        # Set initial widths
        self.table.setColumnWidth(0, 100) # Status
        
        layout.addWidget(self.table)
        
        # Connect
        self.btn_preload.clicked.connect(self._preload)
        self.btn_download.clicked.connect(self._start_download)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_clear.clicked.connect(self._clear_completed)
        
        # Mapping worker -> row index
        self.active_workers = {} 
        self._active_fetchers = set()

    def _preload(self):
        url = self.edit_url.text().strip()
        if not url: return
        
        # Show loader cursor
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.BusyCursor)
        self.btn_preload.setEnabled(False)
        self.edit_url.setEnabled(False)
        
        # Async Fetch
        worker = self.manager.fetch_info(url)
        self._active_fetchers.add(worker)
        
        worker.finished.connect(lambda r, w=worker: self._on_fetch_finished(w, r))
        worker.error.connect(lambda e, w=worker: self._on_fetch_error(w, e))
        
        # Ensure cleanup
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        # Also remove from set when deleted (or when finished)
        worker.finished.connect(lambda: self._active_fetchers.discard(worker))
        worker.error.connect(lambda: self._active_fetchers.discard(worker))
        
    def _on_fetch_finished(self, worker, results):
        self._restore_cursor()
        if not results:
             QMessageBox.warning(self, "Info", "No videos found.")
             
        for job in results:
            self.model.add_jobs([job])
            
        self.edit_url.clear()
    
    def _on_fetch_error(self, worker, err_msg):
        self._restore_cursor()
        QMessageBox.warning(self, "Error", f"Fetch failed: {err_msg}")

    def _restore_cursor(self):
        from PySide6.QtWidgets import QApplication
        QApplication.restoreOverrideCursor()
        self.btn_preload.setEnabled(True)
        self.edit_url.setEnabled(True)

    def _start_download(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            # Fallback: Find all Pending
            rows = []
            for r in range(self.model.rowCount()):
                if self.model.get_job(r)['status'] == 'Pending':
                    rows.append(r)
        else:
            rows = [i.row() for i in indexes]

        started = 0
        for r in rows:
            job = self.model.get_job(r)
            if job['status'] == 'Pending':
                worker = self.manager.start_download(job)
                self.active_workers[worker] = job
                
                worker.progress.connect(lambda p, w=worker: self._on_progress(w, p))
                worker.finished.connect(lambda f, w=worker: self._on_finished(w, f))
                worker.error.connect(lambda e, w=worker: self._on_error(w, e))
                
                job['status'] = 'Starting...'
                job['worker'] = worker # Keep ref
                self.model.update_job_status(r, 'Starting...')
                started += 1
        
        if started == 0 and not rows:
             QMessageBox.information(self, "Info", "No pending jobs to start.")

    def _remove_selected(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes: return
        
        rows_to_remove = []
        for idx in indexes:
            row = idx.row()
            job = self.model.get_job(row)
            if job['status'] == 'Pending' or job['status'] == 'Done' or str(job['status']).startswith('Error'):
                rows_to_remove.append(row)
            else:
                # Active?
                pass
                
        if rows_to_remove:
            self.model.remove_jobs(rows_to_remove)

    def _clear_completed(self):
        rows_to_remove = []
        for r in range(self.model.rowCount()):
            job = self.model.get_job(r)
            if job['status'] == 'Done':
                rows_to_remove.append(r)
        
        if rows_to_remove:
            self.model.remove_jobs(rows_to_remove)

    def _on_progress(self, worker, p):
        if worker in self.active_workers:
            job = self.active_workers[worker]
            try:
                row = self.model.jobs.index(job)
                self.model.update_job_progress(row, p)
            except ValueError:
                pass

    def _on_finished(self, worker, filename):
        if worker in self.active_workers:
            job = self.active_workers[worker]
            try:
                row = self.model.jobs.index(job)
                self.model.update_job_status(row, 'Done')
            except ValueError:
                pass
            # cleanup
            del self.active_workers[worker]

    def _on_error(self, worker, err):
        if worker in self.active_workers:
            job = self.active_workers[worker]
            try:
                row = self.model.jobs.index(job)
                self.model.update_job_status(row, f"Error: {err}")
            except ValueError:
                pass
            del self.active_workers[worker]
