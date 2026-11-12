# Troubleshooting AthenaK

Upstream docs: [FAQ](https://ias-astrophysics.github.io/athenak-docs/faq.html).

Checked against AthenaK commit c5a0d7f (2026-11-09). Each item here was either
confirmed in the source or reproduced on a CPU build. AthenaK writes fatal errors as
`### FATAL ERROR in <file> at line <n>` followed by a one-line reason, on stdout.
Most of them call `std::exit(EXIT_FAILURE)`. Read the reason line first.

## Input parameters

**`### WARNING in .../parameter_input.cpp: input parameter <blk>/<key> = <val> was not used by the code (check for a typo)`**
- Printed once by rank 0 **to stderr**, after every class that reads parameters has been
  built and before the first cycle. With `-v`, it is printed and then the run stops.
  `<comment>` blocks are skipped.
- An unused optional parameter usually means a misspelled key: the code used its default.
  Example: `ndaig = 1` in `<time>` gives this warning and `ndiag` keeps its default.
- These warnings are expected and harmless (all reproduced):
  - unused dimensions in 1D/2D inputs, e.g. `<mesh>/ix2_bc`, `ix3_bc`, `<meshblock>/nx3`.
    Shipped inputs such as `inputs/hydro/sod.athinput` trigger them.
  - on restart: initial-condition keys in `<problem>` that the pgen reads only for a new
    run (e.g. `d_in`, `p_in`), and `<time>/start_time`.
  - `<problem>/pgen_name` in a binary built with a custom `-D PROBLEM=...`, which never reads it.
- Pre-flight any input with `athena -i <file> -v` (see `references/running.md`).

**`Parameter name '<key>' not found in block '<blk>'`**: a **required** parameter is
missing. Example: misspelling `cfl_number` gives this fatal error. Typos in required keys
are fatal; typos in optional keys only produce the warning above.

**`Parameter '<key>' in block '<blk>' on command line not found`** /
**`Block name '<blk>' on command line not found`**: a `block/key=value` override can only
**change** a parameter that already exists in the input file or restart. It cannot add a
new one. Add the key to the input file instead.

**`Invalid <block_name> '<name>' in input file`**: printed after the list of allowed block
names, and the run aborts via `Kokkos::abort` with a backtrace. A block name is accepted
if it *starts with* an allowed name (`output`, `amr_criterion`, `refined_region`, …).
The check runs only on files given with `-i`.

**`Problem generator name could not be found in <problem> block ...`**: `pgen_name` is
missing or names a pgen that is not built in. Rebuild with `-D PROBLEM=<dir/file>`
(`references/build.md`).

**`NoOp hydro|MHD ConsToPrim/PrimToCons called`** (abort, custom pgens): the pgen called the
hydro overload under MHD (pass `b`/`bcc`) or the reverse. With dynamical GRMHD, use
`pmbp->pdyngr->PrimToConInit(...)` / `ConToPrimBC(...)`, not the `<mhd>` EOS functions.

## Mesh and MeshBlock setup

| Message (reason line) | Fix |
|---|---|
| `Mesh must be evenly divisible by MeshBlocks` | `<mesh>/nxN` must be a multiple of `<meshblock>/nxN` |
| `MeshBlock must be >= 4 cells in each active dimension` / `Mesh must be >= 4 cells ...` | enlarge |
| `Number of cells in MeshBlock must be divisible by two in each dimension for SMR/AMR` | even MeshBlock sizes with refinement |
| `Number of ghost zones must be divisible by two for SMR/AMR calculations` | even `nghost` |
| `Fewer MeshBlocks (nmb_total=...) than MPI ranks (nranks=...)` | fewer ranks or smaller MeshBlocks |
| `### WARNING ... Number of MeshBlocks cannot be divided evenly by number of MPI ranks` | uniform-grid load imbalance; choose `nmb_total` divisible by ranks |

`-v` collapses the root grid to a single MeshBlock, so it does **not** catch the
divisibility error. Use `-m` for that, because `-m` builds the real tree (reproduced).

## Memory (GPU out-of-memory) and MeshBlock limits

- With AMR, `<mesh_refinement>/max_nmb_per_rank` is **required**. Without it you get
  `With AMR maximum number of MeshBlocks per rank must be specified ...`.
- Every physics module allocates its device arrays for `max(nmb_thisrank,
  max_nmb_per_rank)` MeshBlocks when it is constructed. Memory use therefore scales with
  `max_nmb_per_rank` × MeshBlock volume (incl. ghosts) × number of variables. The memory
  is reserved **at startup**, and AMR growth does not allocate more later.
  - If you run out of device memory at startup, lower `max_nmb_per_rank`, use larger
    MeshBlocks (fewer ghost cells per active cell), or use more ranks/GPUs.
  - If AMR outgrows the reservation, the run stops with
    `Number of MeshBlocks in this rank on new tree = N ... exceeds <mesh_refinement>/max_nmb_per_rank`.
    Raise `max_nmb_per_rank` (memory permitting) or add ranks, then restart.
- `Root grid requires more MeshBlocks (nmb_thisrank=...) than specified by max_nmb_per_rank`:
  the reservation is smaller than the root grid needs.
- With MPI, `max_nmb_per_rank` must be ≤ 2^14 = 16384
  (`Maximum number of MeshBlocks per rank cannot exceed 2^(NUM_BITS_LID) due to MPI tag limits`).

## MPI requirements

**Tag range (`MPI_TAG_UB`).** Uniform-mesh halo exchanges use tags 0 and 1, so uniform-grid
runs need nothing special. Larger tags `(bufid << 14) | lid` appear only with SMR/AMR (flux
correction), shearing box / orbital advection, and multigrid (`bufid + 64`); AMR load balancing
stays below 2^17. The table gives the requirement for those cases.

In those exchanges `tag = (bufid << 14) | lid`, where `lid`
is the receiving MeshBlock's local ID (< 2^14) and `bufid` is the neighbour-buffer index
(`src/bvals/bvals.hpp`). The buffer ID sits in the high bits, so the tag needed depends
mainly on the dimensionality and only weakly on how many MeshBlocks a rank holds:

| Case | max `bufid` | required `MPI_TAG_UB` ≥ |
|---|---|---|
| 1D | 7 | 7·2^14 + (MBs/rank − 1) ≈ 1.3e5 |
| 2D | 23 | 23·2^14 + (MBs/rank − 1) ≈ 3.8e5 |
| 3D | 55 (56 with orbital advection) | 917,504 + (MBs/rank − 1), i.e. ≤ 2^20 − 1 |
| 3D self-gravity multigrid with refinement | 64 + 55 = 119 | 1,949,696 + (MBs/rank − 1), i.e. ≤ 2^21 − 1 |

- The MPI standard only guarantees `MPI_TAG_UB ≥ 32767`. The source comment
  (`src/athena.hpp`) cites Intel MPI's 20-bit limit as the strictest one known.
  - The multigrid fine/coarse exchange (`src/multigrid/multigrid_bvals.cpp`) offsets
    `bufid` by 64, which can need 21 bits in 3D.
- AthenaK never queries `MPI_TAG_UB`, so a too-small limit shows up as an MPI "invalid tag" error.
- To check the limit, query `MPI_Comm_get_attr(MPI_COMM_WORLD, MPI_TAG_UB, ...)` with the
  target MPI. The machine skill covers library-specific settings.

**Hybrid MPI + OpenMP** calls `MPI_Init_thread(MPI_THREAD_MULTIPLE)`. If the library
provides less, you get `MPI_THREAD_MULTIPLE must be supported for hybrid parallelization`
and the run quits (exit code 0).

**GPU runs need GPU-aware MPI.** Boundary send/receive buffers are device Views passed
straight to `MPI_Isend`/`MPI_Irecv`. On Cray/HPE systems this usually needs an
environment switch; see the machine skill (e.g. `frontier`).

**Works on 1 rank, crashes with MPI (GPU).** Check in order:
1. MPI is not GPU-aware (AthenaK has no host-staging fallback).
2. GPU support is not switched on (e.g. Cray `MPICH_GPU_SUPPORT_ENABLED=1`; see the machine skill).
3. MPI was built for a different CUDA/ROCm version than the AthenaK build.
4. Per-rank GPU isolation blocks device-to-device transfers: try all GPUs visible to every rank
   and let Kokkos map one per local rank (Slurm: `--gpu-bind=none`).

**All ranks on one GPU.** Kokkos picks the device by node-local rank, taken from
`OMPI_COMM_WORLD_LOCAL_RANK`, `MV2_COMM_WORLD_LOCAL_RANK`, `MPI_LOCALRANKID`,
`SLURM_LOCALID` or `PMI_LOCAL_RANK`. If none of these is set, every rank uses the first
visible GPU. Fix it with per-rank `CUDA_VISIBLE_DEVICES`/`ROCR_VISIBLE_DEVICES`/
`ZE_AFFINITY_MASK` (machine skill), `KOKKOS_VISIBLE_DEVICES`, or `--kokkos-device-id=<n>`.

## I/O and restarts

- **No MPI-IO hints.** `src/outputs/io_wrapper.cpp` opens every shared file (restart, `bin`,
  and the input file under MPI) with `MPI_INFO_NULL`. Parallel write speed therefore
  depends on the filesystem's default layout. Set Lustre striping on the output
  directory, or set MPI-IO hints through the environment, as the machine skill describes
  (`aurora` `references/storage.md`, `frontier`, `perlmutter`).
  - The `<outputN>/single_file_per_rank` option writes one file per rank under
    `rst/rank_XXXXXXXX/` instead.
- `Error: Unable to open restart file: <path>` then `File '<path>' could not be opened`:
  wrong path. `-r` paths are resolved from the launch directory, not from `-d`.
- `... read from restart file is incorrect, restart file is broken` / `Header size read
  from restart file is incorrect` / `Incorrect number of MeshBlocks in restart file`: the
  file is truncated or corrupt (e.g. the job died while writing it), or it does not
  match the physics compiled into this binary. Use the previous `.rst`.
- `<par_end> is not found in the first 40KBytes`: the file given to `-r` is not an AthenaK
  restart file.

## Load-balancing report after a restart

The end-of-run line
`N communicated for load balancing, load balancing efficiency = E`
(printed only for AMR + MPI) is wrong after a restart. The per-cycle efficiency sum
(`lb_efficiency_`) starts at 0 in each run, but the code divides it by `ncycle`, and
`ncycle` is restored from the restart and so counts all cycles since t = 0. After a
restart, E is therefore biased low by a factor of about
(cycles in this run)/(total cycles). Reproduced: a 2-rank AMR run printed 1.0 after 72
cycles, and its restart to cycle 144 printed 0.5 with the same layout. The other counters on that line (`MeshBlocks
created/deleted`, `communicated`) and `zone-cycles/cpu_second` cover the current run only.

## NaNs and floors

- AthenaK does not stop when it meets a NaN. Watch the cycle line
  (`elapsed=... cycle=... time=... dt=...`). A collapsing `dt` or `dt=nan` comes before
  the failure. Also check the conserved totals in the `.hst` file.
- The ideal / isothermal EOS (Newtonian, SR, GR in stationary spacetimes) applies floors
  silently. They are set in `<hydro>` or `<mhd>`:
  - `dfloor`, `pfloor`, `tfloor`, `sfloor` (all default to `FLT_MIN`)
  - `gamma_max` (relativistic Lorentz-factor ceiling)
  - `sigma_max` (MHD magnetization ceiling)
  - `fofc = true` enables first-order flux correction.
- Dynamical GRMHD (primitive solver) reads these from `<mhd>`:
  - `dfloor`, `tfloor`, `dthreshold` (atmosphere threshold)
  - `c2p_tol`, `c2p_iter`
  - `c2perrs` (default 1000): the cap on printed messages.
  - Each failure prints `An error occurred during the primitive solve: <reason>` with
    cell location, conserved and metric values. After `c2perrs` messages on a rank you
    get `... C2P errors have been detected on rank R. All future C2P errors on this rank
    will be suppressed.`
- Z4c-specific floors are in `<z4c>`: `chi_div_floor`, `chi_min_floor`, `floor_chi`, `eps_floor`.
- `references/physics-modules.md` has the meaning of each parameter.

## Run control

- `-t` expects `hh:mm:ss`. A bare number such as `-t 600` leaves minutes and seconds
  uninitialised (`sscanf`), so the limit is undefined.
- `[WATCHDOG (...)] Rank R is not progressing.` then `Terminating...` and `abort()`: no
  cycle finished within the `-w` timeout. Raise the timeout above the slowest cycle,
  including restart dumps and AMR. See `references/running.md`.
