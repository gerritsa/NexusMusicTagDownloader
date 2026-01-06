# Nexus Music Tag & Downloader

**Nexus Music Tag & Downloader** is a Python-based desktop application (GUI) built with **PySide6**. It integrates audio downloading (via `yt-dlp`) with advanced metadata editing (via `mutagen`) and Discogs API integration.

## 📂 Project Structure

### Core Directories (`src/`)

*   **`src/main.py`**: The application entry point. Initializes the `QApplication`, Splash Screen, and Main Window.
*   **`src/ui/`**: Contains all PySide6 UI components.
    *   `main_window.py`: The primary container widget and layout. Contains the "Smart Match" logic (`_on_match_discogs_smart`).
    *   `tag_editor.py`: The sidebar widget for editing tags (Artist, Title, Artwork).
    *   `download_queue.py`: Manages the list of active/completed downloads.
    *   `file_list.py`: Displays loaded audio files for batch editing.
    *   `discogs_dialog.py`: Dialogs for Discogs release selection and album mapping review.
*   **`src/core/`**: Contains the business logic, decoupled from the UI where possible.
    *   `metadata_manager.py`: A wrapper around `mutagen`. Handles reading/writing tags (MP3, FLAC, M4A) and filename metadata guessing.
    *   `download_manager.py`: Wraps `yt-dlp` to handle audio downloads.
    *   `discogs_manager.py`: Interacts with the Discogs API for metadata search, supporting structured queries (Artist, Release, Track, CatNo) and duration parsing.
    *   `file_scanner.py`: Scans directories for supported audio files.
*   **`src/assets/`**: Static assets like icons (`icon.png`).

### Build & Distribution

*   **`build_app.py`**: A script using **PyInstaller** to package the application into a standalone executable (`.app` on macOS, `.exe` on Windows).
*   **`requirements.txt`**: List of Python dependencies.

## 🚀 Development Guide

### 1. Environment Setup

The project requires Python 3.10+.

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Application

Execute the main script from the project root:

```bash
python src/main.py
```

### 3. Running Tests

Tests are located in the `tests/` directory and use the standard `unittest` framework. Some tests require **FFmpeg** to generate dummy audio files.

```bash
python -m unittest discover tests
```

### 4. Building for Production

To create a standalone executable/app bundle in the `dist/` folder:

```bash
python build_app.py
```

## 🏗 Architecture & Conventions

*   **UI/Logic Separation**: Heavy operations (downloads, API searches) are offloaded to `QThread` workers (e.g., `DiscogsSearchWorker` in `discogs_manager.py`) to keep the UI responsive.
*   **Signals & Slots**: Communication between the backend logic and the UI relies heavily on PySide6 Signals.
*   **Metadata Handling**: The `MetadataManager` class normalizes tag keys (e.g., 'TIT2' -> 'title') to simplify UI binding. Always use the constants defined in `MetadataManager` (e.g., `KEY_TITLE`, `KEY_ARTIST`) when working with tags.
*   **Smart Matching**: The `_on_match_discogs_smart` workflow (in `MainWindow`) acts as the central logic for metadata enrichment. It prioritizes data in this order:
    1.  Catalog Number (if found in filename).
    2.  Existing Metadata (Artist/Album).
    3.  Filename Guessing (Regex extraction).
    4.  Fallback Probing (Using track titles to find albums).
*   **Asset Paths**: Use `src.core.utils.resource_path()` to resolve file paths for assets like images. This ensures paths work correctly both in development and in the frozen PyInstaller build.

### Additional Coding Preferences

*   **Code Style**: Follow PEP 8 conventions with a focus on readability and maintainability.
*   **Error Handling**: Implement proper error handling and logging using Python's `logging` module.
*   **Testing**: Write unit tests for critical functionality (e.g., metadata parsing, download logic).
*   **Documentation**: Document the codebase using docstrings and comments where necessary.