#!/bin/bash

#SBATCH --time=2:00:00   # walltime limit (HH:MM:SS)
#SBATCH --nodes=1   # number of nodes
#SBATCH --ntasks-per-node=2   # 1 processor core(s) per node X 2 threads per core
#SBATCH --mem=372G   # maximum memory per node
#SBATCH --partition=short    # standard node(s)
#SBATCH --array=2001-2020
#SBATCH --output=slurm_%A_%a.out

# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
module load python_3/3.6.6
module load gdal

# Replicates
for i in {1..3}
do
	python3 ~/gcdl/documentation/multilayer_timings/xarray_approach_timing.py ${SLURM_ARRAY_TASK_ID} --datasets 5
done
