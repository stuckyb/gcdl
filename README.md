# USDA-ARS Geospatial Common Data Library (GeoCDL)

## Installing the GeoCDL

1. Make sure you have a recent release of Python 3 installed.
1. Clone this git repository.
1. Run `pip install -r requirements.txt`.


## Running the GeoCDL

1. Move to the `src` directory (`cd src`).
1. Run `uvicorn api_main:app --reload`.
1. API endpoints will be available at [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (e.g., [http://127.0.0.1:8000/ds_info?id=DaymetV4](http://127.0.0.1:8000/ds_info?id=DaymetV4)).
1. API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

