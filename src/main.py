import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt, QTimer
from src.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Nexus Music Tag & Downloader")
    
    # Set App Icon
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Show Splash Screen
    splash_path = os.path.join(os.path.dirname(__file__), "assets", "splash.png")
    splash = None
    if os.path.exists(splash_path):
        pixmap = QPixmap(splash_path)
        # Scale splash to reasonable size (e.g. 400x400)
        pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        splash = QSplashScreen(pixmap)
        splash.show()
    
    window = MainWindow()
    
    def show_main():
        if splash:
            splash.finish(window)
        window.show()
        
    # Show window after a 1 second delay
    QTimer.singleShot(1000, show_main)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
