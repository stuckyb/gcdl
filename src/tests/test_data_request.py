
import unittest
from pyproj.crs import CRS
from api_core import data_request, RequestDate as RD, DataRequest
from api_core.data_request import ANNUAL, MONTHLY, DAILY
from library.catalog import DatasetCatalog
from library.datasets.gsdataset import GSDataSet
import datetime as dt

# Two stub GSDataSets with different date ranges are needed 
# to test date validation methods
class StubDS1(GSDataSet):
    """
    A concrete child class that stubs abstract methods.
    """
    def __init__(self, store_path):
        super().__init__(store_path, 'stub')
        self.name = 'ds1'
        self.date_ranges['year'] = [
            dt.date(1980, 1, 1), dt.date(2020, 1, 1)
        ]
        self.date_ranges['month'] = [
            dt.date(1980, 1, 1), dt.date(2020, 12, 1)
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
            dt.date(1990, 1, 1), dt.date(2020, 1, 1)
        ]
        self.date_ranges['month'] = [
            dt.date(1990, 1, 1), dt.date(2020, 12, 1)
        ]

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        return None


class TestDataRequest(unittest.TestCase):
    def setUp(self):
        self.dsc =  DatasetCatalog('test_data')
        self.dsc.addDatasetsByClass(StubDS1,StubDS2)
        self.dsvars = {'ds1':'', 'ds2':''}

        # Set up a basic DataRequest object.
        self.dr = DataRequest(
            self.dsc, self.dsvars,
            # Date parameters.
            '1990', None, None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

    def test_init(self):
        # Test a variety of misconfigurations.
        with self.assertRaisesRegex(ValueError, 'Invalid resampling method'):
            dr = DataRequest(
                self.dsc, self.dsvars,
                # Date parameters.
                '1990', None, None, None, None, None,
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
                self.dsc, self.dsvars,
                # Date parameters.
                '1990', None, None, None, None, None,
                # Subset geometry.
                None,
                # Projection/resolution parameters.
                CRS('NAD83'), None, 'cubic',
                # Output parameters.
                data_request.REQ_POINT, None,
                {}
            )

        with self.assertRaisesRegex(ValueError, 'Invalid date grain matching method'):
            dr = DataRequest(
                self.dsc, self.dsvars,
                # Date parameters.
                '1990', None, None, None, 'fakemethod', None,
                # Subset geometry.
                None,
                # Projection/resolution parameters.
                CRS('NAD83'), None, None,
                # Output parameters.
                data_request.REQ_RASTER, None,
                {}
            )

        with self.assertRaisesRegex(ValueError, 'Invalid date range validation method'):
            dr = DataRequest(
                self.dsc, self.dsvars,
                # Date parameters.
                '1990', None, None, None, None, 'fakemethod',
                # Subset geometry.
                None,
                # Projection/resolution parameters.
                CRS('NAD83'), None, None,
                # Output parameters.
                data_request.REQ_RASTER, None,
                {}
            )

        with self.assertRaisesRegex(ValueError, 'No points provided'):
            dr = DataRequest(
                self.dsc, self.dsvars,
                # Date parameters.
                '1990', None, None, None, None, None,
                # Subset geometry.
                None,
                # Projection/resolution parameters.
                CRS('NAD83'), None, 'linear',
                # Output parameters.
                data_request.REQ_POINT, None,
                {}
            )

    def test_parseSimpleDateRange(self):
        dr = self.dr

        # Test annual data request ranges.
        exp = [RD(1980, None, None)]
        r, dg = dr._parseSimpleDateRange('1980', '1980')
        self.assertEqual(exp, r)
        self.assertEqual(ANNUAL, dg)

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
        self.assertEqual(MONTHLY, dg)

        exp = [RD(1980, 1, None), RD(1980, 2, None)]
        r, dg = dr._parseSimpleDateRange('1980-01', '1980-02')
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        exp = [RD(1980, 12, None), RD(1981, 1, None), RD(1981, 2, None)]
        r, dg = dr._parseSimpleDateRange('1980-12', '1981-02')
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        with self.assertRaisesRegex(ValueError, 'end date cannot precede'):
            dr._parseSimpleDateRange('1980-02', '1980-01')

        with self.assertRaisesRegex(ValueError, 'end date cannot precede'):
            dr._parseSimpleDateRange('1980-01', '1979-12')

        # Test daily request ranges.
        exp = [RD(1980, 1, 1)]
        r, dg = dr._parseSimpleDateRange('1980-01-01', '1980-01-01')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        exp = [RD(1980, 1, 1), RD(1980, 1, 2), RD(1980, 1, 3)]
        r, dg = dr._parseSimpleDateRange('1980-01-01', '1980-01-03')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        exp = [RD(1980, 12, 30), RD(1980, 12, 31), RD(1981, 1, 1)]
        r, dg = dr._parseSimpleDateRange('1980-12-30', '1981-01-01')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        with self.assertRaisesRegex(ValueError, 'end date cannot precede'):
            dr._parseSimpleDateRange('1980-01-02', '1980-01-01')

        with self.assertRaisesRegex(ValueError, 'end date cannot precede'):
            dr._parseSimpleDateRange('1980-01-01', '1979-12-31')

        # Verify that leading 0s are not required.
        exp = [RD(1980, 12, None), RD(1981, 1, None), RD(1981, 2, None)]
        r, dg = dr._parseSimpleDateRange('1980-12', '1981-2')
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        exp = [RD(1980, 1, 1), RD(1980, 1, 2), RD(1980, 1, 3)]
        r, dg = dr._parseSimpleDateRange('1980-1-01', '1980-1-03')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        r, dg = dr._parseSimpleDateRange('1980-01-1', '1980-01-3')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        r, dg = dr._parseSimpleDateRange('1980-1-1', '1980-1-3')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        # Test an invalid day of the month.
        with self.assertRaisesRegex(ValueError, 'day is out of range'):
            dr._parseSimpleDateRange('1980-01-40', '1980-01-40')
            
        # Test other error conditions.
        with self.assertRaisesRegex(ValueError, 'Start and end .* specified'):
            dr._parseSimpleDateRange('1980', None)

        with self.assertRaisesRegex(ValueError, 'Start and end .* specified'):
            dr._parseSimpleDateRange('', '1980')

    def test_parseSimpleDates(self):
        dr = self.dr

        # Simple date range processing is thoroughly tested in
        # test_parseSimpleDateRange(), so we only need to test basic
        # functionality here.

        # Test annual date requests.
        exp = [RD(1980, None, None)]
        r, dg = dr._parseSimpleDates('1980')
        self.assertEqual(exp, r)
        self.assertEqual(ANNUAL, dg)

        exp = [RD(1980, None, None), RD(1982, None, None)]
        r, dg = dr._parseSimpleDates('1980,1982')
        self.assertEqual(exp, r)
        self.assertEqual(ANNUAL, dg)

        exp = [
            RD(1980, None, None), RD(1981, None, None), RD(1982, None, None),
            RD(1990, None, None)
        ]
        r, dg = dr._parseSimpleDates('1980:1982,1990')
        self.assertEqual(exp, r)
        self.assertEqual(ANNUAL, dg)

        # Test monthly date requests.
        exp = [RD(1980, 1, None)]
        r, dg = dr._parseSimpleDates('1980-01')
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        exp = [RD(1980, 1, None), RD(1980, 7, None)]
        r, dg = dr._parseSimpleDates('1980-01,1980-07')
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        exp = [
            RD(1980, 1, None), RD(1980, 3, None), RD(1980, 4, None),
            RD(1980, 5, None), RD(1980, 7, None)
        ]
        r, dg = dr._parseSimpleDates('1980-01,1980-03:1980-05,1980-07')
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        # Test daily date requests.
        exp = [RD(1980, 1, 1)]
        r, dg = dr._parseSimpleDates('1980-01-01')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        exp = [RD(1980, 1, 1), RD(1982, 2, 10)]
        r, dg = dr._parseSimpleDates('1980-01-01,1982-02-10')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        exp = [
            RD(1980, 1, 1), RD(1980, 12, 31), RD(1981, 1, 1), RD(1981, 1, 2)
        ]
        r, dg = dr._parseSimpleDates('1980-01-01,1980-12-31:1981-01-02')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        # Test that leading 0s are not required.
        r, dg = dr._parseSimpleDates('1980-1-01,1980-12-31:1981-1-2')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        # Test that dates get (re-)ordered correctly.
        exp = [RD(1980, None, None), RD(1982, None, None)]
        r, dg = dr._parseSimpleDates('1982,1980')
        self.assertEqual(exp, r)
        self.assertEqual(ANNUAL, dg)

        exp = [RD(1980, 1, None), RD(1980, 7, None)]
        r, dg = dr._parseSimpleDates('1980-07,1980-01')
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        exp = [RD(1980, 1, 1), RD(1980, 1, 10)]
        r, dg = dr._parseSimpleDates('1980-01-10,1980-01-01')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        # Test that duplicate dates are correctly handled.
        exp = [RD(1980, 1, 1), RD(1980, 1, 10)]
        r, dg = dr._parseSimpleDates('1980-01-10,1980-01-01,1980-01-10')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        # Test that mixed date grains are correctly detected.
        with self.assertRaisesRegex(ValueError, 'Cannot mix date grains'):
            dr._parseSimpleDates('1980,1980-01')

    def test_parseRangeStr(self):
        dr = self.dr

        # Test basic range specifications.
        exp = [1]
        r = dr._parseRangeStr('1:1', None)
        self.assertEqual(exp, r)

        exp = [1,2]
        r = dr._parseRangeStr('1:2', None)
        self.assertEqual(exp, r)

        exp = [1,2,3,4]
        r = dr._parseRangeStr('1:4', None)
        self.assertEqual(exp, r)

        exp = [4]
        r = dr._parseRangeStr('4:4', None)
        self.assertEqual(exp, r)

        exp = [4,5,6,7]
        r = dr._parseRangeStr('4:7', None)
        self.assertEqual(exp, r)

        # Test ranges with custom increments.
        exp = [4]
        r = dr._parseRangeStr('4:4+2', None)
        self.assertEqual(exp, r)

        exp = [4]
        r = dr._parseRangeStr('4:5+2', None)
        self.assertEqual(exp, r)

        exp = [4,6]
        r = dr._parseRangeStr('4:6+2', None)
        self.assertEqual(exp, r)

        exp = [4,6]
        r = dr._parseRangeStr('4:7+2', None)
        self.assertEqual(exp, r)

        exp = [4,6,8]
        r = dr._parseRangeStr('4:8+2', None)
        self.assertEqual(exp, r)

        # Test ranges with a maximum value.
        exp = [4,5,6,7,8]
        r = dr._parseRangeStr('4:N', 8)
        self.assertEqual(exp, r)

        exp = [4,6,8]
        r = dr._parseRangeStr('4:N+2', 8)
        self.assertEqual(exp, r)

        # Test error conditions.
        with self.assertRaisesRegex(ValueError, 'Invalid range string'):
            dr._parseRangeStr('4', None)

        with self.assertRaisesRegex(ValueError, 'Invalid range string'):
            dr._parseRangeStr('4:10+2+', None)

        with self.assertRaisesRegex(ValueError, 'invalid literal'):
            dr._parseRangeStr('4:a', None)

        with self.assertRaisesRegex(ValueError, 'no maximum'):
            dr._parseRangeStr('4:N', None)

        with self.assertRaisesRegex(ValueError, 'starting value .* exceed'):
            dr._parseRangeStr('4:1', None)

        with self.assertRaisesRegex(ValueError, 'greater than 0'):
            dr._parseRangeStr('0:4', None)

        with self.assertRaisesRegex(ValueError, 'cannot exceed 8'):
            dr._parseRangeStr('4:10', 8)

    def test_parseNumValsStr(self):
        dr = self.dr

        # Test basic number values string parsing.  We don't need to
        # extensively test range strings here, because that functionality is
        # tested separately.
        exp = [1]
        r = dr._parseNumValsStr('1', None)
        self.assertEqual(exp, r)

        exp = [1,2]
        r = dr._parseNumValsStr('1,2', None)
        self.assertEqual(exp, r)
        r = dr._parseNumValsStr('2,1', None)
        self.assertEqual(exp, r)

        exp = [1,4,5,6,8]
        r = dr._parseNumValsStr('1,4:6,8', None)
        self.assertEqual(exp, r)
        r = dr._parseNumValsStr('8,1,4:6', None)
        self.assertEqual(exp, r)

        exp = [1,4,7,10,12,14,16,17,18,40]
        r = dr._parseNumValsStr('1,4:10+3,12:14+2,16:18,40', None)
        self.assertEqual(exp, r)

        # Test including a maximum value.
        exp = [8]
        r = dr._parseNumValsStr('N', 8)

        exp = [1,8]
        r = dr._parseNumValsStr('1,N', 8)

        exp = [1,4,5,6,7,8]
        r = dr._parseNumValsStr('1,4:N', 8)

        # Test overlapping values.
        exp = [1]
        r = dr._parseNumValsStr('1,1', None)
        self.assertEqual(exp, r)

        exp = [1,2,3,4]
        r = dr._parseNumValsStr('1,2:4,3', None)
        self.assertEqual(exp, r)

        # Test error conditions.
        with self.assertRaisesRegex(ValueError, 'greater than 0'):
            dr._parseNumValsStr('0,1', None)

        with self.assertRaisesRegex(ValueError, 'values cannot exceed 8'):
            dr._parseNumValsStr('1,4,7:8,10', 8)

        with self.assertRaisesRegex(ValueError, 'no maximum .* was provided'):
            dr._parseNumValsStr('1,4,7:8,N', None)

    def test_parseYMD(self):
        dr = self.dr

        # Year-only values.
        exp = [RD(1980, None, None)]
        r, dg = dr._parseYMD('1980', None, None)
        self.assertEqual(exp, r)
        self.assertEqual(ANNUAL, dg)

        exp = [RD(1980, None, None), RD(1982, None, None)]
        r, dg = dr._parseYMD('1980:1982+2', None, None)
        self.assertEqual(exp, r)
        self.assertEqual(ANNUAL, dg)

        # Year + month values.
        exp = [RD(1980, 4, None)]
        r, dg = dr._parseYMD('1980', '4', None)
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        exp = [RD(1980, 4, None), RD(1981, 4, None)]
        r, dg = dr._parseYMD('1980:1981', '4', None)
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        exp = [
            RD(1980, 10, None), RD(1980, 12, None),
            RD(1981, 10, None), RD(1981, 12, None)
        ]
        r, dg = dr._parseYMD('1980:1981', '10:N+2', None)
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        # Daily values without month.
        exp = [RD(1980, 1, 10)]
        r, dg = dr._parseYMD('1980', None, '10')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        exp = [
            RD(1980, 1, 10), RD(1980, 1, 12),
            RD(1981, 1, 10), RD(1981, 1, 12)
        ]
        r, dg = dr._parseYMD('1980:1981', None, '10:12+2')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        # Daily values without month, including both leap and common years.
        exp = [
            RD(1980, 2, 28), RD(1980, 2, 29),
            RD(1981, 2, 28), RD(1981, 3, 1)
        ]
        r, dg = dr._parseYMD('1980:1981', None, '59:60')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        exp = [
            RD(1980, 12, 30), RD(1980, 12, 31),
            RD(1981, 12, 31)
        ]
        r, dg = dr._parseYMD('1980:1981', None, '365:N')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        # Daily values with month.
        exp = [RD(1980, 4, 10)]
        r, dg = dr._parseYMD('1980', '4', '10')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        exp = [
            RD(1980, 4, 8), RD(1980, 4, 9), RD(1980, 6, 8), RD(1980, 6, 9),
            RD(1981, 4, 8), RD(1981, 4, 9), RD(1981, 6, 8), RD(1981, 6, 9)
        ]
        r, dg = dr._parseYMD('1980:1981', '4:6+2', '8,9')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

        # Daily values with month, including both leap and common years.
        exp = [
            RD(1980, 2, 20), RD(1980, 2, 29), RD(1980, 3, 20), RD(1980, 3, 31),
            RD(1981, 2, 20), RD(1981, 2, 28), RD(1981, 3, 20), RD(1981, 3, 31),
        ]
        r, dg = dr._parseYMD('1980:1981', '2:3', '20,N')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

    def test_parseDates(self):
        dr = self.dr

        # Test non-temporal (static) requests.
        exp = []
        r, dg = dr._parseDates(None, None, None, None)
        self.assertEqual(exp, r)
        self.assertEqual(data_request.NONE, dg)

        exp = []
        r, dg = dr._parseDates('', '', '', '')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.NONE, dg)

        exp = []
        r, dg = dr._parseDates('', None, '', '')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.NONE, dg)

        # Test simple date strings.  Here, we only need to worry about testing
        # basic parameter handling because _parseSimpleDates() is thoroughly
        # tested elsewhere.
        exp = [RD(1980, 1, None), RD(1980, 2, None)]
        r, dg = dr._parseDates('1980-01,1980-02', None, None, None)
        self.assertEqual(exp, r)

        # Simple date strings should have precedence over YMD parameters.
        exp = [RD(1980, 1, None), RD(1980, 2, None)]
        r, dg = dr._parseDates('1980-01,1980-02', '1980:1990', None, None)
        self.assertEqual(exp, r)
        self.assertEqual(MONTHLY, dg)

        # Test YMD dates.  Again, we only need to worry about testing basic
        # parameter handling.
        exp = [RD(1980, 1, 31), RD(1980, 2, 29)]
        r, dg = dr._parseDates(None, '1980', '1:2', 'N')
        self.assertEqual(exp, r)
        self.assertEqual(DAILY, dg)

    def test_verifyGrains(self):
        dr = self.dr

        # Test strict grain rule with mis-matched available grains.
        with self.assertRaisesRegex(
            ValueError, 'does not have requested date granularity'
        ):
            dr._verifyGrains(self.dsc, self.dsvars, DAILY, 'strict')

        # Test strict grain rule with no mis-matched available grains.
        exp = {'ds1' : ANNUAL, 'ds2' : ANNUAL}
        r = dr._verifyGrains(self.dsc, self.dsvars, ANNUAL, 'strict')
        self.assertEqual(exp, r)

        # Test coarser method 
        exp = {'ds1' : MONTHLY, 'ds2' : MONTHLY}
        r = dr._verifyGrains(self.dsc, self.dsvars, DAILY, 'coarser')
        self.assertEqual(exp, r)

        # Test finer method 
        with self.assertRaisesRegex(
            ValueError, 'has no supported date granularity'
        ):
            dr._verifyGrains(self.dsc, self.dsvars, DAILY, 'finer')

        # Test any method
        exp = {'ds1' : ANNUAL, 'ds2' : ANNUAL}
        r = dr._verifyGrains(self.dsc, self.dsvars, DAILY, 'any')
        self.assertEqual(exp, r)

        # Test skip method
        exp = {'ds1' : None, 'ds2' : None}
        r = dr._verifyGrains(self.dsc, self.dsvars, DAILY, 'skip')
        self.assertEqual(exp, r)

    def test_listAllowedGrains(self):
        dr = self.dr

        # test coarser methods
        exp = [MONTHLY, ANNUAL]
        r = dr._listAllowedGrains(DAILY, 'coarser')
        self.assertEqual(exp, r)

        exp = [ANNUAL]
        r = dr._listAllowedGrains(MONTHLY, 'coarser')
        self.assertEqual(exp, r)

        exp = []
        r = dr._listAllowedGrains(ANNUAL, 'coarser')
        self.assertEqual(exp, r)

        exp = []
        r = dr._listAllowedGrains(data_request.NONE, 'coarser')
        self.assertEqual(exp, r)

        # test finer methods
        exp = []
        r = dr._listAllowedGrains(DAILY, 'finer')
        self.assertEqual(exp, r)

        exp = [DAILY]
        r = dr._listAllowedGrains(MONTHLY, 'finer')
        self.assertEqual(exp, r)

        exp = [MONTHLY, DAILY]
        r = dr._listAllowedGrains(ANNUAL, 'finer')
        self.assertEqual(exp, r)

        exp = []
        r = dr._listAllowedGrains(data_request.NONE, 'finer')
        self.assertEqual(exp, r)

        # test the any method
        exp = [ANNUAL, MONTHLY]
        r = dr._listAllowedGrains(DAILY, 'any')
        self.assertEqual(exp, r)

        exp = [ANNUAL, DAILY]
        r = dr._listAllowedGrains(MONTHLY, 'any')
        self.assertEqual(exp, r)

        exp = [MONTHLY, DAILY]
        r = dr._listAllowedGrains(ANNUAL, 'any')
        self.assertEqual(exp, r)

        exp = []
        r = dr._listAllowedGrains(data_request.NONE, 'any')
        self.assertEqual(exp, r)

    def test_modifySimpleDateGrain(self):
        dr = self.dr

        # Monthly to annual.
        exp = ('1980', '1981')
        r = dr._modifySimpleDateGrain(MONTHLY, ANNUAL, '1980-01', '1981-02')
        self.assertEqual(exp, r)

        r = dr._modifySimpleDateGrain(MONTHLY, ANNUAL, '1980-1', '1981-2')
        self.assertEqual(exp, r)

        # Daily to annual.
        exp = ('1980', '1981')
        r = dr._modifySimpleDateGrain(
            DAILY, ANNUAL, '1980-01-01', '1981-02-01'
        )
        self.assertEqual(exp, r)

        r = dr._modifySimpleDateGrain(DAILY, ANNUAL, '1980-1-1', '1981-2-1')
        self.assertEqual(exp, r)

        # Annual to monthly.
        exp = ('1980-01', '1981-12')
        r = dr._modifySimpleDateGrain(ANNUAL, MONTHLY, '1980', '1981')
        self.assertEqual(exp, r)

        # Daily to monthly.
        exp = ('1980-01', '1981-12')
        r = dr._modifySimpleDateGrain(
            DAILY, MONTHLY, '1980-01-01', '1981-12-01'
        )
        self.assertEqual(exp, r)

        exp = ('1980-1', '1981-12')
        r = dr._modifySimpleDateGrain(
            DAILY, MONTHLY, '1980-1-01', '1981-12-01'
        )
        self.assertEqual(exp, r)

        r = dr._modifySimpleDateGrain(
            DAILY, MONTHLY, '1980-1-1', '1981-12-1'
        )
        self.assertEqual(exp, r)

        # Annual to daily.
        exp = ('1980-01-01', '1981-12-31')
        r = dr._modifySimpleDateGrain(ANNUAL, DAILY, '1980', '1981')
        self.assertEqual(exp, r)

        # Monthly to daily.
        exp = ('1980-01-01', '1981-02-28')
        r = dr._modifySimpleDateGrain(MONTHLY, DAILY, '1980-01', '1981-02')
        self.assertEqual(exp, r)

        exp = ('1980-01-01', '1980-02-29')
        r = dr._modifySimpleDateGrain(MONTHLY, DAILY, '1980-01', '1980-02')
        self.assertEqual(exp, r)

        exp = ('1980-1-01', '1981-2-28')
        r = dr._modifySimpleDateGrain(MONTHLY, DAILY, '1980-1', '1981-2')
        self.assertEqual(exp, r)

    def test_populateDates(self):
        dr = self.dr

        # Test no new grains so no new dates.
        exp = {}
        r = dr._populateDates(
            ANNUAL, {}, 
            '1980',
            None, None, None
        )
        self.assertEqual(exp, r)

        # Test new dates added by a simple dates string.
        exp = {
            MONTHLY: [RD(1980, m+1, None) for m in range(12)]
        }
        r = dr._populateDates(
            ANNUAL, {'ds1': MONTHLY}, 
            '1980', 
            None, None, None
        )
        self.assertEqual(exp, r)

        # Test new dates added by YMD (see test_populateYMD).
        exp = {
            MONTHLY: [RD(1980, m+1, None) for m in range(12)]
        }
        r = dr._populateDates(
            ANNUAL, {'ds1': MONTHLY}, 
            None, 
            '1980', None, None
        )
        self.assertEqual(exp, r)

    def test_populateYMD(self):
        dr = self.dr

        # Test ANNUAL to MONTHLY
        exp = [RD(1980, m+1, None) for m in range(12)]
        r = dr._populateYMD(
            ANNUAL, MONTHLY,
            '1980', None, None
        )
        self.assertEqual(exp, r)

        # Test ANNUAL to DAILY
        exp = []
        for d in range(366):
            ord_year = dt.date(1980, 1, 1).toordinal()
            d = dt.date.fromordinal(ord_year + d)
            exp.append(RD(1980, d.month, d.day)) 
        r = dr._populateYMD(
            ANNUAL, DAILY,
            '1980', None, None
        )
        self.assertEqual(exp, r)

        # Test MONHTLY to ANNUAL
        exp = [RD(1980, None, None)]
        r = dr._populateYMD(
            MONTHLY, ANNUAL,
            '1980', '1', None
        )
        self.assertEqual(exp, r)

        # Test MONTHLY to DAILY
        exp = [RD(1980, 1, d+1) for d in range(31)]
        r = dr._populateYMD(
            MONTHLY, DAILY,
            '1980', '1', None
        )
        self.assertEqual(exp, r)

        # Test DAILY to MONTHLY
        exp = [RD(1980, 1, None)]
        r = dr._populateYMD(
            DAILY, MONTHLY,
            '1980', '1', '1'
        )
        self.assertEqual(exp, r)

        # Test DAILY to ANNUAL
        exp = [RD(1980, None, None)]
        r = dr._populateYMD(
            DAILY, ANNUAL,
            '1980', '1', '1'
        )
        self.assertEqual(exp, r)

    def test_populateSimpleDates(self):
        dr = self.dr

        # Test ANNUAL to MONTHLY
        exp = [RD(1980, m+1, None) for m in range(12)]
        r = dr._populateSimpleDates(
            ANNUAL, MONTHLY,
            '1980:1980'
        )
        self.assertEqual(exp, r)

        # Test ANNUAL to DAILY
        exp = []
        for d in range(366):
            ord_year = dt.date(1980, 1, 1).toordinal()
            d = dt.date.fromordinal(ord_year + d)
            exp.append(RD(1980, d.month, d.day)) 
        r = dr._populateSimpleDates(
            ANNUAL, DAILY,
            '1980:1980'
        )
        self.assertEqual(exp, r)

        # Test MONHTLY to ANNUAL
        exp = [RD(1980, None, None)]
        r = dr._populateSimpleDates(
            MONTHLY, ANNUAL,
            '1980-1:1980-1'
        )
        self.assertEqual(exp, r)

        # Test MONTHLY to DAILY
        exp = [RD(1980, 1, d+1) for d in range(31)]
        r = dr._populateSimpleDates(
            MONTHLY, DAILY,
            '1980-1:1980-1'
        )
        self.assertEqual(exp, r)

        # Test DAILY to MONTHLY
        exp = [RD(1980, 1, None)]
        r = dr._populateSimpleDates(
            DAILY, MONTHLY,
            '1980-1-1:1980-1-1'
        )
        self.assertEqual(exp, r)

        # Test DAILY to ANNUAL
        exp = [RD(1980, None, None)]
        r = dr._populateSimpleDates(
            DAILY, ANNUAL,
            '1980-1-1:1980-1-1'
        )
        self.assertEqual(exp, r)

    def test_requestDateAsDatetime(self):
        dr = self.dr

        # Test daily
        exp = dt.date(1980,1,1)
        r = dr._requestDateAsDatetime(
            RD(1980,1,1), DAILY
        )
        self.assertEqual(exp, r)

        # Test monthly
        exp = dt.date(1980,1,1)
        r = dr._requestDateAsDatetime(
            RD(1980,1, None), MONTHLY
        )
        self.assertEqual(exp, r)

        # Test annual
        exp = dt.date(1980,1,1)
        r = dr._requestDateAsDatetime(
            RD(1980, None, None), ANNUAL
        )
        self.assertEqual(exp, r)

        # Test mixed RD format and grain

    def test_strictDateRangeCheck(self):
        dr = self.dr

        # Test fully available dates - ANNUAL
        exp = True
        r = dr._strictDateRangeCheck(
            [RD(1980,None,None),RD(1981,None,None)],
            [dt.date(1980,1,1),dt.date(1981,12,31)],
            ANNUAL
        )
        self.assertEqual(exp, r)

        # Test front-end partial available dates - ANNUAL
        exp = False
        r = dr._strictDateRangeCheck(
            [RD(1980,None,None),RD(1981,None,None)],
            [dt.date(1981,1,1),dt.date(1981,12,31)],
            ANNUAL
        )
        self.assertEqual(exp, r)

        # Test back-end partial available dates - ANNUAL
        exp = False
        r = dr._strictDateRangeCheck(
            [RD(1980,None,None),RD(1981,None,None)],
            [dt.date(1980,1,1),dt.date(1980,12,31)],
            ANNUAL
        )
        self.assertEqual(exp, r)

        # Test totally unavailable dates - ANNUAL
        exp = False
        r = dr._strictDateRangeCheck(
            [RD(1980,None,None),RD(1981,None,None)],
            [dt.date(1982,1,1),dt.date(1982,12,31)],
            ANNUAL
        )
        self.assertEqual(exp, r)

        # Test fully available dates - MONTHLY
        exp = True
        r = dr._strictDateRangeCheck(
            [RD(1980,1,None),RD(1980,2,None)],
            [dt.date(1980,1,1),dt.date(1981,12,31)],
            MONTHLY
        )
        self.assertEqual(exp, r)

        # Test front-end partial available dates - MONTHLY
        exp = False
        r = dr._strictDateRangeCheck(
            [RD(1980,12,None),RD(1981,1,None)],
            [dt.date(1981,1,1),dt.date(1981,12,31)],
            MONTHLY
        )
        self.assertEqual(exp, r)

        # Test back-end partial available dates - MONTHLY
        exp = False
        r = dr._strictDateRangeCheck(
            [RD(1980,12,None),RD(1981,1,None)],
            [dt.date(1980,1,1),dt.date(1980,12,31)],
            MONTHLY
        )
        self.assertEqual(exp, r)
 
        # Test totally unavailable dates - MONTHLY
        exp = False
        r = dr._strictDateRangeCheck(
            [RD(1980,1,None),RD(1980,2,None)],
            [dt.date(1982,1,1),dt.date(1982,12,31)],
            MONTHLY
        )
        self.assertEqual(exp, r)

        # Test fully available dates - DAILY
        exp = True
        r = dr._strictDateRangeCheck(
            [RD(1980,1,1),RD(1980,1,2)],
            [dt.date(1980,1,1),dt.date(1981,12,31)],
            DAILY
        )
        self.assertEqual(exp, r)

        # Test front-end partial available dates - DAILY
        exp = False
        r = dr._strictDateRangeCheck(
            [RD(1980,12,31),RD(1981,1,1)],
            [dt.date(1981,1,1),dt.date(1981,12,31)],
            DAILY
        )
        self.assertEqual(exp, r)

        # Test back-end partial available dates - DAILY
        exp = False
        r = dr._strictDateRangeCheck(
            [RD(1980,12,31),RD(1981,1,1)],
            [dt.date(1980,1,1),dt.date(1980,12,31)],
            DAILY
        )
        self.assertEqual(exp, r)
 
        # Test totally unavailable dates - DAILY
        exp = False
        r = dr._strictDateRangeCheck(
            [RD(1980,1,1),RD(1980,1,2)],
            [dt.date(1982,1,1),dt.date(1982,12,31)],
            DAILY
        )
        self.assertEqual(exp, r)

    def test_partialDateRangeCheck(self):
        dr = self.dr

        # Test fully available dates - ANNUAL
        exp = [RD(1980,None,None),RD(1981,None,None)]
        r = dr._partialDateRangeCheck(
            [RD(1980,None,None),RD(1981,None,None)],
            [dt.date(1980,1,1),dt.date(1981,12,31)],
            ANNUAL
        )
        self.assertEqual(exp, r)

        # Test front-end partial available dates - ANNUAL
        exp = [RD(1981,None,None)]
        r = dr._partialDateRangeCheck(
            [RD(1980,None,None),RD(1981,None,None)],
            [dt.date(1981,1,1),dt.date(1981,12,31)],
            ANNUAL
        )
        self.assertEqual(exp, r)

        # Test back-end partial available dates - ANNUAL
        exp = [RD(1980,None,None)]
        r = dr._partialDateRangeCheck(
            [RD(1980,None,None),RD(1981,None,None)],
            [dt.date(1980,1,1),dt.date(1980,12,31)],
            ANNUAL
        )
        self.assertEqual(exp, r)

        # Test totally unavailable dates - ANNUAL
        exp = []
        r = dr._partialDateRangeCheck(
            [RD(1980,None,None),RD(1981,None,None)],
            [dt.date(1982,1,1),dt.date(1982,12,31)],
            ANNUAL
        )
        self.assertEqual(exp, r)

        # Test fully available dates - MONTHLY
        exp = [RD(1980,1,None),RD(1980,2,None)]
        r = dr._partialDateRangeCheck(
            [RD(1980,1,None),RD(1980,2,None)],
            [dt.date(1980,1,1),dt.date(1981,12,31)],
            MONTHLY
        )
        self.assertEqual(exp, r)

        # Test front-end partial available dates - MONTHLY
        exp = [RD(1981,1,None)]
        r = dr._partialDateRangeCheck(
            [RD(1980,12,None),RD(1981,1,None)],
            [dt.date(1981,1,1),dt.date(1981,12,31)],
            MONTHLY
        )
        self.assertEqual(exp, r)

        # Test back-end partial available dates - MONTHLY
        exp = [RD(1980,12,None)]
        r = dr._partialDateRangeCheck(
            [RD(1980,12,None),RD(1981,1,None)],
            [dt.date(1980,1,1),dt.date(1980,12,31)],
            MONTHLY
        )
        self.assertEqual(exp, r)
 
        # Test totally unavailable dates - MONTHLY
        exp = []
        r = dr._partialDateRangeCheck(
            [RD(1980,1,None),RD(1980,2,None)],
            [dt.date(1982,1,1),dt.date(1982,12,31)],
            MONTHLY
        )
        self.assertEqual(exp, r)

        # Test fully available dates - DAILY
        exp = [RD(1980,1,1),RD(1980,1,2)]
        r = dr._partialDateRangeCheck(
            [RD(1980,1,1),RD(1980,1,2)],
            [dt.date(1980,1,1),dt.date(1981,12,31)],
            DAILY
        )
        self.assertEqual(exp, r)

        # Test front-end partial available dates - DAILY
        exp = [RD(1981,1,1)]
        r = dr._partialDateRangeCheck(
            [RD(1980,12,31),RD(1981,1,1)],
            [dt.date(1981,1,1),dt.date(1981,12,31)],
            DAILY
        )
        self.assertEqual(exp, r)

        # Test back-end partial available dates - DAILY
        exp = [RD(1980,12,31)]
        r = dr._partialDateRangeCheck(
            [RD(1980,12,31),RD(1981,1,1)],
            [dt.date(1980,1,1),dt.date(1980,12,31)],
            DAILY
        )
        self.assertEqual(exp, r)
 
        # Test totally unavailable dates - DAILY
        exp = []
        r = dr._partialDateRangeCheck(
            [RD(1980,1,1),RD(1980,1,2)],
            [dt.date(1982,1,1),dt.date(1982,12,31)],
            DAILY
        )
        self.assertEqual(exp, r)

    def test_validateDateRange(self):
        dr = self.dr

        # Test strict method with good dates - same grain
        exp = {
            'ds1' : [RD(1990,None,None)],
            'ds2' : [RD(1990,None,None)]
        }
        r = dr._validateDateRange(
            "strict",
            {
                'ds1' : ANNUAL,
                'ds2' : ANNUAL
            },
            {ANNUAL : [RD(1990,None,None)]},
            self.dsc
        )
        self.assertEqual(exp, r)

        # Test strict method with good dates - mixed grain
        exp = {
            'ds1' : [RD(1990,None,None)],
            'ds2' : [RD(1990,1,None)]
        }
        r = dr._validateDateRange(
            "strict",
            {
                'ds1' : ANNUAL,
                'ds2' : MONTHLY
            },
            {
                ANNUAL : [RD(1990,None,None)],
                MONTHLY : [RD(1990,1,None)]
            },
            self.dsc
        )
        self.assertEqual(exp, r)

        # Test strict method with bad dates - all datasets
        with self.assertRaisesRegex(ValueError, 'Date range not available for'):
            dr._validateDateRange(
                "strict",
                {
                    'ds1' : ANNUAL,
                    'ds2' : ANNUAL
                },
                {ANNUAL : [RD(2021,None,None)]},
                self.dsc
            )

        # Test strict method with bad dates - some datasets
        with self.assertRaisesRegex(ValueError, 'Date range not available for'):
            dr._validateDateRange(
                "strict",
                {
                    'ds1' : ANNUAL,
                    'ds2' : ANNUAL
                },
                {ANNUAL : [RD(1989,None,None), RD(1990,None,None)]},
                self.dsc
            )


        # Test overlap method with good dates - same grain
        exp = {
            'ds1' : [RD(1990,None,None)],
            'ds2' : [RD(1990,None,None)]
        }
        r = dr._validateDateRange(
            "overlap",
            {
                'ds1' : ANNUAL,
                'ds2' : ANNUAL
            },
            {ANNUAL : [
                RD(1979,None,None), RD(1980,None,None),
                RD(1990,None,None)
            ]},
            self.dsc
        )
        self.assertEqual(exp, r)

        # Test overlap method with good dates - mixed grains
        exp = {
            'ds1' : [RD(1990,None,None)],
            'ds2' : [RD(1990,1,None)]
        }
        r = dr._validateDateRange(
            "overlap",
            {
                'ds1' : ANNUAL,
                'ds2' : MONTHLY
            },
            {
                ANNUAL : [
                    RD(1979,None,None), RD(1980,None,None),
                    RD(1990,None,None)
                ],
                MONTHLY : [
                    RD(1979,1,None), RD(1980,1,None),
                    RD(1990,1,None)
                ]
            },
            self.dsc
        )
        self.assertEqual(exp, r)

        # Test overlap method with bad dates - all datasets
        with self.assertRaisesRegex(
            ValueError, 'Date range not available in any requested dataset'
        ):
            dr._validateDateRange(
                "overlap",
                {
                    'ds1' : ANNUAL,
                    'ds2' : ANNUAL
                },
                {ANNUAL : [RD(2021,None,None)]},
                self.dsc
            )

        # Test all method with good dates - same grain
        exp = {
            'ds1' : [RD(1980,None,None),RD(1990,None,None)],
            'ds2' : [RD(1990,None,None)]
        }
        r = dr._validateDateRange(
            "all",
            {
                'ds1' : ANNUAL,
                'ds2' : ANNUAL
            },
            {ANNUAL : [
                RD(1979,None,None), RD(1980,None,None),
                RD(1990,None,None)
            ]},
            self.dsc
        )
        self.assertEqual(exp, r)

        # Test all method with good dates - mixed grains
        exp = {
            'ds1' : [RD(1980,None,None),RD(1990,None,None)],
            'ds2' : [RD(1990,1,None)]
        }
        r = dr._validateDateRange(
            "all",
            {
                'ds1' : ANNUAL,
                'ds2' : MONTHLY
            },
            {
                ANNUAL : [
                    RD(1979,None,None), RD(1980,None,None),
                    RD(1990,None,None)
                ],
                MONTHLY : [
                    RD(1979,1,None), RD(1980,1,None),
                    RD(1990,1,None)
                ]
            },
            self.dsc
        )
        self.assertEqual(exp, r)

        # Test all method with bad dates - all datasets
        with self.assertRaisesRegex(
            ValueError, 'Date range not available in any requested dataset'
        ):
            dr._validateDateRange(
                "all",
                {
                    'ds1' : ANNUAL,
                    'ds2' : ANNUAL
                },
                {ANNUAL : [RD(2021,None,None)]},
                self.dsc
            )

