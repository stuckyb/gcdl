
from .gsdataset import GSDataSet
from pathlib import Path
import datetime


class GTOPO(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'gtopo')

        # Basic dataset information.
        self.id = 'GTOPO30'
        self.name = 'Global 30 Arc-Second Elevation'
        self.url = 'https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-global-30-arc-second-elevation-gtopo30'

        # CRS information.
        self.epsg_code = 4326

        # The grid size
        self.grid_size = 0.008333333333333
        self.grid_unit = 'degrees'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'elev': 'elevation'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            None, None
        ]
        self.date_ranges['month'] = [
            None, None
        ]
        self.date_ranges['day'] = [
            None, None
        ]

        # File name patterns for each GTOPO variable.
        self.fpatterns = {
            'elev': 'GTOPO_elevation0.tif'  #temporary
        }

    def _getDataFile(self, varname, year=None, month=None, day=None):
        print(varname)
        return self.fpatterns[varname]


