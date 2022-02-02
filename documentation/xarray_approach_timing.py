from pathlib import Path
import xarray as xr
import rioxarray
import pandas as pd

##################
####	
#### Purpose: test different approaches for reading in data files
#### 	from datasets of different file structures to assess which 
####	approach(es) should be implemented in GeoCDL.
####	
#### To Do:
#### 	1. Save timings of each approach with increasing number of years 
####	 	
#### Future: 
####	1. Incorporate dask and update timings	
##################


### Setup input data path
local_data_path = Path('../src/local_data')  


#########
### Setup relevant example user imput that the API would acquire
#########

# Setup a testing bounding box for clipping operation
bbox = [[-106,36],[-105,32]]
user_geom = [{
                'type': 'Polygon',
                'coordinates': [[
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
                ]]
            }]
user_crs = 4326 

# Set variables
varnames = {
	"prism": ["ppt", "tmax"],
	"daymet": ["prcp", "tmax"],
	"cru": ["pre","tmx"],
	"cru2": ["pre","stn"]
}

# My local test data is 2018-2019 monthly for PRISM, Daymet
date_start = '2018-01'
date_end = '2019-12'
time_coords = pd.date_range(date_start,date_end,freq='MS',name="time")

# List filenames by dataset and variable
#PRISM
prism_time = [t.strftime('%Y%m') for t in time_coords]
prism_fpattern = 'prism/PRISM_{0}_stable_4kmM3_{1}_bil.bil'
prism_files = {}
for v in varnames["prism"]:
	prism_files[v] = [local_data_path/prism_fpattern.format(v,t) for t in prism_time] 

#Daymet
daymet_time = [t.strftime('%Y %m') for t in time_coords]
daymet_years = set([dt.split()[0] for dt in daymet_time])
daymet_fpattern = {
    'prcp': 'daymetv4/daymet_v4_prcp_monttl_na_{0}.tif',
    'tmax': 'daymetv4/daymet_v4_tmax_monavg_na_{0}.tif',
}
daymet_files = {}
for v in varnames["daymet"]:
	daymet_files[v] = [local_data_path/daymet_fpattern[v].format(y) for y in daymet_years]

#CRU
cru_times = [t.strftime('%Y-%m') for t in time_coords]
cru_files = {
	'pre': local_data_path / 'cru/cru_ts4.05.1901.2020.pre.dat.nc', 
	'tmx': local_data_path / 'cru/cru_ts4.05.1901.2020.tmx.dat.nc'
}


#########
### Approach 1: looping over each month and variable - current implemention
#########

## TEST 1.1 PRISM
# Loop over files and perform geospatial operation on each individual file
for var in varnames["prism"]:
	for fpath in prism_files[var]:
		data_loop = rioxarray.open_rasterio(fpath, masked=True)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)

## TEST 1.2.1 Daymet: opening per month (current implementation)
for var in varnames["daymet"]:
	for t in daymet_time: # Not looping over files since Daymet uses 12-bands for months
		cur_y, cur_m = t.split()
		fpath = local_data_path/daymet_fpattern[var].format(cur_y)
		data_loop = rioxarray.open_rasterio(fpath, masked=True).isel(time=int(cur_m)-1)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)

## TEST 1.2.2 Daymet: opening per year (small variation to current implementation)
for var in varnames["daymet"]:
	cur_y = list(daymet_years)[0]
	fpath = local_data_path/daymet_fpattern[var].format(cur_y)
	data_loop_all = rioxarray.open_rasterio(fpath, masked=True)
	for t in daymet_time:
		cur_yy, cur_m = t.split()
		#Update current year and read in new file
		if cur_yy > cur_y:
			fpath = local_data_path/daymet_fpattern.format(var,cur_yy)
			data_loop_all = rioxarray.open_rasterio(fpath, masked=True)
			cur_y = cur_yy
		data_loop = data_loop_all.isel(time=int(cur_m)-1)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)

## TEST 1.3.1 CRU: opening per variable and month combination
for var in varnames["cru"]:
	for t in cru_times: 
		fpath = cru_files[var]
		data_loop = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=t)
		data_loop.rio.write_crs("epsg:4326", inplace=True)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)

## TEST 1.3.2 CRU: opening per variable 
for var in varnames["cru"]:
	fpath = cru_files[var]
	data_loop_all = rioxarray.open_rasterio(fpath, masked=True)[var]
	data_loop_all.rio.write_crs("epsg:4326", inplace=True)
	for t in cru_times:
		data_loop = data_loop_all.sel(time=t)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)


## TEST 1.4.1 CRU2: opening per variable and month combination
fpath = cru_files["pre"]
for var in varnames["cru2"]:
	for t in cru_times: 
		data_loop = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=t)
		data_loop.rio.write_crs("epsg:4326", inplace=True)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)

## TEST 1.4.2 CRU2: opening per variable 
fpath = cru_files["pre"]
for var in varnames["cru2"]:
	data_loop_all = rioxarray.open_rasterio(fpath, masked=True)[var]
	data_loop_all.rio.write_crs("epsg:4326", inplace=True)
	for t in cru_times:
		data_loop = data_loop_all.sel(time=t)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)



#########
### Approach 2: combining all time increments of one variable into one data array, 
### but still looping over variables
#########

## TEST 2.1 PRISM: concatenate monthly files per variable
for var in varnames["prism"]:
	# Create list of DataArrays from files 
	data_stack = [rioxarray.open_rasterio(fpath, masked=True).squeeze(drop=True) for fpath in prism_files[var]]
	# Concatenate files along time dimension (new dimension for PRISM)
	data_stack = xr.concat(data_stack, dim=time_coords)
	clipped_stack = data_stack.rio.clip(user_geom, crs = user_crs)

## TEST 2.2 Daymet: concatenate each year file
for var in varnames["daymet"]:
	# Create list of DataArrays from files 
	data_stack = [rioxarray.open_rasterio(fpath, masked=True).squeeze(drop=True) for fpath in daymet_files[var]]
	# Concatenate files along time dimension (which already exist for daymet). 
	data_stack = xr.concat(data_stack, dim="time") #takes longer than I'd expect
	clipped_stack = data_stack.rio.clip(user_geom, crs = user_crs)

## TEST 2.3 CRU: looping over vars only, don't need time concatenation
for var in varnames["cru"]:
	fpath = cru_files[var]
	data_stack = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=time_coords, method = 'nearest')
	data_stack.rio.write_crs("epsg:4326", inplace=True)
	clipped_stack = data_stack.rio.clip(user_geom, crs = user_crs)

## TEST 2.4 CRU2: looping over vars only, don't need time concatenation
fpath = cru_files["pre"]
for var in varnames["cru2"]:
	data_stack = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=time_coords, method = 'nearest')
	data_stack.rio.write_crs("epsg:4326", inplace=True)
	clipped_stack = data_stack.rio.clip(user_geom, crs = user_crs)

#########
### Approach 3: combining all time increments and variables into one dataset
#########

## TEST 3.1 PRISM: concatenate time, then merge variables into Dataset
prism_arrays = []
for var in varnames["prism"]:
	# Create list of DataArrays from files 
	data_stack = [rioxarray.open_rasterio(fpath, masked=True, default_name = var).squeeze(drop=True) for fpath in prism_files[var]]
	# Concatenate files along time dimension (new dimension for PRISM)
	data_stack = xr.concat(data_stack, dim=time_coords)
	prism_arrays.append(data_stack)

prism_dataset = xr.merge(prism_arrays)
clipped_dataset = prism_dataset.rio.clip(user_geom, crs = user_crs)


## TEST 3.2 Daymet: concatenate time, then merge variables into Dataset
daymet_arrays = []
for var in varnames["daymet"]:
	# Create list of DataArrays from files 
	data_stack = [rioxarray.open_rasterio(fpath, masked=True, default_name = var).squeeze(drop=True) for fpath in daymet_files[var]]
	# Concatenate files along time dimension (which already exist for daymet). 
	data_stack = xr.concat(data_stack, dim="time") #takes longer than I'd expect
	daymet_arrays.append(data_stack)

daymet_dataset = xr.merge(daymet_arrays)
clipped_dataset = daymet_dataset.rio.clip(user_geom, crs = user_crs)

## TEST 3.3 CRU: merge variables
cru_datasets = []
for var in varnames["cru"]:
	fpath = cru_files[var]
	data_stack = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=time_coords, method = 'nearest')
	cru_datasets.append(data_stack)

cru_dataset = xr.merge(cru_datasets)
cru_dataset.rio.write_crs("epsg:4326", inplace=True)
clipped_dataset = cru_dataset.rio.clip(user_geom, crs = user_crs)

## TEST 3.4 CRU2: no steps needed besidess subsetting time
cru_datasets = []
fpath = cru_files['pre']
cru_dataset = rioxarray.open_rasterio(fpath, masked=True).sel(time=time_coords, method = 'nearest')
cru_dataset.rio.write_crs("epsg:4326", inplace=True)
clipped_dataset = cru_dataset.rio.clip(user_geom, crs = user_crs)
