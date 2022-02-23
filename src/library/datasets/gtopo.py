
from .gsdataset import GSDataSet
from pyproj.crs import CRS
from pathlib import Path
import datetime
import rioxarray
from subset_geom import SubsetPolygon, SubsetMultiPoint


class GTOPO(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'gtopo')

        # Basic dataset information.
        self.id = 'GTOPO30'
        self.name = 'Global 30 Arc-Second Elevation'
        self.url = 'https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-global-30-arc-second-elevation-gtopo30'

        # CRS information.
        self.crs = CRS.from_epsg(4326)

        # The grid size.
        self.grid_size = 0.008333333333333
        self.grid_unit = 'degrees'

        # The variables/layers/bands in the dataset.
        self.vars = {
            'elev': 'elevation'
        }

        # Temporal coverage of the dataset.
        self.date_ranges['year'] = [
            None, None
        ]
        self.date_ranges['month'] = [
            None, None
        ]
        self.date_ranges['day'] = [
            None, None
        ]

        # Name of the data file.  For now, this is only one tile of the
        # dataset.  This needs to be implemented as a tiled dataset.
        self.fname = 'gt30w100n40.dem'

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        """
        varname: The variable to return.
        date_grain: The date granularity to return, specified as a constant in
            data_request.
        request_date: A data_request.RequestDate instance.  Since this is a
            non-temporal dataset, request dates are ignored.
        ri_method: The resample/interpolation method to use, if needed.
        subset_geom: An instance of SubsetGeom.  If the CRS does not match the
            dataset, an exception is raised.
        """
        # Get the path to the data file.
        fpath = self.ds_path / self.fname

        data = rioxarray.open_rasterio(fpath, masked=True)

        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )

        if isinstance(subset_geom, SubsetPolygon):
            data = data.rio.clip([subset_geom.json])
        elif isinstance(subset_geom, SubsetMultiPoint):
            # Interpolate all (x,y) points in the subset geometry.  For more
            # information about how/why this works, see
            # https://xarray.pydata.org/en/stable/user-guide/interpolation.html#advanced-interpolation.
            res = data.interp(
                x=('z', subset_geom.geom.x), y=('z', subset_geom.geom.y),
                method=ri_method
            )
            data = res.values[0]

        return data

