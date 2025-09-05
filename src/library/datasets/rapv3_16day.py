
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint
from library.datasets.tileset import TileSet


class RAPV3_16day(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'rapv3-16day')

        # Basic dataset information.
        self._id = 'RAPV3_16day'
        self.name = 'Rangeland Analysis Platform Version 3: 16-Day NPP'
        self.url = 'https://rangelands.app/'
        self.description = (
            "The Rangeland Analysis Platform's vegetation cover product "
            "provides annual percent cover estimates from 1986 to present of: "
            "annual forbs and grasses, perennial forbs and grasses, shrubs, "
            "trees, and bare ground. The estimates were produced by combining "
            "75,000 field plots collected by BLM, NPS, and NRCS with the "
            "historical Landsat satellite record. Cover estimates are "
            "predicted across the United States at 30m resolution, an area "
            "slightly larger than a baseball diamond."
        )

        # Provider information
        self.provider_name = ''
        self.provider_url = ''

        # CRS information.
        self.crs = CRS.from_epsg(4326)

        # The grid size.
        self.grid_size = 53899.0 / 200000000
        self.grid_unit = 'degrees'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'npp_afg': '16-day aboveground biomass: annual forb and grass (lbs/acre)',
            'npp_pfg': '16-day aboveground biomass: perennial forb and grass (lbs/acre)'
        }


        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            None, None
        ]
        self.date_ranges['month'] = [
            None, None
        ]
        self.date_ranges['day'] = [
            datetime.date(1986, 1, 1), datetime.date(2024, 12, 18)
        ]

        # Temporal resolution.
        self.temporal_resolution['day'] = '16 days'

        # File names distinguish year, day of year, and tile.
        # The files don't include layer names, but the band 
        # descriptions indicate:
        #   Band 1: afgNPP
        #   Band 2: pfgNPP
        fpattern = 'vegetation-npp-16day-v3-{0}'
        self.fpat_bid = {
            'npp_afg': {'fpattern' : fpattern, 'band_id' : 1},
            'npp_pfg': {'fpattern' : fpattern, 'band_id' : 2}
        }

        # Attributes for caching loaded and subsetted data.
        self.data_loaded = None
        self.cur_data = None
        self.current_clip = None
        self.cur_data_clipped = None

        # Initialize the TileSet for the RAP 16-day data.
        tile_paths = sorted(self.ds_path.glob('vegetation-npp-16day*.tif'))
        self.tileset = TileSet(tile_paths, self.crs)

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
            date = datetime.date(
                request_date.year, request_date.month, request_date.day
            )
            doy = date.timetuple().tm_yday
            datestr = '{0}-{1:03}'.format(
                request_date.year, doy
            )
            fname = self.fpat_bid[varname]['fpattern'].format(datestr)
        else:
            raise ValueError('Invalid date grain specification.')

        # Load the data from disk, if needed.
        data_needed = (fname)
        if data_needed != self.data_loaded:
            data = self.tileset.getRaster(subset_geom, request_fpattern=fname)

            if data is None:
                return None

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
        request_date: A data_request.RequestDate instance.
        ri_method: The resample/interpolation method to use, if needed.
        subset_geom: An instance of SubsetGeom.  If the CRS does not match the
            dataset, an exception is raised.
        """
        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )

        data = self._loadData(varname, date_grain, request_date, subset_geom)

        if data is None:
            return None

        data = data.sel(band=self.fpat_bid[varname]['band_id'])

        # Without reassignment, the 'long_name' attribute remains the original
        # length and causes an error when writing to file.
        data = data.assign_attrs(
            long_name=varname
        )

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
