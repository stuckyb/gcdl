
from catalog.catalog import DatasetCatalog
from catalog.datasets import PRISM, DAYMET, GTOPO
from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from collections import OrderedDict
from datetime import datetime, timezone
import tempfile
import zipfile
import random
import json
from pathlib import Path


dsc = DatasetCatalog('local_data')
dsc.addDatasetsByClass(PRISM, DAYMET, GTOPO)

# Characters for generating random file names.
fname_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'

# Directory for serving output files.
output_dir = Path('output')

def check_dsid(dsid, ds_catalog):
    """
    Raises an exception if a given dataset ID is invalid.
    """
    if dsid not in ds_catalog:
        raise HTTPException(
            status_code=404, detail=f'Invalid dataset ID: {dsid}'
        )


app = FastAPI(
    title='Geospatial Common Data Library REST API',
    description='Welcome to the interactive documentation for USDA-ARS\'s '
    'Geospatial Common Data Library (GeoCDL) REST API! Here, you can see all '
    'available API endpoints and directly experiment with GeoCDL API calls. '
    'Note that most users will find it easier to access the GeoCDL via one of '
    'our higher-level interfaces, including a web GUI interface and packages '
    'for Python and R.'
)

@app.get(
    '/list_datasets', tags=['Library catalog operations'],
    summary='Returns a list with the ID and name of each dataset in the '
    'library.'
)
async def list_datasets():
    return dsc.getCatalogEntries()


@app.get(
    '/ds_info', tags=['Dataset operations'],
    summary='Returns metadata for the geospatial dataset with the provided ID.'
)
async def ds_info(
    dsid: str = Query(
        ..., alias='id', title='Dataset ID', description='The ID of a dataset.'
    )
):
    check_dsid(dsid, dsc)

    return dsc[dsid].getDatasetMetadata()


def parse_datasets(
    datasets: str = Query(
        ..., title='Datasets and variables', description='The datasets and '
        'variables to include, specified as '
        '"DATASET_ID:VARNAME[,VARNAME...][;DATASET_ID:VARNAME[,VARNAME...]...].  '
        'Examples: "PRISM:tmax", "PRISM:tmax;DaymetV4:tmax,prcp".'
    )
):
    """
    Parses a string specifying datasets and variables.
    """
    ds_vars = {}
    for ds_spec in datasets.split(';'):
        parts = ds_spec.split(':')
        if len(parts) != 2:
            raise HTTPException(
                status_code=400, detail='Incorrect dataset specification.'
            )

        varnames = parts[1].split(',')
        if varnames[0] == '':
            raise HTTPException(
                status_code=400, detail='Incorrect dataset specification.'
            )

        ds_vars[parts[0]] = varnames

    return ds_vars

def parse_rect_bounds(
    bbox: str = Query(
        None, title='Bounding box', description='The upper left and lower '
        'right corners of the bounding box for subsetting the data, specifed '
        'as a comma-separated list of the form '
        '"UPPER_LEFT_X_COORD,UPPER_LEFT_Y_COORD,'
        'LOWER_RIGHT_X_COORD,LOWER_RIGHT_Y_COORD." If no bounding box is '
        'specified, the full spatial extent will be returned. Coordinates '
        'are assumed to match the target CRS or the CRS of the first '
        'requested dataset if no target CRS is specified.'
    )
):
    """
    Parses comma-separated rectangular bounding box coordinates.
    """
    if bbox is None:
        return None

    parts = bbox.split(',')
    if len(parts) != 4:
        raise HTTPException(
            status_code=400, detail='Incorrect bounding box specification.'
        )

    try:
        parts = [float(part) for part in parts]
    except:
        raise HTTPException(
            status_code=400, detail='Incorrect bounding box specification.'
        )

    coords = [[parts[0], parts[1]], [parts[2], parts[3]]]

    return coords

@app.get(
    '/subset', tags=['Dataset operations'],
    summary='Requests a geographic subset (which can be the full dataset) of '
    'one or more variables from one or more geospatial datasets.'
)
async def subset(
    req: Request,
    datasets: str = Depends(parse_datasets),
    date_start: str = Query(
        None, title='Start date (inclusive)', description='The starting date '
        'for which to request data. Dates must be specified as strings, where '
        '"YYYY" means extract annual data, "YYYY-MM" is for monthly data, and '
        '"YYYY-MM-DD" is for daily data. Date can be omitted for non-temporal '
        'data requests.'
    ),
    date_end: str = Query(
        None, title='End date (inclusive)', description='The ending date '
        'for which to request data. Dates must be specified as strings, where '
        '"YYYY" means extract annual data, "YYYY-MM" is for monthly data, and '
        '"YYYY-MM-DD" is for daily data. Date can be omitted for non-temporal '
        'data requests.'
    ),
    bbox: list = Depends(parse_rect_bounds),
    crs: str = Query(
        None, title='Target coordinate reference system.',
        description='The target coordinate reference system (CRS) for the '
        'returned data, specified as an EPSG code.'
    ),
    resample_method: str = Query(
        None, title='Resample method.',
        description='The resampling method used in reprojection. Available '
        'methods: nearest, bilinear, cubic, cubic-spline, lanczos, average, '
        'or mode. Default is nearest. Only used if target crs is provided.'
    )
):
    req_md = OrderedDict()
    ds_metadata = []
    out_paths = []

    # Generate the request metadata.
    req_md['request'] = {}
    req_md['request']['url'] = str(req.url)
    req_md['request']['datetime'] = datetime.now(timezone.utc).isoformat()

    # Subset data
    user_crs = crs
    for dsid in datasets:
        check_dsid(dsid, dsc)

        ds = dsc[dsid]
        if user_crs is None:
            user_crs = ds.epsg_code

        md, paths = ds.getSubset(
            output_dir, date_start, date_end, datasets[dsid], user_crs, bbox, crs, resample_method
        )
        ds_metadata.append(md)
        out_paths.extend(paths)

    req_md['datasets'] = ds_metadata
    
    # Write the metadata file.
    md_path = output_dir / (
        ''.join(random.choices(fname_chars, k=16)) + '.json'
    )
    with open(md_path, 'w') as fout:
        json.dump(req_md, fout, indent=4)

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

    for out_path in out_paths:
        zfile.write(out_path, arcname=out_path.name)

    zfile.close()

    return FileResponse(zfpath, filename=zfpath.name)

