# Frontier Programming Environment Reference

Frontier uses the **Cray Programming Environment (CPE)** with AMD ROCm/HIP for GPU programming.

---

## Cray Programming Environment (CPE)

The CPE provides compiler wrappers (`cc`, `CC`, `ftn`) that automatically link MPI, LibSci, and other Cray libraries when the corresponding modules are loaded.

> **Always use `cc`/`CC`/`ftn` wrappers instead of `gcc`/`g++`/`gfortran` directly.** Direct compilers miss Cray MPI linkage.

### Loading a Programming Environment

```bash
# List available PrgEnv modules
module avail PrgEnv

# Switch to AMD compilers (best for HIP/ROCm on Frontier)
module load PrgEnv-amd
module load amd/5.7.1          # AMD compiler version
module load rocm/5.7.1         # ROCm runtime (HIP, hipcc, etc.)
module load craype-accel-amd-gfx90a   # Set GPU architecture for wrappers
module load cray-mpich                 # Cray GPU-aware MPI

# Cray LLVM compilers (good for OpenMP target offload)
module load PrgEnv-cray

# GCC compilers (broad compatibility)
module load PrgEnv-gnu
```

### CPE Module Versions

Load a specific Cray PE release to pin your environment:
```bash
# List available CPE versions
module avail cpe

# Load CPE 24.11 (December 2024)
module load cpe/24.11
```

### Compiler Wrapper Behavior

| Wrapper | What it invokes | What it links |
|---------|----------------|---------------|
| `cc` | C compiler from active PrgEnv | Cray MPI, LibSci, craype libs |
| `CC` | C++ compiler from active PrgEnv | Same |
| `ftn` | Fortran compiler from active PrgEnv | Same |

```bash
# See what a wrapper will actually do
cc --cray-print-opts
CC -craype-verbose ./empty.cpp
```

---

## HIP / ROCm GPU Programming

### Compilation

```bash
# HIP kernel with hipcc
hipcc --offload-arch=gfx90a -O3 my_kernel.cpp -o my_kernel

# Link HIP device code with host MPI code via CC wrapper
CC -xhip -offload-arch=gfx90a -O3 my_app.cpp -o my_app

# Compile separately then link
hipcc --offload-arch=gfx90a -O3 -c kernels.cpp -o kernels.o
CC -O3 -c host.cpp -o host.o
CC host.o kernels.o -lhipblas -lhipsolver -o my_app
```

### Key Compilation Flags

| Flag | Purpose |
|------|---------|
| `--offload-arch=gfx90a` | Target MI250X (Frontier) |
| `-xhip` | Treat source as HIP (when using CC) |
| `-O3` | Full optimization |
| `--gpu-max-threads-per-block=1024` | Max threads per block |
| `-G` | Debug GPU kernels (disables optimization) |
| `--save-temps` | Keep intermediate GPU assembly |

### HIP Runtime API Key Functions

```cpp
#include <hip/hip_runtime.h>

// Memory
hipMalloc(&ptr, bytes);
hipMallocManaged(&ptr, bytes);   // unified memory (XNACK mode)
hipMemcpy(dst, src, bytes, hipMemcpyHostToDevice);
hipFree(ptr);

// Execution
hipLaunchKernelGGL(my_kernel, dimGrid, dimBlock, sharedMem, stream, args...);
hipDeviceSynchronize();

// Streams
hipStream_t stream;
hipStreamCreate(&stream);
hipStreamSynchronize(stream);

// Error checking
hipError_t err = hipGetLastError();
if (err != hipSuccess) {
    fprintf(stderr, "HIP error: %s\n", hipGetErrorString(err));
}
```

---

## GPU-Aware MPI with Cray MPICH

Frontier's Cray MPICH supports direct GPU buffer passing (no CPU staging needed).

```bash
# Required setup in job script
export MPICH_GPU_SUPPORT_ENABLED=1
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH

# Do NOT set MPICH_RDMA_ENABLED_CUDA=1 (that's for NVIDIA; use GPU_SUPPORT for AMD)
```

In code, pass GPU pointers directly to MPI calls:
```cpp
double *d_buf;  // GPU pointer
hipMalloc(&d_buf, N * sizeof(double));

// Direct GPU-to-GPU MPI (no hipMemcpy needed)
MPI_Send(d_buf, N, MPI_DOUBLE, dest, tag, MPI_COMM_WORLD);
MPI_Recv(d_buf, N, MPI_DOUBLE, src,  tag, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
```

---

## AMD MI250X Architecture

| Property | Value |
|----------|-------|
| GCDs per node | 8 (4 GPUs × 2 GCDs each) |
| Compute units per GCD | 110 |
| HBM2e per GCD | 64 GB |
| XGMI links | GCDs connected via XGMI fabric (within node) |
| Peak perf (per GCD) | ~24 TFLOPs FP64, ~48 TFLOPs FP32 |

Each GCD appears as a separate device. Slurm with `--gpus-per-task=1` assigns 1 GCD per task.

### GPU Selection and Visibility

```bash
# Show visible GPU devices
rocm-smi --showallinfo

# Environment: ROCR_VISIBLE_DEVICES controls which GCDs are visible
export ROCR_VISIBLE_DEVICES=0,1,2,3    # GCDs 0–3 only

# When using srun --gpus-per-task=1, Slurm sets ROCR_VISIBLE_DEVICES automatically
```

---

## OpenMP Target Offload

The Cray compilers and AMD compilers both support OpenMP target offload to the GPU.

```bash
# With PrgEnv-cray (Clang-based)
module load PrgEnv-cray craype-accel-amd-gfx90a rocm

CC -fopenmp -std=c++17 -O3 my_omp_target.cpp -o my_app
# craype-accel-amd-gfx90a sets the target automatically

# With PrgEnv-amd
module load PrgEnv-amd amd/5.7.1 craype-accel-amd-gfx90a rocm

CC -fopenmp -std=c++17 -O3 my_omp_target.cpp -o my_app
```

Enforce GPU offload at runtime:
```bash
export OMP_TARGET_OFFLOAD=MANDATORY    # abort if offload fails
# export OMP_TARGET_OFFLOAD=DISABLED  # force CPU fallback for testing
```

---

## Common Module Sets

```bash
# AMD GPU job (most common)
module load PrgEnv-amd amd/5.7.1 rocm/5.7.1 craype-accel-amd-gfx90a cray-mpich

# GNU + MPI (CPU-only or for compatibility)
module load PrgEnv-gnu cray-mpich

# Cray + GPU (OpenMP offload)
module load PrgEnv-cray craype-accel-amd-gfx90a rocm/5.7.1 cray-mpich

# Scientific libraries
module load cray-hdf5          # HDF5 (linked to Cray MPI automatically)
module load cray-fftw          # FFTW 3
module load cray-libsci        # BLAS/LAPACK/ScaLAPACK
```

---

## Profiling and Debugging

```bash
# ROC Profiler (GPU kernel profiling)
module load rocm
rocprof --stats ./my_app          # timing stats per kernel
rocprof --hip-trace ./my_app      # HIP API trace

# ROC GDB (GPU debugger)
rocgdb ./my_app

# AMD uProf (system-level profiling)
module load amd-uprof

# Sanitizer (memory/race condition debugging)
export AMD_LOG_LEVEL=4            # verbose AMD runtime logging
```

---

## Environment Variables Cheat Sheet

| Variable | Value | Purpose |
|----------|-------|---------|
| `MPICH_GPU_SUPPORT_ENABLED` | `1` | Enable GPU-aware MPI |
| `LD_LIBRARY_PATH` | `$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH` | Runtime library path |
| `ROCR_VISIBLE_DEVICES` | `0,1,...` | Select visible GCDs |
| `OMP_NUM_THREADS` | integer | OpenMP thread count |
| `OMP_TARGET_OFFLOAD` | `MANDATORY` | Enforce GPU offload |
| `OMP_PLACES` | `cores` | CPU binding for OpenMP |
| `OMP_PROC_BIND` | `close` | CPU affinity strategy |
| `HIP_LAUNCH_BLOCKING` | `1` | Synchronous kernel launches (debug) |
| `AMD_LOG_LEVEL` | `0–4` | AMD runtime verbosity |
