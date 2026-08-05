# Aurora Programming Environment Reference

Aurora uses Intel's oneAPI SDK as its primary programming environment.

---

## Loading the Programming Environment

```bash
# Access Spack-managed modules
module use /soft/modulefiles

# Load oneAPI (check latest version with: module avail oneapi)
module load oneapi/eng-compiler/2024.06.28.002

# Verify compilers are available
icx --version
icpx --version
ifx --version
mpicc --version
```

---

## Compilers

| Command | Language | Notes |
|---------|----------|-------|
| `icx` | C | Intel LLVM-based C compiler |
| `icpx` | C++ | Intel LLVM-based C++ compiler |
| `ifx` | Fortran | Intel LLVM-based Fortran compiler |
| `icpx -fsycl` | C++ + SYCL | GPU offload via SYCL/DPC++ |
| `mpicc` | C | Intel MPI wrapper for `icx` |
| `mpicxx` | C++ | Intel MPI wrapper for `icpx` |
| `mpifc` | Fortran | Intel MPI wrapper for `ifx` |

### Compilation Examples

```bash
# Standard MPI C++ with optimization
mpicxx -O3 -std=c++17 my_app.cpp -o my_app

# SYCL GPU code (targets Intel PVC)
icpx -fsycl -O3 my_gpu.cpp -o my_gpu

# SYCL with explicit target
icpx -fsycl -fsycl-targets=spir64_gen \
     -Xs "-device pvc" \
     -O3 my_gpu.cpp -o my_gpu

# OpenMP CPU parallelism
icpx -qopenmp -O3 my_omp.cpp -o my_omp

# OpenMP target offload to GPU
icpx -fiopenmp -fopenmp-targets=spir64 -O3 my_omp_gpu.cpp -o my_omp_gpu

# Link against Intel MKL (math library)
icpx -O3 my_app.cpp -o my_app -mkl
```

---

## SYCL/DPC++ GPU Programming

SYCL is Intel's GPU programming model for Ponte Vecchio (Aurora's GPU).

### Minimal SYCL Example

```cpp
#include <sycl/sycl.hpp>
using namespace sycl;

int main() {
    queue q{gpu_selector_v};
    std::cout << "Device: " << q.get_device().get_info<info::device::name>() << "\n";

    // Allocate unified shared memory
    int N = 1024;
    float *data = malloc_shared<float>(N, q);

    // Submit a kernel
    q.parallel_for(range<1>(N), [=](id<1> i) {
        data[i] = i * 2.0f;
    }).wait();

    free(data, q);
    return 0;
}
// Compile: icpx -fsycl my_kernel.cpp -o my_kernel
```

### Device Selection and Affinity

```bash
# Select all Level Zero (Intel GPU) devices
export ONEAPI_DEVICE_SELECTOR=level_zero:*

# Select specific GPUs by index (GPUs 0 and 1 only)
export ONEAPI_DEVICE_SELECTOR=level_zero:0,level_zero:1

# Per-MPI-rank GPU selection (use ZE_AFFINITY_MASK in a launcher script)
# GPU affinity is usually handled automatically by --gpu-bind=closest in mpiexec
export ZE_AFFINITY_MASK=0   # rank sees only GPU 0

# Debug: trace SYCL device selection
export SYCL_PI_TRACE=1

# Enable Intel Level Zero validation layer (for debugging)
export ZE_ENABLE_VALIDATION_LAYER=1
export ZE_ENABLE_PARAMETER_VALIDATION=1
```

### Multi-GPU SYCL with MPI

```cpp
#include <sycl/sycl.hpp>
#include <mpi.h>
using namespace sycl;

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    // Each MPI rank gets its own GPU (via ZE_AFFINITY_MASK or launcher)
    queue q{gpu_selector_v};
    // ... GPU work per rank ...

    MPI_Finalize();
    return 0;
}
```

---

## Intel Ponte Vecchio (PVC) GPU Architecture

| Component | Details |
|-----------|---------|
| GPUs per node | 6× Intel GPU Max (Ponte Vecchio) |
| Tiles per GPU | 2 (each tile is an independent compute unit) |
| HBM per tile | ~64 GB HBM2e |
| Compute units | 128 per tile |
| Connection | All-to-all via Intel Xe Link (within node) |
| NIC access | Direct GPU↔NIC memory (no CPU copy) |

Each GPU appears as 1 device in SYCL but has 2 sub-devices (tiles). For maximum performance:
- Use `ZE_AFFINITY_MASK` or `--gpu-bind` in `mpiexec` to control GPU assignment
- Consider sub-device partitioning for very fine-grained workloads

---

## Intel MPI on Aurora

```bash
# Launch options
mpiexec -n <total_ranks> -ppn <ranks_per_node> ./my_app

# With CPU and GPU binding
mpiexec -n 24 -ppn 6 \
    --cpu-bind=depth \
    --gpu-bind=closest \
    ./my_app

# With environment variables per rank
mpiexec -n 24 -ppn 6 \
    -env I_MPI_OFFLOAD=1 \
    -env ONEAPI_DEVICE_SELECTOR=level_zero:* \
    ./my_app

# Enable GPU-aware MPI (direct GPU buffer transfer)
export I_MPI_OFFLOAD=1
export I_MPI_OFFLOAD_TOPOLIB=level_zero

# Verbose MPI output for debugging
export I_MPI_DEBUG=5
```

---

## Intel MKL (Math Kernel Library)

```bash
# Link with MKL
icpx -O3 my_app.cpp -o my_app -mkl

# Or use explicit linking
icpx -O3 my_app.cpp -o my_app \
    -L$MKLROOT/lib/intel64 \
    -lmkl_intel_lp64 -lmkl_intel_thread -lmkl_core -liomp5 -lpthread -lm

# MKL with SYCL (oneMKL)
icpx -fsycl -O3 my_mkl_sycl.cpp -o my_mkl_sycl \
    -L$MKLROOT/lib/intel64 \
    -lmkl_sycl -lmkl_intel_ilp64 -lmkl_tbb_thread -lmkl_core
```

---

## Profiling and Debugging

```bash
# Intel VTune Profiler (CPU and GPU)
module load vtune
vtune --collect gpu-hotspots --result-dir vtune_results -- mpiexec -n 6 ./my_app

# Intel Advisor (vectorization and offload analysis)
module load advisor
advisor --collect offload -- mpiexec -n 6 ./my_app

# Intel oneAPI GPU Profiling (for SYCL/OpenCL)
module load intel_compute_runtime
export INTEL_DUMP_DEVICE_CODE=1   # dump GPU binaries

# Low-level debugging with Level Zero
export ZE_ENABLE_VALIDATION_LAYER=1
export ZE_ENABLE_PARAMETER_VALIDATION=1
export SYCL_PI_TRACE=2
```

---

## Cray PE on Aurora (Alternative)

The Cray Programming Environment is also available as an alternative to Intel oneAPI:

```bash
module load PrgEnv-cray   # LLVM/Clang-based Cray compilers
# Then use: cc, CC, ftn wrappers (same as on Frontier)

module load PrgEnv-gnu    # GCC-based
```

This is useful if you have code already working with Cray PE on other systems.
