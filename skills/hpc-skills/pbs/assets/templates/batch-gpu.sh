#!/bin/bash
# =============================================================================
# PBS GPU batch job template
# Copy this file and adjust the parameters for your job.
# =============================================================================

#PBS -N gpu_job
#PBS -A myproject

# --- Resource request ---
#PBS -l select=1:ncpus=32:ngpus=4:mem=128gb   # 1 node, 32 CPUs, 4 GPUs, 128 GB
# To request a specific GPU type (site-dependent):
# #PBS -l select=1:ncpus=32:ngpus=4:gpu_type=A100:mem=128gb
#PBS -l walltime=04:00:00
#PBS -q gpu                          # GPU queue name (site-specific)

# --- Output files ---
#PBS -o gpu_job.out
#PBS -e gpu_job.err

# =============================================================================
# Execution
# =============================================================================

cd $PBS_O_WORKDIR

echo "Job ID:     $PBS_JOBID"
echo "Nodes:      $PBS_NUM_NODES"
echo "GPUs:       $(( PBS_NUM_NODES * 4 ))"   # adjust 4 to ngpus per node

module purge
module load cuda/12.1 gcc/12 openmpi/4.1    # Adjust to your software stack

# GPU visibility is often set by PBS automatically via CUDA_VISIBLE_DEVICES
# or ROCR_VISIBLE_DEVICES. Check site documentation.

# Launch one MPI rank per GPU
mpiexec -n 4 -npernode 4 ./my_gpu_application --input input.dat

echo "Job completed with exit code $?"
