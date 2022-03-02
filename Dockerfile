
FROM python:3.9-slim

WORKDIR /geocdl

COPY requirements.txt .
COPY src ./src/

RUN pip install -r requirements.txt

WORKDIR /geocdl/src
CMD ["uvicorn", "api_main:app"]

