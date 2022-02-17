
import datetime as dt
from collections import namedtuple
from pyproj.crs import CRS
from subset_geom import SubsetMultiPoint


# Date granularity constants.
ANNUAL = 0
MONTHLY = 1
DAILY = 2

# Request type constants.
REQ_RASTER = 0
REQ_POINT = 1

# Define valid resampling/interpolation algorithms.
RESAMPLE_METHODS = (
    'nearest', 'bilinear', 'cubic', 'cubic-spline', 'lanczos', 'average',
    'mode'
)
POINT_METHODS = ('nearest', 'linear')


# A simple struct-like class for capturing data request date information.  We
# need this instead of the standard datetime.date class because the latter does
# not allow year- or month-only dates (i.e., where month or day are None).
RequestDate = namedtuple('RequestDate', ['year', 'month', 'day'])


class DataRequest:
    """
    Encapsulates a single API data request.
    """
    def __init__(
        self, dsvars, date_start, date_end, subset_geom, target_crs,
        target_resolution, ri_method, req_metadata, request_type
    ):
        """
        dsvars: A dict of lists of variables to include for each dataset with
            dataset IDs as keys.
        date_start: Inclusive start date, specied as 'YYYY', 'YYYY-MM', or
            'YYYY-MM-DD'.
        date_end: Inclusive end date, specied as 'YYYY', 'YYYY-MM', or
            'YYYY-MM-DD'.
        subset_geom: A SubsetGeom representing the clipping region or points to
            use or None.
        target_crs: A string specifying the target CRS.
        target_resolution: A float specifying the target spatial resolution in
            units of the target CRS.
        ri_method: The resampling/interpolation algorithm to use for
            reprojection or extracting point data.
        req_metadata: A dictionary of metadata associated with the request.
        request_type: A constant specifying the output type.
        """
        self.dsvars = dsvars
        self.dates, self.date_grain = self._parse_dates(date_start, date_end)
        self.subset_geom = subset_geom
        self.target_crs = CRS(target_crs)
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
        self.metadata = req_metadata

    def _parse_dates(self, date_start, date_end):
        """
        Parses the starting and ending date strings and returns a list of
        RequestDate instances that specifies all dates included in the request.
        We represent request dates this way because it supports sparse date
        ranges.
        """
        dates = []

        if len(date_start) == 4 and len(date_end) == 4:
            # Annual data request.
            date_grain = ANNUAL

            start = int(date_start)
            end = int(date_end) + 1
            if end <= start:
                raise ValueError('The end date cannot precede the start date.')
            
            # Generate the dates data structure.
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

            # Generate the dates data structure.
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

            # Generate the dates data structure.
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

