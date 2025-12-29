import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.utils import resource_path

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont, QLinearGradient, QPainterPath
from PySide6.QtCore import Qt, QTimer
from src.ui.main_window import MainWindow

def create_splash_pixmap():
    width, height = 500, 300
    pixmap = QPixmap(width, height)
    # Background
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0, QColor("#1a1a2e"))
    gradient.setColorAt(1, QColor("#16213e"))
    painter.setBrush(gradient)
    painter.setPen(Qt.NoPen)
    painter.drawRect(0, 0, width, height)
    
    # Logo
    icon_path = resource_path(os.path.join("src", "assets", "icon.png"))
    if os.path.exists(icon_path):
        logo = QPixmap(icon_path)
        logo_size = 64
        scaled_logo = logo.scaled(logo_size, logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        # Draw with rounded corners clipping
        painter.save()
        lx, ly = width - logo_size - 30, 30
        path = QPainterPath()
        path.addRoundedRect(lx, ly, logo_size, logo_size, 14, 14)
        painter.setClipPath(path)
        painter.drawPixmap(lx, ly, scaled_logo)
        painter.restore()
        
    # Title
    font_title = QFont("Helvetica", 32, QFont.Bold)
    painter.setFont(font_title)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(40, 110, "NEXUS")
    
    font_subtitle = QFont("Helvetica", 16)
    painter.setFont(font_subtitle)
    painter.setPen(QColor("#cccccc"))
    painter.drawText(40, 145, "Music Tag & Downloader")
    
    # Author & Version
    font_small = QFont("Helvetica", 11)
    painter.setFont(font_small)
    painter.setPen(QColor("#888888"))
    painter.drawText(40, height - 35, "by BerrieBeer")
    painter.drawText(width - 80, height - 35, "v1.0.0")
    
    painter.end()
    return pixmap

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Nexus Music Tag & Downloader")
    
    # Set App Icon
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Show Splash Screen
    splash_pixmap = create_splash_pixmap()
    splash = QSplashScreen(splash_pixmap)
    splash.show()
    
    window = MainWindow()
    
    def show_main():
        splash.finish(window)
        window.show()
        
    # Show window after a 1.2 second delay for better feel
    QTimer.singleShot(1200, show_main)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
