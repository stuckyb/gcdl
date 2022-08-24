
import datetime as dt
from collections import namedtuple
import calendar as cal
from pyproj.crs import CRS
from subset_geom import SubsetMultiPoint
from library.datasets.gsdataset import getCRSMetadata
import datetime as dt


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

# Define supported strings for validating date ranges
VALIDATE_METHODS = ('strict', 'overlap', 'all')

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
        self, dataset_catalog, dsvars, dates, years, months, days,
        grain_method, validate_method, subset_geom, target_crs, 
        target_resolution, ri_method, request_type, output_format, 
        req_metadata
    ):
        """
        dataset_catalog: The DatasetCatalog associated with this request.
        dsvars: A dict of lists of variables to include for each dataset with
            dataset IDs as keys.
        dates: Dates to include in the request.
        years: Years to include in the request.
        months: Months to include in the request.
        days: Days to include in the request.
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

        # Parse requested dates, determine date grain(s), 
        # and generate date list(s)
        self.dates_raw = dates
        self.dates = {}
        requested_dates, self.inferred_grain = self._parseDates(
            dates, years, months, days
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
            self.dsc, self.dsvars, self.inferred_grain, self.grain_method
        )
        self.dates.update(self._populateDates(
            self.inferred_grain, self.ds_date_grains, dates, 
            years, months, days
        ))

        # Validate requested date range against datasets' 
        # available data date range
        if validate_method is None:
            validate_method = 'strict'

        if validate_method not in VALIDATE_METHODS:
            raise ValueError(
                f'Invalid date range validation method: "{validate_method}".'
            )

        self.validate_method = validate_method
        self.ds_dates = self._validateDateRange(
            self.validate_method, self.ds_date_grains, self.dates,
            self.dsc
        )

        self.subset_geom = subset_geom
        self.target_crs = target_crs
        self.target_resolution = target_resolution

        if target_resolution is not None and subset_geom is not None:
            self.harmonization = True
        else:
            self.harmonization = False

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

        req_md['target_dates'] = self.dates_raw
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

    def _verifyGrains(self, dsc, dsvars, inferred_grain, grain_method):
        """
        Checks for mixed date granularities and returns a dictionary of date
        grains to use for each temporal dataset
        """
        ds_grains = {}
        allowed_grains = self._listAllowedGrains(inferred_grain, grain_method)

        for dsid in dsvars:
            if not(dsc[dsid].nontemporal):
                if inferred_grain in dsc[dsid].supported_grains:
                    ds_grains[dsid] = inferred_grain
                if inferred_grain not in dsc[dsid].supported_grains:
                    if grain_method == 'strict': 
                        raise ValueError(
                            f'{dsid} does not have requested date granularity'
                        )
                    elif grain_method == 'skip':
                        ds_grains[dsid] = None
                    else:
                        new_grain = None
                        for ag in allowed_grains:
                            if ag in dsc[dsid].supported_grains:
                                new_grain = ag
                                break
                        if new_grain is not None:
                            ds_grains[dsid] = new_grain
                        else:
                            raise ValueError(
                                f'{dsid} has no supported date granularity'
                            )

        return ds_grains

    def _populateYMD(self, original_grain, new_grain, years, months, days):
        """
        Creates date lists for modified date grains in YMD format.
        """
        if new_grain == ANNUAL:
            g_months = None
            g_days = None
        elif new_grain == MONTHLY:
            if original_grain == DAILY:
                g_months = months
            else:
                g_months = '1:12'
            g_days = None
        elif new_grain == DAILY:
            g_days = '1:N'
            if original_grain == MONTHLY:
                g_months = months
            else:
                g_months = '1:12'

        new_date_list, grain = self._parseDates(None, years, g_months, g_days)

        return new_date_list

    def _populateSimpleDates(self, original_grain, new_grain, datesstr):
        """
        Returns a list of RequestDate objects for a new granularity applied to
        the provided dates string.
        """
        new_date_strs = []

        for part in datesstr.split(','):
            if ':' in part:
                date_start, date_end = part.split(':')
            else:
                date_start = date_end = part

            new_ds, new_de = self._modifySimpleDateGrain(
                original_grain, new_grain, date_start, date_end
            )

            new_date_strs.append(new_ds + ':' + new_de)

        new_dates_str = ','.join(new_date_strs)

        new_date_list, grain = self._parseDates(
            new_dates_str, None, None, None
        )

        return new_date_list

    def _modifySimpleDateGrain(
        self, original_grain, new_grain, date_start, date_end
    ):
        """
        Returns new starting and ending simple date strings that reflect the
        new grain.  Expects strings of the format "YYYY", "YYYY-MM", or
        "YYYY-MM-DD".  Leading 0s are optional for "MM" and "DD".
        """
        if new_grain == ANNUAL:
            g_start = date_start[0:4]
            g_end = date_end[0:4]
        elif new_grain == MONTHLY:
            if original_grain == DAILY:
                g_start = date_start[0:date_start.rindex('-')]
                g_end = date_end[0:date_end.rindex('-')]
            else:
                g_start = date_start + '-01'
                g_end = date_end + '-12'  
        elif new_grain == DAILY:
            if original_grain == MONTHLY:
                g_start = date_start + '-01'
                end_yr, end_month = [int(p) for p in date_end.split('-')]
                days_in_month = cal.monthrange(end_yr, end_month)[1]
                g_end = f'{date_end}-{days_in_month}'
            else:
                g_start = date_start + '-01-01'
                g_end = date_end + '-12-31' 

        return (g_start, g_end)

    def _populateDates(
        self, original_grain, new_grains, datesstr, years, months, days
    ):
        """
        Creates dictionary of date lists per unique date grain in new_grains.
        """
        new_grains_unique = set(new_grains.values())

        grain_dates = {}

        # Need to modify date inputs per new grain:
        for ug in new_grains_unique:
            if ug is None or ug == original_grain:
                continue
            elif datesstr is not None and datesstr != '':
                grain_dates[ug] = self._populateSimpleDates(
                    original_grain, ug, datesstr
                )
            else:
                grain_dates[ug] = self._populateYMD(
                    original_grain, ug, years, months, days
                )

        return grain_dates

    def _parseSimpleDates(self, datesstr):
        """
        Parses a dates string and returns a list of
        RequestDate instances that specifies all dates included in the request.
        day of month.  The dates string should be of the format (in EBNF):
          DATESSTR = (SINGLEDATE | DATERANGE) , [{",", (SINGLEDATE | DATERANGE)}]
          SINGLEDATE = string of the format "YYYY", "YYYY-MM", or "YYYY-MM-DD".
            "MM" and "DD" may also be specified as "M" or "D" (i.e., leading 0s
            are not required).
          DATERANGE = SINGLEDATE, ":", SINGLEDATE
        The RequestDate instances are returned in order from oldest to most
        recent.
        """
        dvals = set()
        date_grain = None

        parts = datesstr.split(',')

        for part in parts:
            if ':' in part:
                dr_lims = part.split(':')
                if len(dr_lims) != 2:
                    raise ValueError(f'Invalid simple date range: {part}.')

                dr_start, dr_end = dr_lims
            else:
                dr_start = dr_end = part

            new_dates, new_grain = self._parseSimpleDateRange(dr_start, dr_end)

            if date_grain is None:
                date_grain = new_grain
            elif date_grain != new_grain:
                raise ValueError(
                    f'Cannot mix date grains in a dates string: {datesstr}.'
                )

            dvals.update(new_dates)

        return (sorted(dvals), date_grain)

    def _parseSimpleDateRange(self, date_start, date_end):
        """
        Parses starting and ending date strings and returns a list of
        RequestDate instances that specifies all dates included in the request.
        Also returns the date grain of the request.  Results are returned as
        the tuple (dates, grain).
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

        elif len(date_start) in (6,7) and len(date_end) in (6,7):
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

        elif len(date_start) in (8,9,10) and len(date_end) in (8,9,10):
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
                'Mismatched starting and ending date range granularity.'
            )

        return (dates, date_grain)

    def _parseRangeStr(self, rangestr, maxval):
        """
        Parses a range string of the format "STARTVAL:ENDVAL[+INCREMENT]".
        Returns the range as an ordered list of integers (smallest to largest),
        which includes the endpoints unless ENDVAL does not correspond with the
        increment size.  If ENDVAL == 'N', it is interpreted as maxval.

        rangestr: The range string to parse.
        maxval: The maximum value allowed for the range.
        """
        parts = rangestr.split(':')
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
        Parses a string that specifies integer values for year, day of year, or
        day of month.  The string should be of the format (in EBNF):
          NUMVALSSTR = (SINGLEVAL | RANGESTR) , [{",", (SINGLEVAL | RANGESTR)}]
          SINGLEVAL = (integer | "N")
          RANGESTR = integer, ":", integer, ["+", integer]
        Returns the corresponding list of integers in increasing order.  If
        SINGLEVAL == "N", it is interpreted as maxval.

        nvstr: The number values string.
        maxval: The maximum allowed integer value.
        """
        nvals = set()

        parts = nvstr.split(',')

        for part in parts:
            if ':' in part:
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

    def _parseDates(self, datesstr, years, months, days):
        """
        Parses the dates parameter strings and returns a list of RequestDate
        instances that represent all dates included in the request.  We
        represent request dates this way because it supports sparse date
        ranges.
        """
        dates = []

        if all(
            param is None or param == '' for param in
            (datesstr, years, months, days)
        ):
            date_grain = NONE

            return (dates, date_grain)

        if datesstr is not None and datesstr != '':
            dates, date_grain = self._parseSimpleDates(datesstr)
        else:
            dates, date_grain = self._parseYMD(years, months, days)

        return (dates, date_grain)


    def _requestDateAsDatetime(self, rdate, grain):
        if grain == ANNUAL:
            date = dt.date(rdate.year,1,1)
        elif grain == MONTHLY:
            date = dt.date(rdate.year,rdate.month,1)
        elif grain == DAILY:
            date = dt.date(rdate.year,rdate.month,rdate.day)

        return date

    def _strictDateRangeCheck(self, requested_dates, available_range, grain):
        """
        Checks if the dates requested are fully contained in a date range.
        Returns boolean indicating if fully contained or not. 
        """
        # Is the beginning of date range available?
        start_request = self._requestDateAsDatetime(
            requested_dates[0], grain
        )
        start_available = available_range[0]
        start_contained = start_request >= start_available

        # Is the end of date range available?
        end_request = self._requestDateAsDatetime(
            requested_dates[-1], grain
        )
        end_available = available_range[-1]
        end_contained = end_request <= end_available

        result = start_contained and end_contained
        return result

    def _partialDateRangeCheck(self, requested_dates, available_range, grain):
        """
        Checks the requested dates against the available date range
        and returns the subset of requested dates available. 
        """
        available_rdates = [] 
        for rdate in requested_dates:
            available = self._strictDateRangeCheck(
                [rdate], available_range, grain
            )
            if available:
                available_rdates.append(rdate)
        
        return available_rdates

    def _validateDateRange(
        self, method, req_grains, req_dates, dsc
    ):
        """
        Validates the dates requested against available data ranges
        using different validation methods. 
        Assumes dates are chronologically ordered. 

        method : validation method [strict, overlap, all]
        req_grains : a dictionary of date grain per dataset
        req_dates : a dictionary of date list per grain

        Returns a dictionary with date list per dataset
        """

        grain_to_range_key = [None,'year','month','day']

        # For each dataset, check if requested dates are fully
        # contained in their available date range. Store available
        # dates.
        ds_avail_dates = {}
        all_available = True
        for dsid in req_grains:
            ds_grain = req_grains[dsid]
            if ds_grain is None:
                ds_avail_dates[dsid] = [None]
                continue
            ds_req_dates = req_dates[ds_grain]
            ds_range_key = grain_to_range_key[ds_grain]
            ds_avail_date_range = dsc[dsid].date_ranges[ds_range_key]

            fully_available = self._strictDateRangeCheck(
                ds_req_dates, ds_avail_date_range, ds_grain
            )
            if fully_available:
                ds_avail_dates[dsid] = ds_req_dates
            else:
                all_available = False
                if method == 'strict':
                    raise ValueError(
                        f'Date range not available for dataset: "{dsid}".'
                    )
                else:
                    # Find the subset of requested dates available
                    ds_avail_dates[dsid] = self._partialDateRangeCheck(
                        ds_req_dates, ds_avail_date_range, ds_grain
                    )


        # Based on method, return new date dictionary.
        # strict: if you got here w/o error, then all requested dates 
        #   are available so return ds_avail_dates.
        # all: all available dates have been saved in ds_avail_dates,
        #   so return it.
        # overlap: need to find common dates among requested datasets
        if method in ['strict', 'all'] or all_available:
            # Are any dates available?
            num_avail = [len(d) for d in ds_avail_dates.values()]
            if sum(num_avail) > 0:
                return ds_avail_dates
            else:
                raise ValueError(
                    f'Date range not available in any requested dataset'
                )
            
        elif method == 'overlap':
            # For each date grain, accumulate available dates from datasets
            grain_intersection = {}
            all_years = []
            all_months = []
            all_days = []
            for grain in req_dates:
                # Datasets with this grain
                grain_dsid = [dsid for dsid in req_grains if req_grains[dsid] == grain]

                if grain == ANNUAL:
                    # Find available requested years
                    for dsid in grain_dsid:
                        all_years.append([rdate.year for rdate in ds_avail_dates[dsid]])
                elif grain == MONTHLY:
                    # Convert to datetime.date objects
                    for dsid in grain_dsid:
                        all_months.append([self._requestDateAsDatetime(rdate, grain) for rdate in ds_avail_dates[dsid]])
                        all_years.append([rdate.year for rdate in ds_avail_dates[dsid]])
                elif grain == DAILY:
                    # Convert to datetime.date objects
                    for dsid in grain_dsid:
                        all_days.append([self._requestDateAsDatetime(rdate, grain) for rdate in ds_avail_dates[dsid]])
                        all_months.append([self._requestDateAsDatetime(rdate, grain) for rdate in ds_avail_dates[dsid]])
                        all_years.append([rdate.year for rdate in ds_avail_dates[dsid]])
            
            # Per date grain, find intersection of dates
            # Annual: intersection of years from annual, monthly, and daily dates
            if ANNUAL in req_dates.keys():
                yr_int = list(set(all_years[0]).intersection(*all_years[1:]))
                grain_intersection[ANNUAL] = [RequestDate(yr,None,None) for yr in yr_int]
            # Monthly: intersection of months from monthly and daily dates
            if MONTHLY in req_dates.keys():
                month_int = list(set(all_months[0]).intersection(*all_months[1:]))
                grain_intersection[MONTHLY] = [RequestDate(d.year,d.month,None) for d in month_int]
            # Daily: intersection of days from daily dates
            if DAILY in req_dates.keys():
                day_int = list(set(all_days[0]).intersection(*all_days[1:]))
                grain_intersection[DAILY] = [RequestDate(d.year,d.month,d.day) for d in day_int]
                
            # For each dataset, use grain intersection to fill out
            # each dataset's dates
            overlapping_dates = {}
            empty_dates = False
            for dsid in req_grains:
                g_int = grain_intersection[req_grains[dsid]]
                if g_int:
                    overlapping_dates[dsid] = g_int
                else:
                    empty_dates = True

            if empty_dates:
                raise ValueError(
                    f'Date range not available in any requested dataset'
                )

            return overlapping_dates

        else:
            raise ValueError(
                f'Invalid date range validation method: "{method}".'
            )




