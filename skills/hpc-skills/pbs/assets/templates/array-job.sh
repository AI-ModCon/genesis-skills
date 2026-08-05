#!/bin/bash
# =============================================================================
# PBS job array template
# Submits N independent tasks from a single qsub.
# Each task gets a unique PBS_ARRAY_INDEX.
# Resources are allocated independently for EACH array task.
# =============================================================================

#PBS -N sweep
#PBS -A myproject

# --- Array specification ---
#PBS -t 1-100                        # Task indices 1 through 100
# #PBS -t 1-50:2                     # Odd indices only (1,3,5,...,49)
# #PBS -t 1-100%10                   # Max 10 tasks running at once (throttle)

# --- Per-task resources ---
#PBS -l select=1:ncpus=8:mem=16gb    # Resources for EACH task (not total)
#PBS -l walltime=00:30:00
#PBS -q workq

# --- Output files per task ---
# Note: ${PBS_ARRAY_INDEX} expansion happens at runtime, not submission time
# Some PBS versions support %J (job ID) and %I (array index) in paths:
#PBS -o logs/sweep.out
#PBS -e logs/sweep.err
# If your PBS supports it:
# #PBS -o logs/sweep_${PBS_JOBID}_${PBS_ARRAY_INDEX}.out

# =============================================================================
# Execution
# =============================================================================

cd $PBS_O_WORKDIR
mkdir -p logs outputs

TASK_ID=$PBS_ARRAY_INDEX
echo "Array job: $PBS_ARRAY_ID"
echo "Task index: $TASK_ID"

module purge
module load gcc/12

# Option 1: Use task index directly
INPUT_FILE="inputs/input_${TASK_ID}.dat"
OUTPUT_FILE="outputs/output_${TASK_ID}.dat"

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "ERROR: input file $INPUT_FILE not found" >&2
    exit 1
fi

# Option 2: Map task ID to parameters from a config file
# PARAMS=$(sed -n "${TASK_ID}p" parameter_list.txt)

./my_application \
    --input  "$INPUT_FILE" \
    --output "$OUTPUT_FILE" \
    --seed   "$TASK_ID"

echo "Task $TASK_ID completed with exit code $?"
