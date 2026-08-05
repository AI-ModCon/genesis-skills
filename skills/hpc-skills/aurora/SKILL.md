---
name: aurora
description: >
  ALCF Aurora supercomputer at Argonne National Laboratory. Use when
  submitting PBS jobs on Aurora, specifying project accounts (-A) and required
  filesystem declarations (-l filesystems=home:flare), choosing queues (debug,
  prod, prod-large), writing job scripts for Aurora's 6× Intel Ponte Vecchio
  GPU per-node architecture, using the Intel oneAPI/SYCL programming
  environment, working with DAOS or Lustre flare storage, or loading Intel
  modules.
compatibility: Must be logged into an Aurora login node (aurora.alcf.anl.gov).
metadata:
  version: "1.0"
  system: aurora
  facility: alcf
  scheduler: pbs
allowed-tools: Bash(qsub *) Bash(qstat *) Bash(qdel *) Bash(qhold *) Bash(qrls *) Bash(qalter *) Bash(pbsnodes *) Bash(module *) Read Write
---

# Aurora — ALCF Supercomputer

Aurora is Argonne National Laboratory's Intel-GPU-based exascale system. It uses **PBS** as its workload manager.

## System Overview

| Component | Specification |
|-----------|--------------|
| Nodes | 10,624 compute nodes across 166 racks |
| CPU | 2× Intel Xeon CPU Max 9470 (52 cores each, 512 GB DDR5 + 64 GB HBM per socket) |
| GPU | 6× Intel Data Center GPU Max (Ponte Vecchio) per node |
| Network | HPE Slingshot-11 (8 NICs/node), 3-level dragonfly |
| Primary storage | DAOS 260 PB (≥31 TB/s peak) + Lustre `flare` |

## Critical Requirements

> **Two directives are MANDATORY on Aurora. Missing either will cause job failure.**

```bash
#PBS -A myproject                          # project account (required)
#PBS -l filesystems=home:flare             # declare all filesystems accessed (required)
```

The `filesystems` directive must list every filesystem your job reads or writes. Valid tokens: `home`, `flare`, `grand`, `eagle`. Use colon-separated: `filesystems=home:flare`.

## Queues

| Queue | Max nodes | Max walltime | Simultaneous jobs | Notes |
|-------|-----------|-------------|-------------------|-------|
| `debug` | 10 | 1 hr | 1 running, 1 queued | Development and testing |
| `prod` | 496 | 24 hr | varies | Standard production |
| `prod-large` | 10,624 | 24 hr | limited | Full-system runs; needs approval |

Specify with `#PBS -q debug` etc.

## Quick PBS Reference

```bash
qsub script.sh                         # submit
qstat -u $USER                         # your jobs
qstat -f 12345                         # full job detail
qdel 12345                             # cancel
qhold 12345                            # hold pending job
qrls 12345                             # release hold
qstat -Q                               # list queues
pbsnodes -a                            # all node states
```

Job state codes: `Q`=Queued, `R`=Running, `H`=Held, `E`=Exiting, `F`=Finished

## Minimal Job Script — Full Node GPU

```bash
#!/bin/bash
#PBS -N myjob
#PBS -A myproject
#PBS -q prod
#PBS -l select=1:ncpus=104:ngpus=6
#PBS -l walltime=01:00:00
#PBS -l filesystems=home:flare
#PBS -o myjob.out
#PBS -e myjob.err

cd $PBS_O_WORKDIR

module use /soft/modulefiles
module load oneapi/eng-compiler/2024.06.28.002

export ONEAPI_DEVICE_SELECTOR=level_zero:*

# mpiexec is the launcher on Aurora (not srun)
mpiexec -n 6 -ppn 6 --cpu-bind=depth --gpu-bind=closest \
  ./my_gpu_app
```

## Resource Specification

```bash
# Full node (104 CPUs = 2 sockets × 52 cores, 6 GPUs)
#PBS -l select=1:ncpus=104:ngpus=6

# Half node
#PBS -l select=1:ncpus=52:ngpus=3

# Multiple nodes (e.g., 8 full nodes)
#PBS -l select=8:ncpus=104:ngpus=6

# Hybrid MPI+OpenMP (1 MPI rank per GPU, 17 threads each)
#PBS -l select=1:ncpus=104:ngpus=6:mpiprocs=6:ompthreads=17
```

## Intel oneAPI Programming Environment

```bash
# Load the oneAPI programming environment
module use /soft/modulefiles
module load oneapi/eng-compiler/2024.06.28.002

# C/C++ compilers
icx  my_app.c    -o my_app          # Intel C compiler
icpx my_app.cpp  -o my_app          # Intel C++ compiler
icpx -fsycl my_gpu.cpp -o my_gpu    # SYCL for GPU

# Fortran
ifx  my_app.f90  -o my_app

# MPI wrappers (built on Intel MPI)
mpicc   my_mpi.c   -o my_mpi
mpicxx  my_mpi.cpp -o my_mpi
mpifc   my_mpi.f90 -o my_mpi

# MPI launcher (use mpiexec, NOT srun on Aurora)
mpiexec -n <total_ranks> -ppn <ranks_per_node> ./my_app
```

### Key GPU Environment Variables

| Variable | Purpose |
|----------|---------|
| `ONEAPI_DEVICE_SELECTOR=level_zero:*` | Select all Level Zero (Intel GPU) devices |
| `ZE_AFFINITY_MASK=0,1,2,3,4,5` | Select GPUs 0–5 on a node |
| `I_MPI_OFFLOAD=1` | Enable GPU-aware MPI |
| `SYCL_PI_TRACE=1` | Debug: trace SYCL plugin activity |

## Modules

```bash
module avail                           # list available modules
module use /soft/modulefiles           # access Spack PE modules
module load oneapi/...                 # Intel oneAPI compiler suite
module load cray-mpich                 # Cray MPICH (alternative MPI)
module load cmake python               # build tools
module list                            # show loaded
module purge                           # unload all
```

## Storage

| Filesystem | Token | Path | Quota | Purge | Use for |
|-----------|-------|------|-------|-------|---------|
| Home | `home` | `/home/user` | 100 GB | None | Code, configs |
| Flare (Lustre) | `flare` | `/lus/flare/projects/<proj>/` | large | None | Primary job I/O |
| DAOS | n/a | via `dfuse` or daos API | 260 PB | None | Ultra-high-performance |

**All filesystems accessed must be declared with `-l filesystems=`.**

### DAOS Quick Reference

```bash
# Check your pools
daos pool query --pool <pool_label>

# Create a POSIX container
daos container create --pool <pool> --type POSIX --label mycontainer

# Mount container as a POSIX filesystem
mkdir -p /tmp/daos_mount
dfuse --pool <pool> --container mycontainer --mountpoint /tmp/daos_mount

# Use it like any directory
ls /tmp/daos_mount

# Unmount
fusermount3 -u /tmp/daos_mount
```

## Interactive Jobs

```bash
qsub -I \
  -A myproject \
  -q debug \
  -l select=1:ncpus=104:ngpus=6 \
  -l walltime=1:00:00 \
  -l filesystems=home:flare
```

## Common Gotchas

- Missing `-l filesystems=` → job crashes at startup with filesystem error
- Using `srun` instead of `mpiexec` → not available; use `mpiexec`
- Not loading `module use /soft/modulefiles` before `module load oneapi` → module not found
- Writing large files to `home` → quota exceeded; use `flare` for job I/O
- `ZE_AFFINITY_MASK` not set → all 6 GPUs compete for rank 0's device

## Additional Resources

- Annotated job script examples: [references/job-scripts.md](references/job-scripts.md)
- DAOS, flare, Globus data transfer: [references/storage.md](references/storage.md)
- oneAPI, SYCL, GPU programming reference: [references/programming-env.md](references/programming-env.md)
- ALCF docs: https://docs.alcf.anl.gov/aurora/
