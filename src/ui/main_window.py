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
        
        action_discogs_smart = menu_discogs.addAction("Smart &Match...")
        action_discogs_smart.setShortcut("Ctrl+D")
        action_discogs_smart.triggered.connect(self._on_match_discogs_smart)
        
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

    def _on_match_discogs_smart(self):
        """
        Smartly determines whether to match as a single track, an album, or a batch of individual tracks.
        """
        from PySide6.QtWidgets import QMessageBox, QProgressDialog, QDialog
        from PySide6.QtCore import QEventLoop, Qt
        from .discogs_dialog import DiscogsMatchDialog, AlbumMappingDialog, MetadataPreviewDialog
        from difflib import SequenceMatcher
        import os
        from collections import Counter

        # 1. Validation
        if not self.settings.discogs_token:
            QMessageBox.warning(self, "Discogs Token Required", "Please set your Discogs API token in Settings.")
            return
        
        if self.tabs.currentIndex() != 0:
            QMessageBox.information(self, "Not Supported", "Discogs matching is only for Library tracks.")
            return

        selected_rows = self.file_list.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select tracks to match.")
            return

        self.discogs_manager.set_token(self.settings.discogs_token)

        # 2. Analyze Selection
        tracks_data = []
        for row in selected_rows:
            track = self.track_model.get_track(row.row())
            if track:
                # Always attempt to augment missing metadata from filename
                guessed = self.metadata_manager.guess_metadata_from_filename(track.file_path)
                for k, v in guessed.items():
                    if not track.metadata.get(k):
                        track.metadata[k] = v

                tracks_data.append({
                    'track': track,
                    'artist': track.metadata.get('artist', '') or '',
                    'album': track.metadata.get('album', '') or '',
                    'title': track.metadata.get('title', '') or track.filename,
                    'row': row.row()
                })

        is_album_mode = False
        
        # Heuristic: If multiple tracks, ask user intent based on metadata consistency
        if len(tracks_data) > 1:
            artists = [t['artist'] for t in tracks_data if t['artist']]
            albums = [t['album'] for t in tracks_data if t['album']]
            
            common_artist = Counter(artists).most_common(1)[0][0] if artists else ''
            common_album = Counter(albums).most_common(1)[0][0] if albums else ''
            
            msg = f"You have selected {len(tracks_data)} tracks.\n"
            if common_album:
                msg += f"They seem to belong to album '{common_album}' by '{common_artist}'.\n\n"
            else:
                msg += "Metadata varies among these tracks.\n\n"
                
            msg += "How would you like to match them?"
            
            box = QMessageBox(self)
            box.setWindowTitle("Match Mode")
            box.setText(msg)
            btn_album = box.addButton("As a Single Album", QMessageBox.ActionRole)
            btn_individual = box.addButton("Individually (Track by Track)", QMessageBox.ActionRole)
            box.addButton(QMessageBox.Cancel)
            
            box.exec()
            
            if box.clickedButton() == btn_album:
                is_album_mode = True
            elif box.clickedButton() == btn_individual:
                is_album_mode = False
            else:
                return # Cancel

        # 3. Execution
        if is_album_mode:
            self._process_album_match(tracks_data)
        else:
            self._process_individual_match(tracks_data)

    def _process_album_match(self, tracks_data):
        from PySide6.QtWidgets import QMessageBox, QProgressDialog, QDialog
        from PySide6.QtCore import QEventLoop, Qt
        from .discogs_dialog import DiscogsMatchDialog, AlbumMappingDialog
        from difflib import SequenceMatcher
        import os
        from collections import Counter
        
        # 1. Determine Search Query
        artists = [t['artist'] for t in tracks_data if t['artist']]
        albums = [t['album'] for t in tracks_data if t['album']]
        common_artist = Counter(artists).most_common(1)[0][0] if artists else ''
        common_album = Counter(albums).most_common(1)[0][0] if albums else ''
        
        query_artist = common_artist
        query_album = common_album
        
        # If metadata is empty, ask user
        if not query_artist or not query_album:
             # Just use what we have, or fallback to first track
             if not query_artist and tracks_data: query_artist = tracks_data[0]['artist']
             if not query_album and tracks_data: query_album = tracks_data[0]['album']

        query_track = ""
        if not query_album and tracks_data:
             # Fallback: Use the first track's title to find the album
             query_track = tracks_data[0]['title']
             print(f"Album Match: Missing album name. Probing using track: {query_track}")

        print(f"Album Match: Searching for '{query_artist} - {query_album}' (Track: {query_track})")
        
        # 2. Search Discogs
        worker = self.discogs_manager.search_async(query_artist, query_track, query_album)
        if not worker:
            QMessageBox.warning(self, "Error", "Could not start search.")
            return

        progress = QProgressDialog("Searching Discogs for album...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        
        loop = QEventLoop()
        matches = []
        
        worker.finished.connect(lambda res: (matches.extend(res), loop.quit()))
        worker.error.connect(lambda err: (print(f"Search error: {err}"), loop.quit()))
        worker.start()
        
        loop.exec()
        progress.close()
        
        if not matches:
            QMessageBox.information(self, "No Matches", f"No album found for:\n{query_artist} - {query_album}")
            return

        # 3. Select Release
        dialog = DiscogsMatchDialog(matches, self, query_info=f"{query_artist} - {query_album}")
        if dialog.exec() != QDialog.Accepted:
            return
            
        release_id = dialog.get_selected_id()
        
        # 4. Fetch Details
        release_data = self.discogs_manager.get_release_data(release_id)
        if not release_data:
            QMessageBox.warning(self, "Error", "Could not fetch release details.")
            return
            
        discogs_tracks = release_data.get('tracklist', [])
        
        # 5. Map Files to Tracks
        mapping = []
        # Pre-calculate scores to suggest best mapping
        # Create a pool of discogs tracks
        available_d_tracks = list(discogs_tracks)
        
        for tdata in tracks_data:
            local_title = tdata['title']
            local_duration = float(tdata['track'].metadata.get('duration', 0))
            best_match = None
            best_score = 0.0
            
            # Find best match in available tracks
            for i, dt in enumerate(available_d_tracks):
                dt_title = dt['title']
                
                # Check position too if available? 
                # For now just title similarity
                score = SequenceMatcher(None, local_title.lower(), dt_title.lower()).ratio()
                
                # Boost score if duration matches (within 4 seconds)
                dt_duration = dt.get('duration_seconds', 0)
                if local_duration > 0 and dt_duration > 0:
                    diff = abs(local_duration - dt_duration)
                    if diff <= 4:
                        score += 0.4 # Significant boost
                        if score > 1.0: score = 1.0
                    elif diff > 15:
                        score -= 0.2 # Penalty for large duration mismatch
                
                if score > best_score:
                    best_score = score
                    best_match = dt
            
            # If match is decent, assign it and remove from pool to prevent duplicates
            d_track = None
            if best_score > 0.4: # Low threshold, user will verify
                d_track = best_match
                # We generally don't remove from pool because sometimes user has duplicates or different versions
                # But for 1-to-1 mapping it's better. Let's keep it simple for now.
            
            mapping.append({
                'file_name': os.path.basename(tdata['track'].file_path),
                'track': tdata['track'],
                'discogs_track': d_track, # This is now a dict
                'score': best_score,
                'row': tdata['row']
            })

        # 6. Show Mapping Dialog
        map_dialog = AlbumMappingDialog(mapping, discogs_tracks, release_data.get('title', 'Unknown'), self)
        if map_dialog.exec() != QDialog.Accepted:
            return
            
        final_mapping = map_dialog.get_mapping()
        
        # 7. Apply Changes
        # Download cover once
        artwork_path = None
        if release_data.get('cover_image'):
            temp_cover = "temp_discogs_album_cover.jpg"
            if self.discogs_manager.download_cover_art(release_data['cover_image'], temp_cover):
                artwork_path = temp_cover
        
        success_count = 0
        for item in final_mapping:
            track = item['track']
            d_track = item['discogs_track']
            
            # Album global tags
            def update(k, v):
                if v: track.metadata[k] = str(v)
            
            update('album_artist', release_data.get('album_artist'))
            update('album', release_data.get('album'))
            update('year', release_data.get('year'))
            update('genre', release_data.get('genre'))
            update('label', release_data.get('label'))
            update('catalog_number', release_data.get('catalog_number'))
            update('compilation', release_data.get('compilation'))
            
            # Track specific tags
            # Artist: Use track artist if available, otherwise release artist
            track_artist = ""
            if d_track:
                track.metadata['title'] = d_track.get('title', '')
                track.metadata['track'] = d_track.get('position', '')
                track_artist = d_track.get('artists', '')
            
            if not track_artist:
                track_artist = release_data.get('artists', '')
            
            if track_artist:
                track.metadata['artist'] = track_artist
            
            if self.metadata_manager.save_tags(track.file_path, track.metadata, artwork_path):
                self.track_model.update_track(item['row'])
                success_count += 1
                
        if artwork_path and os.path.exists(artwork_path):
            os.remove(artwork_path)
            
        self._on_library_selection(self.file_list.selectionModel().selection(), None)
        QMessageBox.information(self, "Success", f"Updated {success_count} tracks.")

    def _process_individual_match(self, tracks_data):
        from PySide6.QtWidgets import QMessageBox, QProgressDialog, QDialog
        from PySide6.QtCore import QEventLoop, Qt
        from .discogs_dialog import DiscogsMatchDialog, MetadataPreviewDialog
        import os
        
        for i, tdata in enumerate(tracks_data):
            track = tdata['track']
            artist = tdata['artist']
            title = tdata['title']
            album = tdata['album']
            
            # 1. Try Auto-Match
            release_id = self.discogs_manager.auto_match(artist, title)
            
            # 2. If no auto-match, search manually
            if not release_id:
                # Search
                # Pass album and catalog number if available to help find the release
                cat_no = track.metadata.get('catalog_number', '')
                worker = self.discogs_manager.search_async(artist, title, album, cat_no)
                if not worker: continue
                
                # Show generic progress
                loop = QEventLoop()
                matches = []
                worker.finished.connect(lambda res: (matches.extend(res), loop.quit()))
                worker.error.connect(lambda err: loop.quit())
                worker.start()
                loop.exec()
                
                if matches:
                    dialog = DiscogsMatchDialog(matches, self, query_info=f"{artist} - {title}")
                    dialog.setWindowTitle(f"Match: {title}")
                    if dialog.exec() == QDialog.Accepted:
                        release_id = dialog.get_selected_id()
                else:
                    QMessageBox.information(self, "No Matches", 
                        f"No matches found for:\nArtist: {artist}\nTitle: {title}\nAlbum: {album}")
                    continue
            
            if not release_id:
                print(f"Skipping {title} - no match selected")
                continue
                
            # 3. Fetch Data
            release_data = self.discogs_manager.get_release_data(release_id)
            if not release_data: continue
            
            # 4. Propose Changes
            proposed = {}
            for k in ['album', 'year', 'genre', 'label', 'catalog_number', 'compilation', 'album_artist']:
                if release_data.get(k): proposed[k] = release_data[k]
                
            # Track/Title logic
            # Try to match specific track in release
            from difflib import SequenceMatcher
            best_match = None
            best_score = 0.0
            for dt in release_data.get('tracklist', []):
                dt_title = dt.get('title', '')
                score = SequenceMatcher(None, title.lower(), dt_title.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = dt
            
            track_artist = ""
            if best_match and best_score > 0.5:
                proposed['title'] = best_match.get('title', '')
                proposed['track'] = best_match.get('position', '')
                track_artist = best_match.get('artists', '')
            else:
                # If we matched the release but not the specific track (e.g. single), 
                # title might be the release title or we keep local title.
                if len(release_data.get('tracklist', [])) == 1:
                     dt = release_data['tracklist'][0]
                     proposed['title'] = dt.get('title', '')
                     track_artist = dt.get('artists', '')
            
            # Fallback to release artist if track specific artist is missing
            if not track_artist:
                track_artist = release_data.get('artists', '')
            
            if track_artist:
                proposed['artist'] = track_artist
            
            # 5. Preview
            preview = MetadataPreviewDialog(track.metadata, proposed, track.filename, self)
            if preview.exec() == QDialog.Accepted:
                # Apply
                for k, v in proposed.items():
                    if v: track.metadata[k] = str(v)
                
                # Cover Art
                artwork_path = None
                if release_data.get('cover_image'):
                    temp_cover = f"temp_cover_{i}.jpg"
                    if self.discogs_manager.download_cover_art(release_data['cover_image'], temp_cover):
                        artwork_path = temp_cover
                        
                self.metadata_manager.save_tags(track.file_path, track.metadata, artwork_path)
                self.track_model.update_track(tdata['row'])
                
                if artwork_path and os.path.exists(artwork_path):
                    os.remove(artwork_path)
                    
        self._on_library_selection(self.file_list.selectionModel().selection(), None)


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
