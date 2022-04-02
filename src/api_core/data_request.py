
import datetime as dt
from collections import namedtuple
import calendar as cal
from pyproj.crs import CRS
from subset_geom import SubsetMultiPoint
from library.datasets.gsdataset import getCRSMetadata


# Date granularity constants.
NONE = 0
ANNUAL = 1
MONTHLY = 2
DAILY = 3

# Request type constants.
REQ_RASTER = 0
REQ_POINT = 1

# Define valid resampling/interpolation algorithms.
RESAMPLE_METHODS = (
    'nearest', 'bilinear', 'cubic', 'cubic-spline', 'lanczos', 'average',
    'mode'
)
POINT_METHODS = ('nearest', 'linear')

# Define supported strings for handling mixed date grains
GRAIN_METHODS = ('strict', 'skip', 'coarser', 'finer', 'any')

# Define supported strings for output formats
GRID_OUTPUT = ('geotiff','netcdf')
POINT_OUTPUT = ('csv','shapefile','netcdf')
FILE_EXT = {
    'geotiff': '.tif',
    'netcdf': '.nc',
    'csv': '.csv',
    'shapefile': '.shp'
    }

# A simple struct-like class for capturing data request date information.  We
# need this instead of the standard datetime.date class because the latter does
# not allow year- or month-only dates (i.e., where month or day are None).
RequestDate = namedtuple('RequestDate', ['year', 'month', 'day'])


class DataRequest:
    """
    Encapsulates and validates a single API data request.
    """
    def __init__(
        self, dataset_catalog, dsvars, date_start, date_end, years, 
        months, days, grain_method, subset_geom, target_crs, 
        target_resolution, ri_method, request_type, output_format,
        req_metadata
    ):
        """
        dataset_catalog: The DatasetCatalog associated with this request.
        dsvars: A dict of lists of variables to include for each dataset with
            dataset IDs as keys.
        date_start: Inclusive start date, specied as 'YYYY', 'YYYY-MM', or
            'YYYY-MM-DD'.
        date_end: Inclusive end date, specied as 'YYYY', 'YYYY-MM', or
            'YYYY-MM-DD'.
        years: Years to include in request.
        months: Months to include in request.
        days: Days to include in request.
        grain_method: 
        subset_geom: A SubsetGeom representing the clipping region or points to
            use or None.
        target_crs: A CRS instance.
        target_resolution: A float specifying the target spatial resolution in
            units of the target CRS.
        ri_method: The resampling/interpolation algorithm to use for
            reprojection or extracting point data.
        request_type: A constant specifying the output type.
        output_format: A constant specifying the output file format.
        req_metadata: A key/value mapping of metadata associated with the
            request.
        """
        self.dsc = dataset_catalog
        self.dsvars = dsvars
        self.date_start_raw = date_start
        self.date_end_raw = date_end
        self.dates = {}
        requested_dates, self.inferred_grain = self._parseDates(
            date_start, date_end, years, months, days
        )
        self.dates[self.inferred_grain] = requested_dates

        if grain_method is None:
            grain_method = 'strict'

        if grain_method not in GRAIN_METHODS:
            raise ValueError(
                f'Invalid date grain matching method: "{grain_method}".'
            )

        self.grain_method = grain_method
        self.ds_date_grains = self._verifyGrains(
            self.inferred_grain, self.grain_method
        )
        self.dates.update(self._populateDates(
            self.inferred_grain, self.ds_date_grains, date_start, date_end, 
            years, months, days
        ))

        self.subset_geom = subset_geom
        self.target_crs = target_crs
        self.target_resolution = target_resolution

        if request_type not in (REQ_RASTER, REQ_POINT):
            raise ValueError('Invalid request type.')

        self.request_type = request_type

        if ri_method is None:
            ri_method = 'nearest'

        if (
            request_type == REQ_RASTER and
            ri_method not in RESAMPLE_METHODS
        ):
            raise ValueError(
                f'Invalid resampling method: "{ri_method}".'
            )

        if (
            request_type == REQ_POINT and
            ri_method not in POINT_METHODS
        ):
            raise ValueError(
                f'Invalid point interpolation method: "{ri_method}".'
            )

        if (
            request_type == REQ_POINT and
            not(isinstance(subset_geom, SubsetMultiPoint))
        ):
            raise ValueError('No points provided for output.')

        self.ri_method = ri_method
        self.metadata = self._getMetadata(req_metadata)

        if output_format is None:
            if request_type == REQ_RASTER:
                output_format = 'geotiff'
            else:
                output_format = 'csv'

        if (
            request_type == REQ_RASTER and
            output_format not in GRID_OUTPUT
        ):
            raise ValueError(
                f'Invalid output format: "{output_format}".'
            )

        if (
            request_type == REQ_POINT and
            output_format not in POINT_OUTPUT
        ):
            raise ValueError(
                f'Invalid output format: "{output_format}".'
            )

        self.file_extension = FILE_EXT[output_format]

    def _getMetadata(self, req_vals):
        req_md = {}
        req_md.update(req_vals)

        req_md['target_date_range'] = [self.date_start_raw, self.date_end_raw]
        req_md['target_crs'] = getCRSMetadata(self.target_crs)

        if self.request_type == REQ_RASTER:
            req_md['request_type'] = 'raster'
            req_md['target_resolution'] = self.target_resolution
            req_md['resample_method'] = self.ri_method
        elif self.request_type == REQ_POINT:
            req_md['request_type'] = 'points'
            req_md['interpolation_method'] = self.ri_method

        md = {'request': req_md}

        ds_md = []
        for dsid in self.dsvars:
            dsd = self.dsc[dsid].getMetadata()
            dsd['requested_vars'] = self.dsvars[dsid]
            ds_md.append(dsd)

        md['datasets'] = ds_md

        return md

    def _listAllowedGrains(self, grain, method):
        """
        Given a date grain and a grain method, returns a list 
        of other grains allowed by the method from coarser to finer
        """
        grains = []
        if method == 'finer':
            if grain == ANNUAL:
                grains = [MONTHLY, DAILY]
            if grain == MONTHLY:
                grains = [DAILY]
        elif method == 'coarser':
            if grain == DAILY:
                grains = [MONTHLY, ANNUAL]
            if grain == MONTHLY:
                grains = [ANNUAL]
        elif method == 'any' and grain != NONE:
            grains = [g for g in [ANNUAL, MONTHLY, DAILY] if g != grain]

        return grains

    def _verifyGrains(self, inferred_grain, grain_method):
        """
        Checks for mixed date granularities and returns a dictionary of date grains
        to use for each temporal dataset
        """
        ds_grains = {}
        allowed_grains = self._listAllowedGrains(inferred_grain, grain_method)

        for dsid in self.dsvars:
            if not(self.dsc[dsid].nontemporal):
                if inferred_grain in self.dsc[dsid].supported_grains:
                    ds_grains[dsid] = inferred_grain
                if inferred_grain not in self.dsc[dsid].supported_grains:
                    if grain_method == 'strict': 
                        raise ValueError('{0} does not have requested date granularity'.format(dsid))
                    elif grain_method == 'skip':
                        ds_grains[dsid] = None
                    else:
                        new_grain = None
                        for ag in allowed_grains:
                            if ag in self.dsc[dsid].supported_grains:
                                new_grain = ag
                                break
                        if new_grain is not None:
                            ds_grains[dsid] = new_grain
                        else:
                            raise ValueError('{0} has no supported date granularity'.format(dsid))

        return ds_grains

    def _populateYMD(self, original_grain, new_grain, years, months, days):
        """
        Creates date lists for modified date grains in YMD format
        """
        if new_grain == ANNUAL:
            g_months = None
            g_days = None
        elif new_grain == MONTHLY:
            if original_grain == DAILY:
                g_months = months
            else:
                g_months = '1-12'
            g_days = None
        elif new_grain == DAILY:
            g_days = '1-N'
            if original_grain == MONTHLY:
                g_months = months
            else:
                g_months = '1-12'

        new_date_list, grain = self._parseDates(
            None, None, years, g_months, g_days
        )

        return(new_date_list)

    def _populateSimpleDateRange(self, original_grain, new_grain, date_start, date_end):
        if new_grain == ANNUAL:
            g_start = date_start[0:3]
            g_end = date_end[0:3]
        elif new_grain == MONTHLY:
            if original_grain == DAILY:
                g_start = date_start[0:6]
                g_end = date_end[0:6]
            else:
                g_start = date_start + '-01'
                g_end = date_end + '-12'  
        elif new_grain == DAILY:
            if original_grain == MONTHLY:
                g_start = date_start + '-01'
                days_in_month = cal.monthrange(
                    date_start[0:3], date_start[5:6]
                )[1]
                g_end = date_start + '-' + days_in_month 
            else:
                g_start = date_start + '-01-01'
                g_end = date_end + '-12-31' 

        new_date_list, grain  = self._parseDates(
            g_start, g_end, None, None, None
        )

        return(new_date_list)


    def _populateDates(self, original_grain, new_grains, date_start, date_end, 
            years, months, days):
        """
        Creates dictionary of date lists per unique date grain in new_grains 
        """
        new_grains_unique = set(new_grains.values())

        grain_dates = {}

        # Need to modify date inputs per new grain:
        for ug in new_grains_unique:
            if ug is None or ug == original_grain:
                continue
            elif date_start is not None or date_end is not None:
                grain_dates[ug] = self._populateSimpleDateRange(
                    original_grain, ug, years, months, days
                )
            else:
                grain_dates[ug] = self._populateYMD(
                    original_grain, ug, years, months, days
                )

        return grain_dates

    def _parseSimpleDateRange(self, date_start, date_end):
        """
        Parses starting and ending date strings and returns a list of
        RequestDate instances that specifies all dates included in the request.
        """
        dates = []

        if date_start is None:
            date_start = ''
        if date_end is None:
            date_end = ''

        if date_start == '' or date_end == '':
            raise ValueError('Start and end dates must both be specified.')

        if len(date_start) == 4 and len(date_end) == 4:
            # Annual data request.
            date_grain = ANNUAL

            start = int(date_start)
            end = int(date_end) + 1
            if end <= start:
                raise ValueError('The end date cannot precede the start date.')
            
            # Generate the dates list.
            for year in range(start, end):
                dates.append(RequestDate(year, None, None))

        elif len(date_start) == 7 and len(date_end) == 7:
            # Monthly data request.
            date_grain = MONTHLY

            start_y, start_m = [int(val) for val in date_start.split('-')]
            end_y, end_m = [int(val) for val in date_end.split('-')]

            if start_m < 1 or start_m > 12:
                raise ValueError(f'Invalid month value: {start_m}.')
            if end_m < 1 or end_m > 12:
                raise ValueError(f'Invalid month value: {end_m}.')

            if end_y * 12 + end_m < start_y * 12 + start_m:
                raise ValueError('The end date cannot precede the start date.')

            # Generate the dates list.
            cur_y = start_y
            cur_m = start_m
            m_cnt = start_m - 1
            while cur_y * 12 + cur_m <= end_y * 12 + end_m:
                dates.append(RequestDate(cur_y, cur_m, None))

                m_cnt += 1
                cur_y = start_y + m_cnt // 12
                cur_m = (m_cnt % 12) + 1

        elif len(date_start) == 10 and len(date_end) == 10:
            # Daily data request.
            date_grain = DAILY

            start_y, start_m, start_d = [
                int(val) for val in date_start.split('-')
            ]
            end_y, end_m, end_d = [int(val) for val in date_end.split('-')]

            inc_date = dt.date(start_y, start_m, start_d)
            end_date = dt.date(end_y, end_m, end_d)

            if end_date < inc_date:
                raise ValueError('The end date cannot precede the start date.')

            interval = dt.timedelta(days=1)
            end_date += interval

            # Generate the dates list.
            while inc_date != end_date:
                dates.append(
                    RequestDate(inc_date.year, inc_date.month, inc_date.day)
                )

                inc_date += interval

        else:
            raise ValueError(
                'Mismatched starting and ending date granularity.'
            )

        return (dates, date_grain)

    def _parseRangeStr(self, rangestr, maxval):
        """
        Parses a range string of the format "STARTVAL-ENDVAL[+INCREMENT]".
        Returns the range as an ordered list of integers (smallest to largest),
        which includes the endpoints unless ENDVAL does not correspond with the
        increment size.  If ENDVAL == 'N', it is interpreted as maxval.

        rangestr: The range string to parse.
        maxval: The maximum value allowed for the range.
        """
        parts = rangestr.split('-')
        if len(parts) != 2:
            raise ValueError(f'Invalid range string: "{rangestr}".')

        startval = int(parts[0])

        if '+' in parts[1]:
            # Extract the increment size.
            end_parts = parts[1].split('+')
            if len(end_parts) != 2:
                raise ValueError(f'Invalid range string: "{rangestr}".')

            endval_str = end_parts[0]
            inc = int(end_parts[1])
        else:
            endval_str = parts[1]
            inc = 1

        # Determine the ending value of the range.
        if endval_str == 'N':
            if maxval is None:
                raise ValueError(
                    f'Cannot interpret range string "{rangestr}": no maximum '
                    'value was provided.'
                )
            endval = maxval
        else:
            endval = int(endval_str)

        # Check for a bunch of error conditions.
        if startval > endval:
            raise ValueError(
                f'Invalid range string: "{rangestr}". The starting value '
                'cannot exceed the ending value.'
            )
        
        if startval <= 0 or endval <= 0:
            raise ValueError(
                f'Invalid range string: "{rangestr}". The starting and '
                'and ending values must be greater than 0.'
            )

        if maxval is not None and endval > maxval:
            raise ValueError(
                f'Invalid range string: "{rangestr}". The ending value '
                f'cannot exceed {maxval}.'
            )

        return list(range(startval, endval + 1, inc))

    def _parseNumValsStr(self, nvstr, maxval):
        """
        Parses a string that specifies integer values for day of year or day of
        month.  The string should be of the format (in EBNF):
          NUMVALSSTR = (SINGLEVAL | RANGESTR) , [{",", (SINGLEVAL | RANGESTR)}]
          SINGLEVAL = (integer | "N")
          RANGESTR = integer, "-", integer, ["+", integer]
        Returns the corresponding list of integers in increasing order.  If
        SINGLEVAL == 'N", it is interpreted as maxval.

        nvstr: The number values string.
        maxval: The maximum allowed integer value.
        """
        nvals = set()

        parts = nvstr.split(',')

        for part in parts:
            if '-' in part:
                nvals.update(self._parseRangeStr(part, maxval))
            else:
                if part == 'N':
                    if maxval is None:
                        raise ValueError(
                            f'Cannot interpret number values string "{nvstr}": '
                            'no maximum value was provided.'
                        )
                    newval = maxval
                else:
                    newval = int(part)

                if maxval is not None and newval > maxval:
                    raise ValueError(
                        f'Invalid date values string: "{nvstr}". The values '
                        f'cannot exceed {maxval}.'
                    )
                
                if newval <= 0:
                    raise ValueError(
                        f'Invalid date values string: "{nvstr}". The values '
                        f'must be greater than 0.'
                    )

                nvals.add(newval)

        return sorted(nvals)

    def _parseYMD(self, years_str, months_str, days_str):
        """
        Generates a list of RequestDate instances based on the date number
        value strings (see _parseNumValsStr() for details) years, months, and
        days.
        """
        if years_str is None or years_str == '':
            raise ValueError('The years to include were not specified.')

        # Parse the year values.
        years = self._parseNumValsStr(years_str, None)
    
        # Parse the month values.
        if months_str is not None and months_str != '':
            months = self._parseNumValsStr(months_str, 12)
        else:
            months = None

        if days_str == '':
            days_str = None

        dates = []

        if days_str is None:
            if months is None:
                date_grain = ANNUAL

                for year in years:
                    dates.append(RequestDate(year, None, None))

            else:
                date_grain = MONTHLY

                for year in years:
                    for month in months:
                        dates.append(RequestDate(year, month, None))

        else:
            date_grain = DAILY

            if months is None:
                # Pre-parse the day values for leap years and common years so
                # we don't have to repeatedly parse the day values string.
                days_common = self._parseNumValsStr(days_str, 365)
                days_leap = self._parseNumValsStr(days_str, 366)

                for year in years:
                    if cal.isleap(year):
                        days = days_leap
                    else:
                        days = days_common

                    ord_year = dt.date(year, 1, 1).toordinal()

                    for day in days:
                        # Get the month and day of month for the given day of
                        # year.
                        d = dt.date.fromordinal(ord_year + day - 1)
                        dates.append(RequestDate(year, d.month, d.day))

            else:
                for year in years:
                    for month in months:
                        # Get the number of days in the month and use this as
                        # the maxval for parsing the day values string.
                        days_in_month = cal.monthrange(year, month)[1]
                        days = self._parseNumValsStr(days_str, days_in_month)

                        for day in days:
                            dates.append(RequestDate(year, month, day))

        return (dates, date_grain)

    def _parseDates(self, date_start, date_end, years, months, days):
        """
        Parses the starting and ending date strings and returns a list of
        RequestDate instances that specifies all dates included in the request.
        We represent request dates this way because it supports sparse date
        ranges.
        """
        dates = []

        if all(
            param is None or param == '' for param in
            (date_start, date_end, years, months, days)
        ):
            date_grain = NONE

            return (dates, date_grain)

        if date_start is not None or date_end is not None:
            dates, date_grain = self._parseSimpleDateRange(date_start, date_end)
        else:
            dates, date_grain = self._parseYMD(years, months, days)

        return (dates, date_grain)

