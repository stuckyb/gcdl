
from abc import ABC, abstractmethod
from pathlib import Path


def getCRSMetadata(crs):
    """
    A utility function to generate a dictionary of metadata to describe a
    PyProj CRS object.
    """
    if crs is not None:
        crs_md = {}
        crs_md['name'] = crs.name
        crs_md['epsg'] = crs.to_epsg()
        crs_md['proj4'] = crs.to_proj4()
        crs_md['wkt'] = crs.to_wkt('WKT2_2019')
        crs_md['datum'] = crs.datum.name
        crs_md['is_geographic'] = crs.is_geographic
        crs_md['is_projected'] = crs.is_projected
    else:
        crs_md = None

    return crs_md


class GSDataSet(ABC):
    """
    Base class for all geospatial catalog data sets.
    """
    def __init__(self, store_path, dataset_dir=''):
        """
        store_path (Path): The location of on-disk dataset storage.
        dataset_dir (str): The name of a sub-directory for the dataset.
        """
        self.ds_path = Path(store_path) / dataset_dir

        # Basic dataset information.
        self.name = ''
        self.url = ''
        self.description = ''

        # An optional, internal identifier string that should only be
        # externally accessed through the "id" property.
        self._id = None

        # Provider information, if different from the dataset information.
        self.provider_name = ''
        self.provider_url = ''

        # CRS information.
        self.crs = None

        # The grid size
        self.grid_size = None
        self.grid_unit = None

        # The variables/layers/bands in the dataset.
        self.vars = {}

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

    @property
    def id(self):
        if self._id is None:
            return self.name
        else:
            return self._id

    @id.setter
    def id(self, idstr):
        self._id = idstr

    def getMetadata(self):
        """
        Returns a data structure containing the dataset's metadata.
        """
        # Class attributes to copy directly.
        attribs = [
            'name', 'id', 'url', 'description', 'provider_name',
            'provider_url', 'grid_size', 'grid_unit', 'vars'
        ]

        resp = {}
        for attrib in attribs:
            resp[attrib] = getattr(self, attrib)

        # Generate the temporal metadata.
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

        # Generate CRS metadata.
        resp['crs'] = getCRSMetadata(self.crs)

        return resp

    @abstractmethod
    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        """
        varname: The variable to return.
        date_grain: The date granularity to return, specified as a constant in
            data_request.
        request_date: A data_request.RequestDate instance.  Request dates
            should be ignored by non-temporal datasets.
        ri_method: The resample/interpolation method to use, if needed.
        subset_geom: An instance of SubsetGeom.  If the CRS does not match the
            dataset, an exception is raised.
        """
        pass

