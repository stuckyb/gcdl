# USDA-ARS Geospatial Common Data Library (GeoCDL)

## Installing the GeoCDL

1. Make sure you have a recent release of Python 3 installed.
1. Clone this git repository.
1. Run `pip install -r requirements.txt`.


## Running the GeoCDL

1. Move to the `src` directory (`cd src`).
1. Run `uvicorn api_main:app --reload`.
1. API endpoints will be available at [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (e.g., [http://127.0.0.1:8000/ds_info?id=DaymetV4](http://127.0.0.1:8000/ds_info?id=DaymetV4)).
1. API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).


## Using the GeoCDL

Results for different combinations of optional spatial parameters (output structure column is hypothetical at the moment):

| *bbox* or *points*	| *crs*	| *resolution*	| Outcome 	| Output raster strucure 	|
| :---:					| :---:	| :---:			|  :---		| :---						|
| 						|		|				| Full extent of each raster layer is returned in native CRS and spatial resolution. | Can combine variables and/or time, but not datasets. | 
| x						|		|				| Each layer is spatially subsetted but not reprojected in CRS or spatial resolution. *bbox*/*points* assumed to be defined in the first dataset's CRS.| Can combine variables and/or time, but not datasets. |
| x						| x		|				| Each layer is spatially subsetted and reprojected to *crs*, but the spatial resolutions are not changed. *bbox*/*points* assumed to be defined in *crs*.| Can combine variables and/or time, but not datasets. |
| x						|		| x				| Each layer is spatially subsetted and reprojected to *resolution* and the first dataset's CRS, assuming *resolution* is in the units of that CRS. *bbox*/*points* assumed to be defined in that same CRS.| Can combine variables and/or time, AND datasets. |
| x						| x		| x				| Each layer is spatially subsetted and reprojected to *resolution* and *crs*, assuming *resolution* is in the units of *crs*. *bbox*/*points* assumed to be defined in *crs*.| Can combine variables and/or time, AND datasets. |
| 						| x		|				| Full extent of each raster layer is returned in native spatial resolution, but reprojected to *crs*. | Can combine variables and/or time, but not datasets. |
| 						|		| x				| Full extent of each raster layer is reprojected to *resolution* and the first dataset's CRS, assuming *resolution* is in the units of that CRS. *bbox*/*points* assumed to be defined in that same CRS. | Can combine variables and/or time, AND datasets. |
| 						| x		| x				| Full extent of each raster layer is reprojected to *resolution* and *crs*, assuming *resolution* is in the units of *crs*. *bbox*/*points* assumed to be defined in *crs*. | Can combine variables and/or time, AND datasets. |