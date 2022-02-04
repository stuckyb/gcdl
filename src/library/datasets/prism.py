
from .gsdataset import GSDataSet
from pathlib import Path
from pyproj.crs import CRS
import datetime
import rioxarray
import data_request as dr


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
        self.crs = CRS.from_epsg(4269)

        # The grid size
        self.grid_size = 4000
        self.grid_unit = 'meters'

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

    def getData(self, varname, date_grain, request_date, clip_poly=None):
        """
        varname: The variable to return.
        date_grain: The date granularity to return, specified as a constant in
            data_request.
        request_date: A data_request.RequestDate instance.
        clip_poly: An instance of ClipPolygon.  If the CRS does not match the
            dataset, an exception is raised.
        """
        # Get the path to the required data file.
        if date_grain == dr.ANNUAL:
            fname = self.fpatterns[varname].format(request_date.year)
        elif date_grain == dr.MONTHLY:
            datestr = '{0}{1:02}'.format(request_date.year, request_date.month)
            fname = self.fpatterns[varname].format(datestr)
        elif date_grain == dr.DAILY:
            raise NotImplementedError()
        else:
            raise ValueError('Invalid date grain specification.')

        fpath = self.ds_path / fname

        data = rioxarray.open_rasterio(fpath, masked=True)

        if clip_poly is not None:
            if not(self.crs.equals(clip_poly.crs)):
                raise ValueError(
                    'Clip polygon CRS does not match dataset CRS.'
                )

            data = data.rio.clip([clip_poly.gj_dict])

        return data

