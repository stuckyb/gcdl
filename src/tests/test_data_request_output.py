
import unittest
from pyproj.crs import CRS
from library.catalog import DatasetCatalog
from shapely.geometry import Point
import geopandas as gpd
from pathlib import Path
import pandas as pd
import datetime as dt
import tempfile
import xarray as xr
import rioxarray
import numpy as np
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

        with tempfile.TemporaryDirectory() as tdir:
            outdir = Path(tdir)
            fname = outdir / 'writeCSV.csv'
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
            self.assertEqual(
                r['x'].tolist(), self.test_gdf.geometry.x.tolist()
            )
            self.assertEqual(
                r['y'].tolist(), self.test_gdf.geometry.y.tolist()
            )

            # Values are the same
            self.assertEqual(exp['value'].tolist(), r['value'].tolist())
        
            # Column names are the same
            self.assertEqual(exp.columns.tolist(), r.columns.tolist())

            # No geometry column in file
            self.assertFalse('geometry' in r.columns)

    def test_writeShapefile(self):
        dro = self.dro

        with tempfile.TemporaryDirectory() as tdir:
            outdir = Path(tdir)
            fname = outdir / 'writeShapefile.shp'
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
        dro = self.dro

        # Test RAT w/o colormap for geotiff 
        #dro._assignCategories(test_RAT, None, None, fname)

        # Test RAT and colormap for geotiff, single band
        #dro._assignCategories(test_RAT, test_cm, None, fname)

        # Test colormap w/o RAT for geotiff
        #dro._assignCategories(None, test_cm, None, fname)


        # Test RAT w/o colormap for netcdf
        #dro._assignCategories(test_RAT, None, test_data, None)

        # Test RAT and colormap for netcdf, single band
        #dro._assignCategories(test_RAT, None, test_data, None)

        # Test colormap w/o RAT for netcdf
        #dro._assignCategories(test_RAT, None, test_data, None)


        # Test RAT w/o colormap for shapefile
        #dro._assignCategories(test_RAT, None, test_data, None)

        # Test RAT and colormap for shapefile, single band
        #dro._assignCategories(test_RAT, test_cm, test_data, None)

        # Test RAT and colormap for shapefile, multiple bands

        # Test colormap w/o RAT for shapefile


        # Test RAT w/o colormap for csv

        # Test RAT and colormap for csv, single band

        # Test RAT and colormap for csv, multiple bands

        # Test colormap w/o RAT for csv

        

    def test_writeNetCDF(self):
        dro = self.dro

        with tempfile.TemporaryDirectory() as tdir:
            outdir = Path(tdir)
            fname = outdir / 'writeNetCDF.nc'

            # Point data
            dro._writeNetCDF(self.test_gdf, fname)

            exp = pd.DataFrame(
                {
                    'time': [1980, 1980],
                    'dataset': ['ds1', 'ds1'],
                    'variable': ['var1', 'var1'],
                    'value': [11, 22],  
                    'x': [1,2],
                    'y': [2,1]
                }
            ).set_index(['x','y','time']).to_xarray()
            exp.rio.write_crs(self.test_gdf.geometry.crs, inplace=True)
            r = xr.open_dataset(fname)

            # Same CRS
            self.assertEqual(exp['spatial_ref'].crs_wkt, r['spatial_ref'].crs_wkt)

            # Same geometry
            self.assertTrue((exp['x'] == r['x']).all())
            self.assertTrue((exp['y'] == r['y']).all())

            # Same values
            exp_vals = exp['value'].values
            r_vals = r['value'].values
            same = [exp_vals[i] == r_vals[i] for i in [0,1]]
            exp_nan = np.isnan(exp_vals)
            r_nan = np.isnan(r_vals)
            self.assertTrue((same | (exp_nan & r_nan)).all())


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
            '1980', None, None, None, None, None, None,
            # Subset geometry.
            SubsetMultiPoint([[1,2],[2,1]], 'EPSG:4326'),
            # Projection/resolution parameters.
            CRS('EPSG:4326'), None, None,
            # Output parameters.
            data_request.REQ_POINT, 'csv',
            {}
        )

        with tempfile.TemporaryDirectory() as tdir:
            outdir = Path(tdir)

            exp = [outdir / 'ds1_ds2.csv']
            r = dro._writePointFiles(test_output_dict, test_req, outdir)
            self.assertEqual(exp,r)
            self.assertTrue(exp[0].exists())

            # Shapefile
            shp_outdir = outdir / 'shp'
            shp_outdir.mkdir()
            test_req = DataRequest(
                self.dsc, {'ds1' : 'var1', 'ds2' : 'var2'},
                # Date parameters.
                '1980', None, None, None, None, None, None,
                # Subset geometry.
                SubsetMultiPoint([[1,2],[2,1]], 'EPSG:4326'),
                # Projection/resolution parameters.
                CRS('EPSG:4326'), None, None,
                # Output parameters.
                data_request.REQ_POINT, 'shapefile',
                {}
            )
            exp = sorted([
                shp_outdir / 'ds1_ds2.shx',
                shp_outdir / 'ds1_ds2.shp',
                shp_outdir / 'ds1_ds2.cpg',
                shp_outdir / 'ds1_ds2.dbf',
                shp_outdir / 'ds1_ds2.prj'
            ])
            r = sorted(
                dro._writePointFiles(test_output_dict, test_req, shp_outdir)
            )
            self.assertEqual(exp, r)
            self.assertTrue(exp[0].exists())

            # NetCDF

    def test_writeRasterFiles(self):
        pass

    def test_writeMetadataFile(self):
        pass

    def test_writeRequestedData(self):
        pass

