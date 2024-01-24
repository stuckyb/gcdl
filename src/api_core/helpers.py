
from fastapi import Query, HTTPException
from datetime import datetime, timezone
from pyproj.crs import CRS

def parse_datasets_str(datasets_str, ds_catalog):
    """
    Parses a string specifying datasets and variables.
    """
    ds_vars = {}
    for ds_spec in datasets_str.split(';'):
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

        if parts[0] not in ds_catalog:
            raise ValueError('Invalid dataset ID: {dsid}')

        ds_vars[parts[0]] = varnames

    return ds_vars

def parse_coords(coords_str):
    """
    Parses a semicolon-separated list of coordinates of the form
    "x1,y1;x2,y2..." or a comma-separated list of coordinates of the form
    "(x1,y1),(x2,y2)...'.
    """
    if coords_str[0] == '(':
        # Comma-separated coordinates.
        coord_strs = coords_str.split('),')
        coord_strs = [c[1:] for c in coord_strs]
        # Remove the trailing ')' from the last coordinate string.
        if coord_strs[-1][-1] == ')':
            coord_strs[-1] = coord_strs[-1][:-1]
        else:
            raise ValueError('Incorrect coordinate specification.')
    else:
        # Semicolon-separated coordinates.
        coord_strs = coords_str.split(';')

    coords = []
    for coord_str in coord_strs:
        parts = coord_str.split(',')
        if len(parts) != 2:
            raise ValueError('Incorrect coordinate specification.')

        try:
            parts = [float(part) for part in parts]
        except:
            raise ValueError('Incorrect coordinate specification.')

        coords.append(parts)

    return coords

def parse_clip_bounds(
    clip: str = Query(
        '', title='Clip boundary', description='Specifies the clip boundary '
        'for the subset operation.  The boundary can be specified in one of '
        'two ways: 1) The upper left and lower right corners of a '
        'bounding box for subsetting the data, specifed as a comma-separated '
        'list of the form "(UPPER_LEFT_X,UPPER_LEFT_Y),'
        '(LOWER_RIGHT_X,LOWER_RIGHT_Y)" or a semicolon-separated list of the '
        'form "UPPER_LEFT_X,UPPER_LEFT_Y;LOWER_RIGHT_X,LOWER_RIGHT_Y"; 2) A '
        'comma-separated or semicolon-separated list of coordinates defining '
        'the vertices of a clip polygon as in "(X1,Y1),(X2,Y2)..." or '
        '"X1,Y1;X2,Y2...".'
    )
):
    """
    Parses a clip boundary specification.
    """
    if clip == '':
        return ''

    try:
        coords = parse_coords(clip)
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

def get_request_metadata(req):
    """
    Generates a dictionary of basic metadata for an API request.
    """
    req_md = {
        'url': str(req.url),
        'datetime': datetime.now(timezone.utc).isoformat()
    }

    return req_md

def assume_crs(dsc, datasets, input_crs_str):
    """
    Determines what CRS to use for user geomtry if not specified
    in an uploaded file.
    """
    if input_crs_str is not None:
        assumed_crs = CRS(input_crs_str)
    else:
        # Use the CRS of the first dataset in the request 
        # as the target CRS 
        assumed_crs = dsc[list(datasets.keys())[0]].crs

    return assumed_crs

def get_target_crs(input_crs_str, resolution, user_geom):
    """
    Determines the target CRS 
    """

    # If crs parameter provided, use that. Else,
    # use the CRS of the user geometry, which is
    # the uploaded geometry CRS or that of the 
    # first dataset, that was decided above 
    # in the clip geometry.
    if input_crs_str is not None:
        target_crs = CRS(input_crs_str)
    else:
        target_crs = user_geom.geom.crs

    return target_crs



