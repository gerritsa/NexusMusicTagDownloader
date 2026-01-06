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
        
        # Check central widget is QSplitter
        central = window.centralWidget()
        self.assertEqual(central.__class__.__name__, 'QSplitter')
        
        # Check it contains TagEditor and Tabs
        self.assertEqual(central.count(), 2)
        self.assertEqual(central.widget(0).__class__.__name__, 'TagEditor')
        self.assertEqual(central.widget(1).__class__.__name__, 'QTabWidget')
        
        tabs = central.widget(1)
        self.assertEqual(tabs.count(), 2)
        self.assertEqual(tabs.tabText(0), "Library")
        self.assertEqual(tabs.tabText(1), "Downloads")
        
        # Check TagEditor access
        self.assertTrue(window.tag_editor)
        self.assertTrue(window.tag_editor.title_edit)

if __name__ == '__main__':
    unittest.main()