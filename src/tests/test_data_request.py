
import unittest
import geojson
import pyproj
import data_request
from data_request import RequestDate as RD


class TestDataRequest(unittest.TestCase):
    def test_parse_dates(self):
        dr = data_request.DataRequest(None, '1980', '1980', None, 'NAD83')

        # Test annual data request ranges.
        exp = [RD(1980, None, None)]
        r, dg = dr._parse_dates('1980', '1980')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.ANNUAL, dg)

        exp = [RD(1980, None, None), RD(1981, None, None)]
        r, dg = dr._parse_dates('1980', '1981')
        self.assertEqual(exp, r)

        exp = [
            RD(1980, None, None), RD(1981, None, None), RD(1982, None, None)
        ]
        r, dg = dr._parse_dates('1980', '1982')
        self.assertEqual(exp, r)

        with self.assertRaises(ValueError):
            dr._parse_dates('1980', '1979')

        with self.assertRaises(ValueError):
            dr._parse_dates('1980', '1981-01')

        # Test monthly request ranges.
        exp = [RD(1980, 1, None)]
        r, dg = dr._parse_dates('1980-01', '1980-01')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        exp = [RD(1980, 1, None), RD(1980, 2, None)]
        r, dg = dr._parse_dates('1980-01', '1980-02')
        self.assertEqual(exp, r)

        exp = [RD(1980, 12, None), RD(1981, 1, None), RD(1981, 2, None)]
        r, dg = dr._parse_dates('1980-12', '1981-02')
        self.assertEqual(exp, r)

        with self.assertRaises(ValueError):
            dr._parse_dates('1980-02', '1980-01')

        with self.assertRaises(ValueError):
            dr._parse_dates('1980-01', '1979-12')

        # Test daily request ranges.
        exp = [RD(1980, 1, 1)]
        r, dg = dr._parse_dates('1980-01-01', '1980-01-01')
        self.assertEqual(exp, r)

        exp = [RD(1980, 1, 1), RD(1980, 1, 2), RD(1980, 1, 3)]
        r, dg = dr._parse_dates('1980-01-01', '1980-01-03')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        exp = [RD(1980, 12, 30), RD(1980, 12, 31), RD(1981, 1, 1)]
        r, dg = dr._parse_dates('1980-12-30', '1981-01-01')
        self.assertEqual(exp, r)

        with self.assertRaises(ValueError):
            dr._parse_dates('1980-01-02', '1980-01-01')

        with self.assertRaises(ValueError):
            dr._parse_dates('1980-01-01', '1979-12-31')

