
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

    def test_equals(self):
        sg1 = SubsetPolygon(self.geom_dict, 'NAD83')
        sg2 = SubsetPolygon(self.geom_dict, 'NAD83')
        self.assertTrue(sg1 == sg2)

        # Polygons with different numbers of vertices.
        sg2 = SubsetPolygon(
            [ [-105, 40],[-80, 40],[-80, 20],[-105, 40] ], 'NAD83'
        )
        self.assertFalse(sg1 == sg2)

        # Same number of vertices with one coordinate pair different.
        sg1 = SubsetPolygon(
            [ [-105, 40],[-80, 40],[-80, 20],[-105, 40] ], 'NAD83'
        )
        sg2 = SubsetPolygon(
            [ [-105, 40],[-80, 39],[-80, 20],[-105, 40] ], 'NAD83'
        )
        self.assertFalse(sg1 == sg2)

        # Polygons with the same coordinates but different CRSes.
        sg2 = SubsetPolygon(self.geom_dict, 'EPSG:4326')
        self.assertFalse(sg1 == sg2)

        # Different geometry types.
        sg1 = SubsetPolygon(
            [ [-105, 40],[-80, 40],[-80, 20],[-105, 40] ], 'NAD83'
        )
        sg2 = SubsetMultiPoint(
            [ [-105, 40],[-80, 40],[-80, 20],[-105, 20] ], 'NAD83'
        )
        self.assertFalse(sg1 == sg2)

        # Comparison to non-SubsetGeom.
        self.assertFalse(sg1 == 123)

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

    def test_equals(self):
        sg1 = SubsetMultiPoint(self.geom_dict, 'NAD83')
        sg2 = SubsetMultiPoint(self.geom_dict, 'NAD83')
        self.assertTrue(sg1 == sg2)

        # Different numbers of points.
        sg2 = SubsetMultiPoint(
            [ [-105, 40],[-80, 40],[-80, 20] ], 'NAD83'
        )
        self.assertFalse(sg1 == sg2)

        # Same number of points with one coordinate pair different.
        sg1 = SubsetMultiPoint(
            [ [-105, 40],[-80, 40],[-80, 20],[-105, 20] ], 'NAD83'
        )
        sg2 = SubsetMultiPoint(
            [ [-105, 39],[-80, 40],[-80, 20],[-105, 20] ], 'NAD83'
        )
        self.assertFalse(sg1 == sg2)

        # Same coordinates but different CRSes.
        sg2 = SubsetMultiPoint(self.geom_dict, 'EPSG:4326')
        self.assertFalse(sg1 == sg2)

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

