
import rasterio
import pandas as pd
import geopandas as gpd
import shapely.geometry as sg
from rioxarray import open_rasterio, merge
import xarray


class TileSet:
    """
    Implements a high-level interface to geospatial data stored as a local,
    on-disk collection of contiguous tiles.  Currently, only datasets with one
    file per tile are supported.
    """
    def __init__(self, files, crs):
        """
        files: A sequence of paths to the tile files.
        """
        fpaths = []
        polys = []

        # Extract the spatial coverage of each tile.
        for fpath in files:
            fh = rasterio.open(fpath)
            bbox = fh.bounds

            fpaths.append(fpath)

            coords = [
                [bbox.left, bbox.top], [bbox.right, bbox.top],
                [bbox.right, bbox.bottom], [bbox.left, bbox.bottom],
                [bbox.left, bbox.top]
            ]
            polys.append(sg.Polygon(coords))

        self.polys = gpd.GeoSeries(polys, crs=crs)
        self.fpaths = pd.Series(fpaths)

    @property
    def crs(self):
        """
        Returns a pyproj CRS object representing the CRS of this TileSet.
        """
        return self.polys.crs

    @property
    def bounds(self):
        """
        Returns a sequence containing the geographic bounding box of the entire
        tile set as (minx, miny, maxx, maxy).
        """
        return self.polys.total_bounds

    def getTilePaths(self, subset_geom):
        """
        Returns a Series containing the file paths of the tiles required to
        cover the given subset geometry.

        subset_geom: An instance of SubsetGeom.
        """
        if not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'CRS of the subset geometry does not match the CRS of the '
                'data tiles.'
            )

        idxs = self.polys.intersects(subset_geom.geom.unary_union)

        return self.fpaths[idxs]

    def getRaster(self, subset_geom):
        """
        Returns an xarray.DataArray containing a mosaic of the tiles required
        to cover the given subset geometry.

        subset_geom: An instance of SubsetGeom.
        """
        fpaths = self.getTilePaths(subset_geom)
        tiles = []
        
        for fpath in fpaths:
            tiles.append(open_rasterio(fpath, masked=True))

        if len(tiles) > 0 and not(isinstance(tiles[0], xarray.DataArray)):
            raise TypeError(
                f'Expected xarray.DataArray; instead got {type(tiles[0])}.'
            )

        mosaic = merge.merge_arrays(tiles)

        return mosaic

