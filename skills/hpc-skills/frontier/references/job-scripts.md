# Frontier Job Script Examples

Frontier uses Slurm with the Cray Programming Environment. All jobs require `-A <project>` and `-p batch`.

---

## Full-Node GPU Job (AMD MI250X / HIP)

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -N 2
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH -t 2:00:00
#SBATCH -o gpu_%j.out
#SBATCH -e gpu_%j.err

module load PrgEnv-amd
module load amd/5.7.1
module load rocm/5.7.1
module load craype-accel-amd-gfx90a    # required for GPU compilation target
module load cray-mpich

export MPICH_GPU_SUPPORT_ENABLED=1
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH

# 8 GCDs per node × 2 nodes = 16 total GPU tasks
srun -N 2 --ntasks-per-node=8 \
     --gpus-per-task=1 \
     --gpu-bind=closest \
     ./my_hip_app
```

---

## CPU-Only MPI Job

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -N 8
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH --ntasks-per-node=56            # 56 allocatable cores (not 64, due to core-spec=8)
#SBATCH -t 4:00:00
#SBATCH -o cpu_%j.out

module load PrgEnv-gnu
module load cray-mpich

# Use cc/CC/ftn wrappers for compilation (not gcc directly)
srun ./my_mpi_app
```

---

## Hybrid MPI + OpenMP (CPU)

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -N 4
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH --ntasks-per-node=7            # MPI ranks per node
#SBATCH --cpus-per-task=8             # OpenMP threads per rank (7 × 8 = 56)
#SBATCH -t 3:00:00
#SBATCH -o hybrid_%j.out

module load PrgEnv-gnu cray-mpich

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PLACES=cores
export OMP_PROC_BIND=close

srun ./my_hybrid_app
```

---

## Full-Node Hybrid MPI + OpenMP + GPU

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -N 4
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH --ntasks-per-node=8            # 1 MPI rank per GCD
#SBATCH --cpus-per-task=7              # 56 cores / 8 ranks = 7 per rank
#SBATCH --gpus-per-task=1
#SBATCH -t 4:00:00
#SBATCH -o hybrid_gpu_%j.out

module load PrgEnv-amd amd/5.7.1 rocm/5.7.1 craype-accel-amd-gfx90a cray-mpich

export MPICH_GPU_SUPPORT_ENABLED=1
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

srun --gpu-bind=closest ./my_hybrid_gpu_app
```

---

## Debug Interactive Session

```bash
# Allocate 1 node, debug QOS (fast queue, 2 hr max)
salloc -N 1 -p batch --qos=debug -t 2:00:00 -A myproject

# Now you're on a login node with an allocation.
# Launch tasks:
module load PrgEnv-amd rocm/5.7.1 craype-accel-amd-gfx90a cray-mpich
export MPICH_GPU_SUPPORT_ENABLED=1
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH

srun -N 1 --ntasks-per-node=8 --gpus-per-task=1 ./my_app

# Exit releases the allocation
exit
```

---

## Job Array

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH --array=0-99%10               # max 10 running at once
#SBATCH -N 1
#SBATCH --ntasks-per-node=8
#SBATCH --gpus-per-task=1
#SBATCH -t 1:00:00
#SBATCH -o logs/sweep_%A_%a.out
#SBATCH -e logs/sweep_%A_%a.err

module load PrgEnv-amd rocm/5.7.1 craype-accel-amd-gfx90a cray-mpich

export MPICH_GPU_SUPPORT_ENABLED=1
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH

TASK_ID=$SLURM_ARRAY_TASK_ID
INPUT="inputs/config_${TASK_ID}.yaml"
OUTPUT="$MEMBERWORK/results/run_${TASK_ID}/"
mkdir -p "$OUTPUT"

srun --ntasks-per-node=8 --gpus-per-task=1 \
    ./my_sim --config "$INPUT" --outdir "$OUTPUT"
```

---

## OpenMP Target Offload (Cray Compilers)

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -N 2
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH --ntasks-per-node=8
#SBATCH --gpus-per-task=1
#SBATCH -t 2:00:00
#SBATCH -o omp_offload_%j.out

module load PrgEnv-cray
module load craype-accel-amd-gfx90a
module load rocm/5.7.1
module load cray-mpich

export MPICH_GPU_SUPPORT_ENABLED=1
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH
export OMP_TARGET_OFFLOAD=MANDATORY

# Compile with: CC -fopenmp -std=c++17 -O3 my_app.cpp -o my_app
srun --gpus-per-task=1 --gpu-bind=closest ./my_omp_target_app
```

---

## Checkpoint / Restart with SIGTERM Handler

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -N 8
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH --ntasks-per-node=8
#SBATCH --gpus-per-task=1
#SBATCH -t 12:00:00
#SBATCH --signal=B:USR1@300           # USR1 signal 300s before walltime
#SBATCH -o restartable_%j.out

module load PrgEnv-amd rocm/5.7.1 craype-accel-amd-gfx90a cray-mpich

export MPICH_GPU_SUPPORT_ENABLED=1
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH

CHECKPOINT_DIR="$MEMBERWORK/checkpoints"
mkdir -p "$CHECKPOINT_DIR"

# Signal handler — checkpoint then resubmit
on_signal() {
    echo "$(date): signal received, checkpointing..."
    kill -USR1 $APP_PID
    wait $APP_PID
    sbatch --dependency=afterany:$SLURM_JOB_ID "$0"
    exit 0
}
trap on_signal USR1 TERM

srun --ntasks-per-node=8 --gpus-per-task=1 \
    ./my_app --checkpoint-dir "$CHECKPOINT_DIR" --restart-if-exists &
APP_PID=$!
wait $APP_PID
```

---

## Using NVMe Burst Buffer

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -N 1
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH -C nvme                        # request NVMe burst buffer
#SBATCH --ntasks-per-node=8
#SBATCH --gpus-per-task=1
#SBATCH -t 2:00:00

module load PrgEnv-amd rocm/5.7.1 craype-accel-amd-gfx90a cray-mpich

export MPICH_GPU_SUPPORT_ENABLED=1
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH

NVME_DIR="/mnt/bb/$USER"

# Stage data to fast NVMe
cp "$MEMBERWORK/large_input.h5" "$NVME_DIR/"

# Run with fast local I/O
srun --ntasks-per-node=8 --gpus-per-task=1 \
    ./my_app --input "$NVME_DIR/large_input.h5" \
             --output "$NVME_DIR/result.h5"

# Stage result out
cp "$NVME_DIR/result.h5" "$MEMBERWORK/results/"
```
