from pathlib import Path
import xarray as xr
import rioxarray
import matplotlib.pyplot as plt
from rasterio.enums import Resampling
import geopandas as gpd
import shapely.geometry as sg

##################
####    
#### Purpose: testing minimum buffer on user geometries 
####    
#### To Do:
####    1.   
##################

### Setup input data path
local_data_path = Path('../local_data/prism')
fpath = local_data_path / "PRISM_ppt_stable_4kmM2_201906_bil.bil"

#########
### Setup relevant example user imput that the API would acquire
#########

# Setup a testing bounding box for clipping operation
bbox = [[-110.5,38.5],[-101.5,30]]
sh_poly = sg.Polygon([
                    # Top left.
                    [bbox[0][0], bbox[0][1]],
                    # Top right.
                    [bbox[1][0], bbox[0][1]],
                    # Bottom right.
                    [bbox[1][0], bbox[1][1]],
                    # Bottom left.
                    [bbox[0][0], bbox[1][1]],
                    # Top left.
                    [bbox[0][0], bbox[0][1]]
                ])
box_crs = 4269
box_geom0 = gpd.GeoSeries([sh_poly], crs='EPSG:' + str(box_crs))


bbox = [[-109,37],[-103,31.5]]
sh_poly = sg.Polygon([
                    # Top left.
                    [bbox[0][0], bbox[0][1]],
                    # Top right.
                    [bbox[1][0], bbox[0][1]],
                    # Bottom right.
                    [bbox[1][0], bbox[1][1]],
                    # Bottom left.
                    [bbox[0][0], bbox[1][1]],
                    # Top left.
                    [bbox[0][0], bbox[0][1]]
                ])
user_crs = 4269
user_geom0 = gpd.GeoSeries([sh_poly], crs='EPSG:' + str(user_crs))

aggs = [0.25, 0.5, 1, 2, 4, 10]
epsgs = [4326,4269,3857,5070,2163,32613]
res = [0.15, 1, 3, 12]

## Make some pre-made resampled clipped regions of PRISM
if False: 
    data0 = rioxarray.open_rasterio(fpath, masked=True)
    datac = data0.rio.clip(box_geom0)
    for e in epsgs:
        for i in aggs:
            data = datac.rio.reproject(
                dst_crs = 'EPSG:' + str(e)
            )
            data = data.rio.reproject(
                dst_crs = data.rio.crs,
                resolution=tuple(r*i for r in data.rio.resolution())
            )
            data.rio.to_raster("../output/prism_test_input_" + str(e) + '_' + str(i) + ".tif")
            if False:
                plt.figure(figsize=(6,8))
                data.plot(cmap='RdBu', vmin=0, vmax=180)
                plt.savefig('../output/buff_test' + str(e) + '_' + str(i) + '.png')
                plt.close()


## For the different aggregations, starting with no buffer:
## 1. Specify a (few) user CRS
## 2. Reproject user geometry to PRISM CRS
## 3. Clip raster to that geometry
## 4. Reproject clipped result to user CRS
## 5. Clip to user geom 

if True: 

    #each user trial
    for target_e in epsgs:  

        t_res = 0
        # I know these aren't exactly the same but I don't think it matters 
        # since I'm not comparing target_e against each other
        if target_e in [2163,32613,3857,5070]: #meters
            t_res = 4000.0
        else: #degrees
            t_res = 0.04167

        # Reproject user geometry to this trial crs
        user_geom = user_geom0.to_crs('EPSG:' + str(target_e))

        # Experimenting with finer/coarser resolution
        for tr in res:
            target_res = t_res*tr

            target_data = None

            # Create list for collecting result DataArrays
            data_sum = []

            #diff dataset CRS
            for ds_e in epsgs:

                # Reproject user geometry to match dataset
                prism_geom = user_geom.to_crs('EPSG:' + str(ds_e))

                #diff dataset resolution
                for ds_a in aggs:

                    # Read in dataset
                    ds_path = "../output/prism_test_input_" + str(ds_e) + '_' + str(ds_a) + ".tif"
                    ds = rioxarray.open_rasterio(ds_path, masked=True)

                    # Create buffer: what size?
                    this_ds = max(ds.rio.resolution())  # too small -> border differences
                    coarsest_ds = max(ds.rio.resolution())*max(aggs)/ds_a # works! -> no differences
                    coarsest_overall = max(coarsest_ds, target_res) #doesn't seem to be needed
                    buffer_geom = prism_geom.buffer(coarsest_ds)

                    # Clip dataset to buffered user geometry in dataset crs 
                    datac = ds.rio.clip(
                        buffer_geom,
                        all_touched = True
                    )

                    if ds_e == epsgs[0] and ds_a == aggs[0]: # if first dataset
                        # Reproject clipped dataset to target crs
                        datar = datac.rio.reproject(
                            dst_crs = 'EPSG:' + str(target_e),
                            resolution = target_res
                        )
                        # Clip to user geometry in target crs
                        data_final = datar.rio.clip(
                            user_geom,
                            all_touched = True
                        )
                        target_data = data_final
                    else:
                        data_final = datac.rio.reproject_match(
                            target_data
                        )
                        #data_final = datac.rio.reproject(
                        #     dst_crs = 'EPSG:' + str(target_e),
                        #    resolution = target_res
                        #)
                        data_final = data_final.rio.clip(
                            user_geom,
                            all_touched = True
                        )
            
                    # Sum not null cells 
                    data_sum.append(data_final.notnull().astype('int'))
                
              
            data_sum = xr.concat(data_sum, dim='ds').sum('ds')
            plt.figure(figsize=(6,8))
            data_sum.plot(cmap='RdBu', vmin=0, vmax=len(epsgs)*len(aggs))
            plt.savefig('../output/prism_sum_r' + str(target_e) + '_' + str(tr) + '.png')
            plt.close()



