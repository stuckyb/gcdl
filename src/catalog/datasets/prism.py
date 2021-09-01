
from .gsdataset import GSDataSet
import datetime


class PRISM(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path)

        # Basic dataset information.
        self.name = 'PRISM'
        self.url = 'https://prism.oregonstate.edu/'

        # The grid size, in meters.
        self.grid_size = 4000

        # The variables/layers/bands in the dataset.
        self.vars = [
            'precipitation', 'mean temperature', 'minimum temperature',
            'maximum temperature'
        ]

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            datetime.date(1981, 1, 1), datetime.date(2020, 1, 1)
        ]
        self.date_ranges['month'] = [
            datetime.date(1981, 1, 1), datetime.date(2021, 1, 1)
        ]
        self.date_ranges['day'] = [
            datetime.date(1981, 1, 1), datetime.date(2021, 1, 31)
        ]

