
import unittest
import tempfile
import io
from pathlib import Path
import os
import time
from pyproj import CRS
from api_core.upload_cache import DataUploadCache


class TestDataUploadCache(unittest.TestCase):
    # Define test input data of 24 bytes.
    fdata1 = b'lat,long\n0.0,1.0\n2.0,3.0'

    # Define test input data of 32 bytes.
    fdata2 = b'lat,long\n0.0,1.0\n2.0,3.0\n4.0,5.0'

    def test_addFile(self):
        # Create an in-memory file-like object.
        finput = io.BytesIO(self.fdata1)

        # This test needs to write to the cache, so use a temporary directory.
        with tempfile.TemporaryDirectory() as tdir:
            tpath = Path(tdir)

            # Upload file data and verify that the cache file exists and the
            # contents are correct.
            uc = DataUploadCache(tdir, 1024)

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
            uc = DataUploadCache(tdir, len(self.fdata1), chunk_size=2)

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
            uc = DataUploadCache(tdir, len(self.fdata1) - 1, chunk_size=2)

            # There should be 2 files in the cache at this point.
            self.assertEqual(2, len(list(tpath.iterdir())))

            finput.seek(0)
            with self.assertRaisesRegex(Exception, 'exceeded maximum .* size'):
                guid = uc.addFile(finput, 'tfile.csv')

            # Verify that there are still only 2 files in the cache.
            self.assertEqual(2, len(list(tpath.iterdir())))

    def test_contains(self):
        # Create an in-memory file-like object.
        finput = io.BytesIO(self.fdata1)

        # This test needs to write to the cache, so use a temporary directory.
        with tempfile.TemporaryDirectory() as tdir:
            tpath = Path(tdir)

            # Upload file data.
            uc = DataUploadCache(tdir, 1024)
            guid = uc.addFile(finput, 'tfile.csv')

            self.assertFalse(uc.contains('invalid_guid'))
            self.assertTrue(uc.contains(guid))

    def test_getStats(self):
        # This test needs to write to the cache, so use a temporary directory.
        with tempfile.TemporaryDirectory() as tdir:
            tpath = Path(tdir)

            uc = DataUploadCache(tdir, 1024)

            # Upload one file and verify cache stats.
            finput = io.BytesIO(self.fdata1)
            uc.addFile(finput, 'tfile1.csv')

            self.assertEqual((1, 24), uc.getStats())

            # Upload a second file and verify cache stats.
            finput = io.BytesIO(self.fdata2)
            uc.addFile(finput, 'tfile2.csv')

            self.assertEqual((2, 56), uc.getStats())

    def test_readCSV(self):
        # Test files with all allowable lower-case column names.
        file1 = Path('data/upload_cache/csv_1.csv')
        file2 = Path('data/upload_cache/csv_2.csv')
        file3 = Path('data/upload_cache/csv_3.csv')
        # Test file with valid upper-case column names.
        file4 = Path('data/upload_cache/csv_4.csv')
        # Test file with invalid column name.
        file5 = Path('data/upload_cache/csv_5.csv')

        exp = [(0.0, 1.0), (2.0, 3.0)]

        uc = DataUploadCache('data/upload_cache', 1024)

        # Test files with all allowable x and y column names.
        for fpath in (file1, file2, file3):
            r = uc._readCSV(fpath)
            self.assertEqual(exp, r)

        # Verify that column recognition is not case-sensitive.
        r = uc._readCSV(file4)
        self.assertEqual(exp, r)

        # Test a file with an invalid column name.
        with self.assertRaisesRegex(Exception, 'Could not find .* columns'):
            r = uc._readCSV(file5)

    def test_readGeoJSONPoints(self):
        uc = DataUploadCache('data/upload_cache', 1024)

        # Point object.
        exp = [[0.0, 1.0]]
        gfile = Path('data/upload_cache/geojson_point.json')
        r = uc._readGeoJSONPoints(gfile)
        self.assertEqual(exp, r)
        
        # MultiPoint object.
        exp = [[0.0, 1.0], [2.0, 3.0]]
        gfile = Path('data/upload_cache/geojson_multipoint1.json')
        r = uc._readGeoJSONPoints(gfile)
        self.assertEqual(exp, r)
        
        # GeometryCollection object.
        exp = [[0.0, 1.0], [2.0, 3.0], [4.0, 5.0]]
        gfile = Path('data/upload_cache/geojson_geometrycoll.json')
        r = uc._readGeoJSONPoints(gfile)
        self.assertEqual(exp, r)
        
        # Feature object.
        exp = [[0.0, 1.0]]
        gfile = Path('data/upload_cache/geojson_feature_pnt.json')
        r = uc._readGeoJSONPoints(gfile)
        self.assertEqual(exp, r)
        
        # FeatureCollection object.
        exp = [[0.0, 1.0], [2.0, 3.0]]
        gfile = Path('data/upload_cache/geojson_featurecoll_pnt.json')
        r = uc._readGeoJSONPoints(gfile)
        self.assertEqual(exp, r)
        
        # Test an incorrect geometry type (Polygon, in this case).
        gfile = Path('data/upload_cache/geojson_polygon.json')
        with self.assertRaisesRegex(
            Exception, 'Unsupported .* geometry type for point data'
        ):
            r = uc._readGeoJSONPoints(gfile)

    def test_readShapefilePoints(self):
        uc = DataUploadCache('data/upload_cache', 1024)

        # Shapefile without containing folder in archive, no CRS information.
        exp = [(0.0, 1.0), (2.0, 3.0)]
        gfile = Path('data/upload_cache/shapefile_pnt-no_crs-no_dir.zip')
        r, crs = uc._readShapefilePoints(gfile)
        self.assertEqual(exp, r)
        self.assertIsNone(crs)

        # Shapefile with containing folder in archive, no CRS information.
        exp = [(0.0, 1.0), (2.0, 3.0)]
        gfile = Path('data/upload_cache/shapefile_pnt-no_crs-in_dir.zip')
        r, crs = uc._readShapefilePoints(gfile)
        self.assertEqual(exp, r)
        self.assertIsNone(crs)

        # Shapefile with containing folder in archive, with CRS information.
        exp = [(0.0, 1.0), (2.0, 3.0)]
        exp_crs = CRS('epsg:4326')
        gfile = Path('data/upload_cache/shapefile_pnt-with_crs-in_dir.zip')
        r, crs = uc._readShapefilePoints(gfile)
        self.assertEqual(exp, r)
        self.assertEqual(exp_crs.to_authority(), crs.to_authority())

    def test_getMultiPoint(self):
        exp = {
            'coordinates': [[0.0, 1.0], [2.0, 3.0]],
            'type': 'MultiPoint'
        }
        exp_crs = CRS('epsg:4326')

        uc = DataUploadCache('data/upload_cache', 1024)

        # Test pulling data from a CSV file with an extension from the cache.
        r = uc.getMultiPoint('csv_1', 'epsg:4326')
        self.assertEqual(exp, r.json)
        self.assertTrue(exp_crs.equals(r.crs))

        # Test pulling data from a CSV file without an extension from the
        # cache.
        r = uc.getMultiPoint('csv_6', 'epsg:4326')
        self.assertEqual(exp, r.json)
        self.assertTrue(exp_crs.equals(r.crs))

        # Test pulling data from a GeoJSON file with an extension from the
        # cache.
        r = uc.getMultiPoint('geojson_multipoint1', 'epsg:4326')
        self.assertEqual(exp, r.json)
        self.assertTrue(exp_crs.equals(r.crs))

        # Test pulling data from a GeoJSON file without an extension from the
        # cache.
        r = uc.getMultiPoint('geojson_multipoint2', 'epsg:4326')
        self.assertEqual(exp, r.json)
        self.assertTrue(exp_crs.equals(r.crs))

        # Test pulling data from a shapefile with no CRS information.
        r = uc.getMultiPoint('shapefile_pnt-no_crs-in_dir', 'epsg:4326')
        self.assertEqual(exp, r.json)
        self.assertTrue(exp_crs.equals(r.crs))

        # Test pulling data from a shapefile with CRS information.
        r = uc.getMultiPoint('shapefile_pnt-with_crs-in_dir', None)
        self.assertEqual(exp, r.json)
        self.assertFalse(exp_crs.equals(r.crs))
        self.assertEqual(exp_crs.to_authority(), r.crs.to_authority())

        # Test an invalid GUID.
        with self.assertRaisesRegex(Exception, 'No cached .* data found'):
            r = uc.getMultiPoint('invalid_ID')

        # Test a non-unique GUID.
        with self.assertRaisesRegex(Exception, 'does not appear to be unique'):
            r = uc.getMultiPoint('csv_')

        # Test a file that cannot be parsed as point data.
        with self.assertRaisesRegex(Exception, 'No .* point data found'):
            r = uc.getMultiPoint('invalid_data')

    def test_clean(self):
        # This test needs to write to the cache, so use a temporary directory.
        with tempfile.TemporaryDirectory() as tdir:
            tpath = Path(tdir)

            # Create a new upload cache and set the retention time to 1 minute.
            uc = DataUploadCache(tdir, 1024, retention_time=60)

            # Upload two files to the cache.
            finput = io.BytesIO(self.fdata1)
            guid1 = uc.addFile(finput, 'tfile1.csv')

            finput = io.BytesIO(self.fdata2)
            guid2 = uc.addFile(finput, 'tfile2.csv')

            # Set the atime of the second file to 70 seconds ago.
            now = time.time()
            os.utime(tpath / (guid2 + '.csv'), times=(now - 70, now - 70))

            uc.clean()

            # Verify that the first file is still in the cache and the second
            # file is gone.
            self.assertTrue(uc.contains(guid1))
            self.assertFalse(uc.contains(guid2))

