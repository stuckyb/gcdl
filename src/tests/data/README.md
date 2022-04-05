
This directory contains data required for running the automated tests.

## `tiles/`

This folder contains a raster dataset using WGS84 lat/long coordinates (EPSG:4326) with bounding box corners at (-100, 40) (top left) and (-98, 38) (lower right).  Each quadrant of the dataset contains a unique constant value.  The files are as follows.

* `tile_0.tif`
  * bounds: (-100, 40), (-99, 39)
  * value: 4
* `tile_1.tif`: 
  * bounds: (-99, 40), (-98, 39)
  * value: 3
* `tile_2.tif`: 
  * bounds: (-100, 39), (-99, 39)
  * value: 5
* `tile_3.tif`: 
  * bounds: (-99, 39), (-98, 38)
  * value: 8
* `tile_mosaic.tif`: all 4 tiles in a single layer


## `upload_cache/`

This folder contains files for testing the upload cache and geometry file parsing.


