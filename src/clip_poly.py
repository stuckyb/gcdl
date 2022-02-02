
import geopandas as gpd
import geojson
import shapely.geometry as sg


class ClipPolygon:
    """
    Provides a CRS-aware clipping polygon for use in dataset operations.
    """
    def __init__(self, poly_spec, crs_str):
        """
        poly_spec: A GeoJSON string, dictionary, or geojson Polygon
            representing the clipping polygon.
        crs_str: A string representing the CRS of the polygon.
        """
        if isinstance(poly_spec, str):
            poly_dict = geojson.loads(poly_spec)
        else:
            poly_dict = poly_spec

        sh_poly = sg.Polygon(poly_dict['coordinates'][0])
        self.poly = gpd.GeoSeries([sh_poly], crs=crs_str)

    @property
    def gj_dict(self):
        """
        Returns the GeoJSON representation of this polygon as a
        dictionary/geojson Polygon object.
        """
        f_dict = geojson.loads(self.poly.to_json())
        return f_dict['features'][0]['geometry']

    @property
    def crs(self):
        """
        Returns a pyproj CRS object representing the CRS of this polygon.
        """
        return self.poly.crs

