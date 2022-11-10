
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import time


class Timeout(GSDataSet):
    """
    Unpublished dataset for testing behavior of long-running queries without
    imposing a heavy computational/memory burden.  Calls to getData() will run
    for self.default_query_time seconds before returning.  To dynamically
    specify a query time, provide a value for varname that can be parsed as a
    floating-point number.  Custom query times cannot exceed
    self.max_query_time.
    """
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path)

        # Basic dataset information.
        self.id = 'timeout'
        self.name = 'timeout'

        # Do not publish this dataset in the catalog.
        self.publish = False

        # The default and maximum "query" times, in seconds.
        self.default_query_time = 120
        self.max_query_time = 600

        # CRS information: WGS84 lat/long coordinates.
        self.crs = CRS.from_epsg(4326)

        # The grid size.
        self.grid_size = 25.0 / 3000
        self.grid_unit = 'degrees'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'null': 'empty dataset'
        }

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        """
        varname: The variable to return.
        date_grain: The date granularity to return, specified as a constant in
            data_request.
        request_date: A data_request.RequestDate instance.  Since this is a
            non-temporal dataset, request dates are ignored.
        ri_method: The resample/interpolation method to use, if needed.
        subset_geom: An instance of SubsetGeom.  If the CRS does not match the
            dataset, an exception is raised.
        """
        try:
            qtime = float(varname)
            if qtime > self.max_query_time or not(qtime > 0):
                qtime = self.default_query_time
        except:
            qtime = self.default_query_time

        time.sleep(qtime)

        return None

