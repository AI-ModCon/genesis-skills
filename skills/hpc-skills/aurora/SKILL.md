---
name: aurora
description: >-
  ALCF Aurora supercomputer at Argonne National Laboratory. Use when
  submitting PBS jobs on Aurora, choosing a queue (debug, debug-scaling,
  capacity, prod), declaring filesystems (-l filesystems=home:flare,
  daos_user), binding MPI ranks to CPU cores and Intel Data Center GPU Max
  (Ponte Vecchio) GPUs or GPU tiles (6 GPUs / 12 tiles per node,
  gpu_tile_compact.sh, ZE_AFFINITY_MASK), launching with mpiexec (Cray PALS),
  building with the oneAPI compilers and Aurora MPICH (icx/icpx/ifx,
  mpicc/mpicxx/mpifort, SYCL, OpenMP offload), using DAOS or the Flare Lustre
  filesystem, or loading Aurora modules (oneapi, frameworks, /soft).
compatibility: Must be logged into an Aurora login node (aurora.alcf.anl.gov).
metadata:
  version: "2.0"
  system: aurora
  facility: alcf
  scheduler: pbs
allowed-tools: Bash(qsub *) Bash(qstat *) Bash(qdel *) Bash(qhold *) Bash(qrls *) Bash(qalter *) Bash(pbsnodes *) Bash(module *) Bash(myquota *) Read Write
---

# Aurora — ALCF Supercomputer

Aurora is Argonne National Laboratory's Intel-GPU exascale system (HPE Cray EX). It uses **PBS Pro** for scheduling and **Cray PALS `mpiexec`** to launch parallel jobs. There is no Slurm and no `srun`.

Queue limits, module versions, and filesystem names change. The values below were checked on Aurora in October 2026; confirm current values with the commands in [Checking Live Configuration](#checking-live-configuration) before relying on them.

## Safety

- Show the user the job script (or `qsub` command) and the project it will charge, and get confirmation before running `qsub`. Each job charges node-hours for every node requested, for the walltime used.
- Only `qdel`, `qhold`, or `qalter` jobs this session submitted, or jobs the user names.
- Prefer `debug` with a short walltime for first runs of a new script.

## System Overview

| Component | Specification |
|-----------|--------------|
| Nodes | 10,624 compute nodes in 166 racks (64 nodes per rack) |
| CPU | 2× Intel Xeon CPU Max 9470C per node: 52 cores × 2 hyperthreads each, 512 GB DDR5 + 64 GB HBM per socket |
| GPU | 6× Intel Data Center GPU Max 1550 (Ponte Vecchio, PVC) per node; **each GPU has 2 tiles = 12 tiles per node** |
| GPU memory | 128 GB HBM2e per GPU (64 GB per tile), 768 GB per node |
| Network | HPE Slingshot-11, 8 NICs per node, dragonfly (one rack = one dragonfly group) |
| Storage | Flare Lustre (91 PB, `/lus/flare/projects`), DAOS object store (~200 PB usable), Gecko Lustre for `/home` |

### Node Layout You Must Know

- **Socket 0** owns cores 0–51 (hyperthreads 104–155) and GPUs 0, 1, 2. **Socket 1** owns cores 52–103 (hyperthreads 156–207) and GPUs 3, 4, 5.
- **Cores 0 and 52 (hardware threads 0, 104, 52, 156) are reserved for the OS.** Only 102 physical cores are available to applications: 1–51 and 53–103.
- Each GPU exposes 2 tiles (also called stacks). By default (`ZE_FLAT_DEVICE_HIERARCHY=COMPOSITE`), SYCL and Level Zero see **6 devices**, each with 2 sub-devices. The `frameworks` (Python AI/ML) module sets `FLAT`, which exposes **12 devices**, one per tile.
- The most common layout is **12 MPI ranks per node, one per tile**. The second most common is 6 ranks per node, one per GPU.

## Critical Requirements

Every job needs these three, or `qsub` rejects it immediately:

```bash
#PBS -A <project>                  # allocation/project name
#PBS -l walltime=HH:MM:SS
#PBS -l filesystems=home:flare     # every filesystem the job touches
```

- **Filesystem names on Aurora:** `home`, `flare`, `daos_user`, `daos_perf` (only for teams ALCF has approved). A submit hook maps each to a PBS resource (`home_fs`, `flare_fs`, ...), so `home_fs:flare_fs` and `daos_user_fs` are also accepted. **`grand` and `eagle` are Polaris filesystems and are not mounted on Aurora.**
- Missing `filesystems` → `qsub: Resource: filesystems is required to be set.`
- An unknown name → `qsub: Invalid filesystem identifiers grand, eagle`

Strongly recommended:

```bash
#PBS -l select=<nodes>             # nodes are allocated whole; no ncpus/ngpus needed
#PBS -l place=scatter
#PBS -q <queue>
```

**Request nodes, not cores.** Nodes are exclusive (`sharing = force_exclhost`), so you always get the whole node. In PBS, `ncpus` counts hardware threads (208 per node), not cores. `-l select=1:ncpus=52:ngpus=3` is accepted but still allocates and charges for a full node. Use `-l select=N`.

**Submit jobs from your project directory** (`/lus/flare/projects/<project>`), not from `$HOME`. Never submit from `/soft/modulefiles`; an interactive job started there ends abruptly.

## Queues

Submit to `debug`, `debug-scaling`, `capacity`, `prod`, or `visualization`. `prod` is a **routing queue**: you cannot submit to `small`, `medium`, or `large` directly.

| Queue | Nodes | Max walltime | Per-user limits | Notes |
|-------|-------|-------------|-----------------|-------|
| `debug` | 1–2 | 1 hr | 1 job (running or queued) | 64-node pool; nodes may be shared |
| `debug-scaling` | up to 256 | 1 hr | 1 job (running or queued) | Scaling tests and small multi-node runs |
| `capacity` | 1–16 | 168 hr (7 days) | 2 running, 5 queued | 512 nodes total across all users |
| `prod` → `small` | 256–1,024 | 12 hr | | Routed automatically by node count |
| `prod` → `medium` | 1,025–1,999 | 18 hr | | |
| `prod` → `large` | 2,000–10,624 | 24 hr | | |
| `visualization` | 1–32 | 8 hr | 1 running | By request only |

- **`prod` rejects jobs under 256 nodes**: `qsub: Job violates queue and/or server resource limits`. For 3–255 nodes use `debug-scaling` (≤1 hr) or `capacity` (≤16 nodes). Aurora has no small-node production queue.
- Jobs from projects with a negative allocation balance are routed to `backfill-small`, `backfill-medium`, or `backfill-large`, which run at low priority.
- Per project, the `prod` execution queues allow 10 jobs running and 100 queued.
- `prod-large` also exists: a routing queue for ≥1,920-node jobs that feeds `large` and `backfill-large`.

## Minimal Job Script — 12 Ranks per Node, One per GPU Tile

```bash
#!/bin/bash -l
#PBS -N myjob
#PBS -A <project>
#PBS -q debug
#PBS -l select=2
#PBS -l place=scatter
#PBS -l walltime=00:30:00
#PBS -l filesystems=home:flare
#PBS -k doe
#PBS -j oe

cd ${PBS_O_WORKDIR}

NNODES=$(wc -l < ${PBS_NODEFILE})
NRANKS_PER_NODE=12
NTOTRANKS=$(( NNODES * NRANKS_PER_NODE ))

# 8 physical cores per rank, 6 ranks per socket, skipping reserved cores 0 and 52
CPU_BIND="list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100"

export OMP_NUM_THREADS=1

# gpu_tile_compact.sh (on the default PATH) sets ZE_AFFINITY_MASK so that
# local rank 0 -> GPU 0 tile 0, rank 1 -> GPU 0 tile 1, ..., rank 11 -> GPU 5 tile 1
mpiexec -n ${NTOTRANKS} --ppn ${NRANKS_PER_NODE} --cpu-bind=${CPU_BIND} \
    gpu_tile_compact.sh ./my_gpu_app
```

The oneAPI compilers and Aurora MPICH are loaded by default. You do not need a `module load` for a plain SYCL, OpenMP, or MPI application.

For 6 ranks per node (one per whole GPU), use `gpu_dev_compact.sh` and `--cpu-bind=list:1-16:17-32:33-48:53-68:69-84:85-100`. See [references/gpu-affinity.md](references/gpu-affinity.md) for hybrid MPI+OpenMP, `--gpu-bind`, `FLAT` mode, and multiple compute command streamers (CCS).

## Quick PBS Reference

```bash
qsub script.sh                           # submit
qsub -I -l select=1 -l walltime=1:00:00 -l filesystems=home:flare -A <project> -q debug   # interactive
qstat -u $USER                           # your jobs
qstat -f <jobid>                         # full detail, including the "comment" field explaining why a job is not running
qstat -x -f <jobid>                      # finished jobs
qdel <jobid>                             # cancel
qhold <jobid> / qrls <jobid>             # hold / release
qalter -l walltime=02:00:00 <jobid>      # modify a queued job
```

Job states: `Q` queued, `R` running, `H` held, `E` exiting, `F` finished (shown with `qstat -x`), `B` array job with subjobs started.

## Job Arrays

Use `-J`, not `-t` (Torque syntax; Aurora's `qsub` rejects it with `invalid option -- 't'`). **Arrays also need `-r y`**: the server default `-r n` causes `cannot submit non-rerunable Array Job`.

```bash
#PBS -J 1-50%5        # indices 1..50, at most 5 running at once
#PBS -r y             # required for arrays on Aurora
# inside the job: ${PBS_ARRAY_INDEX}
```

**Every subjob counts toward the queue's per-user queued limit, even with a `%N` throttle.** In `capacity` (5 queued per user), `-J 1-5` is accepted, but `-J 1-6` and `-J 1-20%2` are rejected with `would exceed queue generic's per-user limit`. `debug` and `debug-scaling` allow only 1 job. For more than 5 cases, pack several cases into one multi-node job, or use a workflow tool.

## mpiexec Essentials

`mpiexec` comes from Cray PALS. Common options:

| Option | Effect |
|--------|--------|
| `-n N` / `--np N` | Total ranks |
| `--ppn N` / `-ppn N` | Ranks per node |
| `--depth=D` | Hardware threads per rank (used with `--cpu-bind=depth`) |
| `--cpu-bind=list:a-b:c-d:...` | Explicit per-rank CPU sets (recommended on Aurora) |
| `--cpu-bind=depth` | Consecutive blocks of `--depth` threads, skipping reserved cores; can split a rank across sockets |
| `--gpu-bind=list:0.0:0.1:...` | Per-rank tile visibility (alternative to `gpu_tile_compact.sh`); `list:0:1:2:3:4:5` binds whole GPUs |
| `--env VAR=VAL` | Set an environment variable for the ranks (`--genvall`, export everything, is the default) |
| `--hostfile FILE` | Node list (defaults to `$PBS_NODEFILE`) |
| `--no-vni` | Skip Slingshot VNI allocation (currently required for DAOS jobs) |
| `--line-buffer`, `--label` | Readable output |

`--gpu-bind` accepts only `none`, `per_task:<n>`, `single:<n>`, and `list:<list>`. Anything else, such as `closest` or `map_gpu:` (Slurm syntax), fails at launch with `Invalid GPU visibility keyword` and exit code 127.

## Modules

The default environment already loads `oneapi/release/<version>`, `mpich`, `cray-pals`, `libfabric`, and `gcc`. Common commands:

```bash
module -t list                       # what is loaded
module avail oneapi                  # alternative oneAPI releases
module load cmake hdf5               # Spack PE packages in the default path
module load frameworks               # THE way to get Python: PyTorch, TensorFlow, vLLM, mpi4py, ... (sets ZE_FLAT_DEVICE_HIERARCHY=FLAT)
module use /soft/modulefiles         # extra software outside the PE: daos, kokkos, ...
module load daos                     # needs /soft/modulefiles
```

- **For any Python work, start with `module load frameworks`.** If you need extra packages, layer a venv on it (`python3 -m venv --system-site-packages`). Do not use the Spack PE `python` module or your own conda install for applications. The Spack `python` exists as a dependency of other Spack packages, and mixing it with `frameworks` causes conflicts.
- There is no `PrgEnv-*`, `cray-mpich`, or Intel MPI on Aurora. MPI is **Aurora MPICH**, with the wrappers `mpicc`, `mpicxx`, and `mpifort`.
- Loading libraries from `/soft` or project directories at large node counts is slow. See Copper in [references/programming-env.md](references/programming-env.md).

## Checking Live Configuration

```bash
qstat -Qf <queue>      # resources_min/max.nodect, walltime, max_run, max_queued
qstat -Bf | grep -A2 valid_filesystems
pbsnodes -av | less    # resources_available.ncpus/ngpus, state
module -t list
myquota                # home and project quotas
```

## Common Gotchas

- **Small job in `prod`** → rejected below 256 nodes. Use `debug`, `debug-scaling`, or `capacity`.
- **More than 2 nodes in `debug`** → rejected. Use `debug-scaling`.
- **A second `debug` or `debug-scaling` job** → `would exceed queue generic's per-user limit of jobs in 'Q' state`.
- **`grand`/`eagle` in `filesystems`** → rejected. They are not mounted on Aurora.
- **No GPU binding** → every rank sees all 6 GPUs and the runtime picks device 0, so all ranks on a node pile onto one GPU. Use `gpu_tile_compact.sh` or `gpu_dev_compact.sh`, or set `ZE_AFFINITY_MASK` per rank.
- **`--cpu-bind=depth` without `--depth`** → each rank gets one hardware thread, so OpenMP threads all share it. `--cpu-bind=depth:17` is **silently ignored** in the same way; the thread count goes in `--depth=17`.
- **Binding to core 0 or 52** → launch fails (`cpubind list:0[0] has fewer CPUs (0) than depth (1)`). Those cores are reserved; start lists at 1 and 53.
- **PyTorch DDP with `backend="ccl"`** → fails in `frameworks/2026.1.0` with `Unknown backend type ccl`. Use `backend="xccl"`; no `oneccl_bindings_for_pytorch` import is needed. See the DDP setup in [references/job-scripts.md](references/job-scripts.md).
- **`module load python` or a personal conda/pip install for Python apps** → use `module load frameworks` (plus a `--system-site-packages` venv if needed).
- **`srun`, `mpifc`, `mpiicx`, `I_MPI_*` variables** → none of these exist or apply on Aurora.
- **Job arrays without `-r y`** → rejected.
- **Expecting PBS email (`-m be`, `-M`)** → email notifications are not currently enabled on Aurora. Check jobs with `qstat` (`qstat -x` once finished), or have the script write its own completion marker.
- **Compute nodes have no direct internet access** → set `http_proxy`/`https_proxy` to `http://proxy.alcf.anl.gov:3128`.
- **Multiple `mpiexec` calls in one script** → check each exit code. Node or network failures can return non-zero.

## Additional Resources

- Annotated job scripts (debug, debug-scaling, capacity, prod, arrays, DAOS, Python, multiple apps per node): [references/job-scripts.md](references/job-scripts.md)
- CPU and GPU affinity, tiles, `ZE_AFFINITY_MASK`, CCS, HBM: [references/gpu-affinity.md](references/gpu-affinity.md)
- Compilers, SYCL/OpenMP offload flags, MPICH, MKL, Python, profiling: [references/programming-env.md](references/programming-env.md)
- Home, Flare, DAOS, Globus: [references/storage.md](references/storage.md)
- ALCF docs: https://docs.alcf.anl.gov/aurora/ (running jobs: https://docs.alcf.anl.gov/aurora/running-jobs-aurora/)
