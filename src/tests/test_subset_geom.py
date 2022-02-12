
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
        sg = SubsetGeom(self.geom_str_poly, 'NAD83')
        r = sg.crs
        self.assertIsInstance(r, pyproj.crs.CRS)
        self.assertEqual(('EPSG', '4269'), r.to_authority())

    def test_reproject(self):
        geom_multi = {
            'type': 'MultiPoint',
            'coordinates': [
                [-105, 40], [-80, 40]
            ]
        }

        sg = SubsetGeom(geom_multi, 'NAD83')

        # The expected reprojected values in Web Mercator (Pseudo-Mercator),
        # rounded to the nearest integer.
        exp = {
            'type': 'MultiPoint',
            'coordinates': [
                [-11688547, 4865942], [-8905559, 4865942]
            ]
        }

        tr_sg = sg.reproject(pyproj.crs.CRS('EPSG:3857'))
        tr_sg_gj = tr_sg.gj_dict
        self.assertEqual('MultiPoint', tr_sg_gj['type'])
        coords_rounded = [
            [round(c[0]), round(c[1])] for c in tr_sg_gj['coordinates']
        ]
        self.assertEqual(exp['coordinates'], coords_rounded)
        self.assertEqual(('EPSG', '3857'), tr_sg.crs.to_authority())
        
        # Verify that the source SubsetGeom has not changed.
        self.assertEqual(geom_multi, sg.gj_dict)
        self.assertEqual(('EPSG', '4269'), sg.crs.to_authority())

