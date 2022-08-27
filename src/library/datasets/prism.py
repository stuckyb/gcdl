
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class PRISM(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'prism')

        # Basic dataset information.
        self.name = 'PRISM'
        self.url = 'https://prism.oregonstate.edu/'

        # CRS information.
        self.crs = CRS.from_epsg(4269)

        # The grid size.
        self.grid_size = 150.0 / 3600
        self.grid_unit = 'degrees'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'ppt': 'total precipitation (rain+melted snow)', 
            'tmean': 'mean temperature (mean of tmin and tmax)',
            'tmin': 'minimum temperature', 
            'tmax': 'maximum temperature',
            'tdmean': 'mean dew point temperature',
            'vpdmin': 'minimum vapor pressure deficit',
            'vpdmax': 'maximum vapor pressure deficit'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            datetime.date(1895, 1, 1), datetime.date(2020, 1, 1)
        ]
        self.date_ranges['month'] = [
            datetime.date(1895, 1, 1), datetime.date(2021, 1, 1)
        ]
        self.date_ranges['day'] = [
            datetime.date(1981, 1, 1), datetime.date(2021, 1, 31)
        ]

        # File name patterns for each PRISM variable.  Note that for
        # precipation data, the current version of "M2" for years < 1981 and
        # "M3" for years >= 1981.  See
        # https://prism.oregonstate.edu/documents/PRISM_datasets.pdf for
        # details.
        self.fpatterns = 'PRISM_{0}_stable_4km{1}_{2}_bil.bil'

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
            fname = self.fpatterns.format(varname, request_date.year, 'M3')
        elif date_grain == dr.MONTHLY:
            datestr = '{0}{1:02}'.format(request_date.year, request_date.month)
            fname = self.fpatterns.format(varname, datestr, 'M3')
        elif date_grain == dr.DAILY:
            datestr = '{0}{1:02}{2:02}'.format(
                request_date.year, request_date.month. request_date.day
            )
            fname = self.fpatterns.format(varname, datestr, 'D2')
        else:
            raise ValueError('Invalid date grain specification.')

        # For precipation data, the current version of "M2" for years < 1981
        # and "M3" for years >= 1981.  See
        # https://prism.oregonstate.edu/documents/PRISM_datasets.pdf for
        # details.
        if (request_date.year < 1981 and date_grain is not dr.DAILY and 
            varname == 'ppt'
        ):
            fname = fname.replace('M3', 'M2')

        fpath = self.ds_path / fname

        # Open data file
        data = rioxarray.open_rasterio(fpath, masked=True)

        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )

        if isinstance(subset_geom, SubsetPolygon):
            # Drop unnecessary 'band' dimension because rioxarray
            # can't handle >3 dimensions in some later operations
            data = data.squeeze('band')

            data = data.rio.clip([subset_geom.json], all_touched = True)
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

