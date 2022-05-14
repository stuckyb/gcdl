
import unittest
from api_core import data_request, RequestDate as RD, DataRequestHandler
from api_core.data_request import ANNUAL, MONTHLY, DAILY, REQ_RASTER, REQ_POINT
from pyproj.crs import CRS
from library.catalog import DatasetCatalog
from library.datasets.gsdataset import GSDataSet
from subset_geom import SubsetPolygon, SubsetMultiPoint

# Two stub GSDataSets with different grid sizes to test buffering
class StubDS1(GSDataSet):
    """
    A concrete child class that stubs abstract methods.
    """
    def __init__(self, store_path):
        super().__init__(store_path, 'stub1')
        self.name = 'ds1'
        self.crs = CRS.from_epsg(5070)
        self.grid_size = 4000
        self.grid_unit = 'meters'

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        return None

class StubDS2(GSDataSet):
    """
    A concrete child class that stubs abstract methods.
    """
    def __init__(self, store_path):
        super().__init__(store_path, 'stub2')
        self.name = 'ds2'
        self.crs = CRS.from_epsg(4326)
        self.grid_size = 0.05
        self.grid_unit = 'degrees'

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        return None


class TestDataRequestHandler(unittest.TestCase):

    def setUp(self):
        self.dsc =  DatasetCatalog('test_data')
        self.dsc.addDatasetsByClass(StubDS1,StubDS2)
        self.dsvars = {'ds1':'', 'ds2':''}

        # Set up a basic DataRequestHandler object.
        self.drh = DataRequestHandler()

    def test_requestDateAsString(self):
        drh = self.drh

        # Test annual
        exp = '1980'
        r = drh._requestDateAsString(ANNUAL, RD(1980,None,None))
        self.assertEqual(exp, r)

        # Test monthly
        exp = '1980-01'
        r = drh._requestDateAsString(MONTHLY, RD(1980,1,None))
        self.assertEqual(exp, r)

        # Test daily
        exp = '1980-01-01'
        r = drh._requestDateAsString(DAILY, RD(1980,1,1))
        self.assertEqual(exp, r)

        # Test mismatched grain and rdate
        with self.assertRaisesRegex(
            ValueError, 'Invalid date granularity specification'
        ):
            drh._requestDateAsString(DAILY, RD(1980,1,None))


    def test_getPointLayer(self):
        pass

    def test_getRasterLayer(self):
        pass

    def test_buildDatasetSubsetGeoms(self):
        drh = self.drh

        # Test points not needing reprojection
        sg1 = SubsetMultiPoint(
            [ [-105, 40],[-80, 40],[-80, 20],[-105, 40] ], 'EPSG:4326'
        )
        exp = {'ds2' : sg1}
        r = drh._buildDatasetSubsetGeoms(
            self.dsc, {'ds2' : ''},
            sg1, REQ_POINT
        )

        # Test points needing reprojection 
        sg1 = SubsetMultiPoint(
            [ [-105, 40],[-80, 40],[-80, 20],[-105, 40] ], 'EPSG:4269'
        )
        exp = {'ds2' : sg1.reproject('EPSG:4269')}
        r = drh._buildDatasetSubsetGeoms(
            self.dsc, {'ds2' : ''},
            sg1, REQ_POINT
        )

        # Test polygon not needing reprojection
        sg1 = SubsetPolygon(
            [ [-105, 40],[-80, 40],[-80, 20],[-105, 40] ], 'EPSG:4326'
        )
        exp = {'ds2' : sg1}
        r = drh._buildDatasetSubsetGeoms(
            self.dsc, {'ds2' : ''},
            sg1, REQ_RASTER
        )

        # Test polygon needing reprojection 


    def test_getGrainAndDates(self):
        pass

    def test_collectRasterData(self):
        pass

    def test_collectPointData(self):
        pass

    def test_fulfillRequestSynchronous(self):
        pass