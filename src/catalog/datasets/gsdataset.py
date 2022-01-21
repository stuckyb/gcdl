
from pathlib import Path
from pyproj.crs import CRS
from rasterio.enums import Resampling
import rioxarray


class GSDataSet:
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
        self.epsg_code = None
        self.proj4_str = None
        self.wkt_str = None

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

    def _getCRSMetadata(self, epsg_code=None, wkt_str=None, proj4_str=None):
        if epsg_code is not None:
            crs = CRS.from_epsg(epsg_code)
        elif wkt_str is not None:
            crs = CRS.from_wkt(wkt_str)
        elif proj4_str is not None:
            crs = CRS.from_proj4(proj4_str)
        else:
            crs = None

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

    def getDatasetMetadata(self):
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
        resp['crs'] = self._getCRSMetadata(
            self.epsg_code, self.wkt_str, self.proj4_str
        )

        return resp

    def getSubsetMetadata(self, date_start, date_end, varnames, bounds, crs, resample_method):
        md = {}

        md['dataset'] = self.getDatasetMetadata()

        req_md = {}
        req_md['requested_vars'] = varnames
        req_md['target_date_range'] = [date_start, date_end]
        req_md['target_crs'] = self._getCRSMetadata(epsg_code=crs)
        req_md['resample_method'] = resample_method

        md['subset'] = req_md

        return md

    def getSubset(
        self, output_dir, date_start, date_end, varnames, bounds, crs, resample_method
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
        crs: The CRS to use for the output data, specified as an EPSG code. If
            None, the native CRS is used.
        resample_method: The resampling method used in reprojection. If
            None, nearest neighbor method is used. 
        """
        output_dir = Path(output_dir)

        if crs is not None:
            try:
                CRS.from_epsg(crs)
            except Exception:
                raise ValueError(f'{crs} is not a valid EPSG CRS code.')

        if resample_method is not None and resample_method not in ['nearest', 'bilinear',
        'cubic','cubic-spline','lanczos','average','mode']:
            raise ValueError(f'{resample_method} is not a valid resampling method.')

        if date_start == None:
            # Non-temporal data.
            fout_paths = self._getNonTemporalSubset(
                output_dir, varnames, bounds, crs, resample_method
            )
        elif len(date_start) == 4:
            # Annual data.
            fout_paths = self._getAnnualSubset(
                output_dir, date_start, date_end, varnames, bounds, crs, resample_method
            )
        elif len(date_start) == 7:
            # Monthly data.
            fout_paths = self._getMonthlySubset(
                output_dir, date_start, date_end, varnames, bounds, crs, resample_method
            )

        dataset_md = self.getSubsetMetadata(
            date_start, date_end, varnames, bounds, crs, resample_method
        )

        return dataset_md, fout_paths

    def _getNonTemporalSubset(
        self, output_dir, varnames, bounds, crs, resample_method
    ):
        # Check for temporal data interpreted as non-temporal
        print(self.id, self.date_ranges['year'])
        if self.date_ranges['year'] != [None, None]:
            raise ValueError(f'{self.id} is a temporal dataset. Provide start and end dates')

        fout_paths = []

        # Get the data
        for varname in varnames:
            fname = self._getDataFile(varname)
            fpath = self.ds_path / fname
            fout_path = output_dir /'{0}_{1}.tif'.format(
                self.id, varname
            )
            fout_paths.append(fout_path)
            self._extractData(fout_path, fpath, bounds, crs, resample_method)

        return fout_paths

    def _getAnnualSubset(
        self, output_dir, date_start, date_end, varnames, bounds, crs, resample_method
    ):
        fout_paths = []

        #Check for non-temporal dataset included in temporal request
        if self.date_ranges['year'] == [None, None]:
            fout_paths = self._getNonTemporalSubset(
                output_dir, varnames, bounds, crs, resample_method
            )
        else:
            # Parse the start and end years.
            start = int(date_start)
            end = int(date_end) + 1
            if end < start:
                raise ValueError('The end date cannot precede the start date.')

            # Get the data for each year.
            for year in range(start, end):
                for varname in varnames:
                    fname = self._getDataFile(varname, year)
                    fpath = self.ds_path / fname
                    fout_path = output_dir /'{0}_{1}_{2}.tif'.format(
                        self.id, varname, year
                    )
                    fout_paths.append(fout_path)
                    self._extractData(fout_path, fpath, bounds, crs, resample_method)

        return fout_paths

    def _getMonthlySubset(
        self, output_dir, date_start, date_end, varnames, bounds, crs, resample_method
    ):
        fout_paths = []

        #Check for non-temporal dataset included in temporal request
        if self.date_ranges['year'] == [None,None]:
            fout_paths = self._getNonTemporalSubset(
                output_dir, varnames, bounds, crs, resample_method
            )
        else:
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
                    fname = self._getDataFile(varname, cur_y, cur_m)
                    fpath = self.ds_path / fname
                    fout_path = output_dir / '{0}_{1}_{2}-{3:02}.tif'.format(
                        self.id, varname, cur_y, cur_m
                    )
                    fout_paths.append(fout_path)
                    if str(cur_m) not in fname:  #not the safest test
                        layer_val = cur_m - 1
                        self._extractData(fout_path, fpath, bounds, crs, resample_method, t_layer=layer_val)
                    else:
                        self._extractData(fout_path, fpath, bounds, crs, resample_method)

                m_cnt += 1
                cur_y = start_y + m_cnt // 12
                cur_m = (m_cnt % 12) + 1

        return fout_paths

    def _extractData(self, output_path, fpath, bounds, crs, resample_method, t_layer=None):
        data = rioxarray.open_rasterio(fpath, masked=True)

        if t_layer is not None:
            data = rioxarray.open_rasterio(fpath, masked=True).isel(time=t_layer)

        if crs is not None and resample_method is None:
            data = data.rio.reproject('EPSG:' + crs)
        elif crs is not None and resample_method is not None:
            data = data.rio.reproject('EPSG:' + crs, 
                resampling=Resampling[resample_method])

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

