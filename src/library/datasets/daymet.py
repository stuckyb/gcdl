
from .gsdataset import GSDataSet
from pathlib import Path
import datetime


class DAYMET(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'daymetv4')

        # Basic dataset information.
        self.id = 'DaymetV4'
        self.name = 'Daymet Version 4'
        self.url = 'https://daymet.ornl.gov/'

        # CRS information.
        self.proj4_str = '+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 '
        '+x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs'

        # The grid size
        self.grid_size = 1000
        self.grid_unit = 'meters'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'prcp': 'precipitation', 'tmin:': 'minimum temperature',
            'tmax': 'maximum temperature', 'swe': 'snow water equivalent',
            'vp': 'vapor pressure'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            datetime.date(1980, 1, 1), datetime.date(2020, 1, 1)
        ]
        self.date_ranges['month'] = [
            datetime.date(1980, 1, 1), datetime.date(2020, 12, 1)
        ]
        self.date_ranges['day'] = [
            datetime.date(1980, 1, 1), datetime.date(2020, 12, 31)
        ]

        # File name patterns for each DaymetV4 variable.
        self.fpatterns = {
            'prcp': 'daymet_v4_prcp_{0}ttl_na_{1}.tif',
            'tmax': 'daymet_v4_tmax_{0}avg_na_{1}.tif',
        }

    def _getDataFile(self, varname, year, month=None, day=None):
        if day is not None:
            pass
        elif month is not None:
            return self.fpatterns[varname].format('mon',year)
        else:
            return self.fpatterns[varname].format('ann',year)

