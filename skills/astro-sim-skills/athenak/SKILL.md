---
name: athenak
description: >-
  AthenaK (GR)(M)HD and numerical-relativity code (Kokkos). Use when building
  AthenaK with CMake/Kokkos (CUDA, HIP, SYCL, OpenMP, MPI), choosing a problem
  generator, editing .athinput files, running or restarting, or reading,
  plotting or converting (ParaView) .bin, .hst, .tab, sph and tracker output
  with plot-tools (athplot) or vis/python. Covers hydro, MHD, radiation,
  particles, GR, Z4c. Job scripts go to the hpc-skills (slurm, pbs, aurora,
  frontier, perlmutter).
compatibility: >-
  Build: CMake 3.16+ (bundled Kokkos requirement), a C++17 compiler, optional
  MPI (GPU-aware for multi-GPU runs), and the vendor toolchain for GPU
  backends (CUDA, ROCm/HIP, oneAPI SYCL). Analysis: Python 3 with plot-tools
  (athplot) and its dependencies (numpy, matplotlib, vtk, PyCompOSE from
  GitHub); h5py for athdf conversion.
metadata:
  version: "1.0"
  code: athenak
  upstream_commit: c5a0d7f9155a70149931bf0be5a4ffb673f2532a
  plot_tools_commit: f29d3e6754696b9b1f2ea764e4455283fd230437
  checked: "2026-11-09"
allowed-tools: Read Write Bash(git *) Bash(cmake *) Bash(make *) Bash(python3 *)
---

# AthenaK — Performance-Portable AMR (GR)(M)HD and Numerical Relativity

AthenaK (https://github.com/IAS-Astrophysics/athenak) is a rewrite of Athena++ on
[Kokkos](https://kokkos.org): one C++17 source tree runs on CPUs (serial or OpenMP)
and NVIDIA, AMD, and Intel GPUs, with MPI across ranks. It solves Newtonian, special-
and general-relativistic hydro and MHD, grey radiation transport, test particles,
ion-neutral two-fluid MHD, and numerical relativity (Z4c), including dynamical-spacetime GRMHD.

Vocabulary: the **Mesh** is the whole domain. It is split into equal-size
**MeshBlocks** (the unit of parallelism, I/O and refinement). Each rank owns a
contiguous set of MeshBlocks, packed together so a kernel loops over all of them at once.
Static or adaptive mesh refinement (SMR/AMR) adds levels of MeshBlocks in an octree.
A **problem generator (pgen)** sets the initial data.

Everything below was checked against AthenaK commit `c5a0d7f` and plot-tools commit
`f29d3e6` on 2026-11-09. Flags and parameter names change upstream; when in doubt,
check `src/main.cpp`, `src/outputs/outputs.cpp`, or run `athena -h`.

The official user documentation is https://ias-astrophysics.github.io/athenak-docs/
(source: https://github.com/IAS-Astrophysics/athenak-docs). It has a quick start,
per-module pages, problem-generator descriptions, and notes for specific machines. It tracks
upstream `main`, so it may describe features newer than the user's checkout; when it
disagrees with the source the user is building, the source wins.

## Safety

- Never submit a batch job, or start a multi-node run, before showing the user the
  exact command or script and its node-hour cost (nodes × wall time), and getting
  confirmation. Submission itself goes through the `hpc-skills` (see [Running](#running)).
- Never overwrite, move, or delete restart files (`rst/`) or existing output
  directories. Give a new run its own `-d <rundir>`. Restart into the same directory only
  when the user says the run is continuing there.
- Before any production run with a new or edited parameter file:
  1. run `athena -i <file> -n` (merged parameters) and `athena -i <file> -v` (unused-parameter warnings);
  2. run `athena -i <file> -m` to check the MeshBlock layout. With SMR/AMR, `-v` skips the
     refinement blocks: `-m` catches a missing `max_nmb_per_rank`, but misspelt criterion keys
     are reported only by a real run, at start-up.
- Keep runs on shared login nodes small and short (a few ranks, a few minutes).
  Anything larger goes through the scheduler.

## Quick start (laptop, CPU)

```bash
git clone --recursive https://github.com/IAS-Astrophysics/athenak.git
cmake -S athenak -B athenak/build        # serial CPU, built-in test pgens
cmake --build athenak/build -j 4
mkdir -p run-sod && cd run-sod
../athenak/build/src/athena -i ../athenak/inputs/hydro/sod.athinput -n   # check params, exit
../athenak/build/src/athena -i ../athenak/inputs/hydro/sod.athinput      # ~seconds
```

Check: `athena_read.tab('tab/Sod.hydro_w.00010.tab')` (from `<athenak>/vis/python`) returns
`x1v`, `dens`, `velx`, ...; `plot_tab.py` only opens a window (its `-o` saves nothing).

`assets/minimal_hydro.athinput` is an annotated copy of that Sod shock-tube input
(built-in `shock_tube` pgen, no `-D PROBLEM` needed).

## Building

One build directory per backend and pgen. Configure with CMake out of source; the
executable is `<build>/src/athena`.

| Target | Key CMake flags |
|---|---|
| CPU serial | *(none)* |
| CPU OpenMP | `-D Athena_ENABLE_OPENMP=ON` |
| + MPI (any backend) | `-D Athena_ENABLE_MPI=ON` |
| NVIDIA A100 / H100 | `-D Kokkos_ENABLE_CUDA=ON -D Kokkos_ARCH_AMPERE80=ON` / `HOPPER90`; `CMAKE_CXX_COMPILER=<athenak>/kokkos/bin/nvcc_wrapper` |
| AMD MI250X / MI300A | `-D Kokkos_ENABLE_HIP=ON -D Kokkos_ARCH_AMD_GFX90A=ON` / `AMD_GFX942_APU`; `hipcc` or Cray `CC` |
| Intel PVC | `-D Kokkos_ENABLE_SYCL=ON -D Kokkos_ARCH_INTEL_PVC=ON`; `icpx` |
| Single precision | `-D Athena_SINGLE_PRECISION=ON` |
| Custom pgen | `-D PROBLEM=<path under src/pgen, no .cpp>`, e.g. `fluids/blast` |

- The default build compiles every test pgen under `src/pgen/tests/`; pick one at run
  time with `<problem>/pgen_name` (e.g. `shock_tube`, `orszag_tang`, `gr_bondi`).
- Some custom pgens read external initial data and need their library: e.g. Lorene,
  FUKA/Kadath, Elliptica, SGRID, TwoPunctures. See `references/build.md`.
- Always set the GPU arch explicitly (login nodes have no GPU to autodetect).
- `athena -c` prints what a binary was built with.
- Every run, including `-n`/`-v`/`-m`/`-c`, initialises Kokkos first. A GPU build therefore
  aborts on a node with no visible GPU, e.g. a login node. Run the checks on a compute node,
  or with a CPU build of the same pgen.

→ Full option list, the pgen catalogue, compilers per backend: `references/build.md`.

## Input files

```
<block>
key = value     # comment
```

- Required: `<job>` (`basename`), `<mesh>` (`nx1..3`, `x1min..x3max`, `ix1_bc`/`ox1_bc`, ...),
  `<time>` (`evolution`, `cfl_number`, `tlim`), `<problem>` (`pgen_name` for built-in pgens).
  Optional, with defaults: `nghost` (2), `integrator` (rk2), `nlim` (-1), `ndiag` (1);
  `<meshblock>` (`nx1..3`, must divide the mesh).
- Physics is switched on by the presence of its block: `<hydro>`, `<mhd>`, `<radiation>`,
  `<particles>`, `<ion-neutral>`, `<z4c>`, `<adm>`. Relativity is set in `<coord>`
  (`special_rel`, `general_rel`, `a`, `minkowski`, excision).
- Outputs: one `<outputN>` block each (`file_type`, `variable`, `dt` or `dcycle`).
- Command-line `block/key=value` overrides a key **that already exists** in the file;
  an unknown block or key is a fatal error. To add keys, edit a copy of the file.
- A misspelled **optional** key is not an error: the default is used silently and AthenaK
  only warns that the misspelled key was "not used" (run `-v` to see the warnings). A misspelled
  required key is fatal. Some "not used" warnings are harmless, e.g. x2/x3 keys in 1D inputs.
- `scripts/athinput_tool.py <file|.rst|.bin>` summarises a parameter file, or the
  copy embedded in a restart or binary output (mesh, MeshBlock count, physics, outputs).
  It also does `--get block/key`, `--diff a b`, and checks overrides the way AthenaK does.
  Standard library only.

→ Syntax rules, every core block, restarts and parameters, an annotated example:
`references/input-format.md`. Module-by-module map (EOS, reconstruction, Riemann
solvers, floors, allowed combinations, example inputs): `references/physics-modules.md`.

## Running

```bash
mpiexec -n <N> <build>/src/athena -i <file> -t <hh:mm:ss> -d <rundir> [block/key=value ...]
```

| Flag | Meaning |
|---|---|
| `-i <file>` | parameter file |
| `-r <file>` | restart from an `.rst` file (with `-i` too: the file's values override the restart's) |
| `-d <dir>` | create and enter the run directory (after reading input; outputs go there) |
| `-t hh:mm:ss` | wall-time limit: stop cleanly and write every output once more (incl. `rst` if configured) |
| `-w <sec>` | watchdog: abort a rank that has not started a new cycle within `<sec>` |
| `-n` | print merged parameters and exit |
| `-m` | build the mesh, write `mesh_structure.dat`, exit |
| `-v` | validate on one MeshBlock, print unused-parameter warnings, exit |
| `-c` | print build configuration, exit |
| `-h` | help |
| `block/key=value` | override an existing parameter |

- **Restart:** `athena -r <rundir>/rst/<basename>.<nnnnn>.rst -d <rundir> time/tlim=<new>`.
  Mesh size, MeshBlock size, `nghost` and the refinement tree come from the file;
  the enabled physics must match it. `athena -r <file.rst> -n` lists its stored parameters.
- **Layout:** one MPI rank per GPU (or MI250X GCD / PVC tile), at least one MeshBlock
  per rank, and several per rank on GPUs. Multi-GPU runs need GPU-aware MPI. For OpenMP
  builds set `OMP_NUM_THREADS` per rank.
- **Wall time:** set `-t` below the scheduler limit, leaving one cycle plus one full
  output dump of margin, and include an `<outputN>` with `file_type = rst`.
- **Clusters:** for job scripts, queues, binding and filesystems, load the matching skill
  from `hpc-skills`: `slurm` or `pbs` (generic), `aurora`, `frontier`, or `perlmutter`.
  This skill has no job-script templates.

→ Flag details, watchdog behaviour, GPU-device selection, reading cycle lines and the
performance summary, the hpc-skills mapping: `references/running.md`.

## Reading and plotting output

- **Mesh data (`bin`): use plot-tools (`athplot`).** `BinaryData` reads only the header and
  the MeshBlock index, then streams one MeshBlock at a time, so it handles very large 3D dumps.
  Install with `pip install git+https://github.com/jfields7/plot-tools.git`.
  - With streaming, **always fix the colour range** (`norm=` or `vmin`/`vmax`). Otherwise each
    block autoscales and the plot shows block-shaped artifacts.
  - For 3D data, pass a cell-centre `slice_loc`.
  - It also covers derived variables (`register_derived_variable`, `GroupData`),
    `sph` shells (`SphericalData`) and Z4c compact-object tracker files (`Tracker`).
- **Use AthenaK `<athenak>/vis/python`** (do not copy it) only where plot-tools stops:
  - `athena_read.tab` for table files. For history files, use `athena_read.hst` on single runs only:
    on a restarted run it returns just the last segment;
  - `make_athdf.py` / `bin_convert.py` to convert to athdf + XDMF for ParaView, VisIt or yt;
  - `cbin` and `cart` files, which `BinaryData` rejects. For `cbin`, read it with
    `bin_convert.read_coarsened_binary` and convert it to athdf (`write_athdf`). For `cart`,
    use `cartgrid.CartesianGridData`. `vis/python/plot_slice.py` does not read `cbin` either.

```python
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from athplot.load_ath_bin import BinaryData

d = BinaryData("bin/<basename>.mhd_w_bcc.00010.bin")   # header + block index only
kw = {} if d.is_2d() else {"slice_loc": ("z", 0.01)}   # 3D: cell-centre coordinate
fig, ax = plt.subplots()
im = d.plot_slice("dens", ax=ax, cmap="inferno", norm=LogNorm(vmin=1e-2, vmax=1e1), **kw)
fig.colorbar(im, ax=ax); fig.savefig("dens.png", dpi=150)
```

`scripts/hst_summary.py <file.hst>` lists the history columns with their first/last/min/max values
and flags NaNs. `--plot col1,col2` plots columns. It joins all restart segments.

→ Every output `file_type` and its keys, the `athplot` API, which layouts each tool
accepts, and worked examples (reductions over MeshBlocks, `sph` profiles, `hst` plots,
athdf conversion): `references/outputs-and-analysis.md`.

## Troubleshooting

`references/troubleshooting.md` covers:
- "not used" warnings and invalid block names;
- MeshBlock divisibility errors and the per-rank MeshBlock limit;
- GPU out-of-memory and AMR growth;
- MPI requirements: tag range, thread level, GPU-aware MPI;
- restart-file mismatches and I/O;
- the load-balance line after a restart;
- NaNs and floors (`dfloor`, `pfloor`, `tfloor`, ...).

## Additional resources

- AthenaK documentation: https://ias-astrophysics.github.io/athenak-docs/ (source:
  https://github.com/IAS-Astrophysics/athenak-docs)
- AthenaK source: https://github.com/IAS-Astrophysics/athenak (wiki:
  https://github.com/IAS-Astrophysics/athenak/wiki)
- Paper: Stone et al. 2024, *AthenaK: A Performance-Portable Version of the Athena++
  AMR Framework*, arXiv:2409.16053
- plot-tools (`athplot`): https://github.com/jfields7/plot-tools (see its `examples/`)
- Kokkos build configuration: https://kokkos.org/kokkos-core-wiki/get-started/configuration-guide.html
- References in this skill: `references/build.md`, `references/input-format.md`,
  `references/physics-modules.md`, `references/running.md`,
  `references/outputs-and-analysis.md`, `references/troubleshooting.md`
