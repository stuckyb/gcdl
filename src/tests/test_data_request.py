
import unittest
from pyproj.crs import CRS
from api_core import data_request, RequestDate as RD, DataRequest
from library.catalog import DatasetCatalog
import datetime as dt


class TestDataRequest(unittest.TestCase):
    def setUp(self):
        self.dsc =  DatasetCatalog('test_data')

    def test_init(self):
        # Test a variety of misconfigurations.
        with self.assertRaisesRegex(ValueError, 'Invalid resampling method'):
            dr = DataRequest(
                self.dsc, {},
                # Date parameters.
                '1980', None, None, None, None,
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
                '1980', None, None, None, None,
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
                self.dsc, {},
                # Date parameters.
                '1980', None, None, None, 'fakemethod',
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
                self.dsc, {},
                # Date parameters.
                '1980', None, None, None, None,
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
            '1980', None, None, None, None,
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

        # Test an invalid day of the month.
        with self.assertRaisesRegex(ValueError, 'day is out of range'):
            dr._parseSimpleDateRange('1980-01-40', '1980-01-40')
            
        # Test other error conditions.
        with self.assertRaisesRegex(ValueError, 'Start and end .* specified'):
            dr._parseSimpleDateRange('1980', None)

        with self.assertRaisesRegex(ValueError, 'Start and end .* specified'):
            dr._parseSimpleDateRange('', '1980')

    def test_parseSimpleDates(self):
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

        # Simple date range processing is thoroughly tested in
        # test_parseSimpleDateRange(), so we only need to test basic
        # functionality here.

        # Test annual date requests.
        exp = [RD(1980, None, None)]
        r, dg = dr._parseSimpleDates('1980')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.ANNUAL, dg)

        exp = [RD(1980, None, None), RD(1982, None, None)]
        r, dg = dr._parseSimpleDates('1980,1982')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.ANNUAL, dg)

        exp = [
            RD(1980, None, None), RD(1981, None, None), RD(1982, None, None),
            RD(1990, None, None)
        ]
        r, dg = dr._parseSimpleDates('1980:1982,1990')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.ANNUAL, dg)

        # Test monthly date requests.
        exp = [RD(1980, 1, None)]
        r, dg = dr._parseSimpleDates('1980-01')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        exp = [RD(1980, 1, None), RD(1980, 7, None)]
        r, dg = dr._parseSimpleDates('1980-01,1980-07')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        exp = [
            RD(1980, 1, None), RD(1980, 3, None), RD(1980, 4, None),
            RD(1980, 5, None), RD(1980, 7, None)
        ]
        r, dg = dr._parseSimpleDates('1980-01,1980-03:1980-05,1980-07')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        # Test daily date requests.
        exp = [RD(1980, 1, 1)]
        r, dg = dr._parseSimpleDates('1980-01-01')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        exp = [RD(1980, 1, 1), RD(1982, 2, 10)]
        r, dg = dr._parseSimpleDates('1980-01-01,1982-02-10')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        exp = [
            RD(1980, 1, 1), RD(1980, 12, 31), RD(1981, 1, 1), RD(1981, 1, 2)
        ]
        r, dg = dr._parseSimpleDates('1980-01-01,1980-12-31:1981-01-02')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        # Test that dates get (re-)ordered correctly.
        exp = [RD(1980, None, None), RD(1982, None, None)]
        r, dg = dr._parseSimpleDates('1982,1980')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.ANNUAL, dg)

        exp = [RD(1980, 1, None), RD(1980, 7, None)]
        r, dg = dr._parseSimpleDates('1980-07,1980-01')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        exp = [RD(1980, 1, 1), RD(1980, 1, 10)]
        r, dg = dr._parseSimpleDates('1980-01-10,1980-01-01')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        # Test that duplicate dates are correctly handled.
        exp = [RD(1980, 1, 1), RD(1980, 1, 10)]
        r, dg = dr._parseSimpleDates('1980-01-10,1980-01-01,1980-01-10')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        # Test that mixed date grains are correctly detected.
        with self.assertRaisesRegex(ValueError, 'Cannot mix date grains'):
            dr._parseSimpleDates('1980,1980-01')

    def test_parseRangeStr(self):
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

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
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

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
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

        # Year-only values.
        exp = [RD(1980, None, None)]
        r, dg = dr._parseYMD('1980', None, None)
        self.assertEqual(exp, r)
        self.assertEqual(data_request.ANNUAL, dg)

        exp = [RD(1980, None, None), RD(1982, None, None)]
        r, dg = dr._parseYMD('1980:1982+2', None, None)
        self.assertEqual(exp, r)
        self.assertEqual(data_request.ANNUAL, dg)

        # Year + month values.
        exp = [RD(1980, 4, None)]
        r, dg = dr._parseYMD('1980', '4', None)
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        exp = [RD(1980, 4, None), RD(1981, 4, None)]
        r, dg = dr._parseYMD('1980:1981', '4', None)
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        exp = [
            RD(1980, 10, None), RD(1980, 12, None),
            RD(1981, 10, None), RD(1981, 12, None)
        ]
        r, dg = dr._parseYMD('1980:1981', '10:N+2', None)
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        # Daily values without month.
        exp = [RD(1980, 1, 10)]
        r, dg = dr._parseYMD('1980', None, '10')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        exp = [
            RD(1980, 1, 10), RD(1980, 1, 12),
            RD(1981, 1, 10), RD(1981, 1, 12)
        ]
        r, dg = dr._parseYMD('1980:1981', None, '10:12+2')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        # Daily values without month, including both leap and common years.
        exp = [
            RD(1980, 2, 28), RD(1980, 2, 29),
            RD(1981, 2, 28), RD(1981, 3, 1)
        ]
        r, dg = dr._parseYMD('1980:1981', None, '59:60')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        exp = [
            RD(1980, 12, 30), RD(1980, 12, 31),
            RD(1981, 12, 31)
        ]
        r, dg = dr._parseYMD('1980:1981', None, '365:N')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        # Daily values with month.
        exp = [RD(1980, 4, 10)]
        r, dg = dr._parseYMD('1980', '4', '10')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        exp = [
            RD(1980, 4, 8), RD(1980, 4, 9), RD(1980, 6, 8), RD(1980, 6, 9),
            RD(1981, 4, 8), RD(1981, 4, 9), RD(1981, 6, 8), RD(1981, 6, 9)
        ]
        r, dg = dr._parseYMD('1980:1981', '4:6+2', '8,9')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

        # Daily values with month, including both leap and common years.
        exp = [
            RD(1980, 2, 20), RD(1980, 2, 29), RD(1980, 3, 20), RD(1980, 3, 31),
            RD(1981, 2, 20), RD(1981, 2, 28), RD(1981, 3, 20), RD(1981, 3, 31),
        ]
        r, dg = dr._parseYMD('1980:1981', '2:3', '20,N')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

    def test_parseDates(self):
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', None, None, None, None,
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

        # Simple date strings have precedence over YMD parameters.
        exp = [RD(1980, 1, None), RD(1980, 2, None)]
        r, dg = dr._parseDates('1980-01,1980-02', '1980:1990', None, None)
        self.assertEqual(exp, r)
        self.assertEqual(data_request.MONTHLY, dg)

        # Test YMD dates.  Again, we only need to worry about testing basic
        # parameter handling.
        exp = [RD(1980, 1, 31), RD(1980, 2, 29)]
        r, dg = dr._parseDates(None, '1980', '1:2', 'N')
        self.assertEqual(exp, r)
        self.assertEqual(data_request.DAILY, dg)

    def test_verifyGrains(self):
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', None, None, None, 'strict',
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

        # Test strict grain rule with mis-matched available grains.
        #with self.assertRaisesRegex(
        #    ValueError, 'does not have requested date granularity'
        #):
        #    dr._verifyGrains(data_request.ANNUAL, 'strict')

        # Test strict grain rule with no mis-matched available grains.
        #exp = {}
        #r = dr._verifyGrains(data_request.ANNUAL,'strict')
        #self.assertEqual(exp, r)

        # Test single dataset
        #exp = {}

        # Test coarser method but no coarser options

        # Test finer method but no finer options

        # Test any method

        # Test skip method



    def test_listAllowedGrains(self):
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

        # test coarser methods
        exp = [data_request.MONTHLY, data_request.ANNUAL]
        r = dr._listAllowedGrains(data_request.DAILY, 'coarser')
        self.assertEqual(exp, r)

        exp = [data_request.ANNUAL]
        r = dr._listAllowedGrains(data_request.MONTHLY, 'coarser')
        self.assertEqual(exp, r)

        exp = []
        r = dr._listAllowedGrains(data_request.ANNUAL, 'coarser')
        self.assertEqual(exp, r)

        exp = []
        r = dr._listAllowedGrains(data_request.NONE, 'coarser')
        self.assertEqual(exp, r)

        # test finer methods
        exp = []
        r = dr._listAllowedGrains(data_request.DAILY, 'finer')
        self.assertEqual(exp, r)

        exp = [data_request.DAILY]
        r = dr._listAllowedGrains(data_request.MONTHLY, 'finer')
        self.assertEqual(exp, r)

        exp = [data_request.MONTHLY, data_request.DAILY]
        r = dr._listAllowedGrains(data_request.ANNUAL, 'finer')
        self.assertEqual(exp, r)

        exp = []
        r = dr._listAllowedGrains(data_request.NONE, 'finer')
        self.assertEqual(exp, r)

        # test the any method
        exp = [data_request.ANNUAL, data_request.MONTHLY]
        r = dr._listAllowedGrains(data_request.DAILY, 'any')
        self.assertEqual(exp, r)

        exp = [data_request.ANNUAL, data_request.DAILY]
        r = dr._listAllowedGrains(data_request.MONTHLY, 'any')
        self.assertEqual(exp, r)

        exp = [data_request.MONTHLY, data_request.DAILY]
        r = dr._listAllowedGrains(data_request.ANNUAL, 'any')
        self.assertEqual(exp, r)

        exp = []
        r = dr._listAllowedGrains(data_request.NONE, 'any')
        self.assertEqual(exp, r)

    def test_populateDates(self):
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

        # Test no new grains so no new dates.
        exp = {}
        r = dr._populateDates(
            data_request.ANNUAL, {}, 
            '1980',
            None, None, None
        )
        self.assertEqual(exp, r)

        # Test new dates added by a simple dates string.
        exp = {
            data_request.MONTHLY: [RD(1980, m+1, None) for m in range(12)]
        }
        r = dr._populateDates(
            data_request.ANNUAL, {'ds1': data_request.MONTHLY}, 
            '1980', 
            None, None, None
        )
        self.assertEqual(exp, r)

        # Test new dates added by YMD (see test_populateYMD).
        exp = {
            data_request.MONTHLY: [RD(1980, m+1, None) for m in range(12)]
        }
        r = dr._populateDates(
            data_request.ANNUAL, {'ds1': data_request.MONTHLY}, 
            None, 
            '1980', None, None
        )
        self.assertEqual(exp, r)

    def test_populateYMD(self):
        dr = DataRequest(
            self.dsc, {},
            # Date parameters.
            '1980', None, None, None, None,
            # Subset geometry.
            None,
            # Projection/resolution parameters.
            CRS('NAD83'), None, 'bilinear',
            # Output parameters.
            data_request.REQ_RASTER, None,
            {}
        )

        # Test ANNUAL to MONTHLY
        exp = [RD(1980, m+1, None) for m in range(12)]
        r = dr._populateYMD(
            data_request.ANNUAL,data_request.MONTHLY,
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
            data_request.ANNUAL,data_request.DAILY,
            '1980', None, None
        )
        self.assertEqual(exp, r)

        # Test MONHTLY to ANNUAL
        exp = [RD(1980, None, None)]
        r = dr._populateYMD(
            data_request.MONTHLY,data_request.ANNUAL,
            '1980', '1', None
        )
        self.assertEqual(exp, r)

        # Test MONTHLY to DAILY
        exp = [RD(1980, 1, d+1) for d in range(31)]
        r = dr._populateYMD(
            data_request.MONTHLY,data_request.DAILY,
            '1980', '1', None
        )
        self.assertEqual(exp, r)

        # Test DAILY to MONTHLY
        exp = [RD(1980, 1, None)]
        r = dr._populateYMD(
            data_request.DAILY,data_request.MONTHLY,
            '1980', '1', '1'
        )
        self.assertEqual(exp, r)

        # Test DAILY to ANNUAL
        exp = [RD(1980, None, None)]
        r = dr._populateYMD(
            data_request.DAILY,data_request.ANNUAL,
            '1980', '1', '1'
        )
        self.assertEqual(exp, r)

