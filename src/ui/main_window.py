import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QDockWidget, 
                               QFileDialog, QStatusBar, QMessageBox, QVBoxLayout, QTabWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from .file_list import FileList, TrackModel
from .tag_editor import TagEditor
from .download_queue import DownloadQueue
from ..core.file_scanner import FileScanner
from ..core.metadata_manager import MetadataManager
from ..core.download_manager import DownloadManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nexus Music Tag & Downloader")
        self.resize(1000, 700)
        
        # Set Window Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.scanner = FileScanner()
        self.metadata_manager = MetadataManager()
        self.download_manager = DownloadManager()
        
        # Models
        self.track_model = TrackModel()
        
        # Central Layout
        from PySide6.QtWidgets import QSplitter
        
        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)
        
        # Sidebar (Tag Editor)
        self.tag_editor = TagEditor()
        self.tag_editor.setFixedWidth(280) # Default width approximating Mp3Tag
        self.splitter.addWidget(self.tag_editor)
        
        # Tabs (Library / Downloads)
        self.tabs = QTabWidget()
        self.file_list = FileList()
        self.file_list.setModel(self.track_model)
        self.tabs.addTab(self.file_list, "Library")
        
        self.download_queue = DownloadQueue(self.download_manager)
        self.tabs.addTab(self.download_queue, "Downloads")
        
        self.splitter.addWidget(self.tabs)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status_count()

        # Undo Stack
        self.undo_stack = []
        
        # Connect signals
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        # Library Signals
        self.file_list.files_dropped.connect(self.load_paths)
        self.file_list.selectionModel().selectionChanged.connect(self._on_library_selection)
        
        # Downloads Signals
        self.download_queue.table.selectionModel().selectionChanged.connect(self._on_download_selection)
        
        # Editor Signals
        self.tag_editor.save_clicked.connect(self._on_save_tags)
        
        # Menu
        self._create_menu()

    def _create_menu(self):
        menu_file = self.menuBar().addMenu("&File")
        
        action_open_dir = menu_file.addAction("Add Directory...")
        action_open_dir.triggered.connect(self._open_directory_dialog)
        
        menu_file.addSeparator()
        action_exit = menu_file.addAction("Exit")
        action_exit.triggered.connect(self.close)
        
        menu_edit = self.menuBar().addMenu("&Edit")
        self.action_undo = menu_edit.addAction("Undo")
        self.action_undo.setShortcut("Ctrl+Z")
        self.action_undo.setEnabled(False)
        self.action_undo.triggered.connect(self.undo)
        
        menu_convert = self.menuBar().addMenu("&Convert")
        action_tag_to_name = menu_convert.addAction("Tag - Filename")
        action_tag_to_name.setShortcut("Alt+1")
        action_tag_to_name.triggered.connect(self._on_tag_to_filename)
        
        action_name_to_tag = menu_convert.addAction("Filename - Tag")
        action_name_to_tag.setShortcut("Alt+2")
        action_name_to_tag.triggered.connect(self._on_filename_to_tag)

    def _on_tag_to_filename(self):
        indexes = self.file_list.selectionModel().selectedRows()
        if not indexes:
            return
            
        from .dialogs import ConvertDialog
        first_track = self.track_model.get_track(indexes[0].row())
        dialog = ConvertDialog(mode="tag_to_filename", initial_track_info=first_track.metadata.copy(), parent=self)
        dialog.track_info['filepath'] = first_track.file_path
        
        if dialog.exec():
            fmt = dialog.get_format()
            renamed_count = 0
            total = len(indexes)
            
            for idx in indexes:
                track = self.track_model.get_track(idx.row())
                new_basename = self.metadata_manager.resolve_format(fmt, track.metadata)
                new_basename = self.metadata_manager.sanitize_filename(new_basename)
                
                old_path = track.file_path
                dir_name = os.path.dirname(old_path)
                ext = os.path.splitext(old_path)[1]
                new_path = os.path.join(dir_name, f"{new_basename}{ext}")
                
                if old_path != new_path and not os.path.exists(new_path):
                    try:
                        os.rename(old_path, new_path)
                        track.file_path = new_path
                        self.track_model.update_track(idx.row())
                        renamed_count += 1
                    except Exception as e:
                        print(f"Rename error: {e}")
            
            QMessageBox.information(self, "Conversion", f"{renamed_count} of {total} files renamed.")

    def _on_filename_to_tag(self):
        indexes = self.file_list.selectionModel().selectedRows()
        if not indexes:
            return
            
        from .dialogs import ConvertDialog
        first_track = self.track_model.get_track(indexes[0].row())
        dialog = ConvertDialog(mode="filename_to_tag", initial_track_info={'filepath': first_track.file_path}, parent=self)
        
        if dialog.exec():
            fmt = dialog.get_format()
            updated_count = 0
            total = len(indexes)
            
            for idx in indexes:
                track = self.track_model.get_track(idx.row())
                fname = os.path.basename(track.file_path)
                extracted = self.metadata_manager.parse_filename(fmt, fname)
                
                if extracted:
                    # Update metadata
                    track.metadata.update(extracted)
                    if self.metadata_manager.save_tags(track.file_path, track.metadata):
                        self.track_model.update_track(idx.row())
                        updated_count += 1
            
            QMessageBox.information(self, "Conversion", f"{updated_count} of {total} files updated.")

    def undo(self):
        if not self.undo_stack:
            return
            
        last_action = self.undo_stack.pop()
        
        restored_count = 0
        for path, old_tags in last_action:
            if self.metadata_manager.save_tags(path, old_tags):
                for r in range(self.track_model.rowCount()):
                    t = self.track_model.get_track(r)
                    if t.file_path == path:
                        t.metadata = old_tags
                        self.track_model.update_track(r)
                        break
                restored_count += 1
                
        self.status_bar.showMessage(f"Undid changes for {restored_count} files.", 3000)
        self.action_undo.setEnabled(len(self.undo_stack) > 0)

    def _open_directory_dialog(self):
        d = QFileDialog.getExistingDirectory(self, "Select Directory")
        if d:
            self.load_paths([d])

    def load_paths(self, paths):
        self.status_bar.showMessage("Scanning...")
        all_tracks = []
        for p in paths:
            if os.path.isdir(p):
                tracks = self.scanner.scan_directory(p)
                all_tracks.extend(tracks)
            elif os.path.isfile(p):
                if p.lower().endswith(self.metadata_manager.SUPPORTED_EXTENSIONS):
                    tags = self.metadata_manager.load_tags(p)
                    from ..core.track import Track
                    track = Track(file_path=p, metadata=tags)
                    all_tracks.append(track)

        self.track_model.set_tracks(all_tracks)
        self._update_status_count()
        self.status_bar.showMessage(f"Loaded {len(all_tracks)} files.", 3000)

    def _update_status_count(self):
        count = self.track_model.rowCount()
        self.status_bar.showMessage(f"Total Files: {count}")

    def _on_tab_changed(self, index):
        # Refresh editor State based on current selection in the new tab
        if index == 0: # Library
            indexes = self.file_list.selectionModel().selectedRows()
            if not indexes:
                 self.tag_editor.set_data({})
            else:
                 self._on_library_selection(None, None)
        else: # Downloads
            indexes = self.download_queue.table.selectionModel().selectedRows()
            if not indexes:
                 self.tag_editor.set_data({})
            else:
                 self._on_download_selection(None, None)

    def _on_library_selection(self, selected, deselected):
        if self.tabs.currentIndex() != 0: return

        indexes = self.file_list.selectionModel().selectedRows()
        count = len(indexes)
        
        if count == 0:
            pass 
        elif count == 1:
            track = self.track_model.get_track(indexes[0].row())
            if track:
                self.tag_editor.set_data(track.metadata)
        else:
             self.tag_editor.set_data({'title': '<Multiple>', 'artist': '<Multiple>'})

    def _on_download_selection(self, selected, deselected):
        if self.tabs.currentIndex() != 1: return

        indexes = self.download_queue.table.selectionModel().selectedRows()
        count = len(indexes)
        
        if count == 0:
            pass
        elif count == 1:
            job = self.download_queue.model.get_job(indexes[0].row())
            # TagEditor.set_data(job) will handle metadata and 'cover_path'
            self.tag_editor.set_data(job)
        else:
            self.tag_editor.set_data({'title': '<Multiple>', 'artist': '<Multiple>'})

    def _on_save_tags(self, data):
        # Context switching save
        if self.tabs.currentIndex() == 0:
            self._save_library_tags(data)
        else:
            self._save_download_tags(data)

    def _save_library_tags(self, data):
        indexes = self.file_list.selectionModel().selectedRows()
        if not indexes: return
        
        count = 0
        cover_path = data.pop('cover_path', None)
        
        dirty_data = {}
        for k, v in data.items():
            if v != '<Multiple>':
                dirty_data[k] = v
        
        current_undo_batch = []
        
        for idx in indexes:
            track = self.track_model.get_track(idx.row())
            if track:
                current_undo_batch.append((track.file_path, track.metadata.copy()))
                
                current_tags = track.metadata.copy()
                current_tags.update(dirty_data)
                
                success = self.metadata_manager.save_tags(track.file_path, current_tags, cover_path)
                if success:
                    track.metadata = current_tags
                    self.track_model.update_track(idx.row())
                    count += 1
        
        if count > 0:
            self.undo_stack.append(current_undo_batch)
            self.action_undo.setEnabled(True)
        
        self.status_bar.showMessage(f"Updated {count} files.", 3000)

    def _save_download_tags(self, data):
        # Update Pending jobs in download queue
        indexes = self.download_queue.table.selectionModel().selectedRows()
        if not indexes: return
        
        count = 0
        # Ignore cover path for downloads (not supported in pre-download edit yet)
        
        dirty_data = {}
        for k, v in data.items():
            if v != '<Multiple>':
                dirty_data[k] = v
        
        model = self.download_queue.model
        for idx in indexes:
            job = model.get_job(idx.row())
            if job['status'] == 'Pending':
                # Update job dict
                job.update(dirty_data)
                # Signal model update for all columns (0 to 6)
                start_idx = model.index(idx.row(), 0)
                end_idx = model.index(idx.row(), 6)
                model.dataChanged.emit(start_idx, end_idx)
                count += 1
        
        self.status_bar.showMessage(f"Updated {count} pending downloads.", 3000)
