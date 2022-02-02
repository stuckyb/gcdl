
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
        'specified, the full spatial extent will be returned. '
        'If both bbox and points are specified, the bbox will be used. '
        'Coordinates are assumed to match the target CRS or the CRS of the first '
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

def parse_points(
    points: str = Query(
        None, title='Point Extraction', description='The x and y coordinates '
        'of point locations for extracting from the data, specifed '
        'as x1,y1;x2,y2;... If no point coordinates are '
        'specified, the full spatial extent will be returned. '
        'If both bbox and points are specified, the bbox will be used. '
        'Coordinates are assumed to match the target CRS or the CRS of the first '
        'requested dataset if no target CRS is specified.'
    )
):
    """
    Parses comma-separated rectangular bounding box coordinates.
    """
    if points is None:
        return None

    pt_coords = []
    for pt in points.split(';'):
        parts = pt.split(',')
        if len(parts) != 2:
            raise HTTPException(
                status_code=400, detail='Incorrect point coordinate specification.'
            )

        try:
            parts = [float(part) for part in parts]
        except:
            raise HTTPException(
                status_code=400, detail='Incorrect point coordinate specification.'
            )

        pt_coords.append([parts[0], parts[1]])

    return pt_coords


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
    points: list = Depends(parse_points),
    crs: str = Query(
        None, title='Target coordinate reference system.',
        description='The target coordinate reference system (CRS) for the '
        'returned data, specified as an EPSG code.'
    ),
    resolution: str = Query(
        None, title='Target spatial resolution.',
        description='The target spatial resolution for the '
        'returned data, specified in units of target crs or the CRS of '
        'the first dataset.'
    ),
    point_method: str = Query(
        None, title='Point extraction method.',
        description='The method used in extracting point values. Available '
        'methods: nearest or bilinear. Default is nearest. '
        'Only used if point coordinates are provided.'
    ),
    resample_method: str = Query(
        None, title='Resample method.',
        description='The resampling method used in reprojection. Available '
        'methods: nearest, bilinear, cubic, cubic-spline, lanczos, average, '
        'or mode. Default is nearest. Only used if target crs and/or spatial '
        'resolution are provided. '
    )
):
    req_md = OrderedDict()
    ds_metadata = []
    out_paths = []

    # Generate the request metadata.
    req_md['request'] = {}
    req_md['request']['url'] = str(req.url)
    req_md['request']['datetime'] = datetime.now(timezone.utc).isoformat()

    # Define user geometry
    user_geom = None
    if bbox is not None:
        user_geom = [{
                'type': 'Polygon',
                'coordinates': [[
                    # Top left.
                    [bbox[0][0], bbox[0][1]],
                    # Top right.
                    [bbox[1][0], bbox[0][1]],
                    # Bottom right.
                    [bbox[1][0], bbox[1][1]],
                    # Bottom left.
                    [bbox[0][0], bbox[1][1]],
                    # Top left.
                    [bbox[0][0], bbox[0][1]]
                ]]
            }]
    elif points is not None:
        user_geom = [{
            'type': 'Point',
            'coordinates': points
        }]

    # Subset data
    user_crs = crs
    file_ext = 'tif' if points is None else 'csv'
    resample_method = 'nearest' if resample_method is None else resample_method
    for dsid in datasets:
        check_dsid(dsid, dsc)

        ds = dsc[dsid]
        # Assume first dataset's crs for user geometries if target crs is not specified
        if user_crs is None:
            user_crs = ds.epsg_code

        md, paths = ds.getSubset(
            output_dir, date_start, date_end, datasets[dsid], user_crs, user_geom, crs,
            resolution, resample_method, point_method, file_ext
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

