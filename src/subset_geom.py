
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
    def __init__(self, geom_spec, crs_str):
        """
        geom_spec: A GeoJSON string, dictionary, or geojson object
            representing a polygon or multi-point geometry.
        crs_str: A string representing the CRS of the geometry.
        """
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

