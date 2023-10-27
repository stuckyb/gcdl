
from fastapi import (
    FastAPI, Query, HTTPException, Depends, Request, UploadFile, File
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pathlib import Path
import logging
import time
import yaml

from api_core import DataRequest, REQ_RASTER, REQ_POINT
from api_core import DataRequestHandler
from api_core import DataRequestOutput
from api_core.helpers import (
    parse_datasets_str, parse_clip_bounds, parse_coords, 
    get_request_metadata, assume_crs, get_target_crs
)
from library.catalog import DatasetCatalog
from library.datasets import (
    PRISM, DaymetV4, GTOPO, SRTM, MODIS_NDVI, NASS_CDL, VIP, NLCD, Timeout, 
    Soilgrids250mV2, SMAP_HB1km, RAPV3
)
from subset_geom import SubsetPolygon, SubsetMultiPoint
from api_core.upload_cache import DataUploadCache


dsc = DatasetCatalog('../local_data')
dsc.addDatasetsByClass(
    PRISM, DaymetV4, GTOPO, SRTM, MODIS_NDVI, NASS_CDL, VIP, NLCD, Timeout,
    Soilgrids250mV2, SMAP_HB1km, RAPV3
)

# Directory for serving output files.
output_dir = Path('../output')

# Location of access log files.
access_log_path = Path('../logs/access.log')

# Data upload cache.
ul_cache = DataUploadCache('../upload', 1024 * 1024)

# Configure logging and get requests logger.
with open('logging_config.yaml') as fin:
    logging_conf = yaml.safe_load(fin)
logging_conf['handlers']['file']['filename'] = access_log_path
logging.config.dictConfig(logging_conf)
logger = logging.getLogger('api_main')

app = FastAPI(
    title='Geospatial Common Data Library REST API',
    description='Welcome to the interactive documentation for USDA-ARS\'s '
    'Geospatial Common Data Library (GeoCDL) REST API! Here, you can see all '
    'available API endpoints and directly experiment with GeoCDL API calls. '
    'Note that most users will find it easier to access the GeoCDL via one of '
    'our higher-level interfaces, including a web GUI interface and packages '
    'for Python and R.'
)

@app.middleware('http')
async def log_request(request: Request, call_next):
    """
    A "middleware" function that logs details for every incoming API request.
    Log entries for requests follow the "Combined Log Format" standard in
    common use for HTTP servers (see, e.g.,
    https://httpd.apache.org/docs/2.4/logs.html), with one non-standard, extra
    field at the end indicating the total time required to answer the request,
    in seconds.
    """
    req_time = time.time()
    req_time_str = time.strftime('%d/%b/%Y:%H:%M:%S %z', time.localtime())

    response = await call_next(request)

    # Some notes on how information for the log entry is retrieved.  Getting
    # the HTTP version takes advantage of Starlette Request objects acting as
    # mappings that pass keys on to the underlying scope object.  This does not
    # seem to be described well in the documentation, but see
    # https://github.com/encode/starlette/blob/master/starlette/requests.py.
    # The scope key for HTTP version also mirrors that used by uvicorn; see
    # httptools_impl.py in the uvicorn source code.  Note that the "scope"
    # dictionary is also a requirement of the ASGI specification, although
    # protocol-specific keys are not mandated
    # (https://asgi.readthedocs.io/en/latest/specs/main.html).
    if 'user-agent' in request.headers:
        ua_str = '"' + request.headers['user-agent'] + '"'
    else:
        ua_str = '-'
    logger.info('{0}:{1} - - [{2}] "{3} {4} HTTP/{5}" {6} - - {7} {8}'.format(
        request.client.host, request.client.port, req_time_str, request.method,
        request.url, request['http_version'], response.status_code, ua_str,
        time.time() - req_time
    ))

    return response

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


@app.post(
    '/upload_geom', tags=['Geometry uploads'],
    summary='Upload a geometry file (either multipoint or polygon).'
)
def upload_geom(
    geom_file: UploadFile = File(
        ..., title='Uploaded file',
        description='A supported file type containing geometry data (either '
        'point or polygon).  For point data, the following file formats are '
        'supported: CSV (comma-separated values), shapefiles, and GeoJSON.  '
        'For polygon data, the following file formats are supported: '
        'shapefiles and GeoJSON.  CSV files must contain a column named "x", '
        '"long", or "longitude" (not case sensitive) and a column named "y", '
        '"lat", or "latitude" (not case sensitive).  Shapefiles must be '
        'uploaded in a single ZIP archive.  Supported GeoJSON types for point '
        'data uploads are "Point", "MultiPoint", "GeometryCollection", '
        '"Feature", and "FeatureCollection".  Supported GeoJSON types for '
        'polygon data uploads are "Polygon", "MultiPolygon", '
        '"GeometryCollection", "Feature", and "FeatureCollection".  For '
        'polygon data, GeoJSON objects and shapefiles with more than one '
        'polygon definition are not supported (e.g., "MultiPolygon" objects '
        'must only contain one polygon).  "Holes" in polygons will be ignored.'
    )
):
    try:
        guid = ul_cache.addFile(geom_file.file, geom_file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {'geom_guid': guid}


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
    dates: str = Query(
        None, title='Dates to include in request',
        description='The dates for which to request data. Dates must be '
        'specified as strings, where "YYYY" means extract annual data, '
        '"YYYY-MM" is for monthly data, and "YYYY-MM-DD" is for daily data. '
        'Date ranges can be specified using a colon, as in "YYYY:YYYY", '
        '"YYYY-MM:YYYY-MM", or "YYYY-MM-DD:YYYY-MM-DD". Leading 0s in "MM" '
        'and "DD" are optional (e.g., both "2020-01-01" and "2020-1-1" are '
        'valid). Multiple dates and/or date ranges should be separated by '
        'commas. For example: "2000-2010", "2000-1,2005-1,2010-1:2010-6", '
        '"2000-01-01:2000-04-31". Dates can be omitted for non-temporal data '
        'requests. For more complicated, recurring date patterns, use the '
        '"years", "months", and "days" parameters.'
    ),
    years: str = Query(
        None, title='Years to include in request',
        description='Years to subset data. Can be expressed as ranges and '
        'sequences, such as "2004-2005,2009" or "2000-2010+2", which is '
        'interpreted as every other year starting with 2000. Ranges are '
        'inclusive of their endpoints unless the endpoint does not correspond '
        'with the step size increment. If "dates" is also provided, "years" '
        '(and "months" and "days") will be ignored.'
    ),
    months: str = Query(
        None, title='Months to include in request',
        description='Months to include for each year of the data request. '
        'Only valid if "years" is also specified. Accepts values 1-12. Can be '
        'expressed as ranges and sequences, such as "1-3,5,9-12" or "1-12+2", '
        'which is interpreted as every other month. Ranges are inclusive of '
        'their endpoints unless the endpoint does not correspond with the '
        'step size increment.'
    ),
    days: str = Query(
        None, title='Days of year or month to include in request', 
        description='Only valid if "years" or "years" and "months" are also '
        'specified.  If only "years" is specified, "days" is interpreted as '
        'the days of each year (starting from 1) to include in the request. '
        'If "years" and "months" are both specified, "days" is interpreted as '
        'the days of each month (starting from 1) to incude in the request. '
        'The special value "N" represents the last day of a month or year. '
        'Can be expressed as ranges and sequences, such as '
        '"1-100,200-230,266-366", "1-N", or "10-N+10", which is interpreted '
        'as every 10th day of the year or month. Ranges are inclusive of '
        'their endpoints unless the endpoint does not correspond with the '
        'step size increment. Required if "years" or "years" and "months" are '
        'specified and daily data are desired.'
    ), 
    hours: str = Query(
        None, title='Hours of day to include in request',
        description='Only valid for daily requests of datasets with sub-daily '
        'temporal resolutions (parameter is otherwise ignored). Accepts integer ' 
        'values between 0 and 23. Can be expressed as ranges or sequences, such '
        'as "0-6" or "0,12". If not all requested hours are available, only the '
        'hours available will be returned. "hours" is required for daily requests '
        'of datasets with sub-daily data. '
    ),
    grain_method: str = Query(
        None, title='Matching specified date grain to dataset date grains.',
        description='How to handle scenario of requested date grains not '
        'matching date grains of each requested dataset. If "strict" (default), '
        'an error will be returned. If "skip", the dataset will be skipped. '
        'If "coarser", then only coarser grains will be returned. If "finer", ' 
        'then only finer grains will be returned. If "any", then any available '
        'grain will be returned, with coarser having higher priority over finer.'
        'Non-temporal datasets are always returned.'
    ),
    validate_method: str = Query(
        None, title='Validation method for requested date range.',
        description='How to handle requested dates outside of requested dataset '
        'available data range. If "strict" (default), '
        'an error will be returned. If "overlap", the requested dates will be '
        'truncated to the date range available in all requested datasets. If '
        '"all", then the requested dates will be truncated to the available date '
        'range per dataset. Non-temporal datasets are always returned.'
    ),
    clip: list = Depends(parse_clip_bounds),
    geom_guid: str = Query(
        '', title='GUID of uploaded geometry data',
        description='The GUID of previously uploaded polygon geometry '
        'data.  If polygon coordinates are provided as a query parameter, '
        'geom_guid will be ignored.'
    ),
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
        'and/or spatial resolution are provided. If two methods are provided '
        '(comma separated, e.g. "bilinear,nearest"), the first will be used '
        'for continuous variables and the second will be used for categorical '
        'variables. An error will be returned when methods requested for '
        'categorical variables are not applicable (any besides "nearest" or'
        '"mode").', 
    ),
    output_format: str = Query(
        None, title='Output file format.',
        description='The file format of the gridded output. Available options '
        'are: "geotiff", which will be one file per variable and time step, '
        'or "netcdf", which will be one file with a time dimension per '
        'variable.'
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

        # Assume the user geometry CRS from request info
        # in case not provided with uploaded geometry
        assumed_crs = assume_crs(dsc, datasets, crs)

        if clip != '':
            clip_geom = SubsetPolygon(clip, assumed_crs)
        elif geom_guid != '':
            clip_geom = ul_cache.getPolygon(geom_guid, assumed_crs)
        else:
            raise ValueError(
                'One of clip or geom_guid needs to be provided.'
            )

        # Set the target CRS, if applicable
        target_crs = get_target_crs(crs, resolution, clip_geom)

        request = DataRequest(
            dsc, datasets, dates, years, months, days, hours, grain_method, 
            validate_method, clip_geom, target_crs, resolution, 
            resample_method, REQ_RASTER, output_format, req_md
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    req_handler = DataRequestHandler()
    res_data = req_handler.fulfillRequestSynchronous(request)

    req_output = DataRequestOutput()
    res_path = req_output.writeRequestedData(request, res_data, output_dir)

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
    dates: str = Query(
        None, title='Dates to include in request',
        description='The dates for which to request data. Dates must be '
        'specified as strings, where "YYYY" means extract annual data, '
        '"YYYY-MM" is for monthly data, and "YYYY-MM-DD" is for daily data. '
        'Date ranges can be specified using a colon, as in "YYYY:YYYY", '
        '"YYYY-MM:YYYY-MM", or "YYYY-MM-DD:YYYY-MM-DD". Leading 0s in "MM" '
        'and "DD" are optional (e.g., both "2020-01-01" and "2020-1-1" are '
        'valid). Multiple dates and/or date ranges should be separated by '
        'commas. For example: "2000-2010", "2000-1,2005-1,2010-1:2010-6", '
        '"2000-01-01:2000-04-31". Dates can be omitted for non-temporal data '
        'requests. For more complicated, recurring date patterns, use the '
        '"years", "months", and "days" parameters.'
    ),
    years: str = Query(
        None, title='Years to include in request',
        description='Years to subset data. Can be expressed as ranges and '
        'sequences, such as "2004-2005,2009" or "2000-2010+2", which is '
        'interpreted as every other year starting with 2000. Ranges are '
        'inclusive of their endpoints unless the endpoint does not correspond '
        'with the step size increment.'
    ),
    months: str = Query(
        None, title='Months to include in request',
        description='Months to include for each year of the data request. '
        'Only valid if "years" is also specified. Accepts values 1-12. Can be '
        'expressed as ranges and sequences, such as "1-3,5,9-12" or "1-12+2", '
        'which is interpreted as every other month. Ranges are inclusive of '
        'their endpoints unless the endpoint does not correspond with the '
        'step size increment.'
    ),
    days: str = Query(
        None, title='Days of year or month to include in request', 
        description='Only valid if "years" or "years" and "months" are also '
        'specified.  If only "years" is specified, "days" is interpreted as '
        'the days of each year (starting from 1) to include in the request. '
        'If "years" and "months" are both specified, "days" is interpreted as '
        'the days of each month (starting from 1) to incude in the request. '
        'The special value "N" represents the last day of a month or year. '
        'Can be expressed as ranges and sequences, such as '
        '"1-100,200-230,266-366", "1-N", or "10-N+10", which is interpreted '
        'as every 10th day of the year or month. Ranges are inclusive of '
        'their endpoints unless the endpoint does not correspond with the '
        'step size increment. Required if "years" or "years" and "months" are '
        'specified and daily data are desired.'
    ), 
    hours: str = Query(
        None, title='Hours of day to include in request',
        description='Only valid for daily requests of datasets with sub-daily '
        'temporal resolutions (parameter is otherwise ignored). Accepts integer ' 
        'values between 0 and 23. Can be expressed as ranges or sequences, such '
        'as "0-6" or "0,12". If not all requested hours are available, only the '
        'hours available will be returned. "hours" is required for daily requests '
        'of datasets with sub-daily data. '
    ),
    grain_method: str = Query(
        None, title='Matching specified date grain to dataset date grains.',
        description='How to handle scenario of requested date grains not '
        'matching date grains of each requested dataset. If "strict" (default), '
        'an error will be returned. If "skip", the dataset will be skipped. '
        'If "coarser", then only coarser grains will be returned. If "finer", ' 
        'then only finer grains will be returned. If "any", then any available '
        'grain will be returned, with coarser having higher priority over finer.'
        'Non-temporal datasets are always returned.'
    ),
    validate_method: str = Query(
        None, title='Validation method for requested date range.',
        description='How to handle requested dates outside of requested dataset '
        'available data range. If "strict" (default), '
        'an error will be returned. If "overlap", the requested dates will be '
        'truncated to the date range available in all requested datasets. If '
        '"all", then the requested dates will be truncated to the available date '
        'range per dataset. Non-temporal datasets are always returned.'
    ),
    points: str = Query(
        '', title='Geographic points', description='The x and y coordinates '
        'of point locations for extracting from the data, specified '
        'as "x1,y1;x2,y2..." or "(x1,y1),(x2,y2)...".  Coordinates are '
        'assumed to match the target CRS or the CRS of the first requested '
        'dataset if no target CRS is specified.'
    ),
    geom_guid: str = Query(
        '', title='GUID of uploaded geometry data',
        description='The GUID of previously uploaded multipoint geometry '
        'data.  If point coordinates are provided as a query parameter, '
        'geom_guid will be ignored.'
    ),
    crs: str = Query(
        None, title='Target coordinate reference system.',
        description='The target coordinate reference system (CRS) for the '
        'returned data, specified as an EPSG code.'
    ),
    interp_method: str = Query(
        None, title='Point interpolation method.',
        description='The interpolation method used for extracting point '
        'values. Available methods: "nearest" or "linear". Default is '
        '"nearest". If two methods are provided '
        '(comma separated, e.g. "bilinear,nearest"), the first will be used '
        'for continuous variables and the second will be used for categorical '
        'variables. An error will be returned when methods requested for '
        'categorical variables are not applicable ("linear").'
    ),
    output_format: str = Query(
        None, title='Output file format.',
        description='The file format of the point output. Available options '
        'are: "csv", "shapefile", or "netcdf". Each option will return one '
        'file.'
    )
):
    if points == '' and geom_guid == '':
        raise HTTPException(
            status_code=400, detail='No point data were provided.'
        )

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

        # Assume the user geometry CRS from request info
        # in case not provided with uploaded geometry
        assumed_crs = assume_crs(dsc, datasets, crs)
        
        if points != '':
            coords = parse_coords(points)
            sub_points = SubsetMultiPoint(coords, assumed_crs)
        elif geom_guid != '':
            sub_points = ul_cache.getMultiPoint(geom_guid, assumed_crs)
        else:
            raise ValueError(
                'One of points or geom_guid needs to be provided.'
            )

        # Set the target CRS, if applicable
        target_crs = get_target_crs(crs, None, sub_points)

        request = DataRequest(
            dsc, datasets, dates, years, months, days, hours, grain_method,
            validate_method, sub_points, target_crs, None, interp_method, 
            REQ_POINT, output_format, req_md
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    req_handler = DataRequestHandler()
    res_data = req_handler.fulfillRequestSynchronous(request)

    req_output = DataRequestOutput()
    res_path = req_output.writeRequestedData(request, res_data, output_dir)

    return FileResponse(res_path, filename=res_path.name)

