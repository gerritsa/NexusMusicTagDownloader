import os
import discogs_client
import requests
import re
from PySide6.QtCore import QObject, Signal, QThread

class DiscogsSearchWorker(QThread):
    """Worker thread for Discogs search to avoid blocking the UI"""
    finished = Signal(list)  # List of search results
    error = Signal(str)
    
    def __init__(self, discogs_client, artist: str, title: str):
        super().__init__()
        self.client = discogs_client
        self.artist = artist
        self.title = title
    
    def run(self):
        try:
            # Clean query
            raw_query = f"{self.artist} {self.title}"
            query = DiscogsManager.clean_query(raw_query)
            
            print(f"Discogs Search: '{raw_query}' -> Cleaned: '{query}'")
            
            if not query:
                print("Discogs Search: Aborted (empty query)")
                self.error.emit("No artist/title information to search")
                return
                
            results = self.client.search(query, type='release')
            print(f"Discogs Search: Found {len(results)} potential matches")
            
            # Convert to list of dicts for easier handling
            matches = []
            for i, release in enumerate(results):
                if i >= 20: break # Fetch more to find CD versions, then filter
                try:
                    # Accessing certain attributes might trigger more network requests or errors
                    r_id = getattr(release, 'id', None)
                    # Strip numbers from artist names like "Jon Hopkins (4)"
                    def clean_artist_name(name):
                        return re.sub(r'\s*\(\d+\)$', '', name)
                    
                    r_artists = ', '.join([clean_artist_name(a.name) for a in release.artists]) if hasattr(release, 'artists') and release.artists else ''
                    
                    # Clean up titles that include the artist redundantly
                    r_title = getattr(release, 'title', 'Unknown Title')
                    if r_artists and r_title.lower().startswith(r_artists.lower()):
                        # Strip "Artist - " from the start of the title
                        r_title = re.sub(fr"^{re.escape(r_artists)}\s*[-:]\s*", "", r_title, flags=re.I)

                    r_year = getattr(release, 'year', '')
                    r_label = release.labels[0].name if hasattr(release, 'labels') and release.labels else ''
                    r_thumb = getattr(release, 'thumb', '')
                    
                    # Detect format (CD preferred)
                    r_format = ''
                    is_cd = False
                    try:
                        formats = release.formats if hasattr(release, 'formats') else []
                        if formats:
                            format_names = [f.get('name', '') for f in formats]
                            r_format = ', '.join(format_names)
                            is_cd = any('cd' in fn.lower() for fn in format_names)
                    except:
                        pass

                    matches.append({
                        'id': r_id,
                        'title': r_title,
                        'year': r_year,
                        'label': r_label,
                        'artists': r_artists,
                        'thumb': r_thumb,
                        'format': r_format,
                        'is_cd': is_cd,
                    })
                    format_tag = " [CD]" if is_cd else ""
                    print(f"  - Match {i+1}: {r_artists} - {r_title} ({r_year}){format_tag}")
                except Exception as e:
                    print(f"  - Error parsing search result {i+1}: {e}")
                    continue
            
            # Sort to prioritize CD releases, then limit to 10
            matches.sort(key=lambda m: (not m['is_cd'], m.get('year', '9999')))
            matches = matches[:10]
                    
            self.finished.emit(matches)
        except Exception as e:
            err_msg = str(e)
            if "401" in err_msg:
                err_msg = "Discogs API Token is invalid or has expired. Please check your token in Settings."
            self.error.emit(err_msg)


class DiscogsManager(QObject):
    """
    Manages Discogs API interactions for metadata enrichment.
    """
    
    def __init__(self, token: str = None):
        super().__init__()
        self.token = token
        self.client = None
        if self.token:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Discogs client with the API token"""
        try:
            self.client = discogs_client.Client('TagNexus/1.0', user_token=self.token)
        except Exception as e:
            print(f"Failed to initialize Discogs client: {e}")
            self.client = None
    
    def set_token(self, token: str):
        """Update the API token and reinitialize the client"""
        self.token = token
        self._initialize_client()
    
    def search_async(self, artist: str, title: str):
        """
        Search Discogs asynchronously.
        Returns a worker thread that emits results when done.
        """
        if not self.client:
            return None
        
        worker = DiscogsSearchWorker(self.client, artist, title)
        return worker
    
    def get_release_data(self, release_id: int):
        """Fetch detailed release information"""
        if not self.client:
            return None
            
        try:
            release = self.client.release(release_id)
            
            # Extract comprehensive metadata safely
            # Try multiple ways to get label/catno as Discogs data can be inconsistent
            labels = getattr(release, 'labels', [])
            primary_label_name = ""
            primary_catno = ""
            
            if labels:
                primary_label_name = labels[0].name if hasattr(labels[0], 'name') else ""
                # Use .data to get catno safely
                label_data = labels[0].data if hasattr(labels[0], 'data') else {}
                primary_catno = label_data.get('catno', "")
            
            if not primary_label_name or not primary_catno:
                # Fallback to raw data dict
                raw_labels = release.data.get('labels', [{}])
                if raw_labels and not primary_label_name:
                    primary_label_name = raw_labels[0].get('name', "")
                if raw_labels and not primary_catno:
                    primary_catno = raw_labels[0].get('catno', "")

            def clean_artist_name(name):
                return re.sub(r'\s*\(\d+\)$', '', name)
            
            data = {
                'title': release.title,
                'artists': ', '.join([clean_artist_name(a.name) for a in release.artists]) if release.artists else '',
                'album': release.title,  # For releases, title is the album
                'year': str(release.year) if hasattr(release, 'year') and release.year else '',
                'label': primary_label_name,
                'catalog_number': primary_catno,
                'genre': ', '.join(release.genres) if release.genres else '',
                'style': ', '.join(release.styles) if hasattr(release, 'styles') and release.styles else '',
                'cover_image': release.images[0]['uri'] if release.images else '',
                'tracklist': release.tracklist if hasattr(release, 'tracklist') else [],
                'compilation': '1' if self._is_compilation(release) else '0',
            }
            
            return data
        except Exception as e:
            print(f"Error fetching release {release_id}: {e}")
            return None
    
    def _is_compilation(self, release):
        """Detect if a release is a compilation."""
        try:
            # Check for "Various" or "Various Artists" as artist
            if hasattr(release, 'artists') and release.artists:
                artist_names = [a.name.lower() for a in release.artists]
                if any('various' in name for name in artist_names):
                    return True
            
            # Check tracklist for multiple distinct artists
            if hasattr(release, 'tracklist') and release.tracklist:
                track_artists = set()
                for track in release.tracklist:
                    if hasattr(track, 'artists') and track.artists:
                        for a in track.artists:
                            track_artists.add(a.name.lower())
                # If more than 3 distinct track artists, likely a compilation
                if len(track_artists) > 3:
                    return True
            
            return False
        except:
            return False
    
    def download_cover_art(self, image_url: str, output_path: str):
        """Download cover art from Discogs"""
        try:
            # Discogs requires a User-Agent for image downloads
            headers = {
                'User-Agent': 'TagNexus/1.0 +https://github.com/berriebeer/NexusMusicTagDownloader'
            }
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            print(f"Failed to download cover art: {e}")
            return False
    
    def auto_match(self, artist: str, title: str):
        """
        Attempt to auto-match a track to a Discogs release.
        Returns release_id if confident, None otherwise.
        """
        try:
            raw_query = f"{artist} {title}"
            query = self.clean_query(raw_query)
            
            print(f"Discogs Auto-match: Searching for '{query}'")
            
            if not query:
                return None
                
            results = self.client.search(query, type='release')
            
            # Get first result
            first_result = None
            try:
                # results is a SearchList, accessing results[0] might trigger the request/error
                first_result = results[0] if results else None
            except Exception as e:
                # This is likely where the 401 happens
                err_msg = str(e)
                if "401" in err_msg:
                    print("Discogs Auto-match: 401 Unauthorized. Check your API token.")
                return None
            
            if not first_result:
                return None
            
            # Check confidence: exact artist + title match
            result_artist = ', '.join([a.name for a in first_result.artists]) if first_result.artists else ''
            result_title = first_result.title
            
            # Simple fuzzy matching (case-insensitive contains)
            if artist.lower() in result_artist.lower() and title.lower() in result_title.lower():
                print(f"Discogs Auto-match: Confident match found! ID: {first_result.id} ({result_artist} - {result_title})")
                return first_result.id
            
            print(f"Discogs Auto-match: Ambiguous match. Top result: '{result_artist} - {result_title}' does not closely enough match '{artist} - {title}'")
            # If ambiguous, return None (user will manually select)
            return None
            
        except Exception as e:
            print(f"Auto-match error: {e}")
            return None

    @staticmethod
    def clean_query(text: str) -> str:
        """Strips common YouTube/metadata garbage from search queries."""
        if not text: return ""
        
        # Remove anything in brackets or parentheses like (Official Video), [HQ], etc.
        junk_pattern = r'[\(\[][^\]\)]*(Official|Video|Audio|4K|HD|HQ|Lyrics|Visualizer|Live|Set|Stream|Upload|Record|Premiere)[^\]\)]*[\)\]]'
        text = re.sub(junk_pattern, '', text, flags=re.I)
        
        # Remove specific common strings
        junk_strings = [
            'Official Video', 'Official Audio', 'Official Music Video',
            'Full Set', '3-HR SET', 'CLOSING SET', 'at 909 Festival', 'AMSTERDAM',
            'Exclusive', 'Visualizer', 'Music Video'
        ]
        for item in junk_strings:
            text = re.sub(re.escape(item), '', text, flags=re.I)
            
        text = text.replace(' B2B ', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        return text
