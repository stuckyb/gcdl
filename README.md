# USDA-ARS Geospatial Common Data Library (GeoCDL)

## Installing the GeoCDL

1. Make sure you have a recent release of Python 3 installed.
1. Clone this git repository.
1. Run `pip install -r requirements.txt`.
1. You will need to create directories for local data, dataset build outputs, the dataset upload cache, and logging.


## Running the GeoCDL

1. Move to the `src` directory (`cd src`).
1. Run `uvicorn api_main:app --reload`.
1. API endpoints will be available at [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (e.g., [http://127.0.0.1:8000/ds_info?id=DaymetV4](http://127.0.0.1:8000/ds_info?id=DaymetV4)).
1. API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).


## Running the GeoCDL in a Singularity container

1. Clone this git repository.
1. Build the Singularity image.  From the main repo directory, run
    ```
    sudo singularity build geocdl.sif geocdl.def
    ```
    or, if you do not have root privileges,
    ```
    singularity build --fakeroot geocdl.sif geocdl.def
    ```
1. Run the GeoCDL in a Singularity container.  To avoid needing to rebuild the container image every time the source code changes, the source directory is maintained outside of the container image and mounted read-only inside the container at run time.  Local data storage is also mounted read-only inside the container; the output, upload cache, and logging directories are mounted read/write inside the container.  Be default, the container is bound directly to the host's network, so explicit port mapping is not required.
    ```
    singularity run \
      --mount type=bind,src=/path/to/geocdl/src,dst=/geocdl/src,ro \
      --mount type=bind,src=/path/to/local_data,dst=/geocdl/local_data,ro \
      --mount type=bind,src=/path/to/output,dst=/geocdl/output \
      --mount type=bind,src=/path/to/uploads,dst=/geocdl/upload \
      --mount type=bind,src=/path/to/logdir,dst=/geocdl/logs \
      geocdl.sif
    ```


## Running the GeoCDL in a Docker container

1. Clone this git repository.
1. Build the Docker image.  From the main repo directory, run
    ```
    docker build -t geocdl[:tag] .
    ```
1. Run the GeoCDL in a Docker container.  To avoid needing to rebuild the container image every time the source code changes, the source directory is maintained outside of the container image and mounted read-only inside the container at run time.  Local data storage is also mounted read-only inside the container; the output, upload cache, and logging directories are mounted read/write inside the container.  Here, we bind the container directly to the host's network, which is convenient for testing/development purposes, but not ideal for all production situations.  For production, mapping specific ports might be preferred.
    ```
    docker run \
      --mount type=bind,src=/path/to/geocdl/src,dst=/geocdl/src,ro \
      --mount type=bind,src=/path/to/local_data,dst=/geocdl/local_data,ro \
      --mount type=bind,src=/path/to/output,dst=/geocdl/output \
      --mount type=bind,src=/path/to/uploads,dst=/geocdl/upload \
      --mount type=bind,src=/path/to/logdir,dst=/geocdl/logs \
      --network host \
      geocdl
    ```


## Current datasets

| id |          name |
| :---			|   :---	| 
| DaymetV4 |    Daymet Version 4 |
| GTOPO30 |     Global 30 Arc-Second Elevation | 
| MODIS_NDVI |  MODIS NDVI Data, Smoothed and Gap-filled, for the Conterminous US: 2000-2015 |
| NASS_CDL |    NASS Cropland Data Layer |
| NLCD |        National Land Cover Database |
| PRISM |       PRISM |
| RAPV3 |       Rangeland Analysis Platform Version 3 |
| SMAP-HB1km |  SMAP HydroBlocks - 1 km |
| Soilgrids250mV2 | SoilGrids — global gridded soil information |
| VIP |         Vegetation Index and Phenology (VIP) Vegetation Indices Daily Global 0.05Deg CMG V004 | 
