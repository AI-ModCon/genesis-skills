# Slurm Job Script Examples

Annotated, ready-to-use templates for common HPC workload patterns.

---

## Single-Node CPU Job

```bash
#!/bin/bash
#SBATCH --job-name=cpu_serial        # name shown in squeue
#SBATCH --nodes=1
#SBATCH --ntasks=1                   # single MPI rank
#SBATCH --cpus-per-task=32           # OpenMP threads
#SBATCH --mem=64G                    # memory per node
#SBATCH --time=04:00:00
#SBATCH --account=myproject
#SBATCH --partition=regular
#SBATCH --output=cpu_%j.out
#SBATCH --error=cpu_%j.err

module purge
module load gcc/12 openmpi/4.1

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PLACES=cores
export OMP_PROC_BIND=close

srun ./my_openmp_app
```

---

## Multi-Node MPI Job

```bash
#!/bin/bash
#SBATCH --job-name=mpi_run
#SBATCH --nodes=8
#SBATCH --ntasks-per-node=128        # 1 MPI rank per physical core
#SBATCH --time=02:00:00
#SBATCH --account=myproject
#SBATCH --partition=regular
#SBATCH --output=mpi_%j.out
#SBATCH --error=mpi_%j.err

module purge
module load gcc/12 openmpi/4.1

# SLURM_NTASKS = nodes × ntasks-per-node
echo "Running $SLURM_NTASKS tasks on $SLURM_JOB_NUM_NODES nodes"

srun ./my_mpi_app
```

Key points:
- `srun` is the recommended MPI launcher inside Slurm jobs (avoids double-counting)
- `--exclusive` can be added if sharing a node causes interference
- For `mpirun`/`mpiexec`, use `--mca btl ^openib` to suppress InfiniBand warnings in some configs

---

## GPU Job (NVIDIA, Single Node)

```bash
#!/bin/bash
#SBATCH --job-name=gpu_run
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4          # one MPI rank per GPU
#SBATCH --gpus-per-task=1            # 1 GPU per rank
#SBATCH --cpus-per-task=8            # CPU cores serving each GPU
#SBATCH --mem=128G
#SBATCH --time=06:00:00
#SBATCH --account=myproject
#SBATCH --partition=gpu
#SBATCH --output=gpu_%j.out
#SBATCH --error=gpu_%j.err

module purge
module load cuda/12.1 gcc/12 openmpi/4.1

# Each rank sees only its assigned GPU via CUDA_VISIBLE_DEVICES (set by Slurm)
srun ./my_cuda_app
```

Alternative: request GPUs at the node level with `--gres=gpu:4` (all 4 to the job, distributed manually).

---

## Hybrid MPI + OpenMP

```bash
#!/bin/bash
#SBATCH --job-name=hybrid
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=4          # MPI ranks per node
#SBATCH --cpus-per-task=16           # OpenMP threads per rank
#SBATCH --time=03:00:00
#SBATCH --account=myproject
#SBATCH --partition=regular
#SBATCH --output=hybrid_%j.out

module purge
module load gcc/12 openmpi/4.1

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PLACES=cores
export OMP_PROC_BIND=close

# Total ranks: 4 nodes × 4 ranks/node = 16
srun ./my_hybrid_app
```

Check: `ntasks-per-node × cpus-per-task` should equal the number of physical cores per node (e.g., 64 = 4 × 16).

---

## Job Array

```bash
#!/bin/bash
#SBATCH --job-name=param_sweep
#SBATCH --array=0-49                 # 50 tasks (indices 0..49)
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --time=01:00:00
#SBATCH --account=myproject
#SBATCH --partition=regular
#SBATCH --output=sweep_%A_%a.out     # %A=parent ID, %a=task index
#SBATCH --error=sweep_%A_%a.err

# Each task processes a different input file
INPUT="inputs/param_${SLURM_ARRAY_TASK_ID}.json"
OUTPUT="outputs/result_${SLURM_ARRAY_TASK_ID}.hdf5"

srun ./my_simulation --input "$INPUT" --output "$OUTPUT"
```

Throttle to limit concurrency (avoids overwhelming shared filesystems):
```bash
#SBATCH --array=0-499%25   # max 25 running at once
```

---

## Multi-Step Pipeline Within One Job

```bash
#!/bin/bash
#SBATCH --job-name=pipeline
#SBATCH --nodes=16
#SBATCH --ntasks-per-node=128
#SBATCH --time=8:00:00
#SBATCH --account=myproject
#SBATCH --partition=regular
#SBATCH --output=pipeline_%j.out

module load gcc/12 openmpi/4.1 hdf5

echo "=== Stage 1: Preprocessing ==="
srun --nodes=2 --ntasks=256 ./preprocess --input raw/ --output preprocessed/

echo "=== Stage 2: Main simulation ==="
srun --nodes=16 --ntasks=2048 ./simulate --input preprocessed/ --output results/

echo "=== Stage 3: Post-processing ==="
srun --nodes=1 --ntasks=128 ./postprocess --input results/ --output summary/
```

Each `srun` step uses the same node allocation but different task counts.

---

## Checkpoint / Restart (SIGTERM Handler)

```bash
#!/bin/bash
#SBATCH --job-name=restartable
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=128
#SBATCH --time=12:00:00
#SBATCH --account=myproject
#SBATCH --partition=regular
#SBATCH --output=run_%j.out
#SBATCH --signal=B:USR1@300          # send USR1 300s before walltime

CHECKPOINT_DIR="$SCRATCH/checkpoints"
mkdir -p "$CHECKPOINT_DIR"

# Handle SIGTERM / SIGUSR1 → trigger checkpoint
checkpoint() {
    echo "Signal received — writing checkpoint..."
    kill -USR1 $APP_PID    # tell app to checkpoint
    wait $APP_PID
    # Resubmit self
    sbatch --dependency=afterany:$SLURM_JOB_ID "$0"
    exit 0
}
trap checkpoint USR1 TERM

# Start app in background, capture PID
srun ./my_restartable_app --checkpoint-dir "$CHECKPOINT_DIR" &
APP_PID=$!
wait $APP_PID
```

---

## Common `srun` Options

| Option | Effect |
|--------|--------|
| `--nodes=N` | Limit step to N nodes |
| `--ntasks=N` | Override number of tasks for this step |
| `--ntasks-per-node=N` | Tasks per node for this step |
| `--gpus-per-task=N` | GPUs per task |
| `--cpu-bind=cores` | Bind tasks to cores (recommended) |
| `--mem-per-cpu=NM` | Memory per CPU for this step |
| `--exclusive` | Exclusive use of nodes for this step |
| `--label` | Prefix output with task rank |
| `--pty` | Allocate pseudo-terminal (interactive) |
