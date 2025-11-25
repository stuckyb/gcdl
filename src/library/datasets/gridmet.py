
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import affine
import xarray as xr
from pydap.client import open_url
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class gridMET(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of remote dataset storage.
        """
        super().__init__('http://thredds.northwestknowledge.net:8080/thredds/dodsC/', 'MET')

        # Basic dataset information.
        self.id = 'gridMET'
        self.name = 'gridMET (METDATA)'
        self.url = 'https://www.climatologylab.org/gridmet.html'
        
        self.description = ('gridMET is a dataset of daily high-spatial '
        'resolution (~4-km, 1/24th degree) surface meteorological data '
        'covering the contiguous US from 1979-yesterday. These data can '
        'provide important inputs for ecological, agricultural, and '
        'hydrological models. These data are updated daily.  gridMET '
        'is the preferred naming convention for these data; however, '
        'the data are also known as cited as METDATA.')
        self.provider_name = 'Climatology lab, UC Merced'
        self.provider_url = 'https://www.climatologylab.org'

        # CRS information.
        self.crs = CRS.from_epsg(4326)
        # Need to fix GeoTransform (second zero is missing in data files)
        self.transform = affine.Affine(-124.7666666333333, 0.041666666666666, 0,  49.400000000000000, 0, -0.041666666666666)

        # The grid size
        self.grid_size = 0.041666666666666
        self.grid_unit = 'degrees'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'pr': 'Precipitation',
            'tmax': 'Maximum air temperature'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['day'] = [
            datetime.date(1979, 1, 1), datetime.date(2023, 4, 29)
        ]

        # Temporal resolution
        self.temporal_resolution['day'] = '1 day'

        # File name patterns for each variable.
        # <Variable abbreviation>_<year>.nc 
        self.fpatterns = '{0}_{1}.nc'

        # Attributes for caching loaded and subsetted data.
        self.data_loaded = None
        self.cur_data = None
        self.cur_dates = None

    def _loadData(self, varname, date_grain, request_date):
        """
        Opens remote data store, if needed.  Will re-use already opened 
        data store whenever possible.
        """
        # Get the file name of the requested data.
        if date_grain == dr.ANNUAL:
            raise NotImplementedError()
        elif date_grain == dr.MONTHLY:
            raise NotImplementedError()
        elif date_grain == dr.DAILY:
            fname = self.fpatterns.format(varname,request_date.year)
        else:
            raise ValueError('Invalid date grain specification.')

        # Open the data store, if needed.
        data_needed = fname
        if data_needed != self.data_loaded:
            fpath = 'http://thredds.northwestknowledge.net:8080/thredds/dodsC/MET/{0}/{1}'.format(varname, fname) 
            data_store = open_url(fpath)
            data = xr.open_dataset(xr.backends.PydapDataStore(data_store), decode_coords="all")

            # Update the cache.
            self.data_loaded = data_needed
            self.cur_data = data
            self.cur_dates = [str(d) for d in data.coords["day"].values.astype('datetime64[D]')]

        # Return the cached data. 
        return self.cur_data

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

        data = self._loadData(varname, date_grain, request_date)

        # gridMET uses one varname for its file hierarchy
        # then has data variables names that are not unique
        # so they are determined here
        # Check just one data variable
        long_varname = list(data.data_vars)
        if len(long_varname) > 1:
            raise ValueError(
                'More than one data variable in gridMET remote file.'
            )
        else:
            long_varname = long_varname[0]

        # Check if date is in data's sparse dates
        req_date = '{0}-{1:02d}-{2:02d}'.format(request_date.year,request_date.month,request_date.day)
        if req_date in self.cur_dates:

            # Limit download to bbox around user geom and requested date
            sg_bounds = subset_geom.geom.total_bounds
            data = data[long_varname].sel(
                lon = slice(sg_bounds[0],sg_bounds[2]), 
                lat = slice(sg_bounds[3],sg_bounds[1]),
                day = req_date
            )
            data = data.rename({
                'day': 'time',
                'lon': 'x',
                'lat': 'y'
            })
            data = data.rio.write_crs(self.crs)

            if isinstance(subset_geom, SubsetMultiPoint):
                # Interpolate all (x,y) points in the subset geometry.  For more
                # information about how/why this works, see
                # https://xarray.pydata.org/en/stable/user-guide/interpolation.html#advanced-interpolation.
                res = data.interp(
                    x=('z', subset_geom.geom.x), y=('z', subset_geom.geom.y),
                    method=ri_method
                )
                data = res.values

            return data
        else:
            return None


