# Running AthenaK

Upstream docs: [Running the code](https://ias-astrophysics.github.io/athenak-docs/running_the_code.html), [notes for specific machines](https://ias-astrophysics.github.io/athenak-docs/notes_specific_machines.html).

Checked against AthenaK commit c5a0d7f (2026-11-09).

```bash
mpiexec -n <N> <build>/src/athena -i <file> -t <hh:mm:ss> [-d <rundir>] [block/key=value ...]
```

Without MPI, run `<build>/src/athena -i <file>`. For batch scripts, binding and filesystems,
see [Cluster submission](#cluster-submission) below.

## Command-line flags

All flags are parsed in `src/main.cpp`. A flag must be exactly `-x`. Anything containing
both `/` and `=` is taken as a parameter override. A flag missing its argument (or an unknown
`-x` with none) gives `-x must be followed by a valid argument`; an unknown `-x <arg>`
prints the help and exits. Any other argument is ignored.

| Flag | Argument | Effect |
|---|---|---|
| `-i <file>` | input file | read parameters (at least one of `-i`/`-r` is required) |
| `-r <file>` | restart file | restart. With `-i` too, the input file's values override the restart's |
| `-d <dir>` | run directory | `mkdir` + `chdir` **after** reading input/restart and building the mesh. All outputs go there |
| `-t hh:mm:ss` | wall-time limit | stop cleanly when elapsed wall time ≥ limit (below) |
| `-w <sec>` | watchdog timeout | abort if a rank stops making progress (below) |
| `-n` | — | parse the input plus overrides, print the merged parameter set, exit |
| `-m` | — | build the mesh, write `mesh_structure.dat` (2D/3D only), exit. Takes no argument |
| `-v` | — | validate: build everything on one MeshBlock, print unused-parameter warnings, exit |
| `-c` | — | print the build configuration (pgen, precision, MPI, OpenMP), exit |
| `-h` | — | usage plus configuration, exit |
| `block/key=value` | — | override an **existing** parameter (cannot add new ones) |

Notes:
- The input and restart files are read before `-d` takes effect, so relative `-i`/`-r`
  paths are resolved from the launch directory.
  - `-m` exits before the `chdir`, so `mesh_structure.dat` lands in the launch directory.
    Plot it with `<athenak>/vis/python/plot_mesh.py`.
- `-v` sets the root grid to a single MeshBlock and turns refinement off, then builds the
  physics, pgen and outputs. It catches missing required parameters, typos and
  pgen/EOS-table problems in seconds. It does *not* check mesh divisibility (use `-m`),
  and it creates the empty output subdirectories (`bin/`, `rst/`, …).
  - With refinement off, `-v` ignores `<mesh_refinement>`, `<refined_region*>`,
    `<amr_criterion*>` and `<z4c_amr*>`: no typo warnings and no required-key errors there
    (e.g. a missing `max_nmb_per_rank`). For SMR/AMR inputs also run `-m`, which builds the
    real tree and catches a missing `max_nmb_per_rank`. Misspelt refinement keys are reported
    only by a real run, at start-up (before the first cycle).
- `-n` dumps the merged parameter set in input-file syntax, ending with `<par_end>`. Use it
  to see the exact parameters a restart file contains: `athena -r <file.rst> -n`.
- `Kokkos::initialize` runs before any flag is handled, so a GPU build needs a visible GPU even
  for `-n`, `-v`, `-m`, `-c` and `-h`. Without one, Kokkos aborts at initialisation. On login
  nodes, check parameter files with a CPU build of the same pgen, or in a short interactive job.
- Kokkos flags pass straight through, e.g. `--kokkos-print-configuration`,
  `--kokkos-num-threads=<n>`, `--kokkos-device-id=<n>`,
  `--kokkos-map-device-id-by=mpi_rank|random`.

## Wall-time limit `-t`

- The timer starts before the input is read, so setup time counts. The limit is checked
  once per cycle, after that cycle's outputs and AMR. Under MPI, rank 0's clock is broadcast.
- When the limit is reached, the loop exits and `Finalize` writes **every** output block
  once more: a restart dump only if the input has an `<outputN>` with `file_type = rst`.
  - The message is `Terminating on wall clock limit` (reproduced: final `bin` and `rst` written).
- Set `-t` below the scheduler's limit, leaving room for one cycle plus a full set of outputs.
- Always give `hh:mm:ss`. `-t 600` is undefined (see `references/troubleshooting.md`).

## Watchdog `-w`

- `-w <sec>` starts one pthread per rank before the initial outputs. Every `<sec>` seconds
  it checks a timestamp, and if the timestamp has not changed it prints
  `[WATCHDOG (...)] Rank R is not progressing.` and calls `abort()`.
  - Rank 0 also logs `Starting.` and `Everything is fine.` to stderr at each check.
- The timestamp is renewed only at the **top of each cycle** (`src/driver/driver.cpp`,
  `Execute`). Consequences:
  - `<sec>` must exceed the slowest whole cycle, including that cycle's outputs (large
    `rst`/`bin` dumps) and AMR/load balancing.
  - The initial outputs (before cycle 0) and the final outputs in `Finalize` (after the
    last cycle) run under the same timer with no ping. A slow final restart dump can be
    killed by the watchdog.
  - Setup before the driver starts (mesh build, pgen, initial-data readers) is not
    covered. The watchdog starts after it.
- Use it to turn a hung MPI job into a quick failure instead of spending the remaining wall time.

## Restarts

```bash
mpiexec -n <N> <build>/src/athena -r <rundir>/rst/<basename>.<nnnnn>.rst -d <rundir> \
        time/tlim=<new> -t <hh:mm:ss>
```

- Restart files are `rst/<basename>.<nnnnn>.rst`. With `single_file_per_rank = true`
  they are `rst/rank_<8 digits>/<basename>.<nnnnn>.rst`. Pass any one rank's path; the
  path must contain `/rank_`, and each rank substitutes its own number.
- The run continues from the stored `time`/`ncycle`. No initial outputs are written on
  restart, and output counters continue.
  - Reproduced: restart at cycle 49 with `time/tlim=0.02` gave
    `Terminating on time limit`, `time=2.000000e-02 cycle=85`.
- Overrides use the same `block/key=value` syntax, but only for keys stored in the restart.
  The restart stores every parameter the run read, including defaults (tagged
  `# Default value added at run time`), so you can override a defaulted key such as
  `hydro/dfloor=...`. List them with `athena -r <file.rst> -n`.
- To add a key that the restart lacks, also pass `-i <small file>` holding just that block
  and key. Values read with `-i` override the restart's (reproduced with `<hydro>/fofc`).
  Which keys are safe to change is covered in `references/input-format.md`.
- Expect "not used" warnings for `<problem>` initial-condition keys and `<time>/start_time` on restart.
- `MeshBlock-cycles`, `cpu time used` and `zone-cycles/cpu_second` in the summary cover this run only.

## Parallel layout

- **MeshBlocks per rank.** Each rank owns one contiguous (Z-ordered) set of MeshBlocks,
  packed into a single `MeshBlockPack`, so its kernels loop over all of them at once.
  - You need at least one MeshBlock per rank (fatal otherwise).
  - On GPUs, give each rank many MeshBlocks, or large ones, to fill the device.
  - On uniform grids, make `nmb_total` divisible by the number of ranks (warning otherwise).
  - With AMR, `<mesh_refinement>/max_nmb_per_rank` caps the count and reserves device
    memory up front (`references/troubleshooting.md`).
- **GPUs: one MPI rank per GPU**, or per GCD/tile (MI250X GCD, PVC tile).
  - At `Kokkos::initialize`, the device is chosen round-robin by **node-local rank**,
    read from `OMPI_COMM_WORLD_LOCAL_RANK`, `MV2_COMM_WORLD_LOCAL_RANK`,
    `MPI_LOCALRANKID`, `SLURM_LOCALID` or `PMI_LOCAL_RANK`, over the visible devices
    (`KOKKOS_VISIBLE_DEVICES` if set).
  - If no local-rank variable is set, all ranks use device 0.
  - Either restrict visibility per rank (`CUDA_VISIBLE_DEVICES`, `ROCR_VISIBLE_DEVICES`,
    `ZE_AFFINITY_MASK`) or leave all GPUs visible and let Kokkos map one per local rank
    (Slurm: `--gpu-bind=none`). If multi-rank runs fail, see `references/troubleshooting.md`.
  - Multi-rank GPU runs need **GPU-aware MPI**: device buffers go straight to MPI.
- **OpenMP builds.** Set `OMP_NUM_THREADS` (or `--kokkos-num-threads`) per rank, e.g. one
  rank per socket or NUMA domain with threads filling it. Hybrid MPI+OpenMP requires
  `MPI_THREAD_MULTIPLE` from the MPI library.
- **Serial builds** run one thread per rank (flat MPI).

## Reading the terminal output

Startup (rank 0, stdout), then unused-parameter warnings (stderr):

```
Root grid = 4 x 4 x 1 MeshBlocks
Total number of MeshBlocks = 16
Number of logical  levels of refinement = 2 (3 levels total)
Number of physical levels of refinement = 0 (1 levels total)
Number of parallel ranks = 2
  Rank = 0: 8 MeshBlocks, cost = 8
  Rank = 1: 8 MeshBlocks, cost = 8
Load Balancing:
  Maximum normalized cost = 1, Average = 1
```

With refinement, per-level lines `Physical level = L (logical level = ...): N MeshBlocks, cost = C` are added.

Cycle lines, every `<time>/ndiag` cycles (default 1):

```
elapsed=8.501109e-02 cycle=50 time=1.256425e-02 dt=2.220571e-04
```

`elapsed` is wall seconds since start-up (before input is read). A shrinking `dt` is the first sign of trouble.
Set `ndiag` higher for production runs.

End-of-run summary (2-rank AMR run, trimmed):

```
Terminating on time limit          # or: cycle limit / wall clock limit
time=2.683280e-01 cycle=72
tlim=2.683280e-01 nlim=-1

Current number of MeshBlocks = 92                                   # AMR only
72 MeshBlocks created, 12 deleted by AMR                            # AMR only
0 communicated for load balancing, load balancing efficiency = 1.000000e+00   # AMR + MPI

MeshBlock-cycles = 5988
cpu time used  = 2.140238e+00
zone-cycles/cpu_second = 7.162419e+05
particle-updates/cpu_second = 0.000000e+00
```

- `cpu time used` is the wall time of the evolution loop only, without setup.
- `zone-cycles/cpu_second` is (MeshBlock-cycles × cells per MeshBlock) / that time, over the
  whole run (all ranks). Use it to compare builds and layouts.
- The load-balancing efficiency is the mean over cycles of
  (min MeshBlocks on any rank × nranks) / total MeshBlocks, so 1 is perfect. It
  **under-reports after a restart** (`references/troubleshooting.md`).

## Cluster submission

AthenaK needs nothing special from the scheduler beyond the layout above: one rank per
GPU/GCD/tile with the right device visibility, GPU-aware MPI, a `-t` margin under the
job's wall time, and an `rst` output block. Leave scripts, queues, binding and
filesystems to the matching `hpc-skills` skill. Load it and follow it; it will ask
before submitting.

| Scheduler / machine | Skill | Covers |
|---|---|---|
| Any Slurm cluster | `slurm` | `sbatch`/`srun`/`salloc`, `#SBATCH`, arrays, dependencies, accounting |
| Any PBS / OpenPBS cluster | `pbs` | `qsub`, `select`/`ncpus`/`ngpus`, walltime, arrays, dependencies |
| ALCF Aurora (PBS, Intel PVC) | `aurora` | queues, `mpiexec` (PALS), GPU-tile binding (`gpu_tile_compact.sh`, `ZE_AFFINITY_MASK`), oneAPI, Flare/DAOS storage and striping |
| OLCF Frontier (Slurm, AMD MI250X) | `frontier` | Cray PE (`CC`), ROCm modules, `--gpus-per-task`, `MPICH_GPU_SUPPORT_ENABLED`, Lustre |
| NERSC Perlmutter (Slurm, NVIDIA A100) | `perlmutter` | `-C gpu`/`-C cpu`, QOS, `--gpus-per-task`, `$PSCRATCH`, striping |

The upstream [Notes for Specific Machines](https://ias-astrophysics.github.io/athenak-docs/notes_specific_machines.html)
page also has configure lines and job scripts for machines with no hpc-skill (e.g. Polaris,
DeltaAI, Rusty, Della, Stellar, Apollo, Roar Collab). Use them with the generic `slurm` or
`pbs` skill, and check module versions before copying them.
