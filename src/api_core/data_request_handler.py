
import random
import zipfile
import json
from rasterio.enums import Resampling
import api_core.data_request as dr
import geopandas as gpd
import datetime as dt


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
            {'x': request.subset_geom.geom.x, 'y': request.subset_geom.geom.y}
        )

        # Retrieve the point data.
        data = dataset.getData(
            varname, grain, rdate, request.ri_method, subset_geom
        )

        if data is not None:

            # Output the result.
            fout_path = (
                output_dir / (self._getSingleLayerOutputFileName(
                    dataset.id, varname, grain, rdate
                ) + '.csv')
            )
            out_df.assign(value=data).to_csv(fout_path, index=False)

            return fout_path
        else:
            return None

    def _getRasterLayer(
        self, dataset, varname, grain, rdate, subset_geom, request, output_dir
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
                data = data.rio.reproject(
                    dst_crs=request.target_crs,
                    resampling=Resampling[request.ri_method],
                    resolution=request.target_resolution
                )

            # Output the result.
            fout_path = (
                output_dir / (self._getSingleLayerOutputFileName(
                    dataset.id, varname, grain, rdate
                ) + '.tif')
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
        # the source dataset CRSs.  We precompute these to avoid redundant
        # reprojections when processing the data retrievals.
        ds_subset_geoms = {}
        for dsid in request.dsvars:
            if request.subset_geom.crs.equals(dsc[dsid].crs):
                ds_subset_geoms[dsid] = request.subset_geom
            else:
                ds_subset_geoms[dsid] = request.subset_geom.reproject(
                    dsc[dsid].crs
                )

        # Get the requested data.
        fout_paths = []

        for dsid in request.dsvars:
            # If the dataset is non-temporal, we don't need to iterate over the
            # request dates.
            # If the request's date grain is available in the dataset,
            # use that date grain. Otherwise, use next closest date
            # grain, unless request includes strict granularity.

            print(dsc[dsid].supported_grains)

            if dsc[dsid].nontemporal:
                date_list = [None]
                ds_grain = None
            elif request.date_grain in dsc[dsid].supported_grains:
                date_list = request.dates
                ds_grain = request.date_grain
            elif request.strict_granularity:
                # Skip this dataset
                continue 
            else:
                date_list = []
                # Find next date grain and modify request dates
                if request.date_grain == dr.ANNUAL:
                    if dr.MONTHLY in dsc[dsid].supported_grains:
                        # Expand years to months
                        for ydate in request.dates:
                            for month in range(12):
                                new_date = dr.RequestDate(ydate.year, month+1, None)
                                date_list.append(new_date)

                        ds_grain = dr.MONTHLY

                    else:
                        # Must be daily only, so expand to full dates
                        for ydate in request.dates:
                            inc_date = dt.date(ydate.year, 1, 1)
                            end_date = dt.date(ydate.year, 12, 31)

                            interval = dt.timedelta(days=1)
                            end_date += interval

                            # Add each date in the year
                            while inc_date != end_date:
                                new_date = dr.RequestDate(inc_date.year, inc_date.month, inc_date.day)
                                date_list.append(new_date)
                                inc_date += interval

                        ds_grain = dr.DAILY

                elif request.date_grain == dr.MONTHLY:
                    if dr.ANNUAL in dsc[dsid].supported_grains:
                        # Simplify months to years
                        for mdate in request.dates:
                            new_date = dr.RequestDate(mdate.year, None, None)
                            date_list.append(new_date)

                        date_list = list(set(date_list))
                        ds_grain = dr.ANNUAL
                    else:
                        # Must be daily only, so expand to full dates
                        for mdate in request.dates:
                            inc_date = dt.date(mdate.year, mdate.month, 1)
                            interval = dt.timedelta(days=1)

                            # Add each date in the month
                            while inc_date.month == mdate.month:
                                new_date = dr.RequestDate(inc_date.year, inc_date.month, inc_date.day)
                                date_list.append(new_date)
                                inc_date += interval

                        ds_grain = dr.DAILY

                elif request.date_grain == dr.DAILY:
                    if dr.MONTHLY in dsc[dsid].supported_grains:
                        # Simplify dates to months
                        for date in request.dates:
                            new_date = dr.RequestDate(date.year, date.month, None)
                            date_list.append(new_date)

                        date_list = list(set(date_list))
                        ds_grain = dr.MONTHLY
                    else:
                        # Must be annual, simplify dates to years
                        for date in request.dates:
                            new_date = dr.RequestDate(date.year, None, None)
                            date_list.append(new_date)

                        date_list = list(set(date_list))
                        ds_grain = dr.ANNUAL
                else:
                    raise NotImplementedError()




            for varname in request.dsvars[dsid]:
                for rdate in date_list:
                    if request.request_type == dr.REQ_RASTER:
                        raster_layer = self._getRasterLayer(
                            dsc[dsid], varname, ds_grain, rdate, ds_subset_geoms[dsid],
                            request, output_dir
                        )
                        # Check if data returned
                        # (sparse daily data not always returned)
                        if raster_layer is not None:
                            fout_paths.append(raster_layer)
                    elif request.request_type == dr.REQ_POINT:
                        point_layer = self._getPointLayer(
                            dsc[dsid], varname, ds_grain, rdate, ds_subset_geoms[dsid],
                            request, output_dir
                        )
                        # Check if data returned
                        # (sparse daily data not always returned)
                        if point_layer is not None:
                            fout_paths.append(point_layer)
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

