
import json


class GSDataSet:
    """
    Base class for all geospatial catalog data sets.
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
            'provider_url', 'vars'
        ]

        resp = {}
        for attrib in attribs:
            resp[attrib] = getattr(self, attrib)

        resp['date_ranges'] = {}
        if self.date_ranges['year'][0] is None:
            resp['date_ranges']['year'] = [None, None]
        else:
            resp['date_ranges']['year'] = [
                self.date_ranges['year'][0].year,
                self.date_ranges['year'][1].year
            ]

        if self.date_ranges['month'][0] is None:
            resp['date_ranges']['month'] = [None, None]
        else:
            resp['date_ranges']['month'] = [
                self.date_ranges['month'][0].strftime('%Y-%m'),
                self.date_ranges['month'][1].strftime('%Y-%m')
            ]

        if self.date_ranges['day'][0] is None:
            resp['date_ranges']['day'] = [None, None]
        else:
            resp['date_ranges']['day'] = [
                self.date_ranges['day'][0].strftime('%Y-%m-%d'),
                self.date_ranges['day'][1].strftime('%Y-%m-%d')
            ]

        return json.dumps(resp)

