
import random
import zipfile
import json
import data_request as dr


# Characters for generating random file names.
fname_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'


class DataRequestHandler:
    """
    Manages data request fulfillment, including dataset interactions, data
    harmonization/post-processing, and output.
    """
    def __init__(self, dsc):
        """
        dsc: The DatasetCatalog to use.
        """
        self.dsc = dsc

    def _getSingleLayerOutputFileName(self, dsid, varname, grain, rdate):
        if grain == dr.ANNUAL:
            fname = '{0}_{1}_{2}.tif'.format(
                dsid, varname, rdate.year
            )
        elif grain == dr.MONTHLY:
            fname = '{0}_{1}_{2}-{3:02}.tif'.format(
                dsid, varname, rdate.year, rdate.month
            )
        elif grain == dr.DAILY:
            fname = '{0}_{1}_{2}-{3:02}-{4:02}.tif'.format(
                dsid, varname, rdate.year, rdate.month, rdate.day
            )
        else:
            raise ValueError('Invalid date granularity specification.')

        return fname

    def fulfillRequestSynchronous(self, request, output_dir):
        """
        Implements synchronous (i.e., blocking) data request fulfillment.

        request: A DataRequest instance.
        output_dir: A Path instance for the output location.
        """
        fout_paths = []

        for dsid in request.dsvars:
            for varname in request.dsvars[dsid]:
                for rdate in request.dates:
                    data = self.dsc[dsid].getData(
                        varname, request.date_grain, rdate, request.clip_poly
                    )

                    fout_path = (
                        output_dir / self._getSingleLayerOutputFileName(
                            dsid, varname, request.date_grain, rdate
                        )
                    )
                    data.rio.to_raster(fout_path)
                    fout_paths.append(fout_path)

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

