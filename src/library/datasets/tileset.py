
import rasterio
import pandas as pd
import geopandas as gpd
import shapely.geometry as sg
from rioxarray import open_rasterio, merge
import xarray


class TileSet:
    """
    Implements a high-level interface to geospatial data stored as a local,
    on-disk collection of contiguous tiles.
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

    def getTilePaths(self, subset_geom, request_fpattern):
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

        polys = self.polys
        if request_fpattern is not None:
            tile_match = [request_fpattern in path.name for path in self.fpaths]
            # Not every day will have data, so skip if no tiles match.
            if not any(tile_match):
                return None
            polys = polys[tile_match]

        idxs = polys.intersects(subset_geom.geom.unary_union)

        return self.fpaths[idxs]

    def getRaster(self, subset_geom, request_fpattern=None):
        """
        Returns an xarray.DataArray containing a mosaic of the tiles required
        to cover the given subset geometry.

        subset_geom: An instance of SubsetGeom.
        """
        fpaths = self.getTilePaths(subset_geom, request_fpattern)

        if fpaths is None:
            return None
        
        tiles = []
        for fpath in fpaths:
            tiles.append(open_rasterio(fpath, masked=True))

        if len(tiles) > 0 and not(isinstance(tiles[0], xarray.DataArray)):
            raise TypeError(
                f'Expected xarray.DataArray; instead got {type(tiles[0])}.'
            )

        inter_merged = []
        i = 0
        while i < len(tiles):
            j = i + 4
            if j > len(tiles):
                j = len(tiles)

            inter_merged.append(merge.merge_arrays(tiles[i:j]))

            i += 4

        mosaic = merge.merge_arrays(inter_merged)

        return mosaic

