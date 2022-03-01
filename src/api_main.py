
from library.catalog import DatasetCatalog
from library.datasets import PRISM, DaymetV4, GTOPO, SRTM, MODIS_NDVI
from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
import pyproj
from subset_geom import SubsetPolygon, SubsetMultiPoint
from api_core import DataRequest, REQ_RASTER, REQ_POINT
from api_core import DataRequestHandler


dsc = DatasetCatalog('local_data')
dsc.addDatasetsByClass(PRISM, DaymetV4, GTOPO, SRTM, MODIS_NDVI)

# Directory for serving output files.
output_dir = Path('output')

def _check_dsid(dsid, ds_catalog):
    """
    Raises an exception if a given dataset ID is invalid.
    """
    if dsid not in ds_catalog:
        raise HTTPException(
            status_code=404, detail=f'Invalid dataset ID: {dsid}'
        )

def _parse_datasets(
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

        _check_dsid(parts[0], dsc)

        ds_vars[parts[0]] = varnames

    return ds_vars

def _parse_coords_list(coords_str):
    """
    Parses a comma-separated list of coordinates.
    """
    if coords_str[0] != '(':
        raise ValueError('Incorrect coordinate specification.')

    coord_strs = coords_str.split('),')
    coord_strs = [c[1:] for c in coord_strs]
    # Remove the trailing ')' from the last coordinate string.
    if coord_strs[-1][-1] == ')':
        coord_strs[-1] = coord_strs[-1][:-1]
    else:
        raise ValueError('Incorrect coordinate specification.')

    coords = []
    for coord_str in coord_strs:
        parts = coord_str.split(',')

        try:
            parts = [float(part) for part in parts]
        except:
            raise ValueError('Incorrect coordinate specification.')

        coords.append(parts)

    return coords

def _parse_clip_bounds(
    clip: str = Query(
        None, title='Clip boundary', description='Specifies the clip boundary '
        'for the subset operation.  The boundary can be specified in one of '
        'two ways: 1) The upper left and lower right corners of a '
        'bounding box for subsetting the data, specifed as a comma-separated '
        'list of the form "(UPPER_LEFT_X,UPPER_LEFT_Y),'
        '(LOWER_RIGHT_X,LOWER_RIGHT_Y)."; 2) A comma-separated '
        'list of coordinates defining the vertices of a clip polygon as in '
        '"(X1,Y1),(X2,Y2)...".'
    )
):
    """
    Parses a clip boundary specification.
    """
    if clip is None:
        return None

    try:
        coords = _parse_coords_list(clip)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if len(coords) < 2:
        raise HTTPException(
            status_code=400,
            detail='Invalid clip geometry specification.'
        )

    if len(coords) == 2:
        # Interpret 2 coordinates as the top left and lower right corners
        # of a bounding box.
        clip_coords = [
            # Top left.
            [coords[0][0], coords[0][1]],
            # Top right.
            [coords[1][0], coords[0][1]],
            # Bottom right.
            [coords[1][0], coords[1][1]],
            # Bottom left.
            [coords[0][0], coords[1][1]],
            # Top left.
            [coords[0][0], coords[0][1]]
        ]
    else:
        # Interpret more than 2 coordinates as the vertices of a polygon.
        # Close the polygon, if needed.
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        clip_coords = coords

    return clip_coords

def _parse_points(
    points: str = Query(
        ..., title='Point Extraction', description='The x and y coordinates '
        'of point locations for extracting from the data, specified '
        'as x1,y1;x2,y2;... If no point coordinates are specified, the full '
        'spatial extent will be returned. If both bbox and points are '
        'specified, the bbox will be used. Coordinates are assumed to match '
        'the target CRS or the CRS of the first requested dataset if no '
        'target CRS is specified.'
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
                status_code=400,
                detail='Incorrect point coordinate specification.'
            )

        try:
            parts = [float(part) for part in parts]
        except:
            raise HTTPException(
                status_code=400,
                detail='Incorrect point coordinate specification.'
            )

        pt_coords.append(parts)

    return pt_coords

def _get_request_metadata(req):
    """
    Generates a dictionary of basic metadata for an API request.
    """
    req_md = {
        'url': str(req.url),
        'datetime': datetime.now(timezone.utc).isoformat()
    }

    return req_md


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
    _check_dsid(dsid, dsc)

    return dsc[dsid].getMetadata()


@app.get(
    '/subset_polygon', tags=['Dataset operations'],
    summary='Requests a geographic subset (which can be the full dataset) of '
    'one or more variables from one or more geospatial datasets.'
)
async def subset_polygon(
    req: Request,
    datasets: str = Depends(_parse_datasets),
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
    clip: list = Depends(_parse_clip_bounds),
    crs: str = Query(
        None, title='Target coordinate reference system.',
        description='The target coordinate reference system (CRS) for the '
        'returned data.  Can be specified as a PROJ string, CRS WKT string,'
        'authority string (e.g., "EPSG:4269"), or PROJ object name '
        '(e.g., "NAD83").'
    ),
    resolution: float = Query(
        None, title='Target spatial resolution.',
        description='The target spatial resolution for the returned data, '
        'specified in units of the target CRS or of the CRS of the first '
        'dataset if no target CRS is provided.'
    ),
    resample_method: str = Query(
        None, title='Resampling method.',
        description='The resampling method used for reprojection. Available '
        'methods: "nearest", "bilinear", "cubic", "cubic-spline", "lanczos", '
        '"average", or "mode". Default is "nearest".  Only used if target CRS '
        'and/or spatial resolution are provided. '
    )
):
    req_md = _get_request_metadata(req)

    # For complete information about all accepted crs_str formats, see the
    # documentation for the CRS constructor:
    # https://pyproj4.github.io/pyproj/stable/api/crs/crs.html#pyproj.crs.CRS.__init__
    # The CRS constructor calls proj_create() from the PROJ library for some
    # CRS strings.  The documentation for proj_create() provides more
    # information about accepted strings:
    # https://proj.org/development/reference/functions.html#c.proj_create.

    if crs is None:
        # Use the CRS of the first dataset in the request as the target CRS if
        # none was specified.
        target_crs = dsc[list(datasets.keys())[0]].crs
    else:
        target_crs = pyproj.crs.CRS(crs)

    clip_geom = SubsetPolygon(clip, target_crs)

    try:
        request = DataRequest(
            dsc, datasets, date_start, date_end, clip_geom, target_crs,
            resolution, resample_method, REQ_RASTER, req_md
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    req_handler = DataRequestHandler()
    res_path = req_handler.fulfillRequestSynchronous(request, output_dir)

    return FileResponse(res_path, filename=res_path.name)


@app.get(
    '/subset_points', tags=['Dataset operations'],
    summary='Requests a geographic subset of specific geographic points '
    'extracted for one or more variables from one or more geospatial datasets.'
)
async def subset_points(
    req: Request,
    datasets: str = Depends(_parse_datasets),
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
    points: list = Depends(_parse_points),
    crs: str = Query(
        None, title='Target coordinate reference system.',
        description='The target coordinate reference system (CRS) for the '
        'returned data, specified as an EPSG code.'
    ),
    interp_method: str = Query(
        None, title='Point interpolation method.',
        description='The interpolation method used for extracting point '
        'values. Available methods: "nearest" or "linear". Default is '
        '"nearest".'
    )
):
    req_md = _get_request_metadata(req)

    # For complete information about all accepted crs_str formats, see the
    # documentation for the CRS constructor:
    # https://pyproj4.github.io/pyproj/stable/api/crs/crs.html#pyproj.crs.CRS.__init__
    # The CRS constructor calls proj_create() from the PROJ library for some
    # CRS strings.  The documentation for proj_create() provides more
    # information about accepted strings:
    # https://proj.org/development/reference/functions.html#c.proj_create.

    if crs is None:
        # Use the CRS of the first dataset in the request as the target CRS if
        # none was specified.
        target_crs = dsc[list(datasets.keys())[0]].crs
    else:
        target_crs = pyproj.crs.CRS(crs)

    sub_points = SubsetMultiPoint(points, target_crs)

    try:
        request = DataRequest(
            dsc, datasets, date_start, date_end, sub_points, target_crs, None,
            interp_method, REQ_POINT, req_md
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    req_handler = DataRequestHandler()
    res_path = req_handler.fulfillRequestSynchronous(request, output_dir)

    return FileResponse(res_path, filename=res_path.name)

