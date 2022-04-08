
from pathlib import Path
import os.path
import uuid
import csv
import time
import geojson
from subset_geom import SubsetMultiPoint, SubsetPolygon


class DataUploadCache:
    """
    Implements an on-disk cache for uploaded geospatial data.
    """
    # Define valid x column names for tabular point data.  Column names are not
    # case-sensitive.
    x_colnames = ('x', 'long', 'longitude')

    # Define valid y column names for tabular point data.  Column names are not
    # case-sensitive.
    y_colnames = ('y', 'lat', 'latitude')

    def __init__(
        self, cachedir, max_file_size, retention_time=14400, chunk_size=1024
    ):
        """
        cachedir (str or Path): The on-disk storage location.
        max_file_size (int): Maximum file size to accept, in bytes.
        retention_time (int): Maximum file retention time, in seconds (default:
            4 hours) since the last time a cached geometry was accessed.
        chunk_size (int): The chunk size, in bytes, for reading uploaded data
            (default: 1 KB).
        """
        self.cachedir = Path(cachedir)
        self.maxsize = max_file_size
        self.maxtime = retention_time
        self.chunk_size = chunk_size

    def addFile(self, fdata, fname):
        """
        Saves uploaded data in the cache and returns a GUID for the uploaded
        data.

        fdata: A file-like object.
        fname: The name of the original file.
        """
        guid = str(uuid.uuid4())
        ext = os.path.splitext(fname)[1]
        fpath = self.cachedir / (guid + ext)

        byte_cnt = 0

        with open(fpath, 'wb') as fout:
            while chunk := fdata.read(self.chunk_size):
                byte_cnt += len(chunk)
                if byte_cnt > self.maxsize:
                    break

                fout.write(chunk)

        if byte_cnt > self.maxsize:
            fpath.unlink()
            raise Exception(
                'Uploaded file size exceeded maximum file size.'
            )

        return guid

    def contains(self, guid):
        """
        Returns true if the provided GUID is a valid reference to an object in
        the cache.
        """
        fpaths = list(self.cachedir.glob(guid + '*'))

        return len(fpaths) == 1

    def getPolygon(self, guid):
        pass

    def _readCSV(self, fpath):
        """
        Reads point data from a CSV file and returns a list of (x, y)
        float coordinates.  The CSV file must have one column named "x",
        "long", or "longitude" and one column named "y", "lat", or "latitude".
        Column names are not case-sensitive.
        """
        # Get the column names.
        with open(fpath) as fin:
            reader = csv.reader(fin)
            colnames = reader.__next__()

        # Determine the x and y columns.
        x_col = ''
        for colname in colnames:
            if colname.lower() in self.x_colnames:
                x_col = colname

        y_col = ''
        for colname in colnames:
            if colname.lower() in self.y_colnames:
                y_col = colname

        if x_col == '' or y_col == '':
            raise Exception('Could not find x and y columns in CSV file.')

        coords = []
        with open(fpath) as fin:
            reader = csv.DictReader(fin)

            for row in reader:
                x = float(row[x_col])
                y = float(row[y_col])

                coords.append((x, y))

        return coords

    def _extractGeoJSONCoords(self, geom):
        """
        Extracts coordinates from Point and MultiPoint GeoJSON objects and
        recursively from GeometryCollection, Feature, and FeatureCollection
        objects (including support for arbitrary nesting of compound objects).
        """
        coords = []

        if geom['type'] == 'Point':
            coords.append(geom['coordinates'])
        elif geom['type'] == 'MultiPoint':
            coords += geom['coordinates']
        elif geom['type'] == 'GeometryCollection':
            for c_geom in geom['geometries']:
                coords += self._extractGeoJSONCoords(c_geom)
        elif geom['type'] == 'Feature':
            coords += self._extractGeoJSONCoords(geom['geometry'])
        elif geom['type'] == 'FeatureCollection':
            for feature in geom['features']:
                coords += self._extractGeoJSONCoords(feature['geometry'])
        else:
            raise Exception(
                f"Unsupported GeoJSON geometry type for point data: "
                f"\"{geom['type']}\"."
            )

        return coords

    def _readGeoJSONPoints(self, fpath):
        """
        Extracts geographic points from a GeoJSON file and returns a list of
        (x, y) float coordinates.  Coordinates will be taken from Point and
        MultiPoint objects, including Point and MultiPoint objects embedded in
        GeometryCollection, Feature, and FeatureCollection objects.
        """
        with open(fpath) as fin:
            geom = geojson.load(fin)

        return self._extractGeoJSONCoords(geom)

    def getMultiPoint(self, guid, crs_str=None):
        """
        Given a valid GUID and appropriate cache data, returns a
        SubsetMultiPoint object containing the cached geometry data.  If the
        cached data does not include CRS information, a CRS string must be
        provided.  If crs_str is provided, it will take precedence over any CRS
        information included with the cached geometry data.

        guid (str): The GUID of cached geometry data.
        crs_str: The CRS of the cached geometry data.
        """
        fpaths = list(self.cachedir.glob(guid + '*'))

        if len(fpaths) == 0:
            raise Exception(f'No cached uploaded data found with GUID {guid}.')

        if len(fpaths) > 1:
            raise Exception(
                f'The provided uploaded data cache GUID, {guid}, does not '
                'appear to be unique.'
            )

        points = []
        data_crs = None

        # If the cached file has an extension, use that to infer file type.
        f_ext = fpaths[0].suffix
        try:
            if f_ext == '.csv':
                    points = self._readCSV(fpaths[0])
            elif f_ext == '.json' or f_ext == '.geojson':
                    points = self._readGeoJSONPoints(fpaths[0])
        except:
            raise Exception(
                f'Could not parse uploaded geometry object at {guid}.'
            )
 
        # If inferring the file type failed, try each file format directly.
        if len(points) == 0:
            try:
                points = self._readCSV(fpaths[0])
            except:
                pass

            if len(points) == 0:
                try:
                    points = self._readGeoJSONPoints(fpaths[0])
                except:
                    pass

        if len(points) == 0:
            raise Exception(f'No uploaded point data found for GUID {guid}.')
        
        if crs_str is None:
            crs_str = data_crs

        if crs_str is None:
            raise Exception('No CRS string provided for multi-point data.')

        geom = SubsetMultiPoint(points, crs_str)

        return geom

    def clean(self):
        """
        Deletes files from the cache that were last accessed longer ago than
        the maximum retention time.
        """
        now = time.time()

        for fpath in self.cachedir.iterdir():
            if fpath.is_file():
                atime = fpath.stat().st_atime
                if (now - atime) > self.maxtime:
                    fpath.unlink()

    def getStats(self):
        """
        Returns a tuple containing
        (total number of files in the cache, total cache size (in bytes)).
        """
        f_cnt = 0
        t_size = 0

        for fpath in self.cachedir.iterdir():
            if fpath.is_file():
                f_cnt += 1
                t_size += fpath.stat().st_size
            
        return (f_cnt, t_size)

