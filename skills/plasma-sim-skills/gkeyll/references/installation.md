# Gkeyll Installation Reference

## Dependencies

### Required

| Dependency | Notes |
|-----------|-------|
| CMake 3.x+ | Build system |
| C/C++ compiler | gcc/g++ 9+ or clang |
| gfortran | Required by OpenBLAS |
| OpenBLAS | Includes BLAS and LAPACK |
| SuperLU | Sparse linear solver |

### Strongly Recommended

| Dependency | Notes |
|-----------|-------|
| LuaJIT | Essential for Lua scripting layer |
| MPI | OpenMPI or MPICH for parallelism |

### Optional

| Dependency | Notes |
|-----------|-------|
| CUDA | GPU acceleration |
| NCCL | Multi-GPU communication |
| ADIOS2 | Advanced I/O (default output format) |

## Clone

```bash
git clone https://github.com/ammarhakim/gkeyll.git
cd gkeyll
```

## Method 1: Machine Scripts (Recommended)

Pre-configured scripts exist for known HPC systems:

```bash
ls machines/
```

Common machine names:

| Script suffix | System |
|--------------|--------|
| `macos` | macOS with Homebrew |
| `traverse` | Princeton Traverse (IBM Power9 + GPU) |
| `perlmutter` | NERSC Perlmutter (Cray, GPU) |
| `stellar` | Princeton Stellar |
| `della` | Princeton Della |

Build steps:
```bash
./machines/mkdeps.<machine>.sh      # build/install dependencies
./machines/configure.<machine>.sh   # configure CMake
make install -j $(nproc)
```

Binaries land in `$HOME/gkylsoft/gkeyll/bin/`.

## Method 2: Custom Build

### Step 1 — Build dependencies

```bash
cd install-deps
./mkdeps.sh \
  --build-openblas=yes \
  --build-superlu=yes \
  --build-luajit=yes \
  --prefix=$HOME/gkylsoft
```

Options:
- `--build-openmpi=yes` — build MPI from source
- `--build-cuda=no` — skip CUDA (default)
- `--prefix=<path>` — installation prefix (default: `$HOME/gkylsoft`)

### Step 2 — Configure

```bash
cd ..
./configure --help                     # see all options
./configure \
  --prefix=$HOME/gkylsoft/gkeyll \
  --luajit-inc=$HOME/gkylsoft/luajit/include/luajit-2.1 \
  --luajit-lib=$HOME/gkylsoft/luajit/lib \
  --openblas-inc=$HOME/gkylsoft/openblas/include \
  --openblas-lib=$HOME/gkylsoft/openblas/lib \
  --superlu-inc=$HOME/gkylsoft/superlu/include \
  --superlu-lib=$HOME/gkylsoft/superlu/lib
```

For MPI builds, add:
```bash
  --mpi-inc=/path/to/mpi/include \
  --mpi-lib=/path/to/mpi/lib
```

For GPU builds, add:
```bash
  --enable-cuda=yes \
  --cuda-dir=/usr/local/cuda
```

### Step 3 — Compile

```bash
make -j $(nproc)
make install
```

## Per-Layer Build Targets

Gkeyll has five interdependent solver layers. Build only what you need:

```bash
make vlasov -j $(nproc)       # Vlasov-Maxwell solver
make gyrokinetic -j $(nproc)  # Gyrokinetic solver
make moments -j $(nproc)      # Fluid moments solver
make pkpm -j $(nproc)         # 10-moment PKPM
make core -j $(nproc)         # Core utilities only
```

## Running Tests

```bash
make check -j $(nproc)        # unit tests
# or build a specific test
make build/core/unit/ctest_array
./build/core/unit/ctest_array
```

Regression test (example):
```bash
cd Regression/vm-weibel/
mpirun -n 1 $HOME/gkylsoft/gkeyll/bin/gkeyll rt-weibel-2x2v-p2.lua
```

## Common Issues

**OpenBLAS needs gfortran**: Install `gfortran` before running `mkdeps.sh`.

**SuperLU needs cmake**: Ensure CMake is available before building SuperLU.

**LuaJIT not found**: Set `--luajit-inc` and `--luajit-lib` explicitly in `./configure`.

**macOS linking errors**: Use the `macos` machine script which handles Homebrew paths automatically.
