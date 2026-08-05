#!/bin/bash
# =============================================================================
# Slurm job array template
# Submits N independent tasks from a single qsub.
# Each task gets a unique SLURM_ARRAY_TASK_ID.
# =============================================================================

#SBATCH --job-name=sweep
#SBATCH --account=myproject

# --- Array specification ---
#SBATCH --array=0-99              # Task indices 0 through 99
# #SBATCH --array=1-100:2         # Odd indices only (1,3,5,...,99)
# #SBATCH --array=0-999%50        # Max 50 tasks running at once (throttle)

# --- Per-task resources ---
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --partition=regular

# --- Output files (use %A for array job ID, %a for task index) ---
#SBATCH --output=logs/sweep_%A_%a.out
#SBATCH --error=logs/sweep_%A_%a.err

# =============================================================================
# Environment setup
# =============================================================================
module purge
module load gcc/12

mkdir -p logs outputs

TASK_ID=$SLURM_ARRAY_TASK_ID
echo "Array job $SLURM_ARRAY_JOB_ID, task $TASK_ID"

# =============================================================================
# Task-specific logic
# =============================================================================

# Option 1: Use task ID directly as a parameter
PARAM_VALUE=$TASK_ID

# Option 2: Map task ID to a value in a config file
# PARAM_VALUE=$(sed -n "${TASK_ID}p" params.txt)

# Option 3: Map task ID to an input file
INPUT_FILE="inputs/input_${TASK_ID}.dat"
OUTPUT_FILE="outputs/output_${TASK_ID}.dat"

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "ERROR: input file $INPUT_FILE not found" >&2
    exit 1
fi

srun ./my_application \
    --input  "$INPUT_FILE" \
    --output "$OUTPUT_FILE" \
    --seed   "$TASK_ID"
