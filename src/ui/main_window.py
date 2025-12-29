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
from ..core.track import Track
from ..core.utils import resource_path
from ..core.discogs_manager import DiscogsManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nexus Music Tag & Downloader")
        self.resize(1000, 700)
        
        # Set Window Icon
        icon_path = resource_path(os.path.join("src", "assets", "icon.png"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        from ..core.settings_manager import SettingsManager
        self.settings = SettingsManager()
        self.scanner = FileScanner()
        self.metadata_manager = MetadataManager()
        self.download_manager = DownloadManager(self.settings)
        self.discogs_manager = DiscogsManager(self.settings.discogs_token)
        
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
        
        # Apply Column Visibility
        self._apply_column_visibility()
        
        # Save order when manually moved in the view
        self.file_list.horizontalHeader().sectionMoved.connect(self._on_column_moved)
        self.download_queue.table.horizontalHeader().sectionMoved.connect(self._on_column_moved)

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
        
        menu_edit.addSeparator()
        
        # Discogs Sub-Menu
        menu_discogs = menu_edit.addMenu("Match with &Discogs")
        
        action_discogs_track = menu_discogs.addAction("Match &Track(s)...")
        action_discogs_track.setShortcut("Cmd+D")
        action_discogs_track.triggered.connect(self._on_match_discogs_track)
        
        action_discogs_album = menu_discogs.addAction("Match &Album...")
        action_discogs_album.setShortcut("Cmd+Shift+D")
        action_discogs_album.triggered.connect(self._on_match_discogs_album)
        
        menu_discogs.addSeparator()
        
        action_discogs_auto = menu_discogs.addAction("&Auto-Match All (YOLO)")
        action_discogs_auto.triggered.connect(self._on_match_discogs_auto)
        
        menu_convert = self.menuBar().addMenu("&Convert")
        action_tag_to_name = menu_convert.addAction("Tag - Filename")
        action_tag_to_name.setShortcut("Alt+1")
        action_tag_to_name.triggered.connect(self._on_tag_to_filename)
        
        action_name_to_tag = menu_convert.addAction("Filename - Tag")
        action_name_to_tag.setShortcut("Alt+2")
        action_name_to_tag.triggered.connect(self._on_filename_to_tag)
        
        menu_tools = self.menuBar().addMenu("&Tools")
        action_settings = menu_tools.addAction("&Settings")
        from PySide6.QtGui import QAction
        action_settings.setMenuRole(QAction.NoRole) # Prevent macOS from moving it to App menu
        action_settings.triggered.connect(self._on_open_settings)
        
        action_columns = menu_tools.addAction("Set &Columns...")
        action_columns.triggered.connect(self._on_set_columns)
        
        menu_help = self.menuBar().addMenu("&Help")
        action_about = menu_help.addAction("&About")
        action_about.triggered.connect(self._on_about)

    def _on_open_settings(self):
        from .dialogs import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()

    def _on_set_columns(self):
        from .dialogs import ColumnDialog
        if self.tabs.currentIndex() == 0:
            # Library
            meta = self.settings.column_metadata_library
            all_cols = [c['name'] for c in meta]
            visible = [c['name'] for c in meta if c['visible']]
            dialog = ColumnDialog("Library Columns", all_cols, visible, self)
            if dialog.exec():
                self.settings.column_metadata_library = dialog.get_column_state()
                self._apply_column_visibility()
        else:
            # Downloads
            meta = self.settings.column_metadata_downloads
            all_cols = [c['name'] for c in meta]
            visible = [c['name'] for c in meta if c['visible']]
            dialog = ColumnDialog("Downloads Columns", all_cols, visible, self)
            if dialog.exec():
                self.settings.column_metadata_downloads = dialog.get_column_state()
                self._apply_column_visibility()

    def _on_about(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.about(self, "About Nexus",
            "<h3>Nexus Music Tag & Downloader</h3>"
            "<p>Version <b>1.0.0</b></p>"
            "<p>Developed by <b>BerrieBeer</b></p>"
            "<p>A high-performance tool for music enthusiasts, combining "
            "YouTube downloading with advanced metadata management.</p>")

    def _on_match_discogs_track(self):
        """Match selected track(s) with Discogs releases (one by one with approval)"""
        from PySide6.QtWidgets import QMessageBox, QProgressDialog, QDialog
        from .discogs_dialog import DiscogsMatchDialog
        import os
        
        # Check if token is set
        if not self.settings.discogs_token:
            QMessageBox.warning(self, "Discogs Token Required",
                "Please set your Discogs API token in Settings first.\n\n"
                "Click Tools → Settings → Discogs to add your token.")
            return
        
        # Reinitialize manager with current token
        self.discogs_manager.set_token(self.settings.discogs_token)
        
        # Get selected tracks from current tab
        if self.tabs.currentIndex() == 0:
            # Library
            selected_rows = self.file_list.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.information(self, "No Selection", "Please select one or more tracks.")
                return
            
            tracks_data = []
            for row in selected_rows:
                track = self.track_model.get_track(row.row())
                if track:
                    tracks_data.append({
                        'track': track,
                        'artist': track.metadata.get('artist', '') or '',
                        'title': track.metadata.get('title', '') or track.filename,
                        'row': row.row()
                    })
        else:
            # Downloads
            QMessageBox.information(self, "Not Supported", 
                "Discogs matching is currently only available for Library tracks.")
            return
        
        # Process each track
        for track_data in tracks_data:
            artist = track_data['artist']
            title = track_data['title']
            track = track_data['track']
            row_idx = track_data['row']
            
            # Try auto-match first
            release_id = self.discogs_manager.auto_match(artist, title)
            
            if not release_id:
                # Need manual selection
                worker = self.discogs_manager.search_async(artist, title)
                if not worker:
                    QMessageBox.warning(self, "Search Failed", "Could not search Discogs.")
                    continue
                
                # Show progress dialog
                progress = QProgressDialog("Searching Discogs...", "Cancel", 0, 0, self)
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.setValue(0)
                
                # Use an event loop to wait for search results without blocking the main event loop
                from PySide6.QtCore import QEventLoop
                loop = QEventLoop()
                
                matches = []
                
                def on_search_finished(results):
                    nonlocal matches
                    matches = results
                    progress.close()
                    loop.quit()
                
                def on_search_error(error):
                    progress.close()
                    QMessageBox.warning(self, "Search Error", f"Failed to search Discogs: {error}")
                    loop.quit()
                
                worker.finished.connect(on_search_finished)
                worker.error.connect(on_search_error)
                worker.start()
                
                # Execute local event loop until loop.quit() is called
                loop.exec()
                
                if not matches:
                    QMessageBox.information(self, "No Matches", f"No matches found for:\n{artist} - {title}")
                    continue
                
                # Show manual selection dialog
                dialog = DiscogsMatchDialog(matches, self)
                if dialog.exec() == QDialog.Accepted:
                    release_id = dialog.get_selected_id()
                else:
                    continue  # User cancelled
            
            if not release_id:
                continue
            
            # Fetch release data
            release_data = self.discogs_manager.get_release_data(release_id)
            if not release_data:
                QMessageBox.warning(self, "Fetch Failed", "Could not fetch release details.")
                continue
            
            # Build proposed metadata changes
            from difflib import SequenceMatcher
            proposed = {}
            
            if release_data.get('artists'):
                proposed['artist'] = release_data['artists']
            if release_data.get('album'):
                proposed['album'] = release_data['album']
            if release_data.get('year'):
                proposed['year'] = release_data['year']
            if release_data.get('genre'):
                proposed['genre'] = release_data['genre']
            if release_data.get('label'):
                proposed['label'] = release_data['label']
            if release_data.get('catalog_number'):
                proposed['catalog_number'] = release_data['catalog_number']
            if release_data.get('compilation'):
                proposed['compilation'] = release_data['compilation']
            
            # Try to find track number by fuzzy matching against the tracklist
            discogs_tracks = release_data.get('tracklist', [])
            matched_title = None
            if discogs_tracks:
                best_match = None
                best_score = 0.0
                for dt in discogs_tracks:
                    dt_title = dt.title if hasattr(dt, 'title') else str(dt)
                    score = SequenceMatcher(None, title.lower(), dt_title.lower()).ratio()
                    if score > best_score:
                        best_score = score
                        best_match = dt
                
                if best_match and best_score > 0.5:
                    if hasattr(best_match, 'position') and best_match.position:
                        proposed['track'] = str(best_match.position)
                    if hasattr(best_match, 'title') and best_match.title:
                        matched_title = best_match.title
            
            # Show preview dialog
            from .discogs_dialog import MetadataPreviewDialog
            preview = MetadataPreviewDialog(track.metadata, proposed, track.filename, self)
            if preview.exec() != QDialog.Accepted or not preview.was_approved():
                print(f"  - Skipped by user")
                continue
            
            # Apply approved changes
            print(f"Applying metadata for: {track.filename}")
            for key, val in proposed.items():
                if val and str(val).strip():
                    print(f"  - Setting {key}: {val}")
                    track.metadata[key] = str(val)
            
            # Download and embed cover art if available
            artwork_path = None
            if release_data.get('cover_image'):
                temp_cover = f"temp_discogs_cover_{track.filename}.jpg"
                if self.discogs_manager.download_cover_art(release_data['cover_image'], temp_cover):
                    artwork_path = temp_cover
            
            # Save track
            success = self.metadata_manager.save_tags(track.file_path, track.metadata, artwork_path)
            
            # Clean up temp cover
            if artwork_path:
                try:
                    os.remove(artwork_path)
                except:
                    pass
            
            if success:
                # Reload track to reflect changes
                self.track_model.update_track(row_idx)
                # Refresh tag editor
                self._on_library_selection(self.file_list.selectionModel().selection(), None)
        
        QMessageBox.information(self, "Success", "Discogs metadata applied successfully!")

    def _on_match_discogs_album(self):
        """Match multiple tracks as a single album with Discogs."""
        from PySide6.QtWidgets import QMessageBox, QProgressDialog, QDialog
        from PySide6.QtCore import QEventLoop
        from .discogs_dialog import DiscogsMatchDialog
        import os
        from difflib import SequenceMatcher
        
        # Check token
        if not self.settings.discogs_token:
            QMessageBox.warning(self, "Discogs Token Required",
                "Please set your Discogs API token in Settings first.")
            return
        
        self.discogs_manager.set_token(self.settings.discogs_token)
        
        # Get selected tracks
        if self.tabs.currentIndex() != 0:
            QMessageBox.information(self, "Not Supported", 
                "Discogs matching is currently only available for Library tracks.")
            return
            
        selected_rows = self.file_list.selectionModel().selectedRows()
        if len(selected_rows) < 2:
            QMessageBox.information(self, "Select Multiple Tracks", 
                "Please select multiple tracks belonging to the same album.")
            return
        
        tracks_data = []
        for row in selected_rows:
            track = self.track_model.get_track(row.row())
            if track:
                tracks_data.append({
                    'track': track,
                    'artist': track.metadata.get('artist', '') or '',
                    'album': track.metadata.get('album', '') or '',
                    'title': track.metadata.get('title', '') or track.filename,
                    'row': row.row()
                })
        
        # Find consolidated query (most common artist + album)
        from collections import Counter
        artists = [t['artist'] for t in tracks_data if t['artist']]
        albums = [t['album'] for t in tracks_data if t['album']]
        
        common_artist = Counter(artists).most_common(1)[0][0] if artists else ''
        common_album = Counter(albums).most_common(1)[0][0] if albums else ''
        
        query = f"{common_artist} {common_album}".strip()
        if not query:
            # Fallback to first track's title
            query = tracks_data[0]['title'] if tracks_data else ''
        
        print(f"Album Match: Searching for '{query}'")
        
        # Search Discogs
        worker = self.discogs_manager.search_async(common_artist, common_album)
        if not worker:
            QMessageBox.warning(self, "Search Failed", "Could not search Discogs.")
            return
        
        progress = QProgressDialog("Searching Discogs for album...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        loop = QEventLoop()
        matches = []
        
        def on_finished(results):
            nonlocal matches
            matches = results
            progress.close()
            loop.quit()
        
        def on_error(error):
            progress.close()
            QMessageBox.warning(self, "Search Error", f"Failed to search: {error}")
            loop.quit()
        
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.start()
        loop.exec()
        
        if not matches:
            QMessageBox.information(self, "No Matches", f"No album found for: {query}")
            return
        
        # Show selection dialog
        dialog = DiscogsMatchDialog(matches, self)
        dialog.setWindowTitle("Select Album")
        if dialog.exec() != QDialog.Accepted:
            return
        
        release_id = dialog.get_selected_id()
        release_data = self.discogs_manager.get_release_data(release_id)
        if not release_data:
            QMessageBox.warning(self, "Fetch Failed", "Could not fetch release details.")
            return
        
        # Get Discogs tracklist
        discogs_tracks = release_data.get('tracklist', [])
        if not discogs_tracks:
            print("Album Match: No tracklist available, applying album metadata only.")
        
        # Fuzzy match local tracks to Discogs tracklist
        def fuzzy_match_score(local_title, discogs_title):
            return SequenceMatcher(None, local_title.lower(), discogs_title.lower()).ratio()
        
        # Download cover art once
        artwork_path = None
        if release_data.get('cover_image'):
            temp_cover = f"temp_discogs_album_cover.jpg"
            if self.discogs_manager.download_cover_art(release_data['cover_image'], temp_cover):
                artwork_path = temp_cover
        
        # Apply metadata to each track
        success_count = 0
        for tdata in tracks_data:
            track = tdata['track']
            row_idx = tdata['row']
            local_title = tdata['title']
            
            # Try to find best matching track from tracklist
            best_match = None
            best_score = 0.0
            for dt in discogs_tracks:
                dt_title = dt.title if hasattr(dt, 'title') else str(dt)
                score = fuzzy_match_score(local_title, dt_title)
                if score > best_score:
                    best_score = score
                    best_match = dt
            
            print(f"  Local: '{local_title}' -> Best match: '{getattr(best_match, 'title', 'N/A')}' (score: {best_score:.2f})")
            
            # Apply album-level metadata
            def update_if_present(key, val):
                if val and str(val).strip():
                    track.metadata[key] = str(val)
            
            update_if_present('artist', release_data.get('artists'))
            update_if_present('album', release_data.get('album'))
            update_if_present('year', release_data.get('year'))
            update_if_present('genre', release_data.get('genre'))
            update_if_present('label', release_data.get('label'))
            update_if_present('catalog_number', release_data.get('catalog_number'))
            
            # Apply track-level metadata if we have a good match
            if best_match and best_score > 0.5:
                if hasattr(best_match, 'title'):
                    track.metadata['title'] = best_match.title
                if hasattr(best_match, 'position'):
                    track.metadata['track'] = best_match.position
            
            # Save
            if self.metadata_manager.save_tags(track.file_path, track.metadata, artwork_path):
                self.track_model.update_track(row_idx)
                success_count += 1
        
        # Cleanup
        if artwork_path:
            try:
                os.remove(artwork_path)
            except: pass
        
        self._on_library_selection(self.file_list.selectionModel().selection(), None)
        QMessageBox.information(self, "Album Match Complete", 
            f"Successfully updated {success_count} of {len(tracks_data)} tracks.")

    def _on_match_discogs_auto(self):
        """Auto-match all selected tracks without confirmation (YOLO mode)."""
        from PySide6.QtWidgets import QMessageBox, QProgressDialog
        import os
        
        # Check token
        if not self.settings.discogs_token:
            QMessageBox.warning(self, "Discogs Token Required",
                "Please set your Discogs API token in Settings first.")
            return
        
        self.discogs_manager.set_token(self.settings.discogs_token)
        
        # Get selected tracks
        if self.tabs.currentIndex() != 0:
            QMessageBox.information(self, "Not Supported", 
                "Discogs matching is currently only available for Library tracks.")
            return
            
        selected_rows = self.file_list.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select one or more tracks.")
            return
        
        # Confirm YOLO
        reply = QMessageBox.question(self, "Auto-Match All",
            f"This will attempt to auto-match {len(selected_rows)} track(s) without confirmation.\n\n"
            "If no confident match is found, a track will be skipped.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        progress = QProgressDialog("Auto-matching tracks...", "Cancel", 0, len(selected_rows), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        
        success_count = 0
        skip_count = 0
        
        for i, row in enumerate(selected_rows):
            if progress.wasCanceled():
                break
            
            track = self.track_model.get_track(row.row())
            if not track:
                continue
            
            artist = track.metadata.get('artist', '') or ''
            title = track.metadata.get('title', '') or track.filename
            
            progress.setLabelText(f"Matching: {artist} - {title}")
            progress.setValue(i)
            
            # Try auto-match
            release_id = self.discogs_manager.auto_match(artist, title)
            
            if not release_id:
                print(f"YOLO Skip: No confident match for '{artist} - {title}'")
                skip_count += 1
                continue
            
            # Fetch and apply
            release_data = self.discogs_manager.get_release_data(release_id)
            if not release_data:
                skip_count += 1
                continue
            
            def update_if_present(key, val):
                if val and str(val).strip():
                    track.metadata[key] = str(val)
            
            update_if_present('artist', release_data.get('artists'))
            update_if_present('album', release_data.get('album'))
            update_if_present('year', release_data.get('year'))
            update_if_present('genre', release_data.get('genre'))
            update_if_present('label', release_data.get('label'))
            update_if_present('catalog_number', release_data.get('catalog_number'))
            
            # Try to find track number from tracklist
            from difflib import SequenceMatcher
            discogs_tracks = release_data.get('tracklist', [])
            if discogs_tracks:
                best_match = None
                best_score = 0.0
                for dt in discogs_tracks:
                    dt_title = dt.title if hasattr(dt, 'title') else str(dt)
                    score = SequenceMatcher(None, title.lower(), dt_title.lower()).ratio()
                    if score > best_score:
                        best_score = score
                        best_match = dt
                
                if best_match and best_score > 0.5:
                    if hasattr(best_match, 'position') and best_match.position:
                        track.metadata['track'] = str(best_match.position)
            
            # Download cover
            artwork_path = None
            if release_data.get('cover_image'):
                temp_cover = f"temp_yolo_cover_{i}.jpg"
                if self.discogs_manager.download_cover_art(release_data['cover_image'], temp_cover):
                    artwork_path = temp_cover
            
            if self.metadata_manager.save_tags(track.file_path, track.metadata, artwork_path):
                self.track_model.update_track(row.row())
                success_count += 1
            
            if artwork_path:
                try:
                    os.remove(artwork_path)
                except: pass
        
        progress.setValue(len(selected_rows))
        self._on_library_selection(self.file_list.selectionModel().selection(), None)
        
        QMessageBox.information(self, "Auto-Match Complete",
            f"Successfully matched: {success_count}\n"
            f"Skipped (no confident match): {skip_count}")


    def _apply_column_visibility(self):
        # 1. Library
        meta_lib = self.settings.column_metadata_library
        header_lib = self.file_list.horizontalHeader()
        header_lib.blockSignals(True) # Prevent saving while restoring
        all_cols_lib = self.track_model.COLUMNS
        
        for visual_idx, entry in enumerate(meta_lib):
            name = entry['name']
            visible = entry['visible']
            try:
                logical_idx = all_cols_lib.index(name)
                current_visual = header_lib.visualIndex(logical_idx)
                if current_visual != visual_idx:
                    header_lib.moveSection(current_visual, visual_idx)
                self.file_list.setColumnHidden(logical_idx, not visible)
            except ValueError: pass
        header_lib.blockSignals(False)
            
        # 2. Downloads
        meta_dl = self.settings.column_metadata_downloads
        header_dl = self.download_queue.table.horizontalHeader()
        header_dl.blockSignals(True)
        all_cols_dl = self.download_queue.model.COLUMNS
        
        for visual_idx, entry in enumerate(meta_dl):
            name = entry['name']
            visible = entry['visible']
            try:
                logical_idx = all_cols_dl.index(name)
                current_visual = header_dl.visualIndex(logical_idx)
                if current_visual != visual_idx:
                    header_dl.moveSection(current_visual, visual_idx)
                self.download_queue.table.setColumnHidden(logical_idx, not visible)
            except ValueError: pass
        header_dl.blockSignals(False)

    def _on_column_moved(self):
        # Determine which table moved and update its metadata
        # (Actually we can just update both or check sender)
        
        # Library
        header_lib = self.file_list.horizontalHeader()
        all_cols_lib = self.track_model.COLUMNS
        new_meta_lib = []
        for v_idx in range(header_lib.count()):
            l_idx = header_lib.logicalIndex(v_idx)
            name = all_cols_lib[l_idx]
            visible = not self.file_list.isColumnHidden(l_idx)
            new_meta_lib.append({'name': name, 'visible': visible})
        self.settings.column_metadata_library = new_meta_lib
        
        # Downloads
        header_dl = self.download_queue.table.horizontalHeader()
        all_cols_dl = self.download_queue.model.COLUMNS
        new_meta_dl = []
        for v_idx in range(header_dl.count()):
            l_idx = header_dl.logicalIndex(v_idx)
            name = all_cols_dl[l_idx]
            visible = not self.download_queue.table.isColumnHidden(l_idx)
            new_meta_dl.append({'name': name, 'visible': visible})
        self.settings.column_metadata_downloads = new_meta_dl

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
                    track = Track(file_path=p, metadata=tags)
                    all_tracks.append(track)
        
        print(f"Scanned {len(all_tracks)} tracks from dropped paths.")
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

    def _get_common_metadata(self, metadata_list):
        if not metadata_list:
            return {}, {}
        
        # Collect all keys used across all items
        all_keys = set()
        for meta in metadata_list:
            all_keys.update(meta.keys())
            
        common = {}
        variants = {}
        first = metadata_list[0]
        
        for key in all_keys:
            vals = set()
            for meta in metadata_list:
                val = str(meta.get(key, ''))
                if val: vals.add(val)
            
            if len(vals) <= 1:
                common[key] = list(vals)[0] if vals else ''
                variants[key] = []
            else:
                common[key] = '<Multiple>'
                variants[key] = sorted(list(vals))
                
        return common, variants

    def _on_library_selection(self, selected, deselected):
        if self.tabs.currentIndex() != 0: return

        indexes = self.file_list.selectionModel().selectedRows()
        count = len(indexes)
        
        if count == 0:
            self.tag_editor.set_data({})
        elif count == 1:
            track = self.track_model.get_track(indexes[0].row())
            if track:
                self.tag_editor.set_data(track.metadata, {})
        else:
            tracks_meta = [self.track_model.get_track(idx.row()).metadata for idx in indexes]
            common, variants = self._get_common_metadata(tracks_meta)
            self.tag_editor.set_data(common, variants)

    def _on_download_selection(self, selected, deselected):
        if self.tabs.currentIndex() != 1: return

        indexes = self.download_queue.table.selectionModel().selectedRows()
        count = len(indexes)
        
        if count == 0:
            self.tag_editor.set_data({})
        elif count == 1:
            job = self.download_queue.model.get_job(indexes[0].row())
            self.tag_editor.set_data(job, {})
        else:
            jobs = [self.download_queue.model.get_job(idx.row()) for idx in indexes]
            # Since jobs are dicts containing metadata keys
            common, variants = self._get_common_metadata(jobs)
            self.tag_editor.set_data(common, variants)

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
