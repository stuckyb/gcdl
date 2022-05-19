
import unittest
from api_core import data_request, DataRequestOutput


class TestDataRequestOutput(unittest.TestCase):

    def setUp(self):
        # Set up a basic DataRequestOutput object.
        self.dro = DataRequestOutput()

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
        pass

    def test_writeShapefile(self):
        pass

    def _assignCategories(self):
        pass

    def test_writeNetCDF(self):
        pass

    def test_writeGeoTIFF(self):
        pass

    def test_writePointFiles(self):
        pass

    def test_writeRasterFiles(self):
        pass

    def test_writeMetadataFile(self):
        pass

    def test_writeRequestedData(self):
        pass