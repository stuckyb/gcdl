
FROM ubuntu:22.04

WORKDIR /geocdl

COPY requirements.txt .

RUN apt-get update
RUN apt-get install -y python3 python-is-python3 python3-pip python3-gdal
RUN pip install -r requirements.txt

# The pydap package that installs with Python 3.10.4 has several bugs related
# to abstract base class imports.  The following two commands fix those bugs.
RUN sed -i 's/from collections import OrderedDict, Mapping/from collections import OrderedDict\nfrom collections.abc import Mapping/g' /usr/local/lib/python3.10/dist-packages/pydap/model.py
RUN sed -i 's/from collections import Iterable/from collections.abc import Iterable/g' /usr/local/lib/python3.10/dist-packages/pydap/responses/das.py

WORKDIR /geocdl/src
CMD ["uvicorn", "api_main:app"]

