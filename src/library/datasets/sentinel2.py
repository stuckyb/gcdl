
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import datetime
import rioxarray
from rioxarray import merge
import xarray as xr
from pystac_client import Client
import api_core.data_request as dr
from subset_geom import SubsetPolygon, SubsetMultiPoint


class Sentinel2(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of remote dataset storage.
        """
        super().__init__('https://earth-search.aws.element84.com/v0', 'sentinel-s2-l2a-cogs')

        # Basic dataset information.
        self.id = 'Sentinel2-10m'
        self.name = 'Sentinel-2 Mission Level 2A - 10 m bands (R, G, B, NIR)'
        self.url = 'https://registry.opendata.aws/sentinel-2-l2a-cogs/'
        
        self.description = ("The Sentinel-2 mission is a land monitoring constellation "
        "of two satellites that provide high resolution optical imagery and provide "
        "continuity for the current SPOT and Landsat missions. The mission provides a "
        "global coverage of the Earth's land surface every 5 days, making the data of "
        "great use in ongoing studies. This dataset contains all of the scenes in the "
        "original Sentinel-2 Public Dataset and will grow as that does. L2A data are "
        "available from April 2017 over wider Europe region and globally since December "
        "2018.")
        self.provider_name = 'AWS Open Data'
        self.provider_url = 'https://registry.opendata.aws'

        # CRS information.
        self.crs = CRS.from_epsg(32631)

        # The grid size
        self.grid_size = 10
        self.grid_unit = 'meters'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'B': 'blue (Band 2)',
            'G': 'green (Band 3)',
            'R': 'red (Band 4)',
            'NIR': 'near-infrared (Band 8)'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['day'] = [
            datetime.date(2018, 12, 1), datetime.date(2023, 4, 25)
        ]

        # Temporal resolution
        self.temporal_resolution['day'] = '2-3 days'

        # File name patterns for each variable.
        self.client = Client.open('https://earth-search.aws.element84.com/v0')
        self.collection = "sentinel-s2-l2a-cogs"
        self.bpatterns = {
            'B': 'B02',
            'G': 'B03',
            'R': 'B04',
            'NIR': 'B08'
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
        # Get a string of the request date of the requested data.
        if date_grain == dr.ANNUAL:
            raise NotImplementedError()
        elif date_grain == dr.MONTHLY:
            raise NotImplementedError()
        elif date_grain == dr.DAILY:
            req_date = '{0}-{1:02d}-{2:02d}'.format(request_date.year,request_date.month,request_date.day)
        else:
            raise ValueError('Invalid date grain specification.')
        
        bandname = self.bpatterns[varname]

        search = self.client.search(
            collections = [self.collection],
            bbox = subset_geom.geom.total_bounds,
            datetime = [req_date, req_date]
        )
        items = search.item_collection()
        hrefs = [i.assets[bandname].href for i in items]
        data = merge.merge_arrays([rioxarray.open_rasterio(href) for href in hrefs])


        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
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
      


