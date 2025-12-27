import os
from typing import List, Callable
from .metadata_manager import MetadataManager
from .track import Track

class FileScanner:
    def __init__(self):
        self.metadata_manager = MetadataManager()

    def scan_directory(self, path: str, callback: Callable[[Track], None] = None) -> List[Track]:
        """
        Recursively scans a directory for supported audio files.
        :param path: Directory path to scan.
        :param callback: Optional callback function called for each found track (e.g. for progress bar).
        :return: List of Track objects.
        """
        tracks = []
        if not os.path.exists(path):
            return tracks

        # Get supported extensions from MetadataManager
        exts = self.metadata_manager.SUPPORTED_EXTENSIONS

        for root, dirs, files in os.walk(path):
            for file in files:
                if file.lower().endswith(exts):
                    full_path = os.path.join(root, file)
                    try:
                        # Load metadata immediately? 
                        # For large libraries, we might want to do this lazily or in parallel.
                        # For now, let's load it to populate the table.
                        tags = self.metadata_manager.load_tags(full_path)
                        track = Track(file_path=full_path, metadata=tags)
                        tracks.append(track)
                        
                        if callback:
                            callback(track)
                    except Exception as e:
                        print(f"Error scanning {full_path}: {e}")
        
        return tracks
