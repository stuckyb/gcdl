#!/bin/bash

# Launches the GeoCDL with multiple instances for load balancing.  This script
# is intended to be used inside a container.

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 NUM_WORKERS ADDRESS:PORT"
    exit 1
fi

gunicorn api_main:app \
    --workers $1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind $2

