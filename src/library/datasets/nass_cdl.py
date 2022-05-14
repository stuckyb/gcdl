
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class NASS_CDL(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'nass_cdl')

        # Basic dataset information.
        self.name = 'NASS_CDL'
        self.url = 'https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php'

        # CRS information.
        self.crs = CRS.from_epsg(5070)

        # The grid size.
        self.grid_size = 30
        self.grid_unit = 'meters'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'cdl': 'cropland data layer'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            datetime.date(2008, 1, 1), datetime.date(2021, 1, 1)
        ]

        # File name patterns for each variable. 
        self.fpatterns = {
            'cdl': '{0}_30m_cdls.tif'
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
            fname = self.fpatterns[varname].format(request_date.year)
        else:
            raise ValueError('Invalid date grain specification.')

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

