
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class VIP(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'vip')

        # Basic dataset information.
        self.id = 'VIP'
        self.name = 'Vegetation Index and Phenology (VIP) Vegetation Indices Daily Global 0.05Deg CMG V004'
        self.url = 'https://doi.org/10.5067/MEaSUREs/VIP/VIP01.004'

        # CRS information.
        self.crs = CRS.from_wkt('GEOGCS["Unknown datum based upon the Clarke 1866 ellipsoid",DATUM["Not specified (based on Clarke 1866 spheroid)",SPHEROID["Clarke 1866",6378206.4,294.978698213898,AUTHORITY["EPSG","7008"]]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST]]')
        # The grid size
        self.grid_size = 0.05
        self.grid_unit = 'degrees'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'NDVI': 'Normalized Difference Vegetation Index',
            'View Zenith Angle': '',
            'Relative Azimuth Angle': '',
            'EVI2': '',
            'VI Quality': '',
            'Pixel Reliability': '',
            'RED reflectance': '',
            'NIR reflectance': '',
            'BLUE reflectance': '',
            'MIR reflectance': '',
            'Solar Zenith Angle': ''
        }

        # Temporal coverage of the dataset.
        #self.date_ranges['year'] = [
        #    datetime.date(1980, 1, 1), datetime.date(2020, 1, 1)
        #]
        #self.date_ranges['month'] = [
        #    datetime.date(2000, 1, 1), datetime.date(2015, 12, 1)
        #]
        self.date_ranges['day'] = [
            datetime.date(1981, 1, 1), datetime.date(2014, 12, 31)
        ]

        # File name patterns for each variable.
        # Partial filename
        self.fpatterns = 'VIP01.A{0}{1}.004.*' 
        

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
            raise NotImplementedError()
        elif date_grain == dr.MONTHLY:
            raise NotImplementedError()
        elif date_grain == dr.DAILY:
            doy = datetime.date(
                request_date.year, request_date.month, request_date.day
            ).strftime('%j')
            fname = self.fpatterns.format(request_date.year,doy)
        else:
            raise ValueError('Invalid date grain specification.')

        fpath = list(self.ds_path.glob(fname))
        if len(fpath) > 1:
            raise ValueError('Non-unique filename')
        else:
            fpath = fpath[0]
        
        # Open data file
        data = rioxarray.open_rasterio(
            fpath, 
            masked=True
        )['CMG 0.05 Deg Daily ' + varname].squeeze('band')

        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )

        if isinstance(subset_geom, SubsetPolygon):
            data = data.rio.clip([subset_geom.json], all_touched = True)
        elif isinstance(subset_geom, SubsetMultiPoint):
                # Interpolate all (x,y) points in the subset geometry.  For more
                # information about how/why this works, see
                # https://xarray.pydata.org/en/stable/user-guide/interpolation.html#advanced-interpolation.
                res = data.interp(
                    x=('z', subset_geom.geom.x), y=('z', subset_geom.geom.y),
                    method=ri_method
                )
                data = res.values

        return data



