---
name: gkeyll
description: Gkeyll plasma simulation framework. Use when installing gkeyll, writing Lua input files for VlasovMaxwell, Gyrokinetic, or Moments apps, configuring species and field parameters, or launching gkeyll runs on local machines or HPC clusters.
compatibility: "Requires CMake, OpenBLAS (with gfortran), SuperLU, LuaJIT. Optional: MPI, CUDA, NCCL. Linux/macOS."
allowed-tools: Read Write Bash(make *) Bash(git *) Bash(cmake *) Bash(mpirun *) WebFetch WebSearch
---

# Gkeyll — Plasma Simulation Framework

Gkeyll is a multi-physics plasma simulation framework supporting kinetic (Vlasov-Maxwell), gyrokinetic, and multi-fluid moment models. Simulations are configured via Lua scripts and can run on CPUs (serial or MPI) or GPUs (CUDA).

## Installation

**Known machines** (easiest):
```bash
git clone https://github.com/ammarhakim/gkeyll.git
cd gkeyll

# Build dependencies then configure
./machines/mkdeps.<machine>.sh      # e.g., macos, traverse, perlmutter
./machines/configure.<machine>.sh
make install -j $(nproc)
```

**Custom/new systems**:
```bash
cd install-deps
./mkdeps.sh --build-openblas=yes --build-superlu=yes
cd ..
./configure --help                  # review options for compiler paths
make -j $(nproc)
```

See [references/installation.md](references/installation.md) for full dependency list, machine script names, GPU/CUDA options, and per-layer build targets.

## Input File Basics

Gkeyll uses **Lua scripts** (`.lua` files) with four sections:

```lua
-- 1. Load the App
local Plasma = require("App.Plasma").VlasovMaxwell

-- 2. Preamble: user parameters and derived quantities
local vte = math.sqrt(eV * Te / me)   -- thermal velocity

-- 3. App configuration table
local plasmaApp = Plasma.App {
   tEnd = 1e-6,                        -- simulation end time
   nFrame = 10,                        -- output frames
   lower = {-math.pi},                 -- config-space lower bound
   upper = { math.pi},                 -- config-space upper bound
   cells = {64},                       -- config-space resolution
   periodicDirs = {1},

   elc = Plasma.Species {              -- species block
      charge = -eV, mass = me,
      lower = {-6*vte}, upper = {6*vte},
      cells = {32},
      init = ...,
   },

   field = Plasma.Field {              -- field block
      epsilon0 = eps0, mu0 = mu0,
   },
}

-- 4. Run
plasmaApp:run()
```

See [references/input-format.md](references/input-format.md) for all App types, Common/Species/Field keys, and annotated examples.

## Running Simulations

```bash
# Serial
$HOME/gkylsoft/gkeyll/bin/gkeyll input.lua

# MPI parallel
mpirun -np 4 $HOME/gkylsoft/gkeyll/bin/gkeyll input.lua

# Verify MPI support
$HOME/gkylsoft/gkeyll/bin/gkeyll -help   # look for "Built with MPI"
```

Output files: `sim_N.bp` (ADIOS2 / BP format), one file per frame per field/species.

Post-process with **postgkyl**:
```bash
conda install -c gkyl -c conda-forge postgkyl
pgkyl sim_elc_0.bp plot
```

See [references/running.md](references/running.md) for MPI decomposition, GPU flags, postgkyl commands, and regression testing.

## Quick Reference

| App | Physics model |
|-----|--------------|
| `VlasovMaxwell` | Fully kinetic Vlasov-Maxwell |
| `Gyrokinetic` | Gyrokinetic (delta-f or full-f) |
| `Moments` | Multi-fluid moment-Maxwell |
| `PKPM` | 10-moment pressure-kinetic |

## Additional Resources

- [Installation details](references/installation.md)
- [Lua input file format](references/input-format.md)
- [Running and post-processing](references/running.md)
- Gkeyll docs: https://gkeyll.readthedocs.io/
- Source: https://github.com/ammarhakim/gkeyll
- Postgkyl: https://postgkyl.readthedocs.io/
