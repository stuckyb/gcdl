
import unittest
import tempfile
import io
from pathlib import Path
from api_core.upload_cache import UploadDataCache


class TestUploadDataCache(unittest.TestCase):
    # Define test input data of 24 bytes.
    fdata1 = b'lat,long\n0.0,0.0\n1.0,1.0'

    # Define test input data of 32 bytes.
    fdata2 = b'lat,long\n0.0,0.0\n1.0,1.0\n2.0,2.0'

    def test_addFile(self):
        # Create an in-memory file-like object.
        finput = io.BytesIO(self.fdata1)

        with tempfile.TemporaryDirectory() as tdir:
            tpath = Path(tdir)

            # "Upload" file data and verify that the cache file exists and the
            # contents are correct.
            uc = UploadDataCache(tdir, 1024)

            guid = uc.addFile(finput, 'tfile.csv')

            exp_path = tpath / (guid + '.csv')
            self.assertTrue(exp_path.is_file())

            with open(exp_path, 'rb') as fin:
                obs_data = fin.read()
            self.assertEqual(self.fdata1, obs_data)

            # Test maximum upload size enforcement.  First, test that we can
            # upload a file of exactly the maximum allowable size.  Set a small
            # chunk size to ensure that at least some data chunks are
            # processed.
            uc = UploadDataCache(tdir, len(self.fdata1), chunk_size=2)

            finput.seek(0)
            guid = uc.addFile(finput, 'tfile.csv')

            exp_path = tpath / (guid + '.csv')
            self.assertTrue(exp_path.is_file())

            with open(exp_path, 'rb') as fin:
                obs_data = fin.read()
            self.assertEqual(self.fdata1, obs_data)

            # Test maximum upload size enforcement.  Test an upload that is
            # exactly 1 byte more than the maximum allowable size.  Set a small
            # chunk size to ensure that at least some data chunks are
            # processed.
            uc = UploadDataCache(tdir, len(self.fdata1) - 1, chunk_size=2)

            # There should be 2 files in the cache at this point.
            self.assertEqual(2, len(list(tpath.iterdir())))

            finput.seek(0)
            with self.assertRaisesRegex(Exception, 'exceeded maximum .* size'):
                guid = uc.addFile(finput, 'tfile.csv')

            # Verify that there are still only 2 files in the cache.
            self.assertEqual(2, len(list(tpath.iterdir())))

    def test_getCacheStats(self):
        with tempfile.TemporaryDirectory() as tdir:
            tpath = Path(tdir)

            uc = UploadDataCache(tdir, 1024)

            # "Upload" one file and verify cache stats.
            finput = io.BytesIO(self.fdata1)
            uc.addFile(finput, 'tfile1.csv')

            self.assertEqual((1, 24), uc.getCacheStats())

            # "Upload" a second file and verify cache stats.
            finput = io.BytesIO(self.fdata2)
            uc.addFile(finput, 'tfile2.csv')

            self.assertEqual((2, 56), uc.getCacheStats())

