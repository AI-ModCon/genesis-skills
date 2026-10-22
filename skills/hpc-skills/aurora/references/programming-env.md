# Aurora Programming Environment Reference

> Sources: docs.alcf.anl.gov: Aurora "Aurora PE", "Compiling and Linking", "Programming Models" (SYCL, OpenMP), "Python", "Copper", "Aurora MPICH", and "Performance Tools"; module names verified on Aurora, 2026-10.

The Aurora PE (installed under `/opt/aurora`) is the default environment. It consists of the Intel oneAPI SDK, Aurora MPICH, Cray PALS (`mpiexec`), and the Spack PE (cmake, hdf5, boost, python, ...). It is loaded by default; most users need no `module load` to compile.

---

## Modules

```bash
module -t list
# gcc/14.3.0  oneapi/release/2026.1.0  mpich/prd/5.0.0...  libfabric/2.3.1  cray-pals/1.8.0  cray-libpals/1.8.0   (October 2026)

module avail oneapi                      # e.g. oneapi/release/2026.1.0 (default), oneapi/release/2025.3.1
module load oneapi/release/2025.3.1      # switching the SDK reloads mpich and Spack PE packages to match (Lmod hierarchy)

module load cmake autoconf hdf5          # Spack PE packages
module load frameworks                   # recommended Python: conda env with PyTorch, TensorFlow, vLLM, ..., updated roughly quarterly

module use /soft/modulefiles             # software outside the PE: daos, kokkos, ...
```

- Do not pin old names such as `oneapi/eng-compiler/...`. Those modules have been retired. Check `module avail oneapi`.
- Aurora has no `PrgEnv-*` or `cray-mpich`, and the Cray `cc`/`CC`/`ftn` wrappers are not part of the PE.
- Modules in `/soft` can conflict with the PE, and loading libraries from shared filesystems is slow at scale.
- `frameworks` may load a different oneAPI SDK than the default. Do not also load the Spack PE `python` module; it exists as a dependency of other Spack packages, not for user applications.

---

## Compilers and MPI Wrappers

| Command | Language | Notes |
|---------|----------|-------|
| `icx` | C | oneAPI LLVM-based |
| `icpx` | C++ | oneAPI LLVM-based; SYCL with `-fsycl` |
| `ifx` | Fortran | oneAPI LLVM-based |
| `mpicc` | C | Aurora MPICH wrapper around `icx` (`mpicc -show`) |
| `mpicxx` / `mpic++` | C++ | wraps `icpx` |
| `mpifort` / `mpif90` / `mpif77` | Fortran | wraps `ifx` |

There is no `mpifc`, `mpiicx`, or `mpiicpx` (those are Intel MPI names). In mixed C/Fortran codes, build with the same Fortran compiler that MPICH was built with, because `mpi.mod` files are compiler-specific.

The default compilers can build GPU code on the login nodes. Builds that need a GPU at build time must run on a compute node (interactive `debug` job).

---

## GPU Programming Models: Compiler Flags

| Model | JIT (kernels compiled at first run) | AoT for PVC (recommended for production) |
|-------|-------------------------------------|------------------------------------------|
| SYCL | `-fsycl` | `-fsycl -fsycl-targets=intel_gpu_pvc` |
| OpenMP offload | `-fiopenmp -fopenmp-targets=spir64` | `-fiopenmp -fopenmp-targets=spir64_gen -Xopenmp-target-backend=spir64_gen "-device pvc"` |
| OpenCL | link `-lOpenCL` | — |

```bash
# SYCL, AoT
icpx -fsycl -fsycl-targets=intel_gpu_pvc -O3 app.cpp -o app

# SYCL, separate compile and link: pass -fsycl-targets to BOTH steps,
# otherwise the binary silently falls back to JIT
icpx -fsycl -fsycl-targets=intel_gpu_pvc -O3 -c a.cpp
icpx -fsycl -fsycl-targets=intel_gpu_pvc a.o -o app

# Large SYCL codes: -fno-sycl-rdc moves device codegen into the per-file compiles (parallel builds)
icpx -fsycl -fno-sycl-rdc -fsycl-targets=intel_gpu_pvc -O2 -c tu.cpp

# OpenMP offload, C/C++/Fortran
mpicxx  -fiopenmp -fopenmp-targets=spir64_gen -Xopenmp-target-backend=spir64_gen "-device pvc" app.cpp -o app
mpifort -fiopenmp -fopenmp-targets=spir64_gen -Xs "-device pvc" app.F90 -o app

# OpenMP on the CPU only
icpx -fiopenmp -O3 app.cpp -o app      # -qopenmp is equivalent; -fopenmp is LLVM's runtime
```

- `-fsycl-targets=intel_gpu_pvc` is equivalent to the older `-fsycl-targets=spir64_gen -Xsycl-target-backend "-device pvc"`.
- In CMake, escape the quotes: `-Xopenmp-target-backend=spir64_gen \"-device pvc\"`. CMake can find SYCL with `find_package(IntelSYCL REQUIRED)`.
- Kokkos, RAJA, HIP (chipStar), Julia, and OpenCL are also supported; see the ALCF docs, Programming Models.

### Minimal SYCL Example

```cpp
#include <sycl/sycl.hpp>
#include <iostream>

int main() {
    sycl::queue q{sycl::gpu_selector_v};
    std::cout << q.get_device().get_info<sycl::info::device::name>() << "\n";

    constexpr int N = 1024;
    float *x = sycl::malloc_shared<float>(N, q);
    q.parallel_for(sycl::range<1>(N), [=](sycl::id<1> i) { x[i] = 2.0f * i; }).wait();
    sycl::free(x, q);
}
// icpx -fsycl -fsycl-targets=intel_gpu_pvc hello.cpp -o hello
```

Under `gpu_tile_compact.sh`, each rank sees exactly one tile, so `gpu_selector_v` picks the right device without any rank-based device selection in the code.

---

## Aurora MPICH

- GPU-aware MPI (sending and receiving device buffers directly) is **on by default**: `MPIR_CVAR_ENABLE_GPU=1`. Set it to `0` for CPU-only codes to skip GPU setup.
- `I_MPI_*` variables have no effect; that is Intel MPI.
- Environment variable documentation: `$MPI_ROOT/share/doc/mpich/README.envvar`
- To get a core dump on `MPI_Abort`: `ulimit -S -c unlimited; MPIR_CVAR_COREDUMP_ON_ABORT=1 mpiexec --genvall --rlimit CORE ...`

---

## Intel oneMKL

```bash
icpx -O3 app.cpp -qmkl -o app                     # CPU BLAS/LAPACK/FFT (-qmkl is the documented spelling)
mpicxx -fsycl app.cpp -qmkl -o app                # oneMKL SYCL APIs on the GPU
icpx -fsycl -fsycl-targets=intel_gpu_pvc app.cpp -qmkl -o app
```

`-qmkl=sequential` or `-qmkl=parallel` selects the threading layer.

---

## Python

**Use the `frameworks` module for all Python on Aurora.** It is a conda environment built and tested by ALCF for Aurora's GPUs, with PyTorch (XPU), TensorFlow, Horovod, oneCCL, mpi4py, dpnp/dpctl, and more.

- Do not build a personal conda or Miniforge environment. Do not use the Spack PE `module load python`, or `pip install --user`. These lack the Aurora-tuned XPU and oneCCL builds.
- To add packages, extend `frameworks` with a venv:

  ```bash
  module load frameworks
  python3 -m venv /lus/flare/projects/<project>/venvs/myenv --system-site-packages
  source /lus/flare/projects/<project>/venvs/myenv/bin/activate
  ```

  Before each use, `module load frameworks` first, then `source .../bin/activate`.

- At large scale (≥ ~1,000 nodes), importing from Flare or home is slow and can disrupt Lustre. Use **Copper**:

  ```bash
  module load copper
  launch_copper.sh
  mpiexec ... --genv=PYTHONPATH=/tmp/${USER}/copper/<path_to_site-packages>:$PYTHONPATH python app.py
  ```

- Compute nodes reach the internet (for example for `pip install`) only through `http(s)_proxy=http://proxy.alcf.anl.gov:3128`.

---

## Performance and Debugging Tools

| Tool | How to load | Example |
|------|-------------|---------|
| VTune | in `oneapi` (default) | `mpiexec -n 12 ... vtune -collect gpu-hotspots -r vtune_out -- ./app` |
| Advisor | in `oneapi` | `advisor --collect=roofline --profile-gpu --project-dir=adv -- ./app` |
| APS | in `oneapi` | `mpiexec ... aps ./app` |
| unitrace | `module load pti-gpu` | `mpiexec ... unitrace ./app` (see `unitrace --help`) |
| THAPI / iprof | `module load thapi` | `mpiexec ... iprof ./app` |
| xpu-smi | `module load xpu-smi` | `xpu-smi discovery`, `xpu-smi dump -d 0 1 2 3 4 5 -m 0 1 2 5` |
| gdb-oneapi | in `oneapi` | GPU-aware gdb |
| DDT / gdb4hpc | see the ALCF docs | parallel debuggers |

Level Zero debugging: `ZE_ENABLE_VALIDATION_LAYER=1 ZE_ENABLE_PARAMETER_VALIDATION=1`. For SYCL runtime tracing, use `SYCL_UR_TRACE=1`. `SYCL_PI_TRACE` no longer works; the runtime reports `SYCL_PI_TRACE has been removed use SYCL_UR_TRACE instead`.

---

## Node Facts for Tuning

- **CPU:** 2× Xeon CPU Max 9470C, 52 cores and 2 hyperthreads per core. 102 cores are usable (0 and 52 are reserved).
- **CPU memory:** 512 GB DDR5 + 64 GB HBM per socket, in flat mode (HBM is NUMA 2 and 3).
- **GPU:** 6× Max 1550, each with 2 tiles. Each tile has 64 Xe cores (448 active vector engines per tile) and 64 GB HBM2e. The GPU has a 384 MB last-level cache.
- **Interconnect:** GPUs connect all-to-all with Xe Link. Each node has 8 Slingshot-11 NICs, and GPUs can send directly to the NICs over PCIe.
