
from library.catalog import DatasetCatalog
from library.datasets import PRISM, DaymetV4, GTOPO, SRTM, MODIS_NDVI
from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pathlib import Path
import pyproj
from subset_geom import SubsetPolygon, SubsetMultiPoint
from api_core import DataRequest, REQ_RASTER, REQ_POINT
from api_core import DataRequestHandler
from api_core.helpers import (
    parse_datasets_str, parse_clip_bounds, parse_points, get_request_metadata
)


dsc = DatasetCatalog('local_data')
dsc.addDatasetsByClass(PRISM, DaymetV4, GTOPO, SRTM, MODIS_NDVI)

# Directory for serving output files.
output_dir = Path('output')


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
    if dsid not in dsc:
        raise HTTPException(
            status_code=404, detail=f'Invalid dataset ID: {dsid}'
        )

    return dsc[dsid].getMetadata()


@app.get(
    '/subset_polygon', tags=['Dataset operations'],
    summary='Requests a geographic subset (which can be the full dataset) of '
    'one or more variables from one or more geospatial datasets.'
)
async def subset_polygon(
    req: Request,
    datasets: str = Query(
        ..., title='Datasets and variables', description='The datasets and '
        'variables to include, specified as '
        '"DATASET_ID:VARNAME[,VARNAME...][;DATASET_ID:VARNAME[,VARNAME...]...]. '
        'Examples: "PRISM:tmax", "PRISM:tmax;DaymetV4:tmax,prcp".'
    ),
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
    clip: list = Depends(parse_clip_bounds),
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
    req_md = get_request_metadata(req)

    # For complete information about all accepted crs_str formats, see the
    # documentation for the CRS constructor:
    # https://pyproj4.github.io/pyproj/stable/api/crs/crs.html#pyproj.crs.CRS.__init__
    # The CRS constructor calls proj_create() from the PROJ library for some
    # CRS strings.  The documentation for proj_create() provides more
    # information about accepted strings:
    # https://proj.org/development/reference/functions.html#c.proj_create.

    try:
        datasets = parse_datasets_str(datasets, dsc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    datasets: str = Query(
        ..., title='Datasets and variables', description='The datasets and '
        'variables to include, specified as '
        '"DATASET_ID:VARNAME[,VARNAME...][;DATASET_ID:VARNAME[,VARNAME...]...]. '
        'Examples: "PRISM:tmax", "PRISM:tmax;DaymetV4:tmax,prcp".'
    ),
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
    points: list = Depends(parse_points),
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
    req_md = get_request_metadata(req)

    # For complete information about all accepted crs_str formats, see the
    # documentation for the CRS constructor:
    # https://pyproj4.github.io/pyproj/stable/api/crs/crs.html#pyproj.crs.CRS.__init__
    # The CRS constructor calls proj_create() from the PROJ library for some
    # CRS strings.  The documentation for proj_create() provides more
    # information about accepted strings:
    # https://proj.org/development/reference/functions.html#c.proj_create.

    try:
        datasets = parse_datasets_str(datasets, dsc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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

