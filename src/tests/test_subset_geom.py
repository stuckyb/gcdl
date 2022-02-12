
import unittest
import geojson
import pyproj
from subset_geom import SubsetGeom


class TestSubsetGeom(unittest.TestCase):
    # Define test data.
    geom_dict_poly = {
        'type': 'Polygon',
        'coordinates': [[
            # Top left.
            [-105, 40],
            # Top right.
            [-80, 40],
            # Bottom right.
            [-80, 20],
            # Bottom left.
            [-105, 20],
            # Top left.
            [-105, 40]
        ]]
    }

    geom_str_poly = """{
            "type": "Polygon", "coordinates": [[
            [-105, 40],[-80, 40],[-80, 20],[-105, 20],[-105, 40]
        ]]}"""

    geom_dict_multi = {
        'type': 'MultiPoint',
        'coordinates': [
            [-105, 40],
            [-80, 40],
            [-80, 20],
            [-105, 20],
            [-105, 40]
        ]
    }

    def test_gj_dict(self):
        # Test polygon geometries.
        # Test initialization from dictionary.
        sg = SubsetGeom(self.geom_dict_poly, 'NAD83')
        r = sg.gj_dict
        self.assertIsInstance(r, geojson.Polygon)
        self.assertEqual(self.geom_dict_poly, r)

        # Test initialization from string.
        sg = SubsetGeom(self.geom_str_poly, 'NAD83')
        r = sg.gj_dict
        self.assertIsInstance(r, geojson.Polygon)
        self.assertEqual(self.geom_dict_poly, r)

        # Test multi-point geometries.
        # Test initialization from dictionary.
        sg = SubsetGeom(self.geom_dict_multi, 'NAD83')
        r = sg.gj_dict
        self.assertIsInstance(r, geojson.MultiPoint)
        self.assertEqual(self.geom_dict_multi, r)

    def test_crs(self):
        cp = SubsetGeom(self.geom_str_poly, 'NAD83')
        r = cp.crs
        self.assertIsInstance(r, pyproj.crs.CRS)
        self.assertEqual(('EPSG', '4269'), r.to_authority())

