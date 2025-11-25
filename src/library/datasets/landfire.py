
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint
import rasterio
from osgeo import gdal


class LANDFIRE(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'nlcd')

        # Basic dataset information.
        self.id = 'LANDFIRE'
        self.name = 'Landscape Fire and Resource Management Planning Tools'
        self.url = 'https://www.landfire.gov'
        self.description = ("LANDFIRE (LF), Landscape Fire and Resource Management Planning "
        "Tools, is a shared program between the wildland fire management programs of the U.S. "
        "Department of Agriculture Forest Service and U.S. Department of the Interior, providing "
        "landscape scale geo-spatial products to support cross-boundary planning, management, "
        "and operations. This multi-partner program produces consistent, comprehensive, "
        "geospatial data and databases that describe vegetation, wildland fuel, and fire "
        "regimes across the United States and insular areas.")

        # Provider information
        self.provider_name = ('')
        self.provider_url = ''

        # CRS information.
        # self.crs = CRS.from_epsg() # Depends!

        # The grid size.
        self.grid_size = 30
        self.grid_unit = 'meters'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'evt': 'existing vegetation type',
            'nvc': 'national vegetation classification',
            'evc': 'existing vegetation cover',
            'evh': 'existing vegetation height'
        }

        # File name patterns for each variable
        # Currently uses the latest version available for each variable
        # (Numbers XXX before variable name denotes version number X.X.X)
        self.fpatterns = {
            'evt': '220EVT',
            'nvc': '200NVC',
            'evc': '220EVC_22',
            'evh': '220EVH_22'
        }

        # Attributes for caching loaded and subsetted data.
        self.data_loaded = None
        self.cur_data = None

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

        # Since sparse years, check if filename exists. 
        # If it doesn't, skip this request_date.
        if fpath.exists() is False:
            return None

        # Read in colormap and RAT if not already available
        if self.colormap is None:
            self._getColorMap(fpath, varname)
        elif varname not in self.colormap.keys():
            self._getColorMap(fpath, varname)

        if self.RAT is None:
            self._getRAT(fpath, varname)
        elif varname not in self.RAT.keys():
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

            return data 
        
        elif isinstance(subset_geom, SubsetMultiPoint):
            # Interpolate all (x,y) points in the subset geometry.  For more
            # information about how/why this works, see
            # https://xarray.pydata.org/en/stable/user-guide/interpolation.html#advanced-interpolation.
            res = data.interp(
                x=('z', subset_geom.geom.x), y=('z', subset_geom.geom.y),
                method=ri_method
            )

            # Convert crop index to name
            data = [self.RAT[varname][int(class_id)] for class_id in res.values[0]]
            color = [self.colormap[varname][int(class_id)] for class_id in res.values[0]]

            return {'data': data, 'color': color}

