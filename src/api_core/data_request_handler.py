
import random
import zipfile
import json
from rasterio.enums import Resampling
import api_core.data_request as dr
import geopandas as gpd
import datetime as dt
import rioxarray
from pathlib import Path


# Characters for generating random file names.
fname_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'

class DataRequestHandler:
    """
    Manages data request fulfillment, including dataset interactions, data
    harmonization/post-processing, and output.
    """
    def __init__(self):
        pass

    def _getSingleLayerOutputFileName(self, dsid, varname, grain, rdate):
        if grain == dr.NONE or rdate is None:
            fname = '{0}_{1}'.format(
                dsid, varname
            )
        elif grain == dr.ANNUAL:
            fname = '{0}_{1}_{2}'.format(
                dsid, varname, rdate.year
            )
        elif grain == dr.MONTHLY:
            fname = '{0}_{1}_{2}-{3:02}'.format(
                dsid, varname, rdate.year, rdate.month
            )
        elif grain == dr.DAILY:
            fname = '{0}_{1}_{2}-{3:02}-{4:02}'.format(
                dsid, varname, rdate.year, rdate.month, rdate.day
            )
        else:
            raise ValueError('Invalid date granularity specification.')

        return fname

    def _getPointLayer(
        self, dataset, varname, grain, rdate, subset_geom, request, output_dir
    ):
        # Not a great solution to be creating a new base dataframe on every
        # call, but multi-format output handling will eventually take care of
        # this.
        out_df = gpd.GeoDataFrame(
            #{'x': request.subset_geom.geom.x, 'y': request.subset_geom.geom.y}
            geometry = subset_geom.geom
        )

        # Retrieve the point data.
        data = dataset.getData(
            varname, grain, rdate, request.ri_method, subset_geom
        )

        if data is not None:

            # Output the result.
            fname = '{0}_{1}'.format(dataset.id, varname)
            fout_path = output_dir / (fname + request.file_extension)

            if grain == dr.NONE or rdate is None:
                my_date = ''
            elif grain == dr.ANNUAL:
                my_date = rdate.year
            elif grain == dr.MONTHLY:
                my_date = '{0}-{1:02}'.format(
                    rdate.year, rdate.month
                )
            else:
                my_date = '{0}-{1:02}-{2:02}'.format(
                    rdate.year, rdate.month, rdate.day
                )

            if request.file_extension == ".csv":
                out_df = gpd.GeoDataFrame({
                    'x': request.subset_geom.geom.x, 
                    'y': request.subset_geom.geom.y,
                    'time': my_date, 
                    varname: data
                    }
                )
                out_df.to_csv(fout_path, index=False, mode="a")
            else:
                out_df = gpd.GeoDataFrame({
                    'time': my_date, 
                    varname: data
                    },
                    geometry = subset_geom.geom,
                )

                if not(fout_path.exists()):
                    out_df.to_file(fout_path, index=False)
                else:
                    out_df.to_file(fout_path, index=False, mode="a")

                # Return all shapefile's auxillary files
                if request.file_extension == ".shp":
                    p = Path(output_dir).glob(fname+'.*')
                    fout_path = [file for file in p]

            return fout_path
        else:
            return None

    def _getRasterLayer(
        self, dataset, varname, grain, rdate, subset_geom, request, output_dir,
        target_path = None
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
                if target_path is None:
                    data = data.rio.reproject(
                        dst_crs=request.target_crs,
                        resampling=Resampling[request.ri_method],
                        resolution=request.target_resolution
                    )
                else:
                    #Inefficient - but testing if harmonization works for now
                    target_layer = rioxarray.open_rasterio(target_path, masked=True)
                    data = data.rio.reproject_match(target_layer)

                # Clip to the non-modified requested geometry
                data = data.rio.clip([request.subset_geom.json], all_touched = True)

            # Output the result.
            fout_path = (
                output_dir / (self._getSingleLayerOutputFileName(
                    dataset.id, varname, grain, rdate
                ) + request.file_extension)
            )
            data.rio.to_raster(fout_path)

            return fout_path
        else:
            return None

    def fulfillRequestSynchronous(self, request, output_dir):
        """
        Implements synchronous (i.e., blocking) data request fulfillment.

        request: A DataRequest instance.
        output_dir: A Path instance for the output location.
        """
        dsc = request.dsc

        # Build a set of subset geometries, reprojected as needed, that match
        # the source dataset CRSs. A buffer width of the coarsest grid size 
        # is added to each to handle boundary discrepancies. We precompute 
        # these geometries to avoid redundant reprojections when processing 
        # the data retrievals.
        if request.request_type == dr.REQ_RASTER:
            if request.subset_geom.geom.crs.axis_info[0].unit_name == 'metre':
                grid_sizes = [
                    dsc[dsid].grid_size if dsc[dsid].grid_unit == 'meters' 
                    else dsc[dsid].grid_size*111000 for dsid in request.dsvars
                ]
            else:
                grid_sizes = [
                    dsc[dsid].grid_size/111000 if dsc[dsid].grid_unit == 'meters' 
                    else dsc[dsid].grid_size for dsid in request.dsvars
                ]
            rsg = request.subset_geom.buffer(max(grid_sizes))
        else:
            rsg = request.subset_geom

        ds_subset_geoms = {}
        for dsid in request.dsvars:
            if request.subset_geom.crs.equals(dsc[dsid].crs):
                ds_subset_geoms[dsid] = rsg
            else:
                ds_subset_geoms[dsid] = rsg.reproject(
                    dsc[dsid].crs
                )

        # Get the requested data.
        fout_paths = []

        # Check if there needs to be a target layer for harmonization
        harmonization = False
        target_path = None
        if(request.target_resolution is not None and request.subset_geom is not None):
            harmonization = True

        # Create temporary folder for request
        tmp_fname = (
            'geocdl_subset_' + ''.join(random.choices(fname_chars, k=8))
        )
        tmp_path = output_dir / tmp_fname
        tmp_path.mkdir()

        for dsid in request.dsvars:
            # If the dataset is non-temporal, we don't need to iterate over the
            # request dates.
            # If the request's date grain is available in the dataset,
            # use that date grain. Otherwise, use grain_method
            # to determine response.
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
                for rdate in date_list:
                    if request.request_type == dr.REQ_RASTER:
                        raster_layer = self._getRasterLayer(
                            dsc[dsid], varname, ds_grain, rdate, ds_subset_geoms[dsid],
                            request, tmp_path, target_path
                        )
                        if harmonization and target_path is None:
                            target_path = raster_layer
                        # Check if data returned
                        # (sparse daily data not always returned)
                        if raster_layer is not None:
                            fout_paths.append(raster_layer)
                    elif request.request_type == dr.REQ_POINT:
                        point_layer = self._getPointLayer(
                            dsc[dsid], varname, ds_grain, rdate, ds_subset_geoms[dsid],
                            request, tmp_path
                        )
                        # Check if data returned
                        # (sparse daily data not always returned)
                        if point_layer is not None:
                            # Check if multiple files
                            if isinstance(point_layer, Path):
                                fout_paths.append(point_layer)
                            else:
                                for lyr in point_layer:
                                    fout_paths.append(lyr)
                    else:
                        raise ValueError('Unsupported request type.')

        # Write the metadata file.
        md_path = output_dir / (
            ''.join(random.choices(fname_chars, k=16)) + '.json'
        )
        with open(md_path, 'w') as fout:
            json.dump(request.metadata, fout, indent=4)

        # Generate the output ZIP archive.
        zfname = (
            'geocdl_subset_' + ''.join(random.choices(fname_chars, k=8)) +
            '.zip'
        )
        zfpath = output_dir / zfname
        zfile = zipfile.ZipFile(
            zfpath, mode='w', compression=zipfile.ZIP_DEFLATED
        )

        zfile.write(md_path, arcname='metadata.json')

        for fout_path in fout_paths:
            zfile.write(fout_path, arcname=fout_path.name)

        zfile.close()

        return zfpath

