
from rasterio.enums import Resampling
import api_core.data_request as dr
import geopandas as gpd
import rioxarray
import xarray as xr
import pandas as pd

class DataRequestHandler:
    """
    Manages data request fulfillment, including dataset interactions, and
    data harmonization/post-processing.
    """
    def __init__(self):
        pass

    def _requestDateAsString(self, grain, rdate):
        if grain == dr.NONE or rdate is None:
            dstr = ''
        elif grain == dr.ANNUAL:
            dstr = '{0}'.format(
                rdate.year
            )
        elif grain == dr.MONTHLY:
            dstr = '{0}-{1:02}'.format(
                rdate.year, rdate.month
            )
        elif grain == dr.DAILY:
            dstr = '{0}-{1:02}-{2:02}'.format(
                rdate.year, rdate.month, rdate.day
            )
        else:
            raise ValueError('Invalid date granularity specification.')

        return dstr

    def _getPointLayer(
        self, dataset, varname, grain, rdate, subset_geom, request
    ):

        # Retrieve the point data.
        data = dataset.getData(
            varname, grain, rdate, request.ri_method, subset_geom
        )

        my_date = self._requestDateAsString(grain, rdate)

        if data is not None:
            # Not a great solution to be creating a new base dataframe on every
            # call, but multi-format output handling will eventually take care of
            # this.
            out_df = gpd.GeoDataFrame({
                'time': my_date, 
                'dataset': dataset.id,
                'variable': varname,
                'value': data
                }, 
                geometry = request.subset_geom.geom,
            )

            return out_df 
        else:
            return None

    def _getRasterLayer(
        self, dataset, varname, grain, rdate, subset_geom, request,
        target_data = None
    ):
        # Retrieve the (subsetted) data layer.
        data = dataset.getData(
            varname, grain, rdate, request.ri_method, subset_geom
        )

        if data is not None:
            # Reproject to the target resolution, target projection, or both, if
            # needed.
            if (
                not(request.target_crs.equals(dataset.crs)) or
                request.target_resolution is not None
            ):
                # Check if we need to match a reprojection
                if target_data is None:
                    data = data.rio.reproject(
                        dst_crs=request.target_crs,
                        resampling=Resampling[request.ri_method],
                        resolution=request.target_resolution
                    )
                else:
                    data = data.rio.reproject_match(
                        match_data_array=target_data,
                        resampling=Resampling[request.ri_method]
                    )

                # Clip to the non-modified requested geometry
                data = data.rio.clip([request.subset_geom.json], all_touched = True)

                # Assign time coordinate to request date. 
                # Overwrite native time format if present.
                date_series = pd.Series(self._requestDateAsString(grain, rdate))
                time_dim = xr.DataArray(date_series, [('time',date_series)])
                if 'time' in list(data.coords):
                    data = data.drop_vars('time')
                data = data.expand_dims(time=time_dim)

            return data
        else:
            return None

    def _buildDatasetSubsetGeoms(self, request):
        """
        Build a set of subset geometries, reprojected as needed, that match
        the source dataset CRSs. A buffer width of the coarsest grid size 
        is added to each to handle boundary discrepancies. We precompute 
        these geometries to avoid redundant reprojections when processing 
        the data retrievals.
        """

        # If raster-type request, buffer subet geometry
        if request.request_type == dr.REQ_RASTER:
            geom_unit = request.subset_geom.geom.crs.axis_info[0].unit_name
            grid_sizes = [
                    request.dsc[dsid].getGridSize(geom_unit) for dsid in request.dsvars
                ]
            rsg = request.subset_geom.buffer(max(grid_sizes))
        else:
            rsg = request.subset_geom

        # Reproject to datasets' CRS
        ds_subset_geoms = {}
        for dsid in request.dsvars:
            if request.subset_geom.crs.equals(request.dsc[dsid].crs):
                ds_subset_geoms[dsid] = rsg
            else:
                ds_subset_geoms[dsid] = rsg.reproject(
                    request.dsc[dsid].crs
                )

        return ds_subset_geoms

    def fulfillRequestSynchronous(self, request):
        """
        Implements synchronous (i.e., blocking) data request fulfillment.

        request: A DataRequest instance.
        """
        dsc = request.dsc

        # Get subset geoms in datasets' CRSs
        ds_subset_geoms = self._buildDatasetSubsetGeoms(request)

        # Get the requested data.
        output_data = {}

        if request.request_type == dr.REQ_RASTER:
            target_data = None
            for dsid in request.dsvars:
                # If the dataset is non-temporal, we don't need to iterate over the
                # request dates. Otherwise, prepare date lists per date grain 
                # (requested directly and those determined by requested grain_method). 
                ds_grain = request.ds_date_grains[dsid]
                if dsc[dsid].nontemporal:
                    date_list = [None] 
                elif ds_grain in dsc[dsid].supported_grains:
                    date_list = request.dates[ds_grain] 
                elif (
                    ds_grain not in dsc[dsid].supported_grains and
                    request.grain_method == 'skip'
                ):
                    # Skip this dataset
                    continue
                else:
                    raise ValueError('Unsupported date grain.') 

                # Collect requested data in a xarray.Dataset for this requested dataset
                ds_output_data = xr.Dataset()
                for varname in request.dsvars[dsid]:
                    var_date_data = []
                    for rdate in date_list:
                        raster_layer = self._getRasterLayer(
                            dsc[dsid], varname, ds_grain, rdate, ds_subset_geoms[dsid],
                            request, target_data
                        )
                        if request.harmonization and target_data is None:
                            target_data = raster_layer
                        # Check if data returned
                        # (sparse daily data not always returned)
                        if raster_layer is not None:
                            var_date_data.append(raster_layer)        
                    var_date_data = xr.concat(var_date_data, dim='time') 
                    ds_output_data[varname] = var_date_data 
                output_data.update({dsid : ds_output_data})

        elif request.request_type == dr.REQ_POINT:
            for dsid in request.dsvars:
                # If the dataset is non-temporal, we don't need to iterate over the
                # request dates. Otherwise, prepare date lists per date grain 
                # (requested directly and those determined by requested grain_method). 
                ds_grain = request.ds_date_grains[dsid]
                if dsc[dsid].nontemporal:
                    date_list = [None] 
                elif ds_grain in dsc[dsid].supported_grains:
                    date_list = request.dates[ds_grain] 
                elif (
                    ds_grain not in dsc[dsid].supported_grains and
                    request.grain_method == 'skip'
                ):
                    # Skip this dataset
                    continue
                else:
                    raise ValueError('Unsupported date grain.')

                for varname in request.dsvars[dsid]:
                    var_date_data = []
                    for rdate in date_list:
                        point_layer = self._getPointLayer(
                            dsc[dsid], varname, ds_grain, rdate, ds_subset_geoms[dsid],
                            request
                        )
                        # Check if data returned
                        # (sparse daily data not always returned)
                        if point_layer is not None:
                            var_date_data.append(point_layer)
                var_date_data = pd.concat(var_date_data)
                output_data.update({dsid : var_date_data})

        else:
            raise ValueError('Unsupported request type.')

        return output_data

