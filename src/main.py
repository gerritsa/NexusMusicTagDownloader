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
    
    # High DPI (Retina) Support
    dpr = 1.0
    if QApplication.instance():
        dpr = QApplication.instance().primaryScreen().devicePixelRatio()
    
    pixmap = QPixmap(int(width * dpr), int(height * dpr))
    pixmap.setDevicePixelRatio(dpr)
    
    # Background
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    
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
        logo_size = 120
        # Scale to physical pixels (size * dpr) for maximum sharpness
        physical_size = int(logo_size * dpr)
        scaled_logo = logo.scaled(physical_size, physical_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled_logo.setDevicePixelRatio(dpr)
        
        lx, ly = (width - logo_size) // 2, 40
        painter.drawPixmap(lx, ly, scaled_logo)
        
    # Title
    font_title = QFont("Helvetica", 28, QFont.Bold)
    painter.setFont(font_title)
    painter.setPen(QColor("#ffffff"))
    title_rect = painter.fontMetrics().boundingRect("NEXUS")
    painter.drawText((width - title_rect.width()) // 2, 190, "NEXUS")
    
    font_subtitle = QFont("Helvetica", 14)
    painter.setFont(font_subtitle)
    painter.setPen(QColor("#cccccc"))
    subtitle_rect = painter.fontMetrics().boundingRect("Music Tag & Downloader")
    painter.drawText((width - subtitle_rect.width()) // 2, 220, "Music Tag & Downloader")
    
    # Author & Version
    font_small = QFont("Helvetica", 10)
    painter.setFont(font_small)
    painter.setPen(QColor("#666666"))
    painter.drawText(20, height - 20, "by BerrieBeer")
    painter.drawText(width - 60, height - 20, "v1.0.0")
    
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
