
from .gsdataset import GSDataSet
from pyproj.crs import CRS
from pathlib import Path
import datetime
import rioxarray
from subset_geom import SubsetPolygon, SubsetMultiPoint
from library.datasets.tileset import TileSet


class GTOPO(GSDataSet):
    """
    Dataset for USGS EROS Global 30 Arc-Second Elevation (GTOPO30) data.
    ONE CRITICAL DETAIL TO NOTE: When gathering data files for this dataset,
    there will be an extra tile with the name "gt30antarcps".  This is, per the
    official README, an "additional tile that covers all of Antarctica with
    data in a polar stereographic projection."  (The projection in this case is
    EPSG:3031, "Antarctic Polar Stereographic".)  All other tiles (which
    include tiles for Antarctica) are in simple WGS84 coordinates.  Including
    the special Antarctica tile will cause cryptic request failures because of
    CRS confusion.  Do not include this tile in the on-disk data!
    """
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
        self.grid_size = 25.0 / 3000
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

        # Initialize the TileSet for the GTOPO data.
        tile_paths = sorted(self.ds_path.glob('gt30*.dem'))
        self.tileset = TileSet(tile_paths, self.crs)

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
        if subset_geom is None:
            raise ValueError(
                'A subset geometry is required for using GTOPO30 data.'
            )
        
        if not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )

        data = self.tileset.getRaster(subset_geom)

        if isinstance(subset_geom, SubsetPolygon):
            data = data.rio.clip([subset_geom.json], all_touched = True)
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

