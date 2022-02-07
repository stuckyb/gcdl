#!/bin/bash

# job standard output will go to the file slurm-%j.out (where %j is the job ID)

#SBATCH --time=2:00:00   # walltime limit (HH:MM:SS)
#SBATCH --nodes=1   # number of nodes
#SBATCH --ntasks-per-node=2   # 1 processor core(s) per node X 2 threads per core
#SBATCH --mem=372G   # maximum memory per node
#SBATCH --partition=short    # standard node(s)

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
module load python_3/3.6.6
module load gdal

python3 ~/gcdl/documentation/xarray_approach_timing.py 2011
