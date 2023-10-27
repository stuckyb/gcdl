
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class RAPV3(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'rapv3')

        # Basic dataset information.
        self._id = 'RAPV3'
        self.name = 'Rangeland Analysis Platform Version 3'
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
            'cover_afg': 'fractional vegetation cover: annual forb and grass (%)', 
            'cover_bare': 'fractional vegetation cover: bare ground (%)',
            'cover_litter': 'fractional vegetation cover: litter (%)', 
            'cover_pfg': 'fractional vegetation cover: perennial forb and grass (%)',
            'cover_shrub': 'fractional vegetation cover: shrub (%)',
            'cover_tree': 'fractional vegetation cover: tree (%)',
            'biomass_afg': 'annual aboveground biomass: annual forb and grass (lbs/acre)',
            'biomass_pfg': 'annual aboveground biomass: perennial forb and grass (lbs/acre)'
        }


        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            datetime.date(1986, 1, 1), datetime.date(2022, 1, 1)
        ]
        self.date_ranges['month'] = [
            None, None
        ]
        self.date_ranges['day'] = [
            None, None
        ]

        # Temporal resolution.
        self.temporal_resolution['year'] = '1 year'

        # File names distinguish biomass vs cover, as well as year.
        # RAP files don't have layer names, but band IDs that start at 1
        # See dataset READMEs for layer name to band ID mapping:
        #   http://rangeland.ntsg.umt.edu/data/rap/rap-vegetation-cover/v3/README
        #   http://rangeland.ntsg.umt.edu/data/rap/rap-vegetation-biomass/v3/README
        fpattern = 'vegetation-{0}-v3-'
        fpattern_suffix = '{0}.tif'
        cover_fpattern = fpattern.format('cover') + fpattern_suffix
        biomass_fpattern = fpattern.format('biomass') + fpattern_suffix
        self.fpat_bid = {
            'cover_afg': {'fpattern' : cover_fpattern, 'band_id' : 1}, 
            'cover_bare': {'fpattern' : cover_fpattern, 'band_id' : 2},
            'cover_litter': {'fpattern' : cover_fpattern, 'band_id' : 3}, 
            'cover_pfg': {'fpattern' : cover_fpattern, 'band_id' : 4},
            'cover_shrub': {'fpattern' : cover_fpattern, 'band_id' : 5},
            'cover_tree': {'fpattern' : cover_fpattern, 'band_id' : 6},
            'biomass_afg': {'fpattern' : biomass_fpattern, 'band_id' : 1},
            'biomass_pfg': {'fpattern' : biomass_fpattern, 'band_id' : 2}
        }

    def _loadData(self, varname, date_grain, request_date, subset_geom):
        """
        Loads the data from disk, if needed.  Will re-use already loaded (and
        subsetted) data whenever possible.
        """

        # Get the file name of the requested data.
        if date_grain == dr.ANNUAL:
            fname = self.fpat_bid[varname]['fpattern'].format(request_date.year)
        elif date_grain == dr.MONTHLY:
            raise NotImplementedError()
        elif date_grain == dr.DAILY:
            raise NotImplementedError()
        else:
            raise ValueError('Invalid date grain specification.')

        fpath = self.ds_path / fname

        # Load the data from disk, if needed.
        data_needed = (fname)
        if data_needed != self.data_loaded:
            data = rioxarray.open_rasterio(fpath, masked=True)

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

        data = data.sel(band=self.fpat_bid[varname]['band_id'])

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
            data = res.values[0]

        return data
