
from abc import ABC, abstractmethod
from collections.abc import Sequence, Mapping
import geopandas as gpd
import geojson
import shapely.geometry as sg


class SubsetGeom(ABC):
    """
    Provides a CRS-aware geometry object (either a polygon or set of points)
    for use in dataset operations.  Base class for concrete geometry types.
    """
    def __init__(self, geom_spec=None, crs_str=None):
        """
        Creates a new SubsetGeom.  Although the arguments are optional, empty
        SubsetGeoms should not be created by client code.

        geom_spec: A GeoJSON string, dictionary, or geojson object
            representing a polygon or multi-point geometry.
        crs_str: A string representing the CRS of the geometry.
        """
        self.geom = None

        if geom_spec is None and crs_str is None:
            return

        if geom_spec is None or crs_str is None:
            raise Exception(
                'SubsetGeom requires both a geometry specification and a CRS.'
            )

        if isinstance(geom_spec, str):
            # Interpret strings as GeoJSON strings.
            geom_dict = geojson.loads(geom_spec)
            coords = self._getCoordsFromGeomDict(geom_dict)
        elif isinstance(geom_spec, Sequence):
            # Other sequence types are interpreted as a sequence of coordinate
            # pairs.
            coords = geom_spec
        elif isinstance(geom_spec, Mapping):
            # Otherwise, assume we have GeoJSON mapping (dict, e.g.).
            coords = self._getCoordsFromGeomDict(geom_spec)
        else:
            raise Exception(
                'Unsupported type for instantiating a SubsetGeometry.'
            )

        # For complete information about all accepted crs_str formats, see the
        # documentation for CRS.from_user_input():
        # https://pyproj4.github.io/pyproj/stable/api/crs/crs.html#pyproj.crs.CRS.from_user_input
        # CRS.from_user_input() in turn calls the CRS constructor, which then
        # calls proj_create() from the PROJ library for some CRS strings.  The
        # documentation for proj_create() provides more information about
        # accepted strings:
        # https://proj.org/development/reference/functions.html#c.proj_create.

        self._initGeometry(coords, crs_str)

    @abstractmethod
    def _getCoordsFromGeomDict(self, geom_dict):
        """
        Extracts the coordinates list from a GeoJSON geometry dictionary.
        """
        pass

    @abstractmethod
    def _initGeometry(self, coords, crs_str):
        """
        Initializes the internal geometry representation.
        """
        pass

    @abstractmethod
    def _convertToJson(self):
        pass

    @property
    def json(self):
        """
        Returns the GeoJSON representation of this SubsetGeom as a
        dictionary/geojson geometry object.
        """
        return self._convertToJson()

    @property
    def crs(self):
        """
        Returns a pyproj CRS object representing the CRS of this polygon.
        """
        return self.geom.crs

    def reproject(self, target_crs):
        """
        Returns a new SubsetGeom with the geometric feature(s) transformed to
        the target CRS.  The source SubsetGeom is not modified.

        target_crs: A pyproj CRS object representing the target CRS.
        """
        transformed_sg = type(self)()
        transformed_sg.geom = self.geom.to_crs(target_crs)

        return transformed_sg


class SubsetPolygon(SubsetGeom):
    def __init__(self, geom_spec=None, crs_str=None):
        super().__init__(geom_spec, crs_str)

    def _getCoordsFromGeomDict(self, geom_dict):
        """
        Extracts the coordinates list from a GeoJSON geometry dictionary.
        """
        if geom_dict['type'] != 'Polygon':
            raise ValueError(
                'Invalid GeoJSON geometry type for initializing a '
                'SubsetPolygon: "{0}".'.format(geom_dict['type'])
            )

        return geom_dict['coordinates'][0]

    def _initGeometry(self, coords, crs_str):
        sh_poly = sg.Polygon(coords)
        self.geom = gpd.GeoSeries([sh_poly], crs=crs_str)

    def _convertToJson(self):
        f_dict = geojson.loads(self.geom.to_json())

        return f_dict['features'][0]['geometry']


class SubsetMultiPoint(SubsetGeom):
    def _getCoordsFromGeomDict(self, geom_dict):
        """
        Extracts the coordinates list from a GeoJSON geometry dictionary.
        """
        if geom_dict['type'] != 'MultiPoint':
            raise ValueError(
                'Invalid GeoJSON geometry type for initializing a '
                'SubsetMultiPoint: "{0}".'.format(geom_dict['type'])
            )

        return geom_dict['coordinates']

    def _initGeometry(self, coords, crs_str):
        sh_multi = sg.MultiPoint(coords)
        self.geom = gpd.GeoSeries(sh_multi.geoms, crs=crs_str)

    def _convertToJson(self):
        f_dict = geojson.loads(self.geom.to_json())

        coords = [
            p['geometry']['coordinates'] for p in f_dict['features']
        ]
        
        return geojson.MultiPoint(coords)

