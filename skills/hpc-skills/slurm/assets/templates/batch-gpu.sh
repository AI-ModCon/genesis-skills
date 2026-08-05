#!/bin/bash
# =============================================================================
# Slurm GPU batch job template
# Copy this file and adjust the parameters for your job.
# =============================================================================

#SBATCH --job-name=gpu_job        # Name shown in squeue output
#SBATCH --account=myproject       # Project account to charge

# --- Resource request ---
#SBATCH --nodes=1                 # Number of nodes
#SBATCH --ntasks-per-node=4       # MPI ranks per node (usually 1 per GPU)
#SBATCH --gpus-per-task=1         # GPUs per MPI rank
#SBATCH --cpus-per-task=8         # CPU cores per MPI rank
#SBATCH --mem=128G                # Total memory per node
#SBATCH --time=04:00:00           # Wall-clock limit

# --- Queue / partition ---
#SBATCH --partition=gpu           # GPU partition name (check: sinfo)
# #SBATCH --gres=gpu:a100:4       # Alternative: request specific GPU model

# --- Output files ---
#SBATCH --output=gpu_%j.out
#SBATCH --error=gpu_%j.err
# #SBATCH --mail-type=END,FAIL
# #SBATCH --mail-user=user@host

# =============================================================================
# Environment setup
# =============================================================================
module purge
module load cuda/12.1 gcc/12 openmpi/4.1   # Adjust to your software stack

# Slurm sets CUDA_VISIBLE_DEVICES per task when using --gpus-per-task
# Each MPI rank automatically sees only its assigned GPU

echo "Job ID:     $SLURM_JOB_ID"
echo "Nodes:      $SLURM_JOB_NUM_NODES"
echo "Tasks:      $SLURM_NTASKS"
echo "GPUs/task:  $SLURM_GPUS_PER_TASK"

# =============================================================================
# Execution
# =============================================================================
cd "$SLURM_SUBMIT_DIR"

# Bind CPUs to cores for best NUMA locality
export SLURM_CPU_BIND=cores

srun ./my_gpu_application --input input.dat --output output.dat
