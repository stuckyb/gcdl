
import json


class DataSource:
    """
    Base class for all catalog data sources.
    """
    def __init__(self):
        # Basic dataset information.
        self.dataset_name = ''
        self.dataset_url = ''
        self.description = ''

        # Provider information, if different from the dataset information.
        self.provider_name = ''
        self.provider_url = '' 

        # The variables/layers/bands in the dataset.
        self.vars = []

        # Temporal coverage of the dataset. In concrete subclasses, start and
        # end dates should be provided with datetime.date objects.
        self.date_ranges = {
            # Range of annual data.
            'year': [None, None],
            # Range of monthly data.
            'month': [None, None],
            # Range of daily data.
            'day': [None, None]
        }

    def getMetadataJSON(self):
        """
        Returns a JSON representation of the dataset's metadata.
        """
        # Class attributes to copy directly.
        attribs = [
            'dataset_name', 'dataset_url', 'description', 'provider_name',
            'provider_url', 'vars', 'date_ranges'
        ]

        resp = {}
        for attrib in attribs:
            resp[attrib] = getattr(self, attrib)

        return json.dumps(resp)

