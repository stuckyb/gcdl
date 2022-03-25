
import datetime as dt
from collections import namedtuple
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
        self, dataset_catalog, dsvars, date_start, date_end, julian_range,
        month_range, grain_method, subset_geom, target_crs, target_resolution, 
        ri_method, output_format, request_type, req_metadata
    ):
        """
        dataset_catalog: The DatasetCatalog associated with this request.
        dsvars: A dict of lists of variables to include for each dataset with
            dataset IDs as keys.
        date_start: Inclusive start date, specied as 'YYYY', 'YYYY-MM', or
            'YYYY-MM-DD'.
        date_end: Inclusive end date, specied as 'YYYY', 'YYYY-MM', or
            'YYYY-MM-DD'.
        subset_geom: A SubsetGeom representing the clipping region or points to
            use or None.
        target_crs: A CRS instance.
        target_resolution: A float specifying the target spatial resolution in
            units of the target CRS.
        ri_method: The resampling/interpolation algorithm to use for
            reprojection or extracting point data.
        request_type: A constant specifying the output type.
        req_metadata: A key/value mapping of metadata associated with the
            request.
        """
        self.dsc = dataset_catalog
        self.dsvars = dsvars
        self.date_start_raw = date_start
        self.date_end_raw = date_end
        self.dates, self.date_grain = self._parseDates(
            date_start, date_end, julian_range, month_range
        )
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

        if grain_method is None:
            grain_method = 'strict'

        if grain_method not in GRAIN_METHODS:
            raise ValueError(
                f'Invalid date grain matching method: "{grain_method}".'
            )

        self.grain_method = grain_method

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

    def _parseDates(self, date_start, date_end, julian_range, month_range):
        """
        Parses the starting and ending date strings and returns a list of
        RequestDate instances that specifies all dates included in the request.
        We represent request dates this way because it supports sparse date
        ranges.
        """
        dates = []

        if date_start is None:
            date_start = ''
        if date_end is None:
            date_end = ''

        # List out requested julian dates
        if julian_range is None:
            j_range = [i+1 for i in range(366)]
        else:
            j_range = []
            julian_chunks = julian_range.split(',')
            for chunk in julian_chunks:
                cur_range = [int(val) for val in chunk.split('-')]
                if len(cur_range) == 1:
                    j_range.append(cur_range[0])
                else:
                    for j in range(cur_range[0],cur_range[1]+1):
                        j_range.append(j)

        # List out requested months
        if month_range is None:
            m_range = [i+1 for i in range(12)]
        else:
            m_range = []
            month_chunks = month_range.split(',')
            for chunk in month_chunks:
                cur_range = [int(val) for val in chunk.split('-')]
                if len(cur_range) == 1:
                    m_range.append(cur_range[0])
                else:
                    for m in range(cur_range[0],cur_range[1]+1):
                        m_range.append(m)
        
        # Generate RequestDates
        if len(date_start) == 0 and len(date_end) == 0:
            date_grain = NONE

        elif (len(date_start) == 4 and len(date_end) == 4 and
            julian_range is None and month_range is None
        ):
            # Annual data request.
            date_grain = ANNUAL

            start = int(date_start)
            end = int(date_end) + 1
            if end <= start:
                raise ValueError('The end date cannot precede the start date.')
            
            # Generate the dates data structure.
            for year in range(start, end):
                dates.append(RequestDate(year, None, None))

        elif (((len(date_start) == 7 and len(date_end) == 7) or 
            month_range is not None) and julian_range is None
        ):
            # Monthly data request.
            date_grain = MONTHLY

            start_parts = [int(val) for val in date_start.split('-')]
            end_parts = [int(val) for val in date_end.split('-')]

            if len(start_parts) == 2:
                start_y, start_m = start_parts
                end_y, end_m  = end_parts
            else:
                start_y = start_parts[0]
                start_m = 1
                end_y = end_parts[0]
                end_m = 12

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
                if cur_m in m_range:
                    dates.append(RequestDate(cur_y, cur_m, None))

                m_cnt += 1
                cur_y = start_y + m_cnt // 12
                cur_m = (m_cnt % 12) + 1

        elif ((len(date_start) == 10 and len(date_end) == 10) or 
            julian_range is not None
        ):
            # Daily data request.
            date_grain = DAILY

            start_parts = [int(val) for val in date_start.split('-')]
            end_parts = [int(val) for val in date_end.split('-')]

            if len(start_parts) == 3:
                start_y, start_m, start_d = start_parts
                end_y, end_m, end_d  = end_parts
            elif len(start_parts) == 2:
                raise NotImplementedError()
            else:
                start_y = start_parts[0]
                start_m = 1
                start_d = 1
                end_y = end_parts[0]
                end_m = 12
                end_d = 31

            inc_date = dt.date(start_y, start_m, start_d)
            end_date = dt.date(end_y, end_m, end_d)

            if end_date < inc_date:
                raise ValueError('The end date cannot precede the start date.')

            interval = dt.timedelta(days=1)
            end_date += interval

            # Generate the dates data structure.
            while inc_date != end_date:
                jday = inc_date.toordinal() - dt.date(inc_date.year, 1, 1).toordinal() + 1
                if jday in j_range:
                    dates.append(
                        RequestDate(inc_date.year, inc_date.month, inc_date.day)
                    )

                inc_date += interval

        else:
            raise ValueError(
                'Mismatched starting and ending date granularity.'
            )

        return (dates, date_grain)

