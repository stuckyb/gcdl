
import random
import zipfile
import json
from rasterio.enums import Resampling
import data_request as dr
import geopandas as gpd


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
        if grain == dr.ANNUAL:
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

    def _fulfillPointRequest(self, request, output_dir, ds_subset_geoms):
        fout_paths = []
        out_df = gpd.GeoDataFrame(
            {'x': request.subset_geom.geom.x, 'y': request.subset_geom.geom.y}
        )

        for dsid in request.dsvars:
            for varname in request.dsvars[dsid]:
                for rdate in request.dates:
                    # Retrieve the point data.
                    data = request.dsc[dsid].getData(
                        varname, request.date_grain, rdate, request.ri_method,
                        ds_subset_geoms[dsid]
                    )

                    # Output the result.
                    fout_path = (
                        output_dir / (self._getSingleLayerOutputFileName(
                            dsid, varname, request.date_grain, rdate
                        ) + '.csv')
                    )
                    out_df.assign(value=data).to_csv(fout_path, index=False)
                    fout_paths.append(fout_path)

        return fout_paths

    def _fulfillRasterRequest(self, request, output_dir, ds_subset_geoms):
        fout_paths = []

        for dsid in request.dsvars:
            for varname in request.dsvars[dsid]:
                for rdate in request.dates:
                    # Retrieve the (subsetted) data layer.
                    data = request.dsc[dsid].getData(
                        varname, request.date_grain, rdate, request.ri_method,
                        ds_subset_geoms[dsid]
                    )

                    # Reproject to the target resolution, target projection, or
                    # both, if needed.
                    if (
                        not(request.target_crs.equals(request.dsc[dsid].crs)) or
                        request.target_resolution is not None
                    ):
                        data = data.rio.reproject(
                            dst_crs=request.target_crs,
                            resampling=Resampling[request.ri_method],
                            resolution=request.target_resolution
                        )

                    # Output the result.
                    fout_path = (
                        output_dir / (self._getSingleLayerOutputFileName(
                            dsid, varname, request.date_grain, rdate
                        ) + '.tif')
                    )
                    data.rio.to_raster(fout_path)
                    fout_paths.append(fout_path)

        return fout_paths

    def fulfillRequestSynchronous(self, request, output_dir):
        """
        Implements synchronous (i.e., blocking) data request fulfillment.

        request: A DataRequest instance.
        output_dir: A Path instance for the output location.
        """
        dsc = request.dsc

        # Build a set of subset geometries, reprojected as needed, that match
        # the source dataset CRSs.  We precompute these to avoid redundant
        # reprojections when looping through the data retrievals.
        ds_subset_geoms = {}
        for dsid in request.dsvars:
            if request.subset_geom.crs.equals(dsc[dsid].crs):
                ds_subset_geoms[dsid] = request.subset_geom
            else:
                ds_subset_geoms[dsid] = request.subset_geom.reproject(
                    dsc[dsid].crs
                )

        # Get the requested data.
        if request.request_type == dr.REQ_RASTER:
            fout_paths = self._fulfillRasterRequest(
                request, output_dir, ds_subset_geoms
            )
        elif request.request_type == dr.REQ_POINT:
            fout_paths = self._fulfillPointRequest(
                request, output_dir, ds_subset_geoms
            )
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

