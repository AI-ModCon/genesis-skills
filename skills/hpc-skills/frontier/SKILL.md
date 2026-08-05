---
name: frontier
description: >
  OLCF Frontier supercomputer at Oak Ridge National Laboratory. Use when
  submitting Slurm jobs on Frontier, configuring AMD MI250X GPU jobs with
  ROCm/HIP, choosing debug or regular QOS, setting up the Cray programming
  environment (cc/CC/ftn compiler wrappers), loading craype-accel-amd-gfx90a
  and rocm modules, setting MPICH_GPU_SUPPORT_ENABLED for GPU-aware MPI,
  working with Lustre scratch storage, or writing job scripts for Frontier's
  4-GPU (8-GCD) per-node architecture.
compatibility: Must be logged into a Frontier login node (frontier.olcf.ornl.gov).
metadata:
  version: "1.0"
  system: frontier
  facility: olcf
  scheduler: slurm
allowed-tools: Bash(sbatch *) Bash(squeue *) Bash(scancel *) Bash(sinfo *) Bash(sacct *) Bash(salloc *) Bash(srun *) Bash(scontrol *) Bash(module *) Read Write
---

# Frontier — OLCF Supercomputer

Frontier is Oak Ridge National Laboratory's AMD-GPU-based exascale system. It uses **Slurm** as its workload manager and runs the **Cray Programming Environment**.

## System Overview

| Component | Specification |
|-----------|--------------|
| Nodes | 9,856 AMD compute nodes (77 racks) |
| CPU | 1× AMD EPYC 7A53 "Trento" (64 cores, 512 GB DDR4) |
| GPU | 4× AMD MI250X per node; each MI250X has 2 GCDs = **8 GCDs per node** |
| GPU memory | 64 GB HBM2e per GCD (256 GB total HBM per node) |
| Burst buffer | 2× 1.92 TB NVMe per node |
| Network | HPE Slingshot-11, dragonfly topology |

## Critical Requirements

```bash
#SBATCH -A myproject     # project account (required)
#SBATCH -p batch         # partition (only partition available)
#SBATCH --qos=regular    # or --qos=debug for development
```

## Core Specialization

> **Frontier reserves 8 CPU cores per node by default** (Slurm `--core-spec=8`).
> Only 56 of 64 cores are allocatable. Factor this into `--ntasks-per-node` and `--cpus-per-task`.

Override with `--core-spec=0` only when you need all 64 cores and understand the implications.

## QOS

| QOS | Max walltime | Max running jobs | Notes |
|-----|-------------|-----------------|-------|
| `debug` | 2 hr | 1 per user | Up to 2 nodes; fast queue |
| `regular` | 24 hr | 4 per user | Standard production |
| `extended` | > 24 hr | 1 per user | Requires prior approval |

Max 100 total jobs queued at once across all QOS.

## Quick Slurm Reference

```bash
sbatch script.sh                          # submit
squeue -u $USER                           # your jobs
scontrol show job 12345                   # full detail
scancel 12345                             # cancel
scontrol hold/release 12345              # hold/release pending job
sacct -j 12345 --format=JobID,State,Elapsed,MaxRSS,ExitCode
salloc -N1 -p batch --qos=debug -t 1:00:00 -A myproject
```

Job state codes: `PD`=Pending, `R`=Running, `CD`=Completed, `CA`=Cancelled, `F`=Failed, `TO`=Timeout

## Minimal Job Script — AMD GPU

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -N 2
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH -t 1:00:00
#SBATCH -o job_%j.out
#SBATCH -e job_%j.err

module load PrgEnv-amd
module load amd/5.7.1
module load rocm/5.7.1
module load craype-accel-amd-gfx90a
module load cray-mpich

export MPICH_GPU_SUPPORT_ENABLED=1
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH

# 8 GCDs per node × 2 nodes = 16 total GPU tasks
srun -N 2 --ntasks-per-node=8 --gpus-per-task=1 ./my_hip_app
```

## Minimal Job Script — CPU Only

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -N 4
#SBATCH -p batch
#SBATCH --qos=regular
#SBATCH --ntasks-per-node=56    # 56 allocatable cores (not 64)
#SBATCH -t 2:00:00
#SBATCH -o job_%j.out

module load PrgEnv-gnu
module load cray-mpich

srun ./my_mpi_app
```

## Cray Programming Environment

> **Always use Cray compiler wrappers** (`cc`, `CC`, `ftn`) instead of `gcc`/`g++`/`gfortran`. The wrappers automatically link MPI, LibSci, and other libraries.

```bash
cc  my_app.c    -o my_app          # C (wraps Clang, GCC, or AMD depending on PrgEnv)
CC  my_app.cpp  -o my_app          # C++
ftn my_app.f90  -o my_app          # Fortran

# For HIP GPU kernels
hipcc --offload-arch=gfx90a my_kernel.cpp -o my_kernel
# Or compile GPU code with AMD wrapper and link with CC:
CC -xhip -offload-arch=gfx90a my_app.cpp -o my_app
```

### Programming Environment Modules

| PrgEnv module | Compiler toolchain | Use case |
|---------------|--------------------|---------|
| `PrgEnv-cray` (default) | LLVM/Clang | General; supports OpenMP offload |
| `PrgEnv-gnu` | GCC | Broad compatibility |
| `PrgEnv-amd` | AMD LLVM/Clang | Best for HIP/ROCm GPU code |

```bash
module load PrgEnv-amd               # switch to AMD compilers
module load amd/5.7.1                # AMD compiler version
module load rocm/5.7.1               # ROCm runtime (HIP, etc.)
module load craype-accel-amd-gfx90a  # REQUIRED for GPU compilation
module load cray-mpich               # Cray MPI
```

### GPU-Aware MPI

```bash
export MPICH_GPU_SUPPORT_ENABLED=1   # enable direct GPU-to-GPU MPI
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH
```

Without `MPICH_GPU_SUPPORT_ENABLED=1`, MPI communication involving GPU buffers will fail or fall back to slow CPU copies.

## AMD MI250X GPU Architecture

Each physical MI250X has **2 GCDs** (Graphics Compute Dies), each appearing as an independent GPU device:
- 4 GPUs × 2 GCDs = **8 GPU devices per node** (seen as `/dev/dri/renderD*`)
- Use `--gpus-per-task=1` to assign 1 GCD per MPI rank
- `ROCR_VISIBLE_DEVICES` selects which GCDs are accessible

```bash
# Run 8 tasks per node, each using 1 GCD
srun --ntasks-per-node=8 --gpus-per-task=1 ./my_app

# Explicitly bind GPUs to tasks
srun --ntasks-per-node=8 --gpus-per-task=1 \
  --gpu-bind=closest ./my_app
```

## Storage

| Filesystem | Variable | Path | Quota | Purge | Use for |
|-----------|----------|------|-------|-------|---------|
| Home | — | `/ccs/home/user` | 50 GB | None | Code, configs |
| Member work | `$MEMBERWORK` | `/lustre/orion/<proj>/scratch/user` | 50 TB | **90-day auto-purge** | Primary job I/O |
| Project work | `$PROJWORK` | `/lustre/orion/<proj>/proj-shared/` | varies | None | Shared project data |
| World work | `$WORLDWORK` | `/lustre/orion/<proj>/world-shared/` | varies | None | Publicly accessible |
| Burst buffer | — | `/mnt/bb/<user>` | 3.84 TB | Job lifetime | Fast local NVMe |

> **Warning:** Files in `$MEMBERWORK` not accessed for **90 days** are automatically deleted. Check ages with `lfs find $MEMBERWORK --atime +90`.

To request burst buffer (NVMe), add `#SBATCH -C nvme` and access at `/mnt/bb/$USER/`.

## Interactive Jobs

```bash
# Interactive debug session (1 node, 1 hour)
salloc -N 1 -p batch --qos=debug -t 1:00:00 -A myproject

# Inside the allocation, launch GPU tasks
srun --ntasks-per-node=8 --gpus-per-task=1 ./my_app
```

## Modules

```bash
module avail                    # list available modules
module spider <pkg>             # search for a package
module list                     # show what's loaded
module purge                    # unload all
```

## Common Gotchas

- Assuming 64 allocatable cores → use 56 (`--ntasks-per-node=56`) due to core specialization
- Forgetting `MPICH_GPU_SUPPORT_ENABLED=1` → GPU-aware MPI silently falls back or errors
- Forgetting `LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:...` → runtime library not found
- Using `gcc` directly instead of `cc` → misses Cray MPI/LibSci linking
- Skipping `module load craype-accel-amd-gfx90a` → GPU offload architecture not set
- Writing to `$HOME` instead of `$MEMBERWORK` → quota exceeded
- `$MEMBERWORK` files older than 90 days → silently deleted

## Additional Resources

- Annotated job script examples: [references/job-scripts.md](references/job-scripts.md)
- Storage details, 90-day purge, HPSS archiving: [references/storage.md](references/storage.md)
- Cray PrgEnv, ROCm, HIP, profiling: [references/programming-env.md](references/programming-env.md)
- OLCF docs: https://docs.olcf.ornl.gov/systems/frontier_user_guide.html
