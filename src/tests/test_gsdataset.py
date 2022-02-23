
import unittest
import geojson
import pyproj
from library.datasets.gsdataset import GSDataSet


class StubDS(GSDataSet):
    """
    A concrete child class that stubs abstract methods.
    """
    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        return None


class TestGSDataSet(unittest.TestCase):
    def test_id(self):
        ds = StubDS('.')

        self.assertEqual(ds.name, '')
        self.assertIsNone(ds._id)
        self.assertEqual(ds.id, '')

        ds.name = 'stub_ds'
        self.assertIsNone(ds._id)
        self.assertEqual(ds.id, 'stub_ds')

        ds.name = 'a stub dataset'
        ds._id = 'stubds'
        self.assertEqual(ds.id, 'stubds')

    def test_nontemporal(self):
        ds = StubDS('.')

        self.assertTrue(ds.nontemporal)

        ds.date_ranges['year'] = [1980, 1980]

        self.assertFalse(ds.nontemporal)

