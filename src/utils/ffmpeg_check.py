import shutil
import subprocess

def is_ffmpeg_installed() -> bool:
    """
    Checks if ffmpeg is available in the system PATH.
    """
    if shutil.which('ffmpeg'):
        return True
    
    # Fallback: try running it?
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False
