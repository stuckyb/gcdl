
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import xarray as xr
from pydap.client import open_url
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class MODIS_NDVI(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of remote dataset storage.
        """
        super().__init__('https://thredds.daac.ornl.gov/thredds/dodsC/ornldaac', '1299')

        # Basic dataset information.
        self.id = 'MODIS_NDVI'
        self.name = 'MODIS NDVI Data, Smoothed and Gap-filled, for the Conterminous US: 2000-2015'
        self.url = 'https://doi.org/10.3334/ORNLDAAC/1299'

        # CRS information.
        self.crs = CRS.from_proj4('+proj=laea +lat_0=45 +lon_0=-100 +x_0=0 +y_0=0 +ellps=sphere +units=m +no_defs +type=crs')

        # The grid size
        self.grid_size = 250
        self.grid_unit = 'meters'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'NDVI': 'Normalized Difference Vegetation Index'
        }

        # Temporal coverage of the dataset.
        #self.date_ranges['year'] = [
        #    datetime.date(1980, 1, 1), datetime.date(2020, 1, 1)
        #]
        #self.date_ranges['month'] = [
        #    datetime.date(2000, 1, 1), datetime.date(2015, 12, 1)
        #]
        self.date_ranges['day'] = [
            datetime.date(2000, 1, 1), datetime.date(2015, 12, 31)
        ]

        # File name patterns for each variable.
        self.fpatterns = {
            'NDVI': 'MCD13.A{0}.unaccum.nc4'
        }

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
            fname = self.fpatterns[varname].format(request_date.year)
        else:
            raise ValueError('Invalid date grain specification.')

        # Open the data store, if needed.
        data_needed = fname
        if data_needed != self.data_loaded:
            fpath = 'https://thredds.daac.ornl.gov/thredds/dodsC/ornldaac/1299/' + fname
            data_store = open_url(fpath)
            data = xr.open_dataset(xr.backends.PydapDataStore(data_store), decode_coords="all")
            data = data.rio.write_crs("+proj=laea +lat_0=45 +lon_0=-100 +x_0=0 +y_0=0 +ellps=sphere +units=m +no_defs +type=crs") ## DATUM ISSUE IN WKT
            data = data.drop("lat").drop("lon") ## AUXILLARY COORDS?

            # Update the cache.
            self.data_loaded = data_needed
            self.cur_data = data
            self.cur_dates = [str(d) for d in data.coords["time"].values.astype('datetime64[D]')]

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

        # Check if date is in data's sparse dates
        req_date = '{0}-{1:02d}-{2:02d}'.format(request_date.year,request_date.month,request_date.day)
        if req_date in self.cur_dates:

            # Limit download to bbox around user geom and requested date
            sg_bounds = subset_geom.geom.total_bounds
            data = data[varname].sel(
                x = slice(sg_bounds[0],sg_bounds[2]), 
                y = slice(sg_bounds[1],sg_bounds[3]),
                time = req_date
            )

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


