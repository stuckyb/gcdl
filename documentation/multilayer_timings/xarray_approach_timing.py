import argparse
import os
import time
from pathlib import Path
import xarray as xr
import rioxarray
import pandas as pd
import xarray as xr
from pydap.client import open_url
import geopandas as gpd
import shapely.geometry as sg

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

parser = argparse.ArgumentParser()
parser.add_argument("start_year",type=int)
args = parser.parse_args()

print("timing started")
begin_time = time.time()

### Setup input data path
# local_data_path = Path('../src/local_data')
local_data_path = Path('/90daydata/shared/geocdl/gcdl_testing_data')

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

sh_poly = sg.Polygon(user_geom[0]['coordinates'][0])
user_gs = gpd.GeoSeries([sh_poly], crs=user_crs)
daymet_proj = "+proj=lcc +ellps=WGS84 +a=6378137 +b=6356752.314245 +lat_1=25 +lat_2=60 +lon_0=-100 +lat_0=42.5 +x_0=0 +y_0=0 +units=m +no_defs" 
lccbounds = user_gs.to_crs(daymet_proj).bounds

# Set variables
varnames = {
	"prism": ["ppt", "tmax"],
	"daymet": ["prcp", "tmax"],
	"cru": ["pre","tmx"],
	"cru2": ["pre","stn"]
}

# local test data 2011-2020, monthly for PRISM, Daymet
year_start = args.start_year
year_end = 2020
years = year_end - year_start + 1
output = "timing_" + str(year_start) + "-" + str(year_end) + ".csv"

date_start = str(year_start) + '-01'
date_end = str(year_end) + '-12'
time_coords = pd.date_range(date_start,date_end,freq='MS',name="time")

### append each step timing to csv file
def time_to_csv(testid, years, file=output):
    if not Path(file).is_file():
        csv_file = open(file, "w")
        csv_file.write("test_id, num_years, time_sec\n")
        csv_file.close()
    timing = f'{testid}{", "}{years}{", "}{round(time.time() - start_time, 1)}'
    csv_file = open(file, "a")
    csv_file.write(timing + "\n")
    csv_file.close()
    print(timing)

# List filenames by dataset and variable
# PRISM
prism_time = [t.strftime('%Y%m') for t in time_coords]
prism_fpattern = 'prism/PRISM_{0}_stable_4kmM3_{1}_bil.bil'
prism_files = {}
for v in varnames["prism"]:
	prism_files[v] = [local_data_path/prism_fpattern.format(v,t) for t in prism_time] 

# Daymet
daymet_time = [t.strftime('%Y %m') for t in time_coords]
daymet_years = set([dt.split()[0] for dt in daymet_time])
daymet_fpattern = {
		'prcp': 'daymetv4/daymet_v4_prcp_monttl_na_{0}.tif',
		'tmax': 'daymetv4/daymet_v4_tmax_monavg_na_{0}.tif',
}		
daymet_files = {}
for v in varnames["daymet"]:
	daymet_files[v] = [local_data_path/daymet_fpattern[v].format(y) for y in daymet_years]

# Remote Daymet
thredds_url = 'https://thredds.daac.ornl.gov/thredds/dodsC/ornldaac/1855/'
daymet_upattern = {
		'prcp': 'daymet_v4_prcp_monttl_na_{0}.nc',
		'tmax': 'daymet_v4_tmax_monavg_na_{0}.nc',
}
daymet_urls = {}
for v in varnames["daymet"]:
	daymet_urls[v] = [thredds_url + daymet_upattern[v].format(y) for y in daymet_years]

# CRU
cru_times = [t.strftime('%Y-%m') for t in time_coords]
cru_files = {
	'pre': local_data_path / 'cru/cru_ts4.05.1901.2020.pre.dat.nc', 
	'tmx': local_data_path / 'cru/cru_ts4.05.1901.2020.tmx.dat.nc'
}

#########
### Approach 1: looping over each month and variable - current implemention
#########

## TEST 1.1 PRISM: Loop over files and perform geospatial operation on each individual file
start_time = time.time()
for var in varnames["prism"]:
	for fpath in prism_files[var]:
		data_loop = rioxarray.open_rasterio(fpath, masked=True)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)
		print("TEST 1.1 PRISM", var, fpath)
time_to_csv("1.1", years)

## TEST 1.2.1 Daymet: opening per month (current implementation)
if years < 10:
	start_time = time.time()
	for var in varnames["daymet"]:
		for t in daymet_time: # Not looping over files since Daymet uses 12-bands for months
			cur_y, cur_m = t.split()
			fpath = local_data_path/daymet_fpattern[var].format(cur_y)
			data_loop = rioxarray.open_rasterio(fpath, masked=True).isel(time=int(cur_m)-1)
			clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)
			print("TEST 1.2.1 Daymet", var, cur_y, cur_m)
	time_to_csv("1.2.1", years)

## TEST 1.2.2 Daymet: opening per year (small variation to current implementation)
if years < 10:
	start_time = time.time()
	for var in varnames["daymet"]:
		cur_y = list(daymet_years)[0]
		fpath = local_data_path/daymet_fpattern[var].format(cur_y)
		data_loop_all = rioxarray.open_rasterio(fpath, masked=True)
		for t in daymet_time:
			cur_yy, cur_m = t.split()
			#Update current year and read in new file
			if cur_yy > cur_y:
				fpath = local_data_path/daymet_fpattern[var].format(cur_yy)
				# fpath = local_data_path/daymet_fpattern.format(var,cur_yy)
				data_loop_all = rioxarray.open_rasterio(fpath, masked=True)
				cur_y = cur_yy
			data_loop = data_loop_all.isel(time=int(cur_m)-1)
			clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)
			print("TEST 1.2.2 Daymet", var, cur_yy, cur_m)
	time_to_csv("1.2.2", years)

## TEST 1.3.1 CRU: opening per variable and month combination
if years < 10:
	start_time = time.time()
	for var in varnames["cru"]:
		for t in cru_times: 
			fpath = cru_files[var]
			data_loop = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=t)
			data_loop.rio.write_crs("epsg:4326", inplace=True)
			clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)
			print("TEST 1.3.1 CRU", var, t)
	time_to_csv("1.3.1", years)


## TEST 1.3.2 CRU: opening per variable 
start_time = time.time()
for var in varnames["cru"]:
	fpath = cru_files[var]
	data_loop_all = rioxarray.open_rasterio(fpath, masked=True)[var]
	data_loop_all.rio.write_crs("epsg:4326", inplace=True)
	for t in cru_times:
		data_loop = data_loop_all.sel(time=t)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)
		print("TEST 1.3.2 CRU", var, t)
time_to_csv("1.3.2", years)

## TEST 1.4.1 CRU2: opening per variable and month combination
if years < 10:
	start_time = time.time()
	fpath = cru_files["pre"]
	for var in varnames["cru2"]:
		for t in cru_times: 
			data_loop = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=t)
			data_loop.rio.write_crs("epsg:4326", inplace=True)
			clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)
			print("TEST 1.4.1 CRU2", var, t)
	time_to_csv("1.4.1", years)

## TEST 1.4.2 CRU2: opening per variable
start_time = time.time() 
fpath = cru_files["pre"]
for var in varnames["cru2"]:
	data_loop_all = rioxarray.open_rasterio(fpath, masked=True)[var]
	data_loop_all.rio.write_crs("epsg:4326", inplace=True)
	for t in cru_times:
		data_loop = data_loop_all.sel(time=t)
		clipped_loop = data_loop.rio.clip(user_geom, crs = user_crs)
		print("TEST 1.4.2 CRU2", var, t)
time_to_csv("1.4.2", years)

#########
### Approach 2: combining all time increments of one variable into one data array, 
### but still looping over variables
#########


## TEST 2.1 PRISM: concatenate monthly files per variable
start_time = time.time()
for var in varnames["prism"]:
	# Create list of DataArrays from files 
	data_stack = [rioxarray.open_rasterio(fpath, masked=True).squeeze(drop=True) for fpath in prism_files[var]]
	# Concatenate files along time dimension (new dimension for PRISM)
	data_stack = xr.concat(data_stack, dim=time_coords)
	clipped_stack = data_stack.rio.clip(user_geom, crs = user_crs)
	print("TEST 2.1 PRISM", var)
time_to_csv("2.1", years)

## TEST 2.2 Daymet: concatenate each year file
if years < 10:
	start_time = time.time()
	for var in varnames["daymet"]:
		# Create list of DataArrays from files 
		data_stack = [rioxarray.open_rasterio(fpath, masked=True).squeeze(drop=True) for fpath in daymet_files[var]]
		# Concatenate files along time dimension (which already exist for daymet). 
		data_stack = xr.concat(data_stack, dim="time") #takes longer than I'd expect
		clipped_stack = data_stack.rio.clip(user_geom, crs = user_crs)
		print("TEST 2.2 Daymet", var)
	time_to_csv("2.2", years)

## TEST 2.3 CRU: looping over vars only, don't need time concatenation
start_time = time.time()
for var in varnames["cru"]:
	fpath = cru_files[var]
	data_stack = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=time_coords, method = 'nearest')
	data_stack.rio.write_crs("epsg:4326", inplace=True)
	clipped_stack = data_stack.rio.clip(user_geom, crs = user_crs)
	print("TEST 2.3 CRU", var)
time_to_csv("2.3", years)

## TEST 2.4 CRU2: looping over vars only, don't need time concatenation
start_time = time.time()
fpath = cru_files["pre"]
for var in varnames["cru2"]:
	data_stack = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=time_coords, method = 'nearest')
	data_stack.rio.write_crs("epsg:4326", inplace=True)
	clipped_stack = data_stack.rio.clip(user_geom, crs = user_crs)
	print("TEST 2.4 CRU2", var)
time_to_csv("2.4", years)

## TEST 2.5 Remote Daymet: concatenate each year file
start_time = time.time()
for var in varnames["daymet"]:
	var_nc = Path('../../src/output') / (var + '_tdssubset.nc')
	cnt = 0
	for fpath in daymet_urls[var]:
		thredds_ds = open_url(fpath)
		ds = xr.open_dataset(xr.backends.PydapDataStore(thredds_ds), decode_coords="all")
		ds_slice = ds[var].sel(
			x=slice(lccbounds.minx[0],lccbounds.maxx[0]), 
			y=slice(lccbounds.maxy[0],lccbounds.miny[0])
		)

	if cnt==0:
		ds_stack = ds_slice
	else:
		ds_stack = xr.concat([ds_stack, ds_slice], dim="time")
	cnt += 1
	print("TEST 2.5 Remote Daymet", var)
time_to_csv("2.5", years)

#########
### Approach 3: combining all time increments and variables into one dataset
#########

## TEST 3.1 PRISM: concatenate time, then merge variables into Dataset
start_time = time.time()
prism_arrays = []
for var in varnames["prism"]:
	# Create list of DataArrays from files 
	data_stack = [rioxarray.open_rasterio(fpath, masked=True, default_name = var).squeeze(drop=True) for fpath in prism_files[var]]
	# Concatenate files along time dimension (new dimension for PRISM)
	data_stack = xr.concat(data_stack, dim=time_coords)
	prism_arrays.append(data_stack)
	print("TEST 3.1 PRISM", var)

prism_dataset = xr.merge(prism_arrays)
clipped_dataset = prism_dataset.rio.clip(user_geom, crs = user_crs)
time_to_csv("3.1", years)

## TEST 3.2 Daymet: concatenate time, then merge variables into Dataset
if years < 10:	
	start_time = time.time()
	daymet_arrays = []
	for var in varnames["daymet"]:
		# Create list of DataArrays from files 
		data_stack = [rioxarray.open_rasterio(fpath, masked=True, default_name = var).squeeze(drop=True) for fpath in daymet_files[var]]
		# Concatenate files along time dimension (which already exist for daymet). 
		data_stack = xr.concat(data_stack, dim="time") #takes longer than I'd expect
		daymet_arrays.append(data_stack)
		print("TEST 3.2 Daymet", var)

	daymet_dataset = xr.merge(daymet_arrays)
	clipped_dataset = daymet_dataset.rio.clip(user_geom, crs = user_crs)
	time_to_csv("3.2", years)

## TEST 3.3 CRU: merge variables
start_time = time.time()
cru_datasets = []
for var in varnames["cru"]:
	fpath = cru_files[var]
	data_stack = rioxarray.open_rasterio(fpath, masked=True)[var].sel(time=time_coords, method = 'nearest')
	cru_datasets.append(data_stack)
	print("TEST 3.3 CRU", var)

cru_dataset = xr.merge(cru_datasets)
cru_dataset.rio.write_crs("epsg:4326", inplace=True)
clipped_dataset = cru_dataset.rio.clip(user_geom, crs = user_crs)
time_to_csv("3.3", years)


## TEST 3.4 CRU2: no steps needed besidess subsetting time
start_time = time.time()
cru_datasets = []
fpath = cru_files['pre']
cru_dataset = rioxarray.open_rasterio(fpath, masked=True).sel(time=time_coords, method = 'nearest')
cru_dataset.rio.write_crs("epsg:4326", inplace=True)
clipped_dataset = cru_dataset.rio.clip(user_geom, crs = user_crs)
print("TEST 3.4 CRU2", fpath)
time_to_csv("3.4", years)

print(f'{"timing finished in "}{round(time.time() - begin_time, 1)}{" seconds"}')
