---
name: gs2
description: Gyrokinetics simulation code GS2. Use when installing GS2, writing or modifying GS2 input namelists, configuring species/grid/field/collision parameters, or launching GS2 runs on local machines or HPC clusters.
compatibility: Requires Fortran compiler, MPI, NetCDF 4.2+, FFTW3, LAPACK. Linux/HPC environments.
allowed-tools: Read Write Bash(make *) Bash(git *) Bash(mpirun *) WebFetch WebSearch
---

# GS2 — Gyrokinetics Simulation Code

GS2 is an Eulerian gyrokinetic flux-tube code for studying low-frequency turbulence and instabilities in magnetized plasmas. It solves the nonlinear gyrokinetic equation for multiple species with optional electromagnetic fields.

## Installation

```bash
# Clone with all submodules
git clone --recurse-submodules https://bitbucket.org/gyrokinetics/gs2.git
cd gs2

# Set the system name (see references/installation.md for supported systems)
export GK_SYSTEM=your_system_name

# Build
make -I Makefiles
```

If your HPC system is not in `Makefiles/`, create a new `Makefile.$GK_SYSTEM`. See [references/installation.md](references/installation.md) for dependencies, supported systems, and build flags.

## Input File Basics

GS2 uses **Fortran namelist** format (`.in` files):

```fortran
&namelist_name
  parameter = value   ! inline comments allowed
/
```

Key namelists (order in file does not matter):

| Namelist | Purpose |
|----------|---------|
| `knobs` | Timestep, beta, run duration |
| `species_parameters_N` | Per-species mass, charge, temperature, density |
| `theta_grid_knobs` | Magnetic geometry / poloidal grid |
| `fields_knobs` | Field equation algorithm |
| `dist_fn_knobs` | Distribution function evolution |
| `collisions_knobs` | Collision operator |
| `kt_grids_knobs` | Perpendicular wavenumber grid type |
| `init_g_knobs` | Initial condition for distribution function |
| `gs2_diagnostics_knobs` | Output frequency and diagnostics |
| `hyper_knobs` | Hyperviscosity/hyperresistivity |

Start from an existing example rather than writing from scratch:
```bash
ls tests/linear_tests/cyclone_itg_collisional/
```

See [references/namelists.md](references/namelists.md) for parameter details.

## Running Simulations

```bash
# Validate input before running
gs2 --check-input run.in

# Serial run
gs2 run.in

# MPI parallel run
mpirun -np 128 gs2 run.in

# Restart from checkpoint
mpirun -np 128 gs2 run.in --restart
```

Output goes to `run.out` (text) and `run.nc` (NetCDF diagnostics).

See [references/running.md](references/running.md) for MPI decomposition strategies, HPC job scripts, convergence checks, and restart workflow.

## Quick Reference

```
gs2 --help          # list all command-line options
gs2 --check-input   # validate namelists without running
```

Common build flags:
```bash
make -I Makefiles DEBUG=on       # debug build
make -I Makefiles USE_MPI=on     # explicit MPI enable
```

## Additional Resources

- [Installation details](references/installation.md)
- [Namelist parameter reference](references/namelists.md)
- [Running and HPC workflow](references/running.md)
- GS2 docs: https://gyrokinetics.gitlab.io/gs2/
- Namelist reference: https://gyrokinetics.gitlab.io/gs2/page/namelists/index.html
- Source: https://bitbucket.org/gyrokinetics/gs2
