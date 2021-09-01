
from .gsdataset import GSDataSet
import datetime


class DAYMET(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path)

        # Basic dataset information.
        self.name = 'DAYMET'
        self.url = 'https://daymet.ornl.gov/'

        # The variables/layers/bands in the dataset.
        self.vars = [
            'day length', 'shortwave radiation',
            'minimum and maximum temperature', 'precipitation',
            'vapor pressure', 'snow water equivalent'
        ]

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

