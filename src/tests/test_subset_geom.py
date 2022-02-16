
import unittest
import geojson
import pyproj
from subset_geom import SubsetPolygon, SubsetMultiPoint


class TestSubsetPolygon(unittest.TestCase):
    # Define test data.
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

    geom_str = """{
            "type": "Polygon", "coordinates": [[
            [-105, 40],[-80, 40],[-80, 20],[-105, 20],[-105, 40]
        ]]}"""

    geom_coords = [ [-105, 40],[-80, 40],[-80, 20],[-105, 20],[-105, 40] ]

    def test_json(self):
        # Test initialization from dictionary.
        sg = SubsetPolygon(self.geom_dict, 'NAD83')
        r = sg.json
        self.assertIsInstance(r, geojson.Polygon)
        self.assertEqual(self.geom_dict, r)

        # Test initialization from string.
        sg = SubsetPolygon(self.geom_str, 'NAD83')
        r = sg.json
        self.assertIsInstance(r, geojson.Polygon)
        self.assertEqual(self.geom_dict, r)

        # Test initialization from coordinates list.
        sg = SubsetPolygon(self.geom_coords, 'NAD83')
        r = sg.json
        self.assertIsInstance(r, geojson.Polygon)
        self.assertEqual(self.geom_dict, r)

    def test_crs(self):
        sg = SubsetPolygon(self.geom_str, 'NAD83')
        r = sg.crs
        self.assertIsInstance(r, pyproj.crs.CRS)
        self.assertEqual(('EPSG', '4269'), r.to_authority())

    def test_reproject(self):
        sg = SubsetPolygon(self.geom_dict, 'NAD83')

        # The expected reprojected values in Web Mercator (Pseudo-Mercator),
        # rounded to the nearest integer.
        exp = {
            'type': 'Polygon',
            'coordinates': [[
                [-11688547, 4865942],
                [-8905559, 4865942],
                [-8905559, 2273031],
                [-11688547, 2273031],
                [-11688547, 4865942]
            ]]
        }

        tr_sg = sg.reproject(pyproj.crs.CRS('EPSG:3857'))
        tr_sg_gj = tr_sg.json
        self.assertEqual('Polygon', tr_sg_gj['type'])
        coords_rounded = [
            [round(c[0]), round(c[1])] for c in tr_sg_gj['coordinates'][0]
        ]
        self.assertEqual(exp['coordinates'][0], coords_rounded)
        self.assertEqual(('EPSG', '3857'), tr_sg.crs.to_authority())
        self.assertIsInstance(tr_sg, SubsetPolygon)
        
        # Verify that the source SubsetPolygon has not changed.
        self.assertEqual(self.geom_dict, sg.json)
        self.assertEqual(('EPSG', '4269'), sg.crs.to_authority())


class TestSubsetMultiPoint(unittest.TestCase):
    # Define test data.
    geom_dict = {
        'type': 'MultiPoint',
        'coordinates': [
            [-105, 40],
            [-80, 40],
            [-80, 20],
            [-105, 20],
        ]
    }

    geom_str = """{
            "type": "MultiPoint", "coordinates": [
            [-105, 40],[-80, 40],[-80, 20],[-105, 20]
        ]}"""

    geom_coords = [ [-105, 40],[-80, 40],[-80, 20],[-105, 20] ]

    def test_json(self):
        # Test initialization from dictionary.
        sg = SubsetMultiPoint(self.geom_dict, 'NAD83')
        r = sg.json
        self.assertIsInstance(r, geojson.MultiPoint)
        self.assertEqual(self.geom_dict, r)

        # Test initialization from string.
        sg = SubsetMultiPoint(self.geom_str, 'NAD83')
        r = sg.json
        self.assertIsInstance(r, geojson.MultiPoint)
        self.assertEqual(self.geom_dict, r)

        # Test initialization from coordinates list.
        sg = SubsetMultiPoint(self.geom_coords, 'NAD83')
        r = sg.json
        self.assertIsInstance(r, geojson.MultiPoint)
        self.assertEqual(self.geom_dict, r)

    def test_crs(self):
        sg = SubsetMultiPoint(self.geom_str, 'NAD83')
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

        sg = SubsetMultiPoint(geom_multi, 'NAD83')

        # The expected reprojected values in Web Mercator (Pseudo-Mercator),
        # rounded to the nearest integer.
        exp = {
            'type': 'MultiPoint',
            'coordinates': [
                [-11688547, 4865942], [-8905559, 4865942]
            ]
        }

        tr_sg = sg.reproject(pyproj.crs.CRS('EPSG:3857'))
        tr_sg_gj = tr_sg.json
        self.assertEqual('MultiPoint', tr_sg_gj['type'])
        coords_rounded = [
            [round(c[0]), round(c[1])] for c in tr_sg_gj['coordinates']
        ]
        self.assertEqual(exp['coordinates'], coords_rounded)
        self.assertEqual(('EPSG', '3857'), tr_sg.crs.to_authority())
        self.assertIsInstance(tr_sg, SubsetMultiPoint)
        
        # Verify that the source SubsetGeom has not changed.
        self.assertEqual(geom_multi, sg.json)
        self.assertEqual(('EPSG', '4269'), sg.crs.to_authority())

