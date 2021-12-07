
from .gsdataset import GSDataSet
from pathlib import Path
import datetime


class PRISM(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'prism')

        # Basic dataset information.
        self.name = 'PRISM'
        self.url = 'https://prism.oregonstate.edu/'

        # CRS information.
        self.epsg_code = 4269

        # The grid size, in meters.
        self.grid_size = 4000

        # The variables/layers/bands in the dataset.
        self.vars = {
            'ppt': 'precipitation', 'tav': 'mean temperature',
            'tmin:': 'minimum temperature', 'tmax': 'maximum temperature'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            datetime.date(1895, 1, 1), datetime.date(2020, 1, 1)
        ]
        self.date_ranges['month'] = [
            datetime.date(1895, 1, 1), datetime.date(2021, 1, 1)
        ]
        self.date_ranges['day'] = [
            datetime.date(1981, 1, 1), datetime.date(2021, 1, 31)
        ]

        # File name patterns for each PRISM variable.
        self.fpatterns = {
            'ppt': 'PRISM_ppt_stable_4kmM2_{0}_bil.bil',
            'tmax': 'PRISM_tmax_stable_4kmM3_{0}_bil.bil',
        }

    def _getDataFile(self, varname, year, month=None, day=None):
        print(varname, year)
        if day is not None:
            pass
        elif month is not None:
            datestr = '{0}{1:02}'.format(year, month)
            return self.fpatterns[varname].format(datestr)
        else:
            return self.fpatterns[varname].format(year)

