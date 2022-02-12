
import geopandas as gpd
import geojson
import shapely.geometry as sg


# Geometry type constants.
POLYGON = 0
MULTIPOINT = 1


class SubsetGeom:
    """
    Provides a CRS-aware geometry object (either a polygon or set of points)
    for use in dataset operations.
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
        self.geom_type = None

        if geom_spec is None and crs_str is None:
            return

        if geom_spec is None or crs_str is None:
            raise Exception(
                'SubsetGeom requires both a geometry specification and a CRS.'
            )

        if isinstance(geom_spec, str):
            geom_dict = geojson.loads(geom_spec)
        else:
            geom_dict = geom_spec

        if geom_dict['type'] == 'Polygon':
            sh_poly = sg.Polygon(geom_dict['coordinates'][0])
            self.geom = gpd.GeoSeries([sh_poly], crs=crs_str)
            self.geom_type = POLYGON
        elif geom_dict['type'] == 'MultiPoint':
            sh_multi = sg.MultiPoint(geom_dict['coordinates'])
            self.geom = gpd.GeoSeries(sh_multi.geoms, crs=crs_str)
            self.geom_type = MULTIPOINT
        else:
            raise ValueError(
                'Unsupported geometry type: "{0}"'.format(geom_dict['type'])
            )

    @property
    def gj_dict(self):
        """
        Returns the GeoJSON representation of this SubsetGeom as a
        dictionary/geojson geometry object.
        """
        f_dict = geojson.loads(self.geom.to_json())

        if self.geom_type == POLYGON:
            res = f_dict['features'][0]['geometry']
        elif self.geom_type == MULTIPOINT:
            coords = [
                p['geometry']['coordinates'] for p in f_dict['features']
            ]
            res = geojson.MultiPoint(coords)

        return res

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
        transformed_sg = SubsetGeom()
        transformed_sg.geom = self.geom.to_crs(target_crs)
        transformed_sg.geom_type = self.geom_type

        return transformed_sg

