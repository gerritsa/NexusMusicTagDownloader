import os
import shutil
from typing import Dict, Optional, Any, Union

import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, TCON, COMM, APIC, Encoding, TPE2, TCOM, TPOS, TCMP, TXXX
from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover

class MetadataManager:
    """
    Handles reading and writing metadata for MP3, FLAC, and M4A/AAC files.
    Standardizes disparate tag formats into a unified dictionary.
    """

    # Standard internal keys
    KEY_TITLE = 'title'
    KEY_ARTIST = 'artist'
    KEY_ALBUM = 'album'
    KEY_YEAR = 'year'
    KEY_TRACK = 'track'
    KEY_GENRE = 'genre'
    KEY_COMMENT = 'comment'
    KEY_ALBUM_ARTIST = 'album_artist'
    KEY_COMPOSER = 'composer'
    KEY_DISC = 'disc_number'
    KEY_COMPILATION = 'compilation'
    KEY_LABEL = 'label'
    KEY_CATALOG = 'catalog_number'

    SUPPORTED_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.mp4')

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """
        Replaces characters that are invalid in filenames.
        """
        import re
        # keep alphanumeric and some common safe chars
        # remove / \ : * ? " < > |
        safe = re.sub(r'[\\/*?:"<>|]', "", name)
        return safe.strip()

    def load_tags(self, file_path: str) -> Dict[str, Any]:
        """
        Reads tags from a file and returns a unified dictionary.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        tags = {}

        try:
            if ext == '.mp3':
                tags = self._load_mp3(file_path)
            elif ext == '.flac':
                tags = self._load_flac(file_path)
            elif ext in ('.m4a', '.aac'):
                tags = self._load_mp4(file_path)
        except Exception as e:
            print(f"Error loading tags for {file_path}: {e}")
            # Return empty or partial dict on failure, or could re-raise
            return {}

        # Add file path to dict for reference
        tags['filepath'] = file_path
        return tags

    def save_tags(self, file_path: str, tags: Dict[str, Any], cover_art_path: Optional[str] = None) -> bool:
        """
        Writes tags to a file.
        :param file_path: Path to the audio file.
        :param tags: Dictionary of tags to write (using internal keys).
        :param cover_art_path: Optional path to an image file to embed as cover art.
        """
        if not os.path.exists(file_path):
            return False

        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.mp3':
                return self._save_mp3(file_path, tags, cover_art_path)
            elif ext == '.flac':
                return self._save_flac(file_path, tags, cover_art_path)
            elif ext in ('.m4a', '.aac'):
                return self._save_mp4(file_path, tags, cover_art_path)
        except Exception as e:
            print(f"Error saving tags for {file_path}: {e}")
            return False
        
        return False

    def _extract_cover(self, data, ext='.jpg') -> Optional[str]:
        if not data: return None
        import tempfile
        try:
            # Create a consistent hash for filename to resuse existing temp files?
            # Or just unique temp. Unique is safer for now to avoid locking.
            fd, path = tempfile.mkstemp(suffix=ext, prefix='tagnexus_cover_')
            with os.fdopen(fd, 'wb') as f:
                f.write(data)
            return path
        except Exception:
            return None

    # --- MP3 Handlers (ID3v2.4) ---
    def _load_mp3(self, path: str) -> Dict[str, Any]:
        result = {}
        try:
            audio = MP3(path, ID3=ID3)
            result['duration'] = audio.info.length if audio.info else 0
        except mutagen.MutagenError:
            return result
        
        if audio.tags is None:
            return result

        tags = audio.tags
        result[self.KEY_TITLE] = str(tags.get('TIT2', ''))
        result[self.KEY_ARTIST] = str(tags.get('TPE1', ''))
        result[self.KEY_ALBUM] = str(tags.get('TALB', ''))
        result[self.KEY_YEAR] = str(tags.get('TDRC', ''))
        result[self.KEY_TRACK] = str(tags.get('TRCK', ''))
        result[self.KEY_GENRE] = str(tags.get('TCON', ''))
        result[self.KEY_ALBUM_ARTIST] = str(tags.get('TPE2', ''))
        result[self.KEY_COMPOSER] = str(tags.get('TCOM', ''))
        result[self.KEY_DISC] = str(tags.get('TPOS', ''))
        result[self.KEY_LABEL] = str(tags.get('TPUB', ''))
        
        # Compilation
        cpil = tags.get('TCMP')
        result[self.KEY_COMPILATION] = str(cpil.text[0]) if cpil and cpil.text else "0"
        
        # Catalog Number (TXXX)
        for key in tags.keys():
            if key.startswith('TXXX:CATALOGNUMBER') or key.startswith('TXXX:CATALOG NUMBER'):
                result[self.KEY_CATALOG] = str(tags[key])
                break
        
        for key in tags.keys():
            if key.startswith('COMM'):
                result[self.KEY_COMMENT] = str(tags[key])
                break
        
        # Cover Art (APIC)
        for key in tags.keys():
            if key.startswith('APIC'):
                apic = tags[key]
                # data is in apic.data
                ext = '.jpg'
                if apic.mime == 'image/png': ext = '.png'
                cover_path = self._extract_cover(apic.data, ext)
                if cover_path:
                    result['cover_path'] = cover_path
                break
        
        return result

    def _save_mp3(self, path: str, tags: Dict[str, Any], cover_art_path: str = None) -> bool:
        audio = MP3(path, ID3=ID3)
        try:
            audio.add_tags()
        except mutagen.id3.error:
            pass

        def set_frame(frame_cls, key, value):
            if value:
                audio.tags.add(frame_cls(encoding=Encoding.UTF8, text=str(value)))
            elif key in audio.tags:
                 frame_id = frame_cls.__name__
                 if frame_id in audio.tags:
                     del audio.tags[frame_id]

        if self.KEY_TITLE in tags: set_frame(TIT2, 'TIT2', tags[self.KEY_TITLE])
        if self.KEY_ARTIST in tags: set_frame(TPE1, 'TPE1', tags[self.KEY_ARTIST])
        if self.KEY_ALBUM in tags: set_frame(TALB, 'TALB', tags[self.KEY_ALBUM])
        if self.KEY_YEAR in tags: set_frame(TDRC, 'TDRC', tags[self.KEY_YEAR])
        if self.KEY_TRACK in tags: set_frame(TRCK, 'TRCK', tags[self.KEY_TRACK])
        if self.KEY_GENRE in tags: set_frame(TCON, 'TCON', tags[self.KEY_GENRE])
        if self.KEY_ALBUM_ARTIST in tags: set_frame(TPE2, 'TPE2', tags[self.KEY_ALBUM_ARTIST])
        if self.KEY_COMPOSER in tags: set_frame(TCOM, 'TCOM', tags[self.KEY_COMPOSER])
        if self.KEY_DISC in tags: set_frame(TPOS, 'TPOS', tags[self.KEY_DISC])
        if self.KEY_LABEL in tags: # Use standard identifier TPUB for label
             if tags[self.KEY_LABEL]:
                from mutagen.id3 import TPUB
                audio.tags.add(TPUB(encoding=Encoding.UTF8, text=str(tags[self.KEY_LABEL])))
             elif 'TPUB' in audio.tags:
                del audio.tags['TPUB']

        if self.KEY_CATALOG in tags:
            if tags[self.KEY_CATALOG]:
                audio.tags.add(TXXX(encoding=Encoding.UTF8, desc='CATALOGNUMBER', text=str(tags[self.KEY_CATALOG])))
            else:
                # Remove TXXX:CATALOGNUMBER
                for k in list(audio.tags.keys()):
                    if k.startswith('TXXX:CATALOGNUMBER'):
                        del audio.tags[k]

        if self.KEY_COMPILATION in tags:
            val = "1" if str(tags[self.KEY_COMPILATION]) in ("1", "True", "True") else "0"
            audio.tags.add(TCMP(encoding=Encoding.UTF8, text=val))
        
        if self.KEY_COMMENT in tags:
            if tags[self.KEY_COMMENT]:
                audio.tags.add(COMM(encoding=Encoding.UTF8, lang='eng', desc='', text=str(tags[self.KEY_COMMENT])))
            else:
                 keys_to_del = [k for k in audio.tags.keys() if k.startswith('COMM')]
                 for k in keys_to_del:
                     del audio.tags[k]

        if cover_art_path and os.path.exists(cover_art_path):
            with open(cover_art_path, 'rb') as img:
                data = img.read()
            mime = 'image/jpeg'
            if cover_art_path.lower().endswith('.png'):
                mime = 'image/png'
            audio.tags.add(APIC(encoding=Encoding.UTF8, mime=mime, type=3, desc='Cover', data=data))
            
        audio.save()
        return True

    # --- FLAC Handlers (Vorbis Comments) ---
    def _load_flac(self, path: str) -> Dict[str, Any]:
        audio = FLAC(path)
        result = {}
        result['duration'] = audio.info.length if audio.info else 0
        result[self.KEY_TITLE] = audio.get('TITLE', [''])[0]
        result[self.KEY_ARTIST] = audio.get('ARTIST', [''])[0]
        result[self.KEY_ALBUM] = audio.get('ALBUM', [''])[0]
        result[self.KEY_YEAR] = audio.get('DATE', [''])[0]
        result[self.KEY_TRACK] = audio.get('TRACKNUMBER', [''])[0]
        result[self.KEY_GENRE] = audio.get('GENRE', [''])[0]
        result[self.KEY_COMMENT] = audio.get('COMMENT', [''])[0]
        result[self.KEY_ALBUM_ARTIST] = audio.get('ALBUMARTIST', [''])[0]
        result[self.KEY_COMPOSER] = audio.get('COMPOSER', [''])[0]
        result[self.KEY_DISC] = audio.get('DISCNUMBER', [''])[0]
        result[self.KEY_COMPILATION] = audio.get('COMPILATION', ['0'])[0]
        result[self.KEY_LABEL] = audio.get('LABEL', audio.get('PUBLISHER', ['']))[0]
        result[self.KEY_CATALOG] = audio.get('CATALOGNUMBER', [''])[0]
        
        # Cover Art
        if audio.pictures:
            p = audio.pictures[0]
            ext = '.jpg'
            if p.mime == 'image/png': ext = '.png'
            cover_path = self._extract_cover(p.data, ext)
            if cover_path:
                result['cover_path'] = cover_path

        return result

    def _save_flac(self, path: str, tags: Dict[str, Any], cover_art_path: str = None) -> bool:
        audio = FLAC(path)

        def set_tag(key, val_key):
             if val_key in tags:
                if tags[val_key]:
                    audio[key] = str(tags[val_key])
                elif key in audio:
                    del audio[key]

        set_tag('TITLE', self.KEY_TITLE)
        set_tag('ARTIST', self.KEY_ARTIST)
        set_tag('ALBUM', self.KEY_ALBUM)
        set_tag('DATE', self.KEY_YEAR)
        set_tag('TRACKNUMBER', self.KEY_TRACK)
        set_tag('GENRE', self.KEY_GENRE)
        set_tag('COMMENT', self.KEY_COMMENT)
        set_tag('ALBUMARTIST', self.KEY_ALBUM_ARTIST)
        set_tag('COMPOSER', self.KEY_COMPOSER)
        set_tag('DISCNUMBER', self.KEY_DISC)
        set_tag('COMPILATION', self.KEY_COMPILATION)
        set_tag('LABEL', self.KEY_LABEL)
        set_tag('CATALOGNUMBER', self.KEY_CATALOG)

        if cover_art_path and os.path.exists(cover_art_path):
            p = Picture()
            with open(cover_art_path, 'rb') as img:
                p.data = img.read()
            p.type = 3
            if cover_art_path.lower().endswith('.png'):
                p.mime = 'image/png'
            else:
                p.mime = 'image/jpeg'
            audio.clear_pictures()
            audio.add_picture(p)
        audio.save()
        return True

    # --- M4A/AAC Handlers (MP4 Atoms) ---
    def _load_mp4(self, path: str) -> Dict[str, Any]:
        audio = MP4(path)
        result = {}
        result['duration'] = audio.info.length if audio.info else 0
        result[self.KEY_TITLE] = audio.get('\xa9nam', [''])[0]
        result[self.KEY_ARTIST] = audio.get('\xa9ART', [''])[0]
        result[self.KEY_ALBUM] = audio.get('\xa9alb', [''])[0]
        result[self.KEY_YEAR] = audio.get('\xa9day', [''])[0]
        result[self.KEY_GENRE] = audio.get('\xa9gen', [''])[0]
        result[self.KEY_COMMENT] = audio.get('\xa9cmt', [''])[0]
        result[self.KEY_ALBUM_ARTIST] = audio.get('aART', [''])[0]
        result[self.KEY_COMPOSER] = audio.get('\xa9wrt', [''])[0]
        result[self.KEY_LABEL] = audio.get('----:com.apple.iTunes:PUBLISHER', audio.get('----:com.apple.iTunes:LABEL', ['']))[0]
        result[self.KEY_CATALOG] = audio.get('----:com.apple.iTunes:CATALOGNUMBER', [''])[0]

        cpil = audio.get('cpil')
        result[self.KEY_COMPILATION] = "1" if cpil and cpil[0] else "0"

        disk = audio.get('disk')
        if disk:
            result[self.KEY_DISC] = str(disk[0][0])
            
        trkn = audio.get('trkn')
        if trkn:
            result[self.KEY_TRACK] = str(trkn[0][0])
            
        # Cover Art
        if 'covr' in audio:
            covers = audio['covr']
            if covers:
                data = covers[0]
                ext = '.jpg'
                # MP4Cover might have imageformat attr, or we guess
                # The data itself is usually raw bytes
                cover_path = self._extract_cover(data, ext)
                if cover_path:
                    result['cover_path'] = cover_path
            
        return result

    def _save_mp4(self, path: str, tags: Dict[str, Any], cover_art_path: str = None) -> bool:
        audio = MP4(path)
        
        def set_atom(atom, key):
            if key in tags:
                if tags[key]:
                    audio[atom] = str(tags[key])
                elif atom in audio:
                    del audio[atom]
        
        set_atom('\xa9nam', self.KEY_TITLE)
        set_atom('\xa9ART', self.KEY_ARTIST)
        set_atom('\xa9alb', self.KEY_ALBUM)
        set_atom('\xa9day', self.KEY_YEAR)
        set_atom('\xa9gen', self.KEY_GENRE)
        set_atom('\xa9cmt', self.KEY_COMMENT)
        set_atom('aART', self.KEY_ALBUM_ARTIST)
        set_atom('\xa9wrt', self.KEY_COMPOSER)
        set_atom('----:com.apple.iTunes:PUBLISHER', self.KEY_LABEL)
        set_atom('----:com.apple.iTunes:CATALOGNUMBER', self.KEY_CATALOG)

        if self.KEY_COMPILATION in tags:
            audio['cpil'] = [True if str(tags[self.KEY_COMPILATION]) in ("1", "True", "true") else False]

        if self.KEY_DISC in tags and tags[self.KEY_DISC]:
            try:
                d_num = int(tags[self.KEY_DISC])
                existing = audio.get('disk')
                d_total = 0
                if existing and len(existing) > 0:
                    d_total = existing[0][1]
                audio['disk'] = [(d_num, d_total)]
            except: pass
        
        if self.KEY_TRACK in tags and tags[self.KEY_TRACK]:
            try:
                # Need to preserve total tracks if possible, but simplest is just writing track num
                # 'trkn' takes [(track_num, total_tracks)]
                t_num = int(tags[self.KEY_TRACK])
                # Check if there was a total before
                existing = audio.get('trkn')
                t_total = 0
                if existing and len(existing) > 0:
                    t_total = existing[0][1]
                audio['trkn'] = [(t_num, t_total)]
            except ValueError:
                pass
        
        if cover_art_path and os.path.exists(cover_art_path):
             with open(cover_art_path, 'rb') as img:
                data = img.read()
             
             image_format = MP4Cover.FORMAT_JPEG
             if cover_art_path.lower().endswith('.png'):
                 image_format = MP4Cover.FORMAT_PNG
                 
             audio['covr'] = [MP4Cover(data, imageformat=image_format)]

        audio.save()
        return True

    @classmethod
    def resolve_format(cls, format_str: str, tags: Dict[str, Any]) -> str:
        """
        Replaces %placeholder% with actual tag values.
        """
        mapping = {
            '%artist%': tags.get(cls.KEY_ARTIST, ''),
            '%title%': tags.get(cls.KEY_TITLE, ''),
            '%album%': tags.get(cls.KEY_ALBUM, ''),
            '%year%': tags.get(cls.KEY_YEAR, ''),
            '%track%': tags.get(cls.KEY_TRACK, ''),
            '%genre%': tags.get(cls.KEY_GENRE, ''),
            '%comment%': tags.get(cls.KEY_COMMENT, ''),
        }
        
        result = format_str
        for placeholder, value in mapping.items():
            result = result.replace(placeholder, str(value))
        
        return result

    @classmethod
    def parse_filename(cls, format_str: str, filename: str) -> Dict[str, Any]:
        """
        Extracts tags from a filename based on a format string.
        """
        import re
        
        # Remove extension
        name_only = os.path.splitext(filename)[0]
        
        # Placeholders to internal keys mapping
        placeholders = {
            '%artist%': cls.KEY_ARTIST,
            '%title%': cls.KEY_TITLE,
            '%album%': cls.KEY_ALBUM,
            '%year%': cls.KEY_YEAR,
            '%track%': cls.KEY_TRACK,
            '%genre%': cls.KEY_GENRE,
            '%comment%': cls.KEY_COMMENT,
        }
        
        # Build regex pattern by escaping everything BUT the placeholders
        # We'll split the format string by placeholders
        parts = re.split(r'(%[a-z]+%)', format_str)
        
        pattern = ""
        found_any = False
        for i, part in enumerate(parts):
            if part in placeholders:
                key = placeholders[part]
                # If it's the last placeholder or the last non-empty part, make it greedy to capture rest of string
                # Otherwise non-greedy until next delimiter
                is_last_placeholder = (i == len(parts) - 1) or \
                                      (i == len(parts) - 2 and not parts[len(parts) - 1])
                
                pattern += f"(?P<{key}>.+)" if is_last_placeholder else f"(?P<{key}>.+?)"
                found_any = True
            else:
                pattern += re.escape(part)
        
        if not found_any:
            return {}

        pattern = f"^{pattern}$"
        
        try:
            match = re.match(pattern, name_only)
            if match:
                # Filter out empty or None matches
                return {k: v for k, v in match.groupdict().items() if v is not None}
        except Exception as e:
            print(f"Regex error: {e}")
            
        return {}

    @classmethod
    def guess_metadata_from_filename(cls, filename: str) -> Dict[str, Any]:
        """
        Attempts to guess metadata from filename using common patterns.
        Useful when file has no tags.
        """
        import re
        name_only = os.path.splitext(os.path.basename(filename))[0]
        
        guessed = {}

        # 1. Extract Catalog Number (e.g., [CAT001], [CAT-001])
        # Look for square brackets containing letters and numbers
        cat_match = re.search(r'\[([A-Z0-9\-]+)\]', name_only, re.I)
        if cat_match:
            guessed[cls.KEY_CATALOG] = cat_match.group(1)
            # Remove from name to simplify subsequent matching
            name_only = name_only.replace(cat_match.group(0), "").strip()
            name_only = re.sub(r'\s+', ' ', name_only).strip(" -_")

        # Common patterns (evaluated in order of specificity)
        # 1. Artist - Album - Track - Title
        # 2. Artist - Album - Title
        # 3. Artist - Title
        # 4. Track - Artist - Title
        # 5. Track - Title
        
        patterns = [
            # Artist - Album - Track - Title
            (r'^(?P<artist>.+?) - (?P<album>.+?) - (?P<track>\d+) - (?P<title>.+)$', ['artist', 'album', 'track', 'title']),
            # Artist - Album - Title
            (r'^(?P<artist>.+?) - (?P<album>.+?) - (?P<title>.+)$', ['artist', 'album', 'title']),
             # Track - Artist - Title
            (r'^(?P<track>\d+) - (?P<artist>.+?) - (?P<title>.+)$', ['track', 'artist', 'title']),
            # Artist - Title
            (r'^(?P<artist>.+?) - (?P<title>.+)$', ['artist', 'title']),
            # Track - Title
            (r'^(?P<track>\d+) - (?P<title>.+)$', ['track', 'title']),
        ]

        matched_pattern = False
        for regex, keys in patterns:
            match = re.match(regex, name_only)
            if match:
                data = match.groupdict()
                # Clean up
                for k, v in data.items():
                    guessed[k] = v.strip()
                matched_pattern = True
                break
        
        if not matched_pattern:
            guessed[cls.KEY_TITLE] = name_only
        
        return guessed
