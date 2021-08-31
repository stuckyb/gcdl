
from gsdataset import GSDataSet
import datetime


class PRISM(GSDataSet):
    def __init__(self):
        super().__init__()

        # Basic dataset information.
        self.dataset_name = 'PRISM'
        self.dataset_url = 'https://prism.oregonstate.edu/'

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

