
import unittest
from pyproj.crs import CRS
from api_core.helpers import (
    parse_datasets_str, parse_clip_bounds, parse_coords, get_request_metadata,
    assume_crs, get_target_crs
)
from subset_geom import SubsetPolygon


class TestHelpers(unittest.TestCase):

    def test_parse_datasets_str(self):
        pass

    def test_parse_coords(self):
        pass

    def test_parse_clip_bounds(self):
        pass

    def test_get_request_metadata(self):
        pass

    def test_assume_crs(self):
        pass
        # 

    def test_get_target_crs(self):
        pass
        
        # Test user geometries
        poly_geom1 = SubsetPolygon(
            parse_clip_bounds('(0,1),(1,0)'), 
            'EPSG:5070'
        )
        poly_geom2 = SubsetPolygon(
            parse_clip_bounds('(0,1),(1,0)'), 
            'EPSG:4326'
        )

        exp = None
        r = get_target_crs(None, None, poly_geom1)
        self.assertEqual(exp, r)

        exp = CRS('EPSG:5070')
        r = get_target_crs(None, 1, poly_geom1)
        self.assertTrue(exp.equals(r))

        exp = CRS('EPSG:4326')
        r = get_target_crs('EPSG:4326', None, poly_geom1)

        exp = CRS('EPSG:4326')
        r = get_target_crs('EPSG:4326', 1, poly_geom1)

        exp = CRS('EPSG:4326')
        r = get_target_crs('EPSG:4326', None, poly_geom2)

        exp = CRS('EPSG:4326')
        r = get_target_crs('EPSG:4326', 1, poly_geom2)
    
