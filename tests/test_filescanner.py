import unittest
import os
import shutil
import subprocess

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.file_scanner import FileScanner

class TestFileScanner(unittest.TestCase):
    TEST_DIR = 'test_assets_scanner'
    
    @classmethod
    def setUpClass(cls):
        # Create test directory structure
        if os.path.exists(cls.TEST_DIR):
            shutil.rmtree(cls.TEST_DIR)
        os.makedirs(os.path.join(cls.TEST_DIR, 'subdir'))
        
        # Create dummy files (empty is fine for extension check, 
        # but MetadataManager might complain if they are invalid audio.
        # So we should use ffmpeg or just mock MetadataManager.
        # For an integration test, let's copy the one valid MP3 we generated in the previous test steps 
        # or generate new ones.
        
        # Generating 1s silence again is safer as previous test might stick around or be cleaned up class-dependently
        # Note: Previous test cleaned up in tearDownClass.
        
        cls.files = [
            os.path.join(cls.TEST_DIR, 'audio.mp3'),
            os.path.join(cls.TEST_DIR, 'subdir', 'audio.flac'),
            os.path.join(cls.TEST_DIR, 'ignore.txt')
        ]
        
        subprocess.run(['ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', '1', cls.files[0]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', '1', cls.files[1]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        with open(cls.files[2], 'w') as f:
            f.write('dummy')

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TEST_DIR):
             shutil.rmtree(cls.TEST_DIR)

    def test_scan(self):
        scanner = FileScanner()
        tracks = scanner.scan_directory(self.TEST_DIR)
        
        # Should find 2 files
        self.assertEqual(len(tracks), 2)
        
        # Verify paths
        found_paths = [t.file_path for t in tracks]
        self.assertIn(self.files[0], found_paths)
        self.assertIn(self.files[1], found_paths)
        self.assertNotIn(self.files[2], found_paths)

if __name__ == '__main__':
    unittest.main()
