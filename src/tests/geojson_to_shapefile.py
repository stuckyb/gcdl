#!/usr/bin/python

# Simple utility script for converting a GeoJSON FeatureCollection to a
# shapefile.

import sys
import shapefile
import geojson


if len(sys.argv) != 3:
    exit(f'Usage: {sys.argv[0]} GEOJSON_IN SHAPEFILE_OUT')

with open(sys.argv[1]) as fin:
    gj = geojson.load(fin)

# Get the field/property names.
fnames = [fname for fname in gj['features'][0]['properties']]

with shapefile.Writer(sys.argv[2]) as w:
    # Define the fields.  For simplicity, just treat everything as text.
    for fname in fnames:
        w.field(fname, 'C')

    for feature in gj['features']:
        # Get the properties from the feature and write them to the shapefile.
        propvals = [feature['properties'][fname] for fname in fnames]
        w.record(*propvals)

        # Write the geometry.
        w.shape(feature['geometry'])

