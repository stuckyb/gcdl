
import unittest
from pyproj.crs import CRS
from api_core.helpers import (
    parse_datasets_str, parse_clip_bounds, parse_coords, get_request_metadata,
    assume_crs, get_target_crs
)
from library.catalog import DatasetCatalog
from library.datasets.gsdataset import GSDataSet
from subset_geom import SubsetPolygon

# Stub GSDataSet with CRS
class StubDS(GSDataSet):
    """
    A concrete child class that stubs abstract methods.
    """
    def __init__(self, store_path):
        super().__init__(store_path, 'stub1')
        self.name = 'ds1'
        self.crs = CRS.from_epsg(4326)

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        return None

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
        
        # Test catalog and datasets
        ds = {'ds1' : ''}
        dsc =  DatasetCatalog('test_data')
        dsc.addDatasetsByClass(StubDS)

        exp = CRS('EPSG:4326')
        r = assume_crs(dsc, ds, None)
        self.assertTrue(exp.equals(r))

        exp = CRS('EPSG:3857')
        r = assume_crs(dsc, ds, 'EPSG:3857')
        self.assertTrue(exp.equals(r))


    def test_get_target_crs(self):
        
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
        self.assertTrue(exp.equals(r))

        exp = CRS('EPSG:4326')
        r = get_target_crs('EPSG:4326', 1, poly_geom1)
        self.assertTrue(exp.equals(r))

        exp = CRS('EPSG:4326')
        r = get_target_crs('EPSG:4326', None, poly_geom2)
        self.assertTrue(exp.equals(r))

        exp = CRS('EPSG:4326')
        r = get_target_crs('EPSG:4326', 1, poly_geom2)
        self.assertTrue(exp.equals(r))
    
