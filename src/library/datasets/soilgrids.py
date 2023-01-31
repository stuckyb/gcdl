
from .gsdataset import GSDataSet
from pyproj.crs import CRS
import rioxarray
from subset_geom import SubsetMultiPoint
from owslib.wcs import WebCoverageService
import itertools
import re
import io


class Soilgrids250mV2(GSDataSet):
    def __init__(self, store_path):
        """
        store_path (Path): The location of remote dataset storage.
        """
        super().__init__('http://maps.isric.org/mapserv?map=/map/', '')

        # Basic dataset information.
        self.id = 'Soilgrids250mV2'
        self.name = 'SoilGrids — global gridded soil information'
        self.url = 'https://www.isric.org/explore/soilgrids'
        
        self.description = ('SoilGrids is a system for global digital soil '
        'mapping that uses state-of-the-art machine learning methods to map the spatial distribution '
        'of soil properties across the globe. SoilGrids prediction models are fitted using over 230000 '
        'soil profile observations from the WoSIS database and a series of environmental covariates. '
        'Covariates were selected from a pool of over 400 environmental layers from Earth observation '
        'derived products and other environmental information including climate, land cover and terrain '
        'morphology. The outputs of SoilGrids are global soil property maps at six standard depth '
        'intervals (according to the GlobalSoilMap IUSS working group and its specifications) at a '
        'spatial resolution of 250 meters.')
        self.provider_name = 'ISRIC - World Soil Information'
        self.provider_url = 'https://www.isric.org'

        # CRS information.
        # Sometimes written as EPSG:152160, but that is not an offical EPSG code
        # and not recognized in this CRS database
        self.crs = CRS.from_proj4('+proj=igh +datum=WGS84 +no_defs +towgs84=0,0,0') 

        # The grid size
        self.grid_size = 250
        self.grid_unit = 'meters'

        # The variables/layers/bands in the dataset.
        self.properties = {
            'bdod': 'Bulk density of the fine earch fraction [cg/cm3]',
            'cec': 'Cation exchange capacity of the soil at pH 7 [mmol(c)/kg]',
            'cfvo': 'Volumetric fraction of coarse fragments (> 2 mm) [cm3/dm3 (vol%)]',
            'clay': 'Proportion of clay particles (< 0.002 mm) in the fine earth fraction [g/kg]',
            'nitrogen': 'Total nitrogen (N) [cg/kg]',
            'phh2o': 'Soil pH in H2O [pHx10]',
            'sand': 'Proportion of sand particles (> 0.05 mm) in the fine earth fraction [g/kg]',
            'silt': 'Proportion of silt particles (≥ 0.002 mm and ≤ 0.05 mm) in the fine earth fraction [g/kg]',
            'soc': 'Soil organic carbon content in the fine earth fraction [dg/kg]',
            'ocs': 'Soil organic carbon stocks [t/ha]',
            'ocd': 'Organic carbon density [hg/m3]'
        }
        # The depth intervals
        self.depths = ['0-5cm','5-15cm','15-30cm','30-60cm','60-100cm','100-200cm']
        # The quantiles
        self.quantiles = {
            'mean': 'mean',
            'Q0.05': '5% quantile',
            'Q0.5': '50% quantile',
            'Q0.95': '95% quantile',
            'uncertainty': 'ratio between the inter-quantile range and the median'}
        # All combinations of Properties, Depth intervals, and Quantiles (PDQ)
        self.pdq_list = [list(self.properties.keys()), self.depths, list(self.quantiles.keys())]
        self.pdq_list = list(itertools.product(*self.pdq_list))
        self.var_names = ['{0}_{1}_{2}'.format(*pdq) for pdq in self.pdq_list]
        [print(pdq) for pdq in self.pdq_list]
        self.pdq_list = [[self.properties[pdq[0]], pdq[1], self.quantiles[pdq[2]]] for pdq in self.pdq_list]
        self.var_descriptions = ['{0} at {1} - {2}'.format(*pdq) for pdq in self.pdq_list]
        self.vars = dict(zip(self.var_names,self.var_descriptions))
        

    def getData(
        self, varname, date_grain, request_date, ri_method, subset_geom=None
    ):
        """
        varname: The variable to return.
        date_grain: The date granularity to return, specified as a constant in
            data_request.
        request_date: A data_request.RequestDate instance.  Since this is a
            non-temporal dataset, request dates are ignored.
        ri_method: The resample/interpolation method to use, if needed.
        subset_geom: An instance of SubsetGeom.  If the CRS does not match the
            dataset, an exception is raised.
        """
        if subset_geom is not None and not(self.crs.equals(subset_geom.crs)):
            raise ValueError(
                'Subset geometry CRS does not match dataset CRS.'
            )

        # Extract property name from varname (property_depth_quantile)
        propname = re.search('[^\W_]+',varname).group(0)
        
        fpath = 'https://maps.isric.org/mapserv?map=/map/{0}.map'.format(propname)
        wcs = WebCoverageService(fpath, version='2.0.1')

        sg_bounds = subset_geom.geom.total_bounds
        response = wcs.getCoverage(
            identifier=[varname], 
            crs="http://www.opengis.net/def/crs/EPSG/0/152160",
            subsets=[('X',sg_bounds[0],sg_bounds[2]), ('Y',sg_bounds[1],sg_bounds[3])], 
            resx=250, resy=250, 
            format='GEOTIFF_INT16')

        data = rioxarray.open_rasterio(io.BytesIO(response.read()))

        if isinstance(subset_geom, SubsetMultiPoint):
            # Interpolate all (x,y) points in the subset geometry.  For more
            # information about how/why this works, see
            # https://xarray.pydata.org/en/stable/user-guide/interpolation.html#advanced-interpolation.
            res = data.interp(
                x=('z', subset_geom.geom.x), y=('z', subset_geom.geom.y),
                method=ri_method
            )
            data = res.values

        return data


