
FROM ubuntu:22.04

WORKDIR /geocdl

COPY requirements.txt .

RUN apt-get update
RUN apt-get install -y python3 python-is-python3 python3-pip python3-gdal

# Don't install pydap from pypi because the latest release is not available
# there (as of 2022-08-24).  Instead, comment it out in requirements.txt and
# install directly from the release archive.
RUN sed -i 's/pydap/#pydap/g' /geocdl/requirements.txt
RUN python -m pip install -r /geocdl/requirements.txt
RUN python -m pip install https://github.com/pydap/pydap/archive/refs/tags/3.3.0.tar.gz

WORKDIR /geocdl/src
CMD ["uvicorn", "api_main:app"]

