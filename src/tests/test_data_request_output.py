
import unittest
from pyproj.crs import CRS
from library.catalog import DatasetCatalog
from shapely.geometry import Point
import geopandas as gpd
from pathlib import Path
import pandas as pd
import datetime as dt
from api_core import data_request, DataRequest, DataRequestOutput
from library.datasets.gsdataset import GSDataSet
from subset_geom import SubsetPolygon, SubsetMultiPoint


class StubDS1(GSDataSet):
    """
    A concrete child class that stubs abstract methods.
    """
    def __init__(self, store_path):
        super().__init__(store_path, 'stub')
        self.name = 'ds1'
        self.date_ranges['year'] = [
            dt.date(1980, 1, 1), dt.date(1980, 1, 1)
        ]

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        return None

class StubDS2(GSDataSet):
    """
    A concrete child class that stubs abstract methods.
    """
    def __init__(self, store_path):
        super().__init__(store_path, 'stub')
        self.name = 'ds2'
        self.date_ranges['year'] = [
            dt.date(1980, 1, 1), dt.date(1980, 1, 1)
        ]

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        return None

class TestDataRequestOutput(unittest.TestCase):

    # Write test output files to temp output folder
    outdir = Path('../../output/testing')
    outdir.mkdir(exist_ok=True)

    # Test point data
    test_gdf = gpd.GeoDataFrame(
        {
            'time': [1980, 1980],
            'dataset': ['ds1', 'ds1'],
            'variable': ['var1', 'var1'],
            'value': [11, 22],  
            'geometry': [Point(1, 2), Point(2, 1)]
        }, 
        crs="EPSG:4326"
    )

    test_gdf2 = gpd.GeoDataFrame(
        {
            'time': [1980, 1980],
            'dataset': ['ds2', 'ds2'],
            'variable': ['var2', 'var2'],
            'value': [111, 222],  
            'geometry': [Point(1, 2), Point(2, 1)]
        }, 
        crs="EPSG:4326"
    )


    def setUp(self):
        # Set up a basic DataRequestOutput object.
        self.dro = DataRequestOutput()
        self.dsc =  DatasetCatalog('test_data')
        self.dsc.addDatasetsByClass(StubDS1,StubDS2)


    def test_getSingleLayerOutputFileName(self):
        dro = self.dro

        # Test with date
        exp = 'ds1_var1_2021'
        r = dro._getSingleLayerOutputFileName('ds1','var1','2021')
        self.assertEqual(exp, r)

        # Test without date
        exp = 'ds1_var1'
        r = dro._getSingleLayerOutputFileName('ds1','var1','')
        self.assertEqual(exp, r)

    def test_rgbaToHex(self):
        dro = self.dro

        # Test white with alpha
        exp = '#ffffff'
        r = dro._rgbaToHex((255,255,255,255))
        self.assertEqual(exp, r)

        # Test white without alpha
        exp = '#ffffff'
        r = dro._rgbaToHex((255,255,255))
        self.assertEqual(exp, r)

        # Test some random color
        exp = '#32a852'
        r = dro._rgbaToHex((50, 168, 82))
        self.assertEqual(exp, r)

    def test_writeCSV(self):
        dro = self.dro

        fname = self.outdir / 'writeCSV.csv'
        dro._writeCSV(self.test_gdf, fname)

        exp = pd.DataFrame(
            {
                'time': [1980, 1980],
                'dataset': ['ds1', 'ds1'],
                'variable': ['var1', 'var1'],
                'value': [11, 22], 
                'x': [1,2],
                'y': [2,1]
            }
        )
        r = pd.read_csv(fname)

        # x,y columns equivalent to point coordinates
        self.assertEqual(r['x'].tolist(), self.test_gdf.geometry.x.tolist())
        self.assertEqual(r['y'].tolist(), self.test_gdf.geometry.y.tolist())

        # Values are the same
        self.assertEqual(exp['value'].tolist(), r['value'].tolist())
    
        # Column names are the same
        self.assertEqual(exp.columns.tolist(), r.columns.tolist())

        # No geometry column in file
        self.assertFalse('geometry' in r.columns)

    def test_writeShapefile(self):
        dro = self.dro

        fname = self.outdir / 'writeShapefile.shp'
        dro._writeShapefile(self.test_gdf, fname)

        exp = self.test_gdf
        r = gpd.read_file(fname)

        # Same CRS
        self.assertEqual(exp.geometry.crs, r.geometry.crs)

        # Same geometry
        self.assertEqual(exp.geom_type.tolist(), r.geom_type.tolist())
        self.assertEqual(exp.geometry.x.tolist(), r.geometry.x.tolist())
        self.assertEqual(exp.geometry.y.tolist(), r.geometry.y.tolist())

        # Same values
        self.assertEqual(exp['value'].tolist(), r['value'].tolist())


    def test_assignCategories(self):
        pass

    def test_writeNetCDF(self):
        dro = self.dro

        fname = self.outdir / 'writeNetCDF.nc'

        # Point data
        r = dro._writeNetCDF(self.test_gdf, fname)

        #exp = 



    def test_writeGeoTIFF(self):
        pass

    def test_writePointFiles(self):
        dro = self.dro

        test_output_dict = {
            'ds1' : self.test_gdf,
            'ds2' : self.test_gdf2
        }

        # CSV
        test_req = DataRequest(
            self.dsc, {'ds1' : 'var1', 'ds2' : 'var2'},
            # Date parameters.
            '1980', None, None, None, None, None,
            # Subset geometry.
            SubsetMultiPoint([[1,2],[2,1]], 'EPSG:4326'),
            # Projection/resolution parameters.
            CRS('EPSG:4326'), None, None,
            # Output parameters.
            data_request.REQ_POINT, 'csv',
            {}
        )
        exp = [self.outdir / 'ds1_ds2.csv']
        r = dro._writePointFiles(test_output_dict, test_req, self.outdir)
        self.assertEqual(exp,r)
        self.assertTrue(exp[0].exists())

        # Shapefile
        shp_outdir = self.outdir / 'shp'
        shp_outdir.mkdir(exist_ok=True)
        test_req = DataRequest(
            self.dsc, {'ds1' : 'var1', 'ds2' : 'var2'},
            # Date parameters.
            '1980', None, None, None, None, None,
            # Subset geometry.
            SubsetMultiPoint([[1,2],[2,1]], 'EPSG:4326'),
            # Projection/resolution parameters.
            CRS('EPSG:4326'), None, None,
            # Output parameters.
            data_request.REQ_POINT, 'shapefile',
            {}
        )
        exp = [
            shp_outdir / 'ds1_ds2.shx',
            shp_outdir / 'ds1_ds2.shp',
            shp_outdir / 'ds1_ds2.cpg',
            shp_outdir / 'ds1_ds2.dbf',
            shp_outdir / 'ds1_ds2.prj']
        r = dro._writePointFiles(test_output_dict, test_req, shp_outdir)
        self.assertEqual(exp,r)
        self.assertTrue(exp[0].exists())

        # NetCDF



    def test_writeRasterFiles(self):
        pass

    def test_writeMetadataFile(self):
        pass

    def test_writeRequestedData(self):
        pass