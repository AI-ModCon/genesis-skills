# GS2 Installation Reference

## Dependencies

| Dependency | Required | Notes |
|-----------|----------|-------|
| Fortran compiler | Yes | gfortran 9+ or Intel ifort |
| MPI | Recommended | OpenMPI, MPICH, or Cray MPICH |
| NetCDF | Yes | v4.2.0 or later; enables diagnostic output |
| HDF5 | Recommended | Required for parallel NetCDF |
| FFTW3 | Yes (nonlinear) | Required for nonlinear runs |
| LAPACK | Yes | Often via OpenBLAS or MKL |
| Python 3.6+ | Build-time | Code generation, tests, and docs |

## Clone

```bash
git clone --recurse-submodules https://bitbucket.org/gyrokinetics/gs2.git
cd gs2
```

If you forgot `--recurse-submodules`:
```bash
git submodule update --init --recursive
```

## Build System

GS2 uses a Make-based build controlled by the `GK_SYSTEM` environment variable.

```bash
export GK_SYSTEM=<system_name>
make -I Makefiles
```

System-specific Makefiles live in `Makefiles/Makefile.$GK_SYSTEM`. The build picks up compiler paths, library locations, and flags from there.

## Supported GK_SYSTEM Values

| System | Description |
|--------|-------------|
| `archer2` | UK national supercomputer (Cray) |
| `marconi` | CINECA Marconi (Intel) |
| `cobra` | MPCDF Cobra |
| `generic_parallel` | Generic MPI build starting point |
| `generic_serial` | Non-MPI fallback |

Run `ls Makefiles/` to see all available systems.

## Adding a New System

1. Copy a similar system's Makefile as a starting point:
   ```bash
   cp Makefiles/Makefile.generic_parallel Makefiles/Makefile.my_cluster
   export GK_SYSTEM=my_cluster
   ```

2. Edit `Makefiles/Makefile.my_cluster` to set:
   - `FC` — Fortran compiler or MPI wrapper (e.g., `mpif90`)
   - `NETCDF_DIR`, `HDF5_DIR`, `FFTW_DIR`, `LAPACK_LIB`
   - Compiler flags (`FFLAGS`, `FPPFLAGS`)

3. Build and watch for missing library errors, updating paths as needed.

## Build Flags

Pass as `make` arguments alongside `GK_SYSTEM`:

| Flag | Effect |
|------|--------|
| `DEBUG=on` | Enable debug symbols and bounds checking |
| `OPT=defined` | Enable optimization flags |
| `USE_MPI=defined` | Explicitly enable MPI (usually set in Makefile) |
| `USE_HDF5=on` | Enable HDF5/parallel NetCDF |
| `USE_FFTW=on` | Enable FFTW (required for nonlinear) |

Example:
```bash
make -I Makefiles DEBUG=on USE_HDF5=on
```

## Verifying the Build

```bash
./gs2 --help
mpirun -np 4 ./gs2 tests/linear_tests/cyclone_itg_collisional/cyclone_itg_collisional.in
```

Check for a clean output without MPI errors. The test directory contains reference output for comparison.

## Common Build Issues

**Missing NetCDF**: Set `NETCDF_DIR` in your Makefile, or load the module:
```bash
module load netcdf-fortran
```

**FFTW not found**: GS2 requires FFTW3 (not FFTW2). Ensure `FFTW_DIR` points to the FFTW3 installation.

**Submodule errors**: Run `git submodule update --init --recursive` from the repo root.
