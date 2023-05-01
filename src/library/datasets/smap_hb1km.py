
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class SMAP_HB1km(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'smap-hb1km')

        # Basic dataset information.
        self.id = 'SMAP-HB1km'
        self.name = 'SMAP HydroBlocks - 1 km'
        self.url = 'https://doi.org/10.5281/zenodo.5206725'
        self.description = ('SMAP-HydroBlocks (SMAP-HB) is a hyper-resolution '
        "satellite-based surface soil moisture product that combines NASA's "
        "Soil Moisture Active-Passive (SMAP) L3 Enhance product, hyper-resolution "
        "land surface modeling, radiative transfer modeling, machine learning, "
        "and in-situ observations. The dataset was developed over the continental "
        "United States at 30-m 6-hourly resolution (2015-2019), and it reports "
        "the top 5-cm surface soil moisture in volumetric units (m3/m3).")

        # Provider information
        self.provider_name = 'Noemi Vergopolan'
        self.provider_url = 'https://waterai.earth'

        # CRS information.
        self.crs = CRS.from_wkt(
            'PROJCS["World_Plate_Carree_Degrees",'
            'GEOGCS["GCS_WGS_1984",' 
            'DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]], '
            'PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],'
            'PROJECTION["Plate_Carree"],PARAMETER["False_Easting",0],'
            'PARAMETER["False_Northing",0],PARAMETER["Central_Meridian",0],'
            'UNIT["Degree",111319.49079327357264771338267056]]'
        )

        # The grid size.
        # (0.008333333333333302, -0.0083333333333333) 
        self.grid_size = 3.0 / 360
        self.grid_unit = 'degrees'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'sm': 'surface soil moisture [m3/m3]'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            None, None
        ]
        self.date_ranges['month'] = [
            None, None
        ]
        self.date_ranges['day'] = [
            datetime.date(2015, 1, 1), datetime.date(2019, 12, 31)
        ]

        # Temporal resolution
        self.hours = [0, 6, 12, 18]
        self.temporal_resolution['day'] = '{0} hours (h = {1})'.format(
            self.hours[1] - self.hours[0],
            ', '.join([str(h) for h in self.hours])
        )

        # File name patterns for each variable. 
        # One file per month with YYYYMM format in filename
        self.fpatterns = 'SMAP-HB_1km_surface-soil-moisture_{0}.nc'

        # Attributes for caching loaded and subsetted data.
        self.data_loaded = None
        self.cur_data = None
        self.current_clip = None
        self.cur_data_clipped = None

    def _loadData(self, varname, date_grain, request_date, subset_geom):
        """
        Loads the data from disk, if needed.  Will re-use already loaded (and
        subsetted) data whenever possible.
        """

        # Get the file name of the requested data.
        if date_grain == dr.ANNUAL:
            raise NotImplementedError()
        elif date_grain == dr.MONTHLY:
            raise NotImplementedError()
        elif date_grain == dr.DAILY:
            date_month = '{0}{1:02}'.format(request_date.year, request_date.month)
            fname = self.fpatterns.format(date_month)
        else:
            raise ValueError('Invalid date grain specification.')

        fpath = self.ds_path / fname

        # Load the data from disk, if needed.
        data_needed = (fname, varname)
        if data_needed != self.data_loaded:
            data = rioxarray.open_rasterio(fpath, masked=True)
            data.rio.write_crs(self.crs, inplace=True)

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
        request_date: Because this is a sub-daily dataset - a dictionary of a 
            data_request.RequestDate instance and a list of requested hours. 
        ri_method: The resample/interpolation method to use, if needed.
        subset_geom: An instance of SubsetGeom.  If the CRS does not match the
            dataset, an exception is raised.
        """
        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )
        
        rdate = request_date['date']
        data = self._loadData(varname, date_grain, rdate, subset_geom)

        # Filter to the requested date and hour
        rhour = request_date['hour']
        if rhour not in self.hours:
            return None
        dt_hour = datetime.datetime(rdate.year, rdate.month, rdate.day, rhour)
        data = data.sel(t=dt_hour)
        data = data.rename({'t': 'time'})

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
            data = res.values

        return data

