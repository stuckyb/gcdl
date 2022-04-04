
import unittest
import tempfile
import io
from pathlib import Path
from api_core.upload_cache import UploadDataCache


class TestUploadDataCache(unittest.TestCase):
    def test_addFile(self):
        # Define test input data and an in-memory file-like object.
        fdata = b'lat,long\n0.0,0.0\n1.0,1.0'
        finput = io.BytesIO(fdata)

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
            self.assertEqual(fdata, obs_data)

            # Test maximum upload size enforcement.  First, test that we can
            # upload a file of exactly the maximum allowable size.  Set a small
            # chunk size to ensure that at least some data chunks are
            # processed.
            uc = UploadDataCache(tdir, len(fdata), chunk_size=2)

            finput.seek(0)
            guid = uc.addFile(finput, 'tfile.csv')

            exp_path = tpath / (guid + '.csv')
            self.assertTrue(exp_path.is_file())

            with open(exp_path, 'rb') as fin:
                obs_data = fin.read()
            self.assertEqual(fdata, obs_data)

            # Test maximum upload size enforcement.  Test an upload that is
            # exactly 1 byte more than the maximum allowable size.  Set a small
            # chunk size to ensure that at least some data chunks are
            # processed.
            uc = UploadDataCache(tdir, len(fdata) - 1, chunk_size=2)

            # There should be 2 files in the cache at this point.
            self.assertEqual(2, len(list(tpath.glob('*'))))

            finput.seek(0)
            with self.assertRaisesRegex(Exception, 'exceeded maximum .* size'):
                guid = uc.addFile(finput, 'tfile.csv')

            # Verify that there are still only 2 files in the cache.
            self.assertEqual(2, len(list(tpath.glob('*'))))

