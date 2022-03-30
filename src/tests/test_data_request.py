
import unittest
import geojson
from pyproj.crs import CRS
from api_core import data_request, RequestDate as RD, DataRequest
from library.catalog import DatasetCatalog


class TestDataRequest(unittest.TestCase):
    def setUp(self):
        self.dsc =  DatasetCatalog('test_data')

    def test_init(self):
        # Test a variety of misconfigurations.
        with self.assertRaisesRegex(ValueError, 'Invalid resampling method'):
            dr = DataRequest(
                self.dsc, {},
                # Date parameters.
                '1980', '1980', None, None, None, None,
                # Subset geometry.
                None,
                # Projection/resolution parameters.
                CRS('NAD83'), None, 'fakemethod',
                # Output parameters.
                data_request.REQ_RASTER, None,
                {}
            )

        with self.assertRaisesRegex(ValueError, 'Invalid point .* method'):
            dr = DataRequest(
                self.dsc, {},
                # Date parameters.
                '1980', '1980', None, None, None, None,
                # Subset geometry.
                None,
                # Projection/resolution parameters.
                CRS('NAD83'), None, 'cubic',
                # Output parameters.
                data_request.REQ_POINT, None,
                {}
            )

        with self.assertRaisesRegex(ValueError, 'No points provided'):
            dr = DataRequest(
                self.dsc, {},
                # Date parameters.
                '1980', '1980', None, None, None, None,
                # Subset geometry.
                None,
                # Projection/resolution parameters.
                CRS('NAD83'), None, 'linear',
                # Output parameters.
                data_request.REQ_POINT, None,
                {}
            )

    def test_parseSimpleDateRange(self):
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', '1980', None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

        # Test annual data request ranges.
        exp = [RD(1980, None, None)]
        r, dg = dr._parseSimpleDateRange('1980', '1980')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.ANNUAL, dg)

        exp = [RD(1980, None, None), RD(1981, None, None)]
        r, dg = dr._parseSimpleDateRange('1980', '1981')
        self.assertEqual(exp, r)

        exp = [
            RD(1980, None, None), RD(1981, None, None), RD(1982, None, None)
        ]
        r, dg = dr._parseSimpleDateRange('1980', '1982')
        self.assertEqual(exp, r)

        with self.assertRaisesRegex(ValueError, 'end date cannot precede'):
            dr._parseSimpleDateRange('1980', '1979')

        with self.assertRaisesRegex(ValueError, 'Mismatched .* granularity'):
            dr._parseSimpleDateRange('1980', '1981-01')

        # Test monthly request ranges.
        exp = [RD(1980, 1, None)]
        r, dg = dr._parseSimpleDateRange('1980-01', '1980-01')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        exp = [RD(1980, 1, None), RD(1980, 2, None)]
        r, dg = dr._parseSimpleDateRange('1980-01', '1980-02')
        self.assertEqual(exp, r)

        exp = [RD(1980, 12, None), RD(1981, 1, None), RD(1981, 2, None)]
        r, dg = dr._parseSimpleDateRange('1980-12', '1981-02')
        self.assertEqual(exp, r)

        with self.assertRaisesRegex(ValueError, 'end date cannot precede'):
            dr._parseSimpleDateRange('1980-02', '1980-01')

        with self.assertRaisesRegex(ValueError, 'end date cannot precede'):
            dr._parseSimpleDateRange('1980-01', '1979-12')

        # Test daily request ranges.
        exp = [RD(1980, 1, 1)]
        r, dg = dr._parseSimpleDateRange('1980-01-01', '1980-01-01')
        self.assertEqual(exp, r)

        exp = [RD(1980, 1, 1), RD(1980, 1, 2), RD(1980, 1, 3)]
        r, dg = dr._parseSimpleDateRange('1980-01-01', '1980-01-03')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        exp = [RD(1980, 12, 30), RD(1980, 12, 31), RD(1981, 1, 1)]
        r, dg = dr._parseSimpleDateRange('1980-12-30', '1981-01-01')
        self.assertEqual(exp, r)

        with self.assertRaisesRegex(ValueError, 'end date cannot precede'):
            dr._parseSimpleDateRange('1980-01-02', '1980-01-01')

        with self.assertRaisesRegex(ValueError, 'end date cannot precede'):
            dr._parseSimpleDateRange('1980-01-01', '1979-12-31')

        # Test other error conditions.
        with self.assertRaisesRegex(ValueError, 'Start and end .* specified'):
            dr._parseSimpleDateRange('1980', None)

        with self.assertRaisesRegex(ValueError, 'Start and end .* specified'):
            dr._parseSimpleDateRange('', '1980')

    def test_parseDates(self):
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', '1980', None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

        # Test non-temporal (static) requests.
        exp = []
        r, dg = dr._parseDates(None, None, None, None, None)
        self.assertEqual(exp, r)
        self.assertEqual(data_request.NONE, dg)

        exp = []
        r, dg = dr._parseDates('', '', '', '', '')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.NONE, dg)

        exp = []
        r, dg = dr._parseDates(None, '', None, '', '')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.NONE, dg)

        # Test simple date ranges.  Here, we only need to worry about testing
        # basic parameter handling because _parseSimpleDateRange() is
        # thoroughly tested elsewhere.
        exp = [RD(1980, 1, None), RD(1980, 2, None)]
        r, dg = dr._parseDates('1980-01', '1980-02', None, None, None)
        self.assertEqual(exp, r)

        # Simple ranges have precedence over YMD parameters.
        exp = [RD(1980, 1, None), RD(1980, 2, None)]
        r, dg = dr._parseDates('1980-01', '1980-02', '1980-1990', None, None)
        self.assertEqual(exp, r)

