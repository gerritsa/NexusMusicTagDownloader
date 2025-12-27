import os
from PySide6.QtCore import QObject, Signal, QThread
import yt_dlp

class DownloadWorker(QThread):
    progress = Signal(float)
    finished = Signal(str) # Emits filename
    error = Signal(str)
    log = Signal(str)

    def __init__(self, url: str, output_dir: str, format_key: str = 'mp3'):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.format_key = format_key

    def run(self):
        # Hooks for yt-dlp
        def progress_hook(d):
            if d['status'] == 'downloading':
                # Calculate progress
                try:
                    # Prefer byte calculation if available (more reliable for float)
                    if d.get('total_bytes') and d.get('downloaded_bytes'):
                         p = (d['downloaded_bytes'] / d['total_bytes']) * 100
                         self.progress.emit(p)
                    elif d.get('total_bytes_estimate') and d.get('downloaded_bytes'):
                         p = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                         self.progress.emit(p)
                    else:
                        # Fallback to string parsing
                        p_str = d.get('_percent_str', '0%')
                        import re
                        p_clean = re.sub(r'\x1b\[[0-9;]*m', '', p_str) # strip colors
                        p_clean = p_clean.replace('%','')
                        self.progress.emit(float(p_clean))
                except:
                    pass
            elif d['status'] == 'finished':
                self.progress.emit(100.0)
                self.log.emit(f"Download complete: {d['filename']}")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.format_key,
                    'preferredquality': '192',
                },
                {'key': 'EmbedThumbnail'},
                # {'key': 'FFmpegMetadata'}, # Disabled to prevent unwanted tags
            ],
            'writethumbnail': True,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            # Network stability fixes
            'force_ipv4': True,
            'retries': 10,
            'socket_timeout': 30,
            'continuedl': False, # Disable resume to prevent 416 errors
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                # Determine final filename
                # info['requested_downloads'] might contain the list
                filename = ydl.prepare_filename(info)
                # After post-processing, ext changes. 
                # Simple guess: replace ext with preferredcodec
                base, _ = os.path.splitext(filename)
                final_path = f"{base}.{self.format_key}"
                
                self.finished.emit(final_path)
        except Exception as e:
            self.error.emit(str(e))

class DownloadManager(QObject):
    """
    Manages multiple downloads.
    """
    download_added = Signal(DownloadWorker)

    def __init__(self, output_dir: str = None):
        super().__init__()
        self.output_dir = output_dir or os.path.expanduser("~/Downloads")
        self.workers = []

class FetchInfoWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }
        
        results = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                
                if 'entries' in info:
                    entries = list(info['entries'])
                else:
                    entries = [info]
                
                for entry in entries:
                    # Construct URL
                    video_url = entry.get('url')
                    if not video_url and entry.get('id'):
                         video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    
                    if video_url:
                        # Parse artist/title
                        title = entry.get('title', 'Unknown Title')
                        artist = entry.get('uploader', 'Unknown Artist')
                        # Basic split heuristic: "Artist - Title"
                        if ' - ' in title:
                            parts = title.split(' - ', 1)
                            artist = parts[0]
                            title = parts[1]
                        
                        # Extract Year
                        upload_date = entry.get('upload_date') # YYYYMMDD
                        year = ''
                        if upload_date and len(upload_date) >= 4:
                            year = upload_date[:4]

                        # Download Thumbnail
                        cover_path = None
                        thumb_url = entry.get('thumbnail')
                        if not thumb_url and entry.get('thumbnails'):
                             # Get last (usually highest res)
                             thumb_url = entry['thumbnails'][-1].get('url')
                        
                        if thumb_url:
                            print(f"DEBUG: Fetching thumbnail from: {thumb_url[:50]}...")
                            import urllib.request
                            import tempfile
                            try:
                                # Create temp file
                                temp_dir = tempfile.gettempdir()
                                valid_name = "".join(x for x in title if x.isalnum())[:20]
                                temp_path = os.path.join(temp_dir, f"tagnexus_thumb_{valid_name}.jpg")
                                
                                # Use User-Agent to avoid 403 Forbidden
                                req = urllib.request.Request(
                                    thumb_url, 
                                    headers={'User-Agent': 'Mozilla/5.0'}
                                )
                                with urllib.request.urlopen(req) as response, open(temp_path, 'wb') as out_file:
                                    out_file.write(response.read())
                                    
                                cover_path = temp_path
                            except Exception as e:
                                print(f"Thumbnail download failed: {e}")

                        results.append({
                            'url': video_url,
                            'title': title,
                            'artist': artist,
                            'year': year,
                            'comment': '', 
                            'track': '',   
                            'cover_path': cover_path, # Add cover path
                            'status': 'Pending'
                        })
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class DownloadManager(QObject):
    """
    Manages multiple downloads.
    """
    download_added = Signal(DownloadWorker)

    def __init__(self, output_dir: str = None):
        super().__init__()
        self.output_dir = output_dir or os.path.expanduser("~/Downloads")
        self.workers = []

    def fetch_info(self, url: str):
        """
        Starts an async fetch for metadata.
        Returns the worker instance so UI can connect signals.
        """
        worker = FetchInfoWorker(url)
        # We don't track fetch workers in self.workers necessarily, 
        # or we could if we want to cancel them.
        # But UI normally handles waiting.
        worker.start()
        return worker

    def start_download(self, job_data: dict):
        """
        Starts a download for a single job item.
        job_data: {'url', 'title', 'artist', ...}
        """
        url = job_data.get('url')
        worker = DownloadWorker(url, self.output_dir)
        self.workers.append(worker)
        
        # We need to pass metadata to apply post-download
        worker.job_data = job_data
        
        worker.finished.connect(lambda f: self._on_worker_finished(worker, f))
        worker.error.connect(lambda e: self._cleanup(worker))
        
        self.download_added.emit(worker)
        worker.start()
        return worker

    def _on_worker_finished(self, worker, filepath):
        # Apply metadata overrides
        if hasattr(worker, 'job_data'):
            from .metadata_manager import MetadataManager
            mm = MetadataManager()
            
            # 1. Apply Tags
            tags = mm.load_tags(filepath)
            
            job_title = worker.job_data.get('title')
            job_artist = worker.job_data.get('artist')
            job_year = worker.job_data.get('year')

            if job_title: tags['title'] = job_title
            if job_artist: tags['artist'] = job_artist
            if job_year: tags['year'] = job_year
            
            # Explicitly clear others if not in job_data (or if we want them empty)
            # But TagEditor might have set them? Check job_data
            if 'comment' in worker.job_data: tags['comment'] = worker.job_data['comment']
            if 'track' in worker.job_data: tags['track'] = worker.job_data['track']
            if 'genre' in worker.job_data: tags['genre'] = worker.job_data['genre']
            
            data_dict = {
               'title': tags.get('title'),
               'artist': tags.get('artist'),
               'year': tags.get('year'),
               'comment': tags.get('comment'),
               'track': tags.get('track'),
               'genre': tags.get('genre'),
            }
            
            # 2. Thumbnail Handling
            # Priority: 
            # 1. Preloaded cover from job_data (guaranteed to be the one user saw)
            # 2. Sidecar file from yt-dlp
            cover_path = worker.job_data.get('cover_path')
            
            if not cover_path or not os.path.exists(cover_path):
                # Fallback to looking for sidecar
                base_path, _ = os.path.splitext(filepath)
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    possible_thumb = base_path + ext
                    if os.path.exists(possible_thumb):
                        cover_path = possible_thumb
                        break
            
            # Save tags + Cover
            mm.save_tags(filepath, data_dict, cover_path)
            
            # Cleanup sidecar thumbnail ONLY (not the preloaded one, or do we want to clean that too?)
            # The preloaded one is in temp, OS cleans it, but we can be nice.
            # However, logic below was assuming sidecar.
            # If we use preloaded, we might want to keep it if user re-downloads? 
            # Actually temp files are fine to leave or clean.
            # Let's clean if it looks like a Sidecar (same basename).
            if cover_path and os.path.exists(cover_path):
                # Only delete if it looks like a sidecar generated by yt-dlp near the mp3
                if os.path.dirname(cover_path) == os.path.dirname(filepath):
                     try:
                        os.remove(cover_path)
                     except:
                        pass
            
            # Cleanup thumbnail
            if cover_path and os.path.exists(cover_path):
                try:
                    os.remove(cover_path)
                except:
                    pass

            # 3. Rename to "Artist - Title.ext"
            final_title = tags.get('title', 'Unknown Title')
            final_artist = tags.get('artist', 'Unknown Artist')
            
            # Sanitize
            safe_title = MetadataManager.sanitize_filename(final_title)
            safe_artist = MetadataManager.sanitize_filename(final_artist)
            
            new_filename = f"{safe_artist} - {safe_title}"
            _, ext = os.path.splitext(filepath)
            
            new_filepath = os.path.join(os.path.dirname(filepath), new_filename + ext)
            
            if new_filepath != filepath:
                # Collision check
                counter = 1
                while os.path.exists(new_filepath):
                    new_filepath = os.path.join(os.path.dirname(filepath), f"{new_filename} ({counter}){ext}")
                    counter += 1
                
                try:
                    os.rename(filepath, new_filepath)
                    print(f"Renamed to: {new_filepath}")
                except OSError as e:
                    print(f"Rename failed: {e}")

        self._cleanup(worker)

    def _cleanup(self, worker):
        if worker in self.workers:
            worker.wait()
            # self.workers.remove(worker) 
            pass
