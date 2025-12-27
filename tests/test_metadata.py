import unittest
import os
import shutil
import subprocess
from PIL import Image

# Import the class to test (adjust path if needed or run from root)
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.metadata_manager import MetadataManager

class TestMetadataManager(unittest.TestCase):
    TEST_DIR = 'test_assets'
    
    @classmethod
    def setUpClass(cls):
        # Create test directory
        if os.path.exists(cls.TEST_DIR):
            shutil.rmtree(cls.TEST_DIR)
        os.makedirs(cls.TEST_DIR)
        
        # Create dummy cover art
        cls.cover_jpg = os.path.join(cls.TEST_DIR, 'cover.jpg')
        img = Image.new('RGB', (100, 100), color = 'red')
        img.save(cls.cover_jpg)

        # Generate audio files using ffmpeg
        # 1 second of silence
        cls.files = {
            'mp3': os.path.join(cls.TEST_DIR, 'test.mp3'),
            'flac': os.path.join(cls.TEST_DIR, 'test.flac'),
            'm4a': os.path.join(cls.TEST_DIR, 'test.m4a'),
        }

        print("Generating test files...")
        subprocess.run(['ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', '1', '-q:a', '9', cls.files['mp3']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', '1', cls.files['flac']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(['ffmpeg', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-t', '1', '-c:a', 'aac', cls.files['m4a']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def tearDownClass(cls):
        # Cleanup
        if os.path.exists(cls.TEST_DIR):
             shutil.rmtree(cls.TEST_DIR)

    def setUp(self):
        self.mm = MetadataManager()
        self.sample_tags = {
            'title': 'Test Title',
            'artist': 'Test Artist',
            'album': 'Test Album',
            'year': '2023',
            'track': '1',
            'genre': 'Test Genre',
            'comment': 'Test Comment'
        }

    def test_mp3_metadata(self):
        path = self.files['mp3']
        # Write
        self.assertTrue(self.mm.save_tags(path, self.sample_tags, self.cover_jpg))
        
        # Read
        tags = self.mm.load_tags(path)
        self.assertEqual(tags.get('title'), 'Test Title')
        self.assertEqual(tags.get('artist'), 'Test Artist')
        self.assertEqual(tags.get('year'), '2023')
        # Check comment
        self.assertEqual(tags.get('comment'), 'Test Comment')

    def test_flac_metadata(self):
        path = self.files['flac']
        # Write
        self.assertTrue(self.mm.save_tags(path, self.sample_tags, self.cover_jpg))
        
        # Read
        tags = self.mm.load_tags(path)
        self.assertEqual(tags.get('title'), 'Test Title')
        self.assertEqual(tags.get('artist'), 'Test Artist')

    def test_m4a_metadata(self):
        path = self.files['m4a']
        # Write
        self.assertTrue(self.mm.save_tags(path, self.sample_tags, self.cover_jpg))
        
        # Read
        tags = self.mm.load_tags(path)
        self.assertEqual(tags.get('title'), 'Test Title')
        self.assertEqual(tags.get('artist'), 'Test Artist')
        self.assertEqual(tags.get('track'), '1')

    def test_utf8_chars(self):
        path = self.files['mp3']
        utf8_tags = {
            'title': 'F?nky Title ???',
            'artist': 'Bj?rk'
        }
        self.mm.save_tags(path, utf8_tags)
        read_tags = self.mm.load_tags(path)
        self.assertEqual(read_tags.get('title'), 'F?nky Title ???')
        self.assertEqual(read_tags.get('artist'), 'Bj?rk')

if __name__ == '__main__':
    unittest.main()
