
FROM ubuntu:22.04

WORKDIR /geocdl

COPY requirements.txt .
COPY bin/geocdl.sh .

RUN apt-get update
RUN apt-get install -y python3 python-is-python3 python3-pip
RUN apt-get install -y python3-gdal libgdal-dev

# Don't install pydap from pypi because the latest release is not available
# there (as of 2022-08-24).  Instead, comment it out in requirements.txt and
# install directly from the release archive.
RUN sed -i 's/pydap/#pydap/g' /geocdl/requirements.txt

# Don't install install rasterio from the binaries on pypi because they have
# a minimal gdal that lacks HDF5 or HDF4 support.  Instead, build rasterio
# from source to ensure we have HDF4/5 support.
RUN python -m pip install -r /geocdl/requirements.txt --no-binary rasterio
RUN python -m pip install https://github.com/pydap/pydap/archive/refs/tags/3.3.0.tar.gz

RUN chmod ugo+x /geocdl/geocdl.sh

WORKDIR /geocdl/src
ENTRYPOINT ["/geocdl/geocdl.sh"]

