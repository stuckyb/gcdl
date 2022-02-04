
import unittest
import geojson
import pyproj
import data_request


class TestDataRequest(unittest.TestCase):
    def test_parse_dates(self):
        dr = data_request.DataRequest(None, '1980', '1980', None, 'NAD83')

        # Note: We assume here that this is running under at least Python 3.7,
        # which is the point at which dict insertion order preservation became
        # an official feature.

        # Test annual data request ranges.
        exp = {1980: {}}
        r, dg = dr._parse_dates('1980', '1980')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.ANNUAL, dg)

        exp = {1980: {}, 1981: {}}
        r, dg = dr._parse_dates('1980', '1981')
        self.assertEqual(exp, r)

        exp = {1980: {}, 1981: {}, 1982: {}}
        r, dg = dr._parse_dates('1980', '1982')
        self.assertEqual(exp, r)

        with self.assertRaises(ValueError):
            dr._parse_dates('1980', '1979')

        with self.assertRaises(ValueError):
            dr._parse_dates('1980', '1981-01')

        # Test monthly request ranges.
        exp = {
            1980: {1: []}
        }
        r, dg = dr._parse_dates('1980-01', '1980-01')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        exp = {
            1980: {1: [], 2: []}
        }
        r, dg = dr._parse_dates('1980-01', '1980-02')
        self.assertEqual(exp, r)

        exp = {
            1980: {12: []},
            1981: {1: [], 2: []}
        }
        r, dg = dr._parse_dates('1980-12', '1981-02')
        self.assertEqual(exp, r)

        with self.assertRaises(ValueError):
            dr._parse_dates('1980-02', '1980-01')

        with self.assertRaises(ValueError):
            dr._parse_dates('1980-01', '1979-12')

        # Test daily request ranges.
        exp = {
            1980: {1: [1]}
        }
        r, dg = dr._parse_dates('1980-01-01', '1980-01-01')
        self.assertEqual(exp, r)

        exp = {
            1980: {1: [1,2,3]}
        }
        r, dg = dr._parse_dates('1980-01-01', '1980-01-03')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        exp = {
            1980: {12: [30,31]},
            1981: {1: [1]}
        }
        r, dg = dr._parse_dates('1980-12-30', '1981-01-01')
        self.assertEqual(exp, r)

        with self.assertRaises(ValueError):
            dr._parse_dates('1980-01-02', '1980-01-01')

        with self.assertRaises(ValueError):
            dr._parse_dates('1980-01-01', '1979-12-31')

