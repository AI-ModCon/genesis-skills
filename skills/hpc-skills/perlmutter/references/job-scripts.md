# Perlmutter Job Script Examples

Perlmutter uses Slurm. All jobs require `-A <account>` and `-C cpu` or `-C gpu`.

---

## CPU Job (regular QOS)

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C cpu
#SBATCH --qos=regular
#SBATCH -N 4
#SBATCH --ntasks-per-node=128          # 128 physical cores per CPU node
#SBATCH -t 4:00:00
#SBATCH -o cpu_%j.out
#SBATCH -e cpu_%j.err

module load PrgEnv-gnu cray-mpich

srun ./my_mpi_app
```

---

## GPU Job (4× A100 per node)

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C gpu
#SBATCH --qos=regular
#SBATCH -N 2
#SBATCH --ntasks-per-node=4            # 4 tasks = 4 GPUs per node
#SBATCH --gpus-per-task=1              # 1 A100 per task
#SBATCH -c 32                          # 128 cores / 4 tasks = 32 cores each
#SBATCH -t 6:00:00
#SBATCH -o gpu_%j.out
#SBATCH -e gpu_%j.err

module load cudatoolkit cray-mpich

# Perlmutter recommendation: bind CPUs to cores for NUMA locality
export SLURM_CPU_BIND="cores"

srun ./my_cuda_app
```

---

## Shared QOS (partial node — single GPU)

Use `shared` when your job needs only 1 GPU and you want to avoid being charged for a full node.

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C gpu
#SBATCH --qos=shared
#SBATCH -n 1                           # 1 MPI task
#SBATCH -c 32                          # 32 CPU cores
#SBATCH --gpus-per-task=1             # 1 GPU
#SBATCH --mem=80G                      # Memory (not the full node amount)
#SBATCH -t 2:00:00
#SBATCH -o shared_%j.out

module load cudatoolkit

srun ./my_single_gpu_app
```

You are billed for the fraction of the node you use, not the full node.

---

## Debug QOS (rapid iteration)

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C gpu
#SBATCH --qos=debug
#SBATCH -N 1
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-task=1
#SBATCH -c 32
#SBATCH -t 00:30:00
#SBATCH -o debug_%j.out

module load cudatoolkit cray-mpich

srun ./my_app --test-mode
```

Debug jobs start fast; max 30 minutes and 8 nodes.

---

## Preempt QOS (discounted but interruptible)

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C gpu
#SBATCH --qos=preempt
#SBATCH -N 8
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-task=1
#SBATCH -c 32
#SBATCH -t 24:00:00
#SBATCH --open-mode=append            # append to output if requeued
#SBATCH -o preempt_%j.out

module load cudatoolkit cray-mpich

# Add a checkpoint handler for graceful preemption
checkpoint() {
    echo "Preempted — writing checkpoint"
    kill -SIGUSR1 $APP_PID
    wait $APP_PID
    sbatch --dependency=afterany:$SLURM_JOB_ID "$0"
    exit 0
}
trap checkpoint USR1 TERM

srun ./my_restartable_app &
APP_PID=$!
wait $APP_PID
```

---

## Big Job with Discount (≥128 GPU nodes)

Jobs at ≥128 GPU nodes or ≥256 CPU nodes are charged at 50% SU.

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C gpu
#SBATCH --qos=regular
#SBATCH -N 256                         # ≥128 GPU nodes triggers 50% discount
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-task=1
#SBATCH -c 32
#SBATCH -t 12:00:00
#SBATCH -o big_%j.out
#SBATCH -e big_%j.err

module load cudatoolkit cray-mpich

export SLURM_CPU_BIND="cores"
srun ./my_large_scale_app
```

---

## Hybrid MPI + OpenMP (CPU Nodes)

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C cpu
#SBATCH --qos=regular
#SBATCH -N 16
#SBATCH --ntasks-per-node=8           # MPI ranks per node
#SBATCH --cpus-per-task=16            # Threads per rank (8 × 16 = 128)
#SBATCH -t 8:00:00
#SBATCH -o hybrid_%j.out

module load PrgEnv-gnu cray-mpich

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PLACES=cores
export OMP_PROC_BIND=close

srun ./my_hybrid_app
```

---

## Building Code with Cray Wrappers

```bash
# On a login node or in an interactive salloc session
module load PrgEnv-gnu cray-mpich     # or PrgEnv-cray, PrgEnv-nvidia

# C: cc wraps gcc + links Cray MPI
cc -O3 -o my_mpi_app my_mpi_app.c

# C++: CC
CC -O3 -std=c++17 -o my_cpp_app my_cpp_app.cpp

# Fortran: ftn
ftn -O3 -o my_f90_app my_f90_app.f90

# CUDA: use nvcc directly or cudatoolkit wrappers
module load cudatoolkit
nvcc -O3 -arch=sm_80 -o my_cuda_app my_cuda_app.cu
```

---

## Job Array on Perlmutter

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C cpu
#SBATCH --qos=regular
#SBATCH --array=0-49%10              # 50 tasks, max 10 at once
#SBATCH -N 1
#SBATCH --ntasks-per-node=128
#SBATCH -t 1:00:00
#SBATCH -o logs/sweep_%A_%a.out

module load PrgEnv-gnu

INPUT="inputs/config_${SLURM_ARRAY_TASK_ID}.yaml"
OUTPUT="$SCRATCH/results/run_${SLURM_ARRAY_TASK_ID}/"
mkdir -p "$OUTPUT"

srun ./my_sim --config "$INPUT" --outdir "$OUTPUT"
```
