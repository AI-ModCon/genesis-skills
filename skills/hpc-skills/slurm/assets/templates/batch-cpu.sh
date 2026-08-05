#!/bin/bash
# =============================================================================
# Slurm CPU batch job template
# Copy this file and adjust the parameters for your job.
# =============================================================================

#SBATCH --job-name=myjob          # Name shown in squeue output
#SBATCH --account=myproject       # Project account to charge

# --- Resource request ---
#SBATCH --nodes=1                 # Number of nodes
#SBATCH --ntasks-per-node=32      # MPI ranks per node (set to physical cores)
#SBATCH --cpus-per-task=1         # CPU threads per MPI rank (set >1 for OpenMP)
#SBATCH --mem=64G                 # Total memory per node (or use --mem-per-cpu)
#SBATCH --time=01:00:00           # Wall-clock limit: HH:MM:SS or D-HH:MM:SS

# --- Queue / partition ---
#SBATCH --partition=regular       # Partition name (check: sinfo)
# #SBATCH --qos=regular           # Uncomment if QOS is separate from partition
# #SBATCH --exclusive             # Uncomment for exclusive node access

# --- Output files ---
#SBATCH --output=myjob_%j.out     # %j = job ID
#SBATCH --error=myjob_%j.err
# #SBATCH --mail-type=END,FAIL    # Email when job ends or fails
# #SBATCH --mail-user=user@host   # Your email address

# =============================================================================
# Environment setup
# =============================================================================
module purge
module load gcc/12 openmpi/4.1    # Adjust to your software stack

# For OpenMP jobs: match threads to --cpus-per-task
# export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
# export OMP_PLACES=cores
# export OMP_PROC_BIND=close

echo "Job ID:       $SLURM_JOB_ID"
echo "Nodes:        $SLURM_JOB_NUM_NODES"
echo "Tasks:        $SLURM_NTASKS"
echo "CPUs/task:    $SLURM_CPUS_PER_TASK"
echo "Node list:    $SLURM_JOB_NODELIST"
echo "Submitted from: $SLURM_SUBMIT_DIR"

# =============================================================================
# Execution
# =============================================================================
cd "$SLURM_SUBMIT_DIR"

srun ./my_application --input input.dat --output output.dat
