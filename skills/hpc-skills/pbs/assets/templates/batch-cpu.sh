#!/bin/bash
# =============================================================================
# PBS CPU batch job template
# Copy this file and adjust the parameters for your job.
# =============================================================================

#PBS -N myjob                        # Job name
#PBS -A myproject                    # Account/project to charge (usually required)

# --- Resource request ---
#PBS -l select=1:ncpus=32:mem=64gb   # N nodes : CPUs per node : memory per node
#PBS -l walltime=01:00:00            # Wall-clock limit: HH:MM:SS
#PBS -q workq                        # Queue name (check available: qstat -Q)

# --- Output files ---
#PBS -o myjob.out                    # Stdout file (default: <jobname>.o<id>)
#PBS -e myjob.err                    # Stderr file (default: <jobname>.e<id>)
# #PBS -j oe                         # Merge stdout+stderr into one file

# --- Notifications (optional) ---
# #PBS -m abe                        # Email on Abort, Begin, End
# #PBS -M user@institution.edu       # Email address

# --- Environment ---
# #PBS -V                            # Export all current env vars to job

# =============================================================================
# Execution
# =============================================================================

# Always change to the submission directory
cd $PBS_O_WORKDIR

echo "Job ID:      $PBS_JOBID"
echo "Job name:    $PBS_JOBNAME"
echo "Nodes:       $PBS_NUM_NODES"
echo "Total CPUs:  $PBS_NP"
echo "Queue:       $PBS_QUEUE"
echo "Workdir:     $PBS_O_WORKDIR"

# Load required software
module purge
module load gcc/12 openmpi/4.1     # Adjust to your software stack

# For OpenMP jobs, set thread count
# export OMP_NUM_THREADS=32
# export OMP_PLACES=cores
# export OMP_PROC_BIND=close

# Run the application
mpiexec -n $PBS_NP ./my_application --input input.dat --output output.dat

echo "Job completed with exit code $?"
