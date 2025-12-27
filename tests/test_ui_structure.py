import unittest
import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.ui.main_window import MainWindow

# Initialize App once
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

class TestUIStructure(unittest.TestCase):
    def test_mainwindow_components(self):
        window = MainWindow()
        
        # Check central widget is TabWidget
        central = window.centralWidget()
        self.assertEqual(central.__class__.__name__, 'QTabWidget')
        
        # Check tabs exist
        self.assertEqual(central.count(), 2)
        self.assertEqual(central.tabText(0), "Library")
        self.assertEqual(central.tabText(1), "Downloads")
        
        # Check Dock
        docks = window.findChildren(type(window.dock))
        self.assertTrue(len(docks) >= 1)
        
        # Check TagEditor
        self.assertTrue(window.tag_editor)
        self.assertTrue(window.tag_editor.btn_save)

if __name__ == '__main__':
    unittest.main()
