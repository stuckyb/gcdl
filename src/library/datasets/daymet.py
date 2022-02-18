
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class DAYMET(GSDataSet):
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
        self.crs = CRS.from_proj4('+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 '
        '+x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs')

        # The grid size
        self.grid_size = 1000
        self.grid_unit = 'meters'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'prcp': 'precipitation', 'tmin:': 'minimum temperature',
            'tmax': 'maximum temperature', 'swe': 'snow water equivalent',
            'vp': 'vapor pressure'
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

        # File name patterns for each DaymetV4 variable.
        self.fpatterns = {
            'prcp': 'daymet_v4_prcp_{0}ttl_na_{1}.tif',
            'tmax': 'daymet_v4_tmax_{0}avg_na_{1}.tif',
        }

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
        # Get the path to the required data file.
        if date_grain == dr.ANNUAL:
            fname = self.fpatterns[varname].format('ann',request_date.year)
            fpath = self.ds_path / fname
            data = rioxarray.open_rasterio(fpath, masked=True).squeeze(drop=True)
        elif date_grain == dr.MONTHLY:
            fname = self.fpatterns[varname].format('mon',request_date.year)
            fpath = self.ds_path / fname
            data = rioxarray.open_rasterio(fpath, masked=True).squeeze(drop=True).isel(time=request_date.month-1)
        elif date_grain == dr.DAILY:
            raise NotImplementedError()
        else:
            raise ValueError('Invalid date grain specification.')


        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )

        if isinstance(subset_geom, SubsetPolygon):
            data = data.rio.clip([subset_geom.json])
        elif isinstance(subset_geom, SubsetMultiPoint):
            # Interpolate all (x,y) points in the subset geometry.  For more
            # information about how/why this works, see
            # https://xarray.pydata.org/en/stable/user-guide/interpolation.html#advanced-interpolation.
            res = data.interp(
                x=('z', subset_geom.geom.x), y=('z', subset_geom.geom.y),
                method=ri_method
            )
            data = res.values[0]

        return data


