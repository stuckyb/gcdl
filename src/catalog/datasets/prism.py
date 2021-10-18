
from .gsdataset import GSDataSet
from pathlib import Path
import datetime
import rioxarray


class PRISM(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of on-disk dataset storage.
        """
        super().__init__(store_path)

        # Basic dataset information.
        self.name = 'PRISM'
        self.url = 'https://prism.oregonstate.edu/'

        # CRS information.
        self.epsg_code = 4269

        # The grid size, in meters.
        self.grid_size = 4000

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

    def getSubset(self, output_dir, date_start, date_end, varnames, bounds):
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
              [upper_left_lat, upper_left_long],
              [lower_right_lat, lower_right_long]
            ]. If None, the entire layer is returned.
        """
        fout_paths = []
        output_dir = Path(output_dir)

        if len(date_start) == 4:
            start = int(date_start)
            end = int(date_end) + 1

            for year in range(start, end):
                for varname in varnames:
                    fname = self.fpatterns[varname].format(year)
                    fpath = self.store_path / fname
                    fout_path = output_dir / 'PRISM_{0}_{1}.tif'.format(
                        varname, year
                    )
                    fout_paths.append(fout_path)
                    self._extractData(fout_path, fpath, bounds)

        return fout_paths

    def _extractData(self, output_path, fpath, bounds):
        data = rioxarray.open_rasterio(fpath, masked=True)

        if bounds is None:
            data.rio.to_raster(output_path)
        else:
            clip_geom = [{
                'type': 'Polygon',
                'coordinates': [[
                    # Top left.
                    [bounds[0][1], bounds[0][0]],
                    # Top right.
                    [bounds[1][1], bounds[0][0]],
                    # Bottom right.
                    [bounds[1][1], bounds[1][0]],
                    # Bottom left.
                    [bounds[0][1], bounds[1][0]],
                    # Top left.
                    [bounds[0][1], bounds[0][0]]
                ]]
            }]
            
            clipped = data.rio.clip(clip_geom)
            clipped.rio.to_raster(output_path)

