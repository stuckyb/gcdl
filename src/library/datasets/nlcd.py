
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint
import rasterio
from osgeo import gdal


class NLCD(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'nlcd')

        # Basic dataset information.
        self.id = 'NLCD'
        self.name = 'National Land Cover Database'
        self.url = 'https://www.mrlc.gov/data/type/land-cover'
        self.description = ("The National Land Cover Database (NLCD) provides nationwide "
        "data on land cover and land cover change at a 30m resolution with a 16-class "
        "legend based on a modified Anderson Level II classification system. The database "
        "is designed to provide cyclical updates of United States land cover and associated "
        "changes. Systematically aligned over time, the database provides the ability to "
        "understand both current and historical land cover and land cover change, and "
        "enables monitoring and trend assessments. The latest evolution of NLCD products "
        "are designed for widespread application in biology, climate, education, land "
        "management, hydrology, environmental planning, risk and disease analysis, "
        "telecommunications and visualization.")

        # Provider information
        self.provider_name = ('Multi-Resolution Land Characteristics (MRLC) Consortium')
        self.provider_url = 'https://www.mrlc.gov/'

        # CRS information.
        self.crs = CRS.from_epsg(5070)

        # The grid size.
        self.grid_size = 30
        self.grid_unit = 'meters'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'land_cover': 'land cover classification'#,
            #'change_index': 'land cover change index'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            datetime.date(2001, 1, 1), datetime.date(2019, 1, 1)
        ]

        # Temporal resolution
        self.temporal_resolution['year'] = (
            'Non regular: 2001, 2004, 2006, 2008, '
            '2011, 2013, 2016, and 2019')

        # File name patterns for each variable. 
        self.fpatterns = {
            'land_cover': 'nlcd_{0}_land_cover_l48_20210604.img'#,
            #'change_index': 'nlcd_2001_2019_land_cover_l48_20210604.img'
        }

        # Categorical dataset, 
        # with one band with RAT and colormap read with methods
        self.categorical_vars = ['land_cover'] #,'change_index']
        self.RAT = None
        self.colormap = None

        # Additional information about the dataset's configuration
        # in GeoCDL
        self.notes = ('The irregular temporal resolution applies to the '
        'land_cover variable, while the change_index variable represents '
        'changes between the first and last year available for land_cover.'
        'Requests for change_index will only be returned when the request'
        'is for the latest year.')

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

