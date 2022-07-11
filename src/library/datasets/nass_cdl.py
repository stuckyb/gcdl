
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint
import rasterio
from osgeo import gdal


class NASS_CDL(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'nass_cdl')

        # Basic dataset information.
        self.id = 'NASS_CDL'
        self.name = 'NASS Cropland Data Layer'
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

        # Categorical dataset, 
        # with one band with RAT and colormap read with methods
        self.categorical_vars = ['cdl']
        self.RAT = None
        self.colormap = None

    def _getColorMap(self, fname, varname):
        # Reads in a dictionary with integer keys and 
        # rgba tuples as values
        with rasterio.open(fname) as ds:
            self.colormap = {varname: ds.colormap(1)}

    def _getRAT(self, fname, varname):
        # Creates a dictionary with integer keys and 
        # class names as values
        ds = gdal.Open(str(fname))
        RAT = ds.GetRasterBand(1).GetDefaultRAT()
        nrows = RAT.GetRowCount()
        class_names = [RAT.GetValueAsString(i,0) for i in range(nrows)]
        class_id = [i for i in range(nrows)]
        self.RAT = {varname: {k:v for k,v in zip(class_id,class_names)}}
        ds = None

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

        # Read in colormap and RAT if not already available
        if self.colormap is None:
            self._getColorMap(fpath, varname)

        if self.RAT is None:
            self._getRAT(fpath, varname)

        # Open data file
        data = rioxarray.open_rasterio(fpath, masked=True)

        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )

        if isinstance(subset_geom, SubsetPolygon):
            # Drop unnecessary 'band' dimension because rioxarray
            # can't handle >3 dimensions in some later operations
            data = data.rio.clip([subset_geom.json], 
                all_touched = True,
                from_disk = True)
        elif isinstance(subset_geom, SubsetMultiPoint):
            # Interpolate all (x,y) points in the subset geometry.  For more
            # information about how/why this works, see
            # https://xarray.pydata.org/en/stable/user-guide/interpolation.html#advanced-interpolation.
            res = data.interp(
                x=('z', subset_geom.geom.x), y=('z', subset_geom.geom.y),
                method=ri_method
            )

            # Convert crop index to name
            data = [self.RAT[class_id] for class_id in res.values[0]] 

        return data

