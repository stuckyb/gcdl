
from .gsdataset import GSDataSet
from pathlib import Path
import datetime
import rioxarray


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
                fout_path = output_dir / '{0}_{1}_{2}.tif'.format(
                    self.id, varname, year
                )
                fout_paths.append(fout_path)
                self._extractData(fout_path, fpath, bounds, crs)

        return fout_paths

    def _getMonthlySubset(
        self, output_dir, date_start, date_end, varnames, bounds, crs
    ):
        fout_paths = []

        # Parse the start and end years and months.
        start_y, start_m = [int(val) for val in date_start.split('-')]
        end_y, end_m = [int(val) for val in date_end.split('-')]
        if end_y * 12 + end_m < start_y * 12 + start_m:
            raise ValueError('The end date cannot precede the start date.')

        # Get the data for each month.
        cur_y = start_y
        cur_m = start_m
        m_cnt = start_m - 1
        while cur_y * 12 + cur_m <= end_y * 12 + end_m:
            #print(cur_y, cur_m, datestr)
            for varname in varnames:
                datestr = '{0}{1:02}'.format(cur_y, cur_m)
                fname = self.fpatterns[varname].format(datestr)
                fpath = self.ds_path / fname
                fout_path = output_dir / 'PRISM_{0}_{1}-{2:02}.tif'.format(
                    varname, cur_y, cur_m
                )
                fout_paths.append(fout_path)
                self._extractData(fout_path, fpath, bounds, crs)

            m_cnt += 1
            cur_y = start_y + m_cnt // 12
            cur_m = (m_cnt % 12) + 1

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
            print(clip_geom)
            
            clipped = data.rio.clip(clip_geom)
            clipped.rio.to_raster(output_path)

