---
name: perlmutter
description: >
  NERSC Perlmutter supercomputer (Lawrence Berkeley National Lab). Use when
  submitting Slurm jobs on Perlmutter, choosing CPU vs GPU node types (-C cpu
  or -C gpu), selecting QOS tiers (debug, regular, premium, preempt, shared),
  checking NERSC allocations with the iris command or iris.nersc.gov, working
  with scratch storage ($SCRATCH/$PSCRATCH), loading modules, or writing job
  scripts for Perlmutter's NVIDIA A100 GPU nodes or AMD Milan CPU nodes.
compatibility: Must be logged into a Perlmutter login node (perlmutter.nersc.gov).
metadata:
  version: "1.0"
  system: perlmutter
  facility: nersc
  scheduler: slurm
allowed-tools: Bash(sbatch *) Bash(squeue *) Bash(scancel *) Bash(sinfo *) Bash(sacct *) Bash(salloc *) Bash(srun *) Bash(scontrol *) Bash(module *) Bash(iris *) Read Write
---

# Perlmutter — NERSC Supercomputer

Perlmutter is NERSC's GPU-accelerated Cray EX system at Lawrence Berkeley National Laboratory. It uses **Slurm** as its workload manager.

## System Overview

| Component | Specification |
|-----------|--------------|
| CPU nodes | 3,072 × 2× AMD EPYC 7763 "Milan" (128 cores/node, 512 GB RAM) |
| GPU nodes | 1,792 × 1× AMD Milan + 4× NVIDIA A100 40 GB (256 GB RAM) |
| Network | HPE Slingshot-11, 3-hop dragonfly |
| Scratch | 44 PB Lustre (all-flash, >6 TB/s) |

## Critical Requirements

> **Every Perlmutter job MUST include `-A <account>` and `-C cpu` or `-C gpu`.**
> Jobs without these will fail or target the wrong node type.

```bash
#SBATCH -A myproject       # your NERSC project name (required)
#SBATCH -C gpu             # or -C cpu (required)
```

## Partitions and QOS

| QOS | Max walltime | Max nodes | SU cost | Notes |
|-----|-------------|-----------|---------|-------|
| `debug` | 30 min | 8 (GPU), 8 (CPU) | 1× | Fast start; use for testing |
| `regular` | 12 hr | 256 (GPU), 512 (CPU) | 1× | Standard production |
| `premium` | 24 hr | same as regular | 2× | Higher priority |
| `preempt` | 48 hr | larger | 0.25× (GPU) / 0.5× (CPU) | Discounted; may be preempted |
| `shared` | 12 hr | — | fractional | Partial node, billed per resource |

**Big job discount:** jobs using ≥128 GPU nodes or ≥256 CPU nodes are charged at 50% SU rate.

Specify with `--qos=<name>`, e.g. `#SBATCH --qos=debug`.

## Quick Slurm Reference

```bash
sbatch script.sh                   # submit
squeue -u $USER                    # your jobs
squeue -j 12345 --start            # estimated start time
scontrol show job 12345            # full detail
scancel 12345                      # cancel
sacct -j 12345 --format=JobID,State,Elapsed,MaxRSS,ExitCode
salloc -N1 -C gpu --qos=debug -t 30:00 -A myproject   # interactive
```

Job state codes: `PD`=Pending, `R`=Running, `CD`=Completed, `CA`=Cancelled, `F`=Failed, `TO`=Timeout

## Minimal Job Script — GPU

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -N 1
#SBATCH --ntasks-per-node=4
#SBATCH --gpus-per-task=1
#SBATCH -c 32                    # CPU cores per task (128 cores / 4 tasks)
#SBATCH -t 2:00:00
#SBATCH -o job_%j.out
#SBATCH -e job_%j.err

module load cudatoolkit
export SLURM_CPU_BIND="cores"
srun ./my_gpu_app
```

## Minimal Job Script — CPU

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -C cpu
#SBATCH -q regular
#SBATCH -N 4
#SBATCH --ntasks-per-node=128
#SBATCH -t 4:00:00
#SBATCH -o job_%j.out

module load PrgEnv-gnu cray-mpich
srun ./my_mpi_app
```

## Checking Allocations

```bash
# CLI (run on any Perlmutter login node)
iris                          # summary of your projects
iris hours                    # CPU/GPU hours used vs. allocated
iris jobs                     # recent job history with charges
iris jobs --project myproject # filter by project

# Web
# https://iris.nersc.gov  — "My Account" tab shows remaining balance
```

## Storage

| Filesystem | Path | Quota | Purge policy | Use for |
|-----------|------|-------|-------------|---------|
| `$HOME` | `/global/homes/u/user` | 40 GB | None | Code, configs |
| `$SCRATCH` / `$PSCRATCH` | `/pscratch/sd/u/user` | 20 TB | **8-week auto-purge** | Job I/O |
| `$CFS` | `/global/cfs/cdirs/<proj>` | varies | None | Long-term project data |
| `$TMPDIR` | node-local | ~200 GB | Job lifetime | Fast temporary scratch |

> **Warning:** Files in `$SCRATCH` not accessed for 8 weeks are **automatically deleted** without notice. Always check ages with `lfs find $SCRATCH --atime +56 -maxdepth 2`.

Always write job output to `$SCRATCH`, not `$HOME`.

## Modules

```bash
module avail                      # list available modules
module spider <pkg>               # search for a package
module load PrgEnv-gnu            # GCC-based Cray PE
module load cudatoolkit           # NVIDIA CUDA for GPU nodes
module load cray-mpich            # Cray MPI library
module list                       # show what's loaded
module purge                      # unload everything
```

Cray compiler wrappers (`cc`, `CC`, `ftn`) link the correct MPI and libraries automatically when the appropriate `PrgEnv` module is loaded.

## Interactive Jobs

```bash
# GPU interactive session (debug QOS, 30 min)
salloc -N 1 -C gpu --qos=debug -t 30:00 -A myproject \
  --ntasks-per-node=4 --gpus-per-task=1 -c 32

# CPU interactive session
salloc -N 2 -C cpu --qos=debug -t 30:00 -A myproject \
  --ntasks-per-node=128

# Once inside, run steps with srun
srun -n 4 --gpus-per-task=1 ./my_app
```

## Common Gotchas

- Forget `-C cpu`/`-C gpu` → job may queue indefinitely or hit wrong partition
- Write to `$HOME` instead of `$SCRATCH` → quota exceeded, job fails
- `$SCRATCH` files older than 8 weeks → silently deleted
- Not setting `SLURM_CPU_BIND=cores` on GPU nodes → suboptimal CPU affinity
- Using wrong account name → charges wrong allocation or job rejected

## Additional Resources

- Annotated job script examples: [references/job-scripts.md](references/job-scripts.md)
- Storage details, Lustre striping, HPSS archiving: [references/storage.md](references/storage.md)
- Allocation system, iris, ERCAP, sacct: [references/allocations.md](references/allocations.md)
- NERSC docs: https://docs.nersc.gov/
