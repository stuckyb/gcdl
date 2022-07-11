
from abc import ABC, abstractmethod
from pathlib import Path

# Date granularity constants.
NONE = 0
ANNUAL = 1
MONTHLY = 2
DAILY = 3

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

        # If the dataset has any raster attribute
        # tables and/or colormaps.  
        self.RAT = None
        self.colormap = None

    @property
    def id(self):
        if self._id is None:
            return self.name
        else:
            return self._id

    @id.setter
    def id(self, idstr):
        self._id = idstr

    @property
    def nontemporal(self):
        """
        True if the dataset is non-temporal.
        """
        no_dates = True

        for grain, drange in self.date_ranges.items():
            if drange[0] is not None or drange[1] is not None:
                no_dates = False

        return no_dates

    @property
    def supported_grains(self):
        """
        Lists supported date grains
        """
        grains = []

        # Translate dataset grain to request grain format
        ds_to_request = {
            'year': ANNUAL,
            'month': MONTHLY,
            'day': DAILY
        }

        for grain, drange in self.date_ranges.items():
            if drange[0] is not None or drange[1] is not None:
                grains.append(ds_to_request[grain])

        return grains

    def getGridSize(self, unit=None):
        """
        Returns dataset's grid size in specified unit, or in dataset's
        grid unit if not specified.
        """
        gs_unit = unit
        if gs_unit is None:
            gs_unit = self.grid_unit

        if gs_unit in ['meters','metre']:
            if self.grid_unit in ['meters','metre']:
                return self.grid_size
            else:
                return self.grid_size*111000
        elif gs_unit in ['degrees','degree']:
            if self.grid_unit == 'degrees':
                return self.grid_size
            else:
                return self.grid_size/111000
        else:
            raise ValueError('Unsupported dataset grid unit.')


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
        Returns an xarray.DataArray object containing the requested data.

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

