
from catalog.catalog import DatasetCatalog
from catalog.datasets import PRISM, DAYMET
from fastapi import FastAPI, Query, HTTPException


dsc = DatasetCatalog('local_data')
dsc.addDatasetsByClass(PRISM, DAYMET)

app = FastAPI(
    title='Common Geospatial Data Library REST API',
    description='Welcome to the interactive documentation for USDA-ARS\'s '
    'Common Geospatial Data Library (CGDL) REST API! Here, you can see all '
    'available API endpoints and directly experiment with CGDL API calls. '
    'Note that most users will find it easier to access the CGDL via one of '
    'our higher-level interfaces, including a web GUI interface and packages '
    'for Python and R.'
)

@app.get(
    '/list_datasets',
    summary='Returns a list with the ID and name of each dataset in the '
    'library.'
)
async def list_datasets():
    return dsc.getCatalogEntries()

@app.get(
    '/ds_info',
    summary='Returns metadata for the geospatial dataset with the provided ID.'
)
async def ds_info(
    dsid: str = Query(
        ..., alias='id', title='Dataset ID', description='The ID of a dataset.'
    )
):
    try:
        return dsc[dsid].getMetadata()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

