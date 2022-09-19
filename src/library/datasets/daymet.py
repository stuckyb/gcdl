
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class DaymetV4(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'daymetv4')

        # Basic dataset information.
        self.id = 'DaymetV4'
        self.name = 'Daymet Version 4'
        self.url = 'https://daymet.ornl.gov/'

        # CRS information.
        self.crs = CRS.from_proj4(
            '+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 '
            '+x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs'
        )

        # The grid size
        self.grid_size = 1000
        self.grid_unit = 'meters'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'prcp': 'precipitation', 
            'tmin': 'minimum temperature',
            'tmax': 'maximum temperature', 
            'swe': 'snow water equivalent',
            'vp': 'water vapor pressure'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            datetime.date(1980, 1, 1), datetime.date(2020, 1, 1)
        ]
        self.date_ranges['month'] = [
            datetime.date(1980, 1, 1), datetime.date(2020, 12, 1)
        ]
        self.date_ranges['day'] = [
            datetime.date(1980, 1, 1), datetime.date(2020, 12, 31)
        ]

        # Temporal resolution
        self.temporal_resolution['year'] = '1 year'
        self.temporal_resolution['month'] = '1 month'
        self.temporal_resolution['day'] = '1 day'

        # File name patterns for each DaymetV4 variable.
        self.fpatterns = {
            'prcp': 'daymet_v4_prcp_{0}ttl_na_{1}',
            'tmin': 'daymet_v4_tmin_{0}avg_na_{1}',
            'tmax': 'daymet_v4_tmax_{0}avg_na_{1}',
            'swe': 'daymet_v4_swe_{0}avg_na_{1}',
            'vp': 'daymet_v4_vp_{0}avg_na_{1}'
        }

        # Attributes for caching loaded and subsetted data.
        self.data_loaded = None
        self.cur_data = None
        self.current_clip = None
        self.cur_data_clipped = None

        # Additional information about the dataset's configuration
        # in GeoCDL
        self.notes = ('DaymetV4 original timestamps are in YYYY-MM-DD HH '
        'but are truncated to YYYY-MM.')

    def _loadData(self, varname, date_grain, request_date, subset_geom):
        """
        Loads the data from disk, if needed.  Will re-use already loaded (and
        subsetted) data whenever possible.
        """
        # DaymetV4 data comes in both TIFF and NetCDF format; we will support
        # both, but define a preferred format for each date grain.
        exts = ('.tif', '.nc')

        # Get the file name of the requested data.
        if date_grain == dr.ANNUAL:
            fname = self.fpatterns[varname].format('ann', request_date.year)
            pref_ext = 0
        elif date_grain == dr.MONTHLY:
            fname = self.fpatterns[varname].format('mon',request_date.year)
            pref_ext = 0
        elif date_grain == dr.DAILY:
            raise NotImplementedError()
        else:
            raise ValueError('Invalid date grain specification.')

        # See if the data file is available in the preferred format; if not,
        # try the other format.
        fpath = self.ds_path / (fname + exts[pref_ext])
        if not(fpath.is_file()):
            fpath = self.ds_path / (fname + exts[(pref_ext + 1) % 2])

        # Load the data from disk, if needed.
        data_needed = (fname, varname)
        if data_needed != self.data_loaded:
            data = rioxarray.open_rasterio(fpath, masked=True)

            # Opening the .nc version of the data will return a list with the
            # relevant xarray Dataset as the second element, so we need to
            # extract the xarray DataArray for the target variable.  Opening
            # the .tif version will give us the DataArray directly.
            if isinstance(data, list):
                data = data[1][varname]

            # Update the cache.
            self.data_loaded = data_needed
            self.cur_data = data
            self.current_clip = None
            self.cur_data_clipped = None

        if isinstance(subset_geom, SubsetPolygon):
            # Another option here would be to test for object identity, which
            # would in theory be faster but less flexible.
            if subset_geom != self.current_clip:
                # Clip the data and update the cache.
                self.cur_data_clipped = data.rio.clip(
                    [subset_geom.json], 
                    all_touched = True,
                    from_disk=True
                )
                self.current_clip = subset_geom

            # Return the cached, subsetted data.
            data_ret = self.cur_data_clipped
        else:
            # Return the cached data.
            data_ret = self.cur_data

        return data_ret

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        """
        varname: The variable to return.
        date_grain: The date granularity to return, specified as a constant in
            data_request.
        request_date: A data_request.RequestDate instance.
        ri_method: The resample/interpolation method to use, if needed.
        subset_geom: An instance of SubsetGeom.  If the CRS does not match the
            dataset, an exception is raised.
        """
        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )

        data = self._loadData(varname, date_grain, request_date, subset_geom)

        if date_grain == dr.MONTHLY:
            data = data.isel(time=request_date.month - 1)

        # If the subset request is a polygon, the data will already be
        # subsetted by _loadData(), so we don't need to handle that here.

        if isinstance(subset_geom, SubsetMultiPoint):
            # Interpolate all (x,y) points in the subset geometry.  For more
            # information about how/why this works, see
            # https://xarray.pydata.org/en/stable/user-guide/interpolation.html#advanced-interpolation.
            res = data.interp(
                x=('z', subset_geom.geom.x), y=('z', subset_geom.geom.y),
                method=ri_method
            )
            data = res.values[0]

        return data

