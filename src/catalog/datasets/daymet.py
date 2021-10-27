
from .gsdataset import GSDataSet
from pathlib import Path
import datetime
import rioxarray


class DAYMET(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path, 'daymetv4')

        # Basic dataset information.
        self.id = 'DaymetV4'
        self.name = 'Daymet Version 4'
        self.url = 'https://daymet.ornl.gov/'

        # CRS information.
        self.proj4_str = '+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 '
        '+x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs'

        # The grid size, in meters.
        self.grid_size = 1000

        # The variables/layers/bands in the dataset.
        self.vars = {
            'prcp': 'precipitation', 'tmin:': 'minimum temperature',
            'tmax': 'maximum temperature', 'swe': 'snow water equivalent',
            'vp': 'vapor pressure'
        }

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

        # File name patterns for each PRISM variable.
        self.fpatterns = {
            'prcp': 'daymet_v4_prcp_annttl_na_{0}.tif',
            'tmax': 'daymet_v4_tmax_annavg_na_{0}.tif',
        }

    def getSubset(
        self, output_dir, date_start, date_end, varnames, bounds, crs
    ):
        """
        Extracts a subset of the data. Dates must be specified as strings,
        where 'YYYY' means extract annual data, 'YYYY-MM' is for monthly data,
        and 'YYYY-MM-DD' is for daily data.  Returns a list of output file
        paths.

        output_dir: Directory for output files.
        date_start: Starting date (inclusive).
        date_end: Ending date (inclusive).
        varnames: A list of variable names to include.
        bounds: A sequence defining the opposite corners of a bounding
            rectangle, specifed as: [
              [upper_left_x, upper_left_y],
              [lower_right_x, lower_right_y]
            ]. If None, the entire layer is returned.
        crs: The CRS to use for the output data. If None, the native CRS is
            used.
        """
        output_dir = Path(output_dir)

        if crs is not None and len(crs) == 4:
            crs = 'EPSG:' + crs

        if len(date_start) == 4:
            # Annual data.
            fout_paths = self._getAnnualSubset(
                output_dir, date_start, date_end, varnames, bounds, crs
            )
        elif len(date_start) == 7:
            # Monthly data.
            fout_paths = self._getMonthlySubset(
                output_dir, date_start, date_end, varnames, bounds, crs
            )

        return fout_paths

    def _getAnnualSubset(
        self, output_dir, date_start, date_end, varnames, bounds, crs
    ):
        fout_paths = []

        # Parse the start and end years.
        start = int(date_start)
        end = int(date_end) + 1
        if end < start:
            raise ValueError('The end date cannot precede the start date.')

        # Get the data for each year.
        for year in range(start, end):
            for varname in varnames:
                fname = self.fpatterns[varname].format(year)
                fpath = self.ds_path / fname
                fout_path = output_dir /'{0}_{1}_{2}.tif'.format(
                    self.id, varname, year
                )
                fout_paths.append(fout_path)
                self._extractData(fout_path, fpath, bounds, crs)

        return fout_paths

    def _extractData(self, output_path, fpath, bounds, crs):
        data = rioxarray.open_rasterio(fpath, masked=True)
        if crs is not None:
            data = data.rio.reproject(crs)

        if bounds is None:
            data.rio.to_raster(output_path)
        else:
            clip_geom = [{
                'type': 'Polygon',
                'coordinates': [[
                    # Top left.
                    [bounds[0][0], bounds[0][1]],
                    # Top right.
                    [bounds[1][0], bounds[0][1]],
                    # Bottom right.
                    [bounds[1][0], bounds[1][1]],
                    # Bottom left.
                    [bounds[0][0], bounds[1][1]],
                    # Top left.
                    [bounds[0][0], bounds[0][1]]
                ]]
            }]
            
            clipped = data.rio.clip(clip_geom)
            clipped.rio.to_raster(output_path)

