
import unittest
import geojson
import pyproj
from clip_poly import ClipPolygon


class TestClipPolygon(unittest.TestCase):
    def test_gj_dict(self):
        geom_dict = {
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

        cp = ClipPolygon(geom_dict, 'NAD83')
        r = cp.gj_dict
        self.assertIsInstance(r, geojson.Polygon)
        self.assertEqual(geom_dict, r)

        geom_str = """{
                "type": "Polygon", "coordinates": [[
                [-105, 40],[-80, 40],[-80, 20],[-105, 20],[-105, 40]
            ]]}"""
        cp = ClipPolygon(geom_dict, 'NAD83')
        r = cp.gj_dict
        self.assertIsInstance(r, geojson.Polygon)
        self.assertEqual(geom_dict, r)

    def test_crs(self):
        geom_str = """{
                "type": "Polygon", "coordinates": [[
                [-105, 40],[-80, 40],[-80, 20],[-105, 20],[-105, 40]
            ]]}"""
        cp = ClipPolygon(geom_str, 'NAD83')
        r = cp.crs
        self.assertIsInstance(r, pyproj.crs.CRS)
        self.assertEqual(('EPSG', '4269'), r.to_authority())

