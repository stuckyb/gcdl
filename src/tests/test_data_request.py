
import unittest
import geojson
import pyproj
from data_request import DataRequest


class TestDataRequest(unittest.TestCase):
    def test_parse_dates(self):
        dr = DataRequest(None, None, None, None, None)

        # Note: We assume here that this is running under at least Python 3.7,
        # which is the point at which dict insertion order preservation became
        # an official feature.

        # Test annual data request ranges.
        exp = {1980: {}}
        r = dr._parse_dates('1980', '1980')
        self.assertEqual(exp, r)

        exp = {1980: {}, 1981: {}}
        r = dr._parse_dates('1980', '1981')
        self.assertEqual(exp, r)

        exp = {1980: {}, 1981: {}, 1982: {}}
        r = dr._parse_dates('1980', '1982')
        self.assertEqual(exp, r)

        with self.assertRaises(ValueError):
            dr._parse_dates('1980', '1979')

        with self.assertRaises(ValueError):
            dr._parse_dates('1980', '1981-01')

        # Test monthly request ranges.
        exp = {
            1980: {1: {}}
        }
        r = dr._parse_dates('1980-01', '1980-01')
        self.assertEqual(exp, r)

        exp = {
            1980: {1: {}, 2: {}}
        }
        r = dr._parse_dates('1980-01', '1980-02')
        self.assertEqual(exp, r)

        exp = {
            1980: {12: {}},
            1981: {1: {}, 2: {}}
        }
        r = dr._parse_dates('1980-12', '1981-02')
        self.assertEqual(exp, r)

        with self.assertRaises(ValueError):
            dr._parse_dates('1980-02', '1980-01')

