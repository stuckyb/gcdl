
import unittest
import geojson
import pyproj
from pathlib import Path
from pyproj.crs import CRS
from subset_geom import SubsetPolygon, SubsetMultiPoint
from library.datasets.tileset import TileSet


class TestTileSet(unittest.TestCase):
    def setUp(self):
        tdir = Path('data/tiles/')
        crs = CRS.from_epsg(4326)

        self.files = sorted(tdir.glob('tile_?.tif'))

        self.ts = TileSet(self.files, crs)

    def test_init(self):
        ts = self.ts

        self.assertTrue(CRS.from_epsg(4326).equals(ts.crs))

        self.assertEqual(4, len(ts.polys))
        self.assertEqual(4, len(ts.fpaths))

        # Define the expected coordinates of each tile in numerical order.
        exp = [
            [(-100,40), (-99,40), (-99,39), (-100,39), (-100,40)],
            [(-99,40), (-98,40), (-98,39), (-99,39), (-99,40)],
            [(-100,39), (-99,39), (-99,38), (-100,38), (-100,39)],
            [(-99,39), (-98,39), (-98,38), (-99,38), (-99,39)]
        ]

        for i, poly in enumerate(ts.polys):
            self.assertEqual(4.0, poly.length)
            self.assertEqual(exp[i], list(poly.exterior.coords))

    def test_getTilePaths(self):
        ts = self.ts

        # Test a single point in the middle of tile 0.
        sg = SubsetMultiPoint([[-99.5,39.5]], 'EPSG:4326')
        self.assertEqual(
            [self.files[0]], list(ts.getTilePaths(sg))
        )

        # Test points in the middle of tiles 0 and 3.
        sg = SubsetMultiPoint([[-99.5,39.5], [-98.5,38.5]], 'EPSG:4326')
        self.assertEqual(
            [self.files[0], self.files[3]], list(ts.getTilePaths(sg))
        )

        # Test a single point on the border between tiles 0 and 1.
        sg = SubsetMultiPoint([[-99.0,39.5]], 'EPSG:4326')
        self.assertEqual(
            [self.files[0], self.files[1]], list(ts.getTilePaths(sg))
        )

        # Test a polygon (triangle, in this case) inside tile 2.
        sg = SubsetPolygon(
            [(-99.8,38.5), (-99.2,38.8), (-99.2,38.2), (-99.8,38.5)],
            'EPSG:4326'
        )
        self.assertEqual(
            [self.files[2]], list(ts.getTilePaths(sg))
        )

        # Test a polygon that intersects tiles 2 and 3.
        sg = SubsetPolygon(
            [(-99.5,38.5), (-98.5,38.8), (-98.5,38.2), (-99.5,38.5)],
            'EPSG:4326'
        )
        self.assertEqual(
            [self.files[2], self.files[3]], list(ts.getTilePaths(sg))
        )

    def test_getRaster(self):
        ts = self.ts

        # Test a polygon (triangle, in this case) inside tile 2.
        sg = SubsetPolygon(
            [(-99.8,38.5), (-99.2,38.8), (-99.2,38.2), (-99.8,38.5)],
            'EPSG:4326'
        )
        mosaic = ts.getRaster(sg)
        self.assertEqual((-100, 38, -99, 39), mosaic.rio.bounds())
        self.assertEqual(5, mosaic.isel(band=0,x=0,y=0))

        # Test a polygon that intersects tiles 2 and 3.
        sg = SubsetPolygon(
            [(-99.5,38.5), (-98.5,38.8), (-98.5,38.2), (-99.5,38.5)],
            'EPSG:4326'
        )
        mosaic = ts.getRaster(sg)
        self.assertEqual((-100, 38, -98, 39), mosaic.rio.bounds())
        self.assertEqual(5, mosaic.isel(band=0,x=0,y=0))
        self.assertEqual(8, mosaic.isel(band=0,x=2,y=0))

