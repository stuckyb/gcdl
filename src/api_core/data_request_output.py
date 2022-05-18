
import random
import zipfile
import json
import api_core.data_request as dr
from pathlib import Path
import xarray as xr
from osgeo import gdal
import rasterio


# Characters for generating random file names.
fname_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'

class DataRequestOutput:
    """
    Manages data request output.
    """
    def __init__(self):
        pass

    def _getSingleLayerOutputFileName(self, dsid, varname, date_str):

        if date_str == '':
           fname = '{0}_{1}'.format(
                    dsid, varname
                ) 
        else:
            fname = '{0}_{1}_{2}'.format(
                    dsid, varname, date_str
                )

        return fname


    def _writeCSV(self, data_gdf, fout_path):
        # Modify geometry to list coordinates in x,y columns
        data_gdf['x'] = data_gdf.geometry.x
        data_gdf['y'] = data_gdf.geometry.y
        data_gdf = data_gdf.drop(columns=['geometry'])
        # Write to CSV
        data_gdf.to_csv(fout_path, index=False)

    def _writeShapefile(self, data_gdf, fout_path):
        data_gdf.to_file(fout_path, index=False)

    def _writeNetCDF(self, data, fout_path, RAT=None, colormap=None):
        if isinstance(data, xr.Dataset):
            if RAT is not None:
                trim_RAT = {k:v for (k,v) in RAT.items() if k > -1}
                # NetCDF convention has flag_values formatted as
                # a single string of comma-separated integers and 
                # flag_meanings as a single string of space-separated
                # names where spaces in names are underscores.
                data.attrs['flag_values'] = ','.join([str(k) for k in trim_RAT.keys()])
                data.attrs['flag_meanings'] = ' '.join(
                    [class_id.replace(' ','_') for class_id in trim_RAT.values()]
                )
                if colormap is not None:
                    rat_colors = []
                    for class_id in trim_RAT.keys():
                        rat_colors.append('#{:02x}{:02x}{:02x}'.format(*colormap[class_id]))
                    data.attrs['flag_colors'] = ' '.join(rat_colors)
        else:
            # Modify geometry to list coordinates in x,y columns
            g_crs = data.geometry.crs
            data['x'] = data.geometry.x
            data['y'] = data.geometry.y
            data = data.drop(columns=['geometry'])
            data = data.set_index(['x', 'y', 'time'])
            # Pivot wider
            data['dsvar'] = data['dataset'] + '_' + data['variable']
            data = data.pivot(
                columns = 'dsvar',
                values = 'value'
            )
            # Convert to xarray DataArray
            data = data.to_xarray()
            data.rio.write_crs(g_crs, inplace=True)

        # Write to netCDF
        data.to_netcdf(fout_path)

    def _writeGeoTIFF(self, data_xrda, rdate, fout_path, RAT=None, colormap=None):
        data_xrda.sel(time = rdate).rio.to_raster(fout_path)
        all_fpaths = [fout_path]

        if RAT is not None:
            ds = gdal.Open(str(fout_path))
            rb = ds.GetRasterBand(1)
            rat = gdal.RasterAttributeTable()
            rat.SetRowCount(256)
            rat.CreateColumn('CLASS', gdal.GFT_String, gdal.GFU_Generic)
            for i in RAT:
                rat.SetValueAsString(i, 0, RAT[i])

            rb.SetDefaultRAT(rat)
            ds = None
            rat_path = fout_path.parent / (fout_path.name + '.aux.xml')
            all_fpaths.append(rat_path)

            if colormap is not None:
                with rasterio.open(fout_path, 'r+') as dst:
                    dst.write_colormap(1, colormap)


        return all_fpaths

    def _writePointFiles(self, ds_output_dict, request, output_dir):
        fname = '_'.join(request.dsvars.keys())
        fout_path = output_dir / (fname + request.file_extension)

        # Merge list of geodataframes into one geodataframe
        # Assuming long format for now:
        ds_output_list = [gdf for gdf in ds_output_dict.values()]
        final_gdf = ds_output_list[0]
        for gdf in ds_output_list[1:]:
            final_gdf = final_gdf.append(gdf)

        if request.file_extension == ".csv":
            self._writeCSV(final_gdf, fout_path)
            fout_paths = [fout_path]
        elif request.file_extension == ".shp":
            self._writeShapefile(final_gdf, fout_path)
            # Return all shapefile's auxillary files
            p = Path(output_dir).glob(fname+'.*')
            fout_paths = [file for file in p]
        elif request.file_extension == ".nc":
            self._writeNetCDF(final_gdf, fout_path)
            fout_paths = [fout_path]
        else:
            raise ValueError('Unsupported point output format.')

        return fout_paths


    def _writeRasterFiles(self, ds_output_dict, request, output_dir):
        fout_paths = []
        if request.file_extension == ".tif":
            # Write a geoTIFF per dataset, variable, and date. 
            for dsid in ds_output_dict:
                ds = ds_output_dict[dsid]
                for varname in list(ds.data_vars):
                    dsvar = ds[varname]
                    for t in dsvar.coords['time'].values:
                        fname = self._getSingleLayerOutputFileName(dsid, varname, t)
                        fout_path = output_dir / (fname + request.file_extension)
                        aux_fout_paths = self._writeGeoTIFF(
                            dsvar, t, fout_path, request.dsc[dsid].RAT, 
                            request.dsc[dsid].colormap
                        )
                        for fp in aux_fout_paths:
                            fout_paths.append(fp)
        elif request.file_extension == ".nc":
            # Write a netcdf per dataset. 
            for dsid in ds_output_dict:
                fname = dsid
                fout_path = output_dir / (fname + request.file_extension)
                ds_dataset = ds_output_dict[dsid]
                self._writeNetCDF(
                    ds_dataset,fout_path, request.dsc[dsid].RAT, 
                    request.dsc[dsid].colormap
                )
                fout_paths.append(fout_path)
        else:
            raise ValueError('Unsupported raster output format.')

        return fout_paths

    def _writeMetadataFile(self, req_md, output_dir):
        # Write the metadata file.
        md_path = output_dir / (
            ''.join(random.choices(fname_chars, k=16)) + '.json'
        )
        with open(md_path, 'w') as fout:
            json.dump(req_md, fout, indent=4)

        return md_path


    def writeRequestedData(self, request, req_data, output_dir):
        """
        Writes requested data in requested output format
        """

        # Create random id for this request
        req_id = random.choices(fname_chars, k=8)

        # Create temporary output folder for request
        tmp_fname = (
            'geocdl_subset_' + ''.join(req_id)
        )
        tmp_path = output_dir / tmp_fname
        tmp_path.mkdir()

        # Write requested data
        if request.request_type == dr.REQ_RASTER:
            fout_paths = self._writeRasterFiles(req_data, request, tmp_path)
        elif request.request_type == dr.REQ_POINT:
            fout_paths = self._writePointFiles(req_data, request, tmp_path)

        md_path = self._writeMetadataFile(request.metadata, tmp_path)
        

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

