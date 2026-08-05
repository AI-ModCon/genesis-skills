# GS2 Running Reference

## Basic Commands

```bash
# Validate input file (no run)
gs2 --check-input run.in

# Serial run
gs2 run.in

# MPI parallel run
mpirun -np <N> gs2 run.in

# Restart from checkpoint
mpirun -np <N> gs2 run.in --restart

# List all command-line options
gs2 --help
```

## Output Files

| File | Contents |
|------|----------|
| `run.out` | Text log: frequencies, growth rates, timing |
| `run.nc` | NetCDF diagnostics (phi, moments, fluxes vs. time) |
| `run.restart_*` | Restart checkpoint files |

## MPI Parallelization

GS2 parallelizes over:
- **ky modes** (primary — most efficient)
- **kx modes**
- **species**
- **Velocity space** (energy and pitch angle)

For a box run with `ny=32` and `nx=32`, a good starting point is `nproc = ny/2 = 16` (one ky per process). Check `run.out` for load balance information.

Common efficient process counts: powers of 2 or multiples of ky modes.

## HPC Job Script (SLURM example)

```bash
#!/bin/bash
#SBATCH --job-name=gs2_run
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=32
#SBATCH --time=04:00:00
#SBATCH --partition=regular

module load netcdf-fortran fftw openmpi

export GK_SYSTEM=my_cluster

mpirun -np 64 /path/to/gs2 run.in
```

## Restart Workflow

1. Enable restart output in input file:
   ```fortran
   &gs2_diagnostics_knobs
     save_for_restart = .true.
   /
   ```

2. Run until checkpoint is written (at each `nwrite` step or at end).

3. Restart:
   ```bash
   mpirun -np 64 gs2 run.in --restart
   ```
   GS2 reads `run.restart_*` files and continues from the last saved state.

4. To extend the run time, increase `nstep` or `tend` in the input file before restarting.

## Convergence and Resolution Checks

GS2 output is not guaranteed to be correct without convergence verification. Always check:

| Parameter | Check | How |
|-----------|-------|-----|
| `ntheta` | Poloidal resolution | Double it; results should not change significantly |
| `naky`/`ny` | Spectral resolution | Ensure energy spectra decay at high k |
| `negrid` | Energy grid points | Typically 8–16; increase and recheck |
| `ngauss` | Pitch-angle grid | Typically 3–10; increase and recheck |
| `delt` | Timestep | Halve it; growth rates/frequencies should be unchanged |

For linear runs: compare growth rate `ω_i` and real frequency `ω_r` across resolution scans.

For nonlinear runs: check heat flux convergence vs. time and spectral power law.

## Reading Output with Python

```python
import netCDF4 as nc
import numpy as np

ds = nc.Dataset("run.nc")
phi2 = ds.variables["phi2"][:]    # |phi|^2 vs time
t    = ds.variables["t"][:]
omega = ds.variables["omega"][:]  # complex frequency
```

The GS2 project also provides `gs2_diagnostics` Python tools in the `utils/` directory.

## Common Issues

**Run hangs at startup**: Usually MPI launcher issue. Check `mpirun` path and hostfile.

**NetCDF errors**: Ensure NetCDF libraries match the version used at compile time.

**`NaN` in output**: Timestep too large — reduce `delt` or switch to `delt_option = 'cfl'`.

**No restart files**: Check `save_for_restart = .true.` is set and disk quota is not exceeded.
