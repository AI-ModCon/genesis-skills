# Building AthenaK

Upstream docs: [Build](https://ias-astrophysics.github.io/athenak-docs/build.html), [requirements](https://ias-astrophysics.github.io/athenak-docs/requirements.html), [notes for specific machines](https://ias-astrophysics.github.io/athenak-docs/notes_specific_machines.html), [problem generators](https://ias-astrophysics.github.io/athenak-docs/problem_generators.html).

Checked against AthenaK commit c5a0d7f (2026-11-09), bundled Kokkos 4.7.2.

AthenaK is a single executable, `athena`, built with CMake. Kokkos is a git
submodule (`<athenak>/kokkos`) and is compiled together with AthenaK. The backend
(Serial, OpenMP, CUDA, HIP, SYCL) and the problem generator are fixed when you
configure. Use one build directory for each backend/pgen combination.

## Get the source

```bash
git clone --recursive https://github.com/IAS-Astrophysics/athenak.git <athenak>
# already cloned without --recursive:
git -C <athenak> submodule update --init
```

The top-level `CMakeLists.txt` calls `add_subdirectory(kokkos)`. Without the submodule, configure fails.

## Out-of-source build

```bash
cmake -S <athenak> -B <build> [options]
cmake --build <build> -j 8          # or: make -C <build> -j 8
# executable: <build>/src/athena
```

- In-source builds are refused (`FATAL: In-source builds disabled`).
- The default build type is `Release`. `-D CMAKE_BUILD_TYPE=Debug` also turns on Kokkos
  debug mode and View bounds checking, so it runs much slower. Use it for debugging only.
- CMake version: AthenaK asks for 3.10, but the bundled Kokkos needs **3.16** or newer.
- C++17 is forced (`CMAKE_CXX_STANDARD 17`).
- Check what a binary was built with: `<build>/src/athena -c` prints the problem
  generator, precision, MPI and OpenMP settings.
- Use a fresh `<build>` directory per backend/pgen: Kokkos options are cached in
  `CMakeCache.txt` and persist across reconfigures.

## AthenaK CMake options

| Option | Default | Effect |
|---|---|---|
| `Athena_ENABLE_MPI` | `OFF` | `find_package(MPI)`, links MPI, also sets `Kokkos_ENABLE_MPI` |
| `Athena_ENABLE_OPENMP` | `OFF` | `find_package(OpenMP)`, also sets `Kokkos_ENABLE_OPENMP` (host backend) |
| `Athena_SINGLE_PRECISION` | `OFF` | `Real` = `float` (binary32) instead of `double` |
| `PROBLEM` | `built_in_pgens` | compile one custom pgen file (next section) |

There are no other `Athena_*` options. AthenaK sets the Kokkos defaults
`Kokkos_ENABLE_AGGRESSIVE_VECTORIZATION=ON`, plus `Kokkos_ENABLE_CUDA_LAMBDA=ON` when CUDA is on.

## Problem generator: `-D PROBLEM=`

- **Default (`built_in_pgens`).** The test problems in `src/pgen/tests/*.cpp` and the two
  `src/pgen/unit_tests/*.cpp` are always compiled in. At run time, `<problem>/pgen_name`
  picks one of them:
  `advection, cpaw, gr_bondi, cshock, divb_amr, diffusion, linear_wave, implode,
  gr_monopole, mri3d, orszag_tang, rad_linear_wave, rad_beam, shock_tube, shwave,
  z4c_boosted_puncture, z4c_linear_wave, gravity, binary_gravity, be_collapse`
  and the unit tests `eos_compose, gauss_legendre`.
- **Custom.** `-D PROBLEM=<path under src/pgen, no .cpp>`, e.g. `-D PROBLEM=fluids/blast`
  or `-D PROBLEM=z4c/z4c_one_puncture`. The file's `ProblemGenerator::UserProblem()` is
  then always called, and `pgen_name` is ignored. If the input still sets it, you get a
  "not used" warning (see `references/troubleshooting.md`).
- An input with no `<problem>/pgen_name` needs a custom build, usually the pgen of the same
  name (e.g. `inputs/hydro/blast_hydro.athinput` → `-D PROBLEM=fluids/blast`).
- An input that needs a custom pgen fails on a default build with:
  `Problem generator name could not be found in <problem> block ... Rerun cmake with -D PROBLEM=file`.
- To write your own pgen, put a `.cpp` file under `src/pgen/` (any subdirectory) and pass its
  relative path. A shipped file such as `fluids/blast.cpp` is a good template.

### Custom pgens shipped upstream

| Directory | Files (`-D PROBLEM=<dir>/<file>`) | External library |
|---|---|---|
| `fluids/` | `blast`, `current_sheet`, `disk-magnetosphere`, `field_loop`, `gr_torus`, `kh`, `mri2d`, `rt`, `shock_cloud`, `shu_osher`, `slotted_cyl`, `turb`, `twofluid` | none |
| `radiation/` | `rad_diffusion`, `rad_hohlraum`, `rad_relax`, `rad_shadow`, `rad_snake` | none |
| `particles/` | `part_random` | none |
| `z4c/` | `kerr_schild`, `z4c_gauge_wave`, `z4c_one_puncture`, `z4c_stability` | none |
| `z4c/two_punctures/` | `z4c_two_puncture` | TwoPunctures (C version) + GSL |
| `z4c/spectre/` | `z4c_spectre_bbh` | SpECTRE `BundledExporter` |
| `dyn_grmhd/` | `dyngr_tov`, `dynbbh` | none |
| `dyn_grmhd/lorene/` | `lorene_bns` | LORENE + Fortran runtime, BLAS, LAPACK, GSL |
| `dyn_grmhd/kadath/` | `kadath_bns` | Kadath (FUKA) + Boost, FFTW3, LAPACK, GSL, OpenMP |
| `dyn_grmhd/elliptica/` | `elliptica` | Elliptica ID reader + OpenMP |
| `dyn_grmhd/sgrid/` | `sgrid_bns` | SGRID (`libsgrid.a`) |
| `dyn_grmhd/rns/` | *(only `.gitkeep`; no source file at this commit)* | RNSC (CMake hook only) |

How the external libraries are found. Do not write install guides here; point the user to each library's own documentation.

- Most are expected **inside the AthenaK checkout**, as a directory or symlink:
  - `<athenak>/twopuncturesc/{include,lib/libTwoPunctures.a}`
  - `<athenak>/Lorene/...`
  - `<athenak>/kadath/{include,lib/libkadath.a}`
  - `<athenak>/Elliptica_ID_Reader/{include,lib/libelliptica_id_reader.a}`
  - `<athenak>/sgrid/lib/libsgrid.a`
  - `<athenak>/rnsc/{include,lib/libRNS.a}`
- SpECTRE is found with `find_library`. Pass `-D SPECTRE_ROOT=<spectre build>`.
- These hooks match on the `PROBLEM` string, e.g. `${PROBLEM} MATCHES "dyn_grmhd/lorene/*"`.
  Renaming a pgen directory therefore drops its link step.

## Kokkos backend and architecture

Choose **one** device backend. The host backend is Serial, or OpenMP if you set `Athena_ENABLE_OPENMP=ON`.
Set the GPU arch explicitly: autodetection needs a GPU on the build node, and login nodes
usually have none.

| Hardware | Backend flag | Arch flag(s) |
|---|---|---|
| NVIDIA A100 | `-D Kokkos_ENABLE_CUDA=ON` | `-D Kokkos_ARCH_AMPERE80=ON` |
| NVIDIA H100 | `-D Kokkos_ENABLE_CUDA=ON` | `-D Kokkos_ARCH_HOPPER90=ON` |
| NVIDIA GH200 | `-D Kokkos_ENABLE_CUDA=ON` | `-D Kokkos_ARCH_HOPPER90=ON -D Kokkos_ARCH_ARMV9_GRACE=ON` |
| NVIDIA V100 | `-D Kokkos_ENABLE_CUDA=ON` | `-D Kokkos_ARCH_VOLTA70=ON` |
| AMD MI250X | `-D Kokkos_ENABLE_HIP=ON` | `-D Kokkos_ARCH_AMD_GFX90A=ON` (alias `VEGA90A`) |
| AMD MI300A (APU) | `-D Kokkos_ENABLE_HIP=ON` | `-D Kokkos_ARCH_AMD_GFX942_APU=ON` |
| AMD MI300X | `-D Kokkos_ENABLE_HIP=ON` | `-D Kokkos_ARCH_AMD_GFX942=ON` |
| Intel Data Center GPU Max (PVC) | `-D Kokkos_ENABLE_SYCL=ON` | `-D Kokkos_ARCH_INTEL_PVC=ON` |
| CPU, OpenMP | `-D Athena_ENABLE_OPENMP=ON` | optional host arch, e.g. `Kokkos_ARCH_NATIVE`, `ZEN3`, `ZEN4`, `SPR`, `ARMV9_GRACE` |
| CPU, serial | *(none)* | optional host arch as above |

Arch names were checked in `kokkos/cmake/kokkos_arch.cmake` (Kokkos 4.7.2). For other
devices, see https://kokkos.org/kokkos-core-wiki/get-started/configuration-guide.html.
You can add a host arch flag next to a GPU arch, e.g. `Kokkos_ARCH_ZEN3` on MI250X nodes.

### Compilers expected per backend

| Backend | `CMAKE_CXX_COMPILER` | Notes |
|---|---|---|
| CUDA | `<athenak>/kokkos/bin/nvcc_wrapper` (or clang++) | If you give a plain host compiler, Kokkos routes it through `nvcc_wrapper` itself (via `kokkos/bin/kokkos_launch_compiler`). |
| HIP | `hipcc`, `amdclang++`, or a vendor wrapper (e.g. Cray `CC`) | With a non-`hipcc` clang, Kokkos adds `-xhip`. Upstream docs add `-I${ROCM_PATH}/include` and `-L${ROCM_PATH}/lib -lamdhip64` when using `CC`. |
| SYCL | `icpx` (oneAPI 2024.2.1 or newer, per Kokkos), or the MPI wrapper around it | |
| OpenMP / Serial | any C++17 compiler (GCC ≥ 8.2, Clang ≥ 8, oneAPI `icpx`), or `mpicxx` | |

With `Athena_ENABLE_MPI=ON`, CMake's `FindMPI` looks at the compiler or `PATH`. A Cray `CC`
wrapper or `mpicxx` used as the compiler is the simplest choice. For the modules and
environment of a specific machine, load the machine skill (`aurora`, `frontier`,
`perlmutter`; see `references/running.md`).

### Example configure lines

```bash
# CPU, serial (no MPI)
cmake -S <athenak> -B <build>

# CPU, MPI + OpenMP, tuned for the build host
cmake -S <athenak> -B <build> -D Athena_ENABLE_MPI=ON -D Athena_ENABLE_OPENMP=ON \
      -D Kokkos_ARCH_NATIVE=ON

# NVIDIA A100 (use HOPPER90 for H100), MPI, custom pgen
cmake -S <athenak> -B <build> -D Kokkos_ENABLE_CUDA=ON -D Kokkos_ARCH_AMPERE80=ON \
      -D CMAKE_CXX_COMPILER=<athenak>/kokkos/bin/nvcc_wrapper \
      -D Athena_ENABLE_MPI=ON -D PROBLEM=fluids/blast

# AMD MI250X (use AMD_GFX942_APU for MI300A), MPI via a Cray-style wrapper
cmake -S <athenak> -B <build> -D Kokkos_ENABLE_HIP=ON -D Kokkos_ARCH_AMD_GFX90A=ON \
      -D CMAKE_CXX_COMPILER=CC -D Athena_ENABLE_MPI=ON

# Intel PVC, MPI
cmake -S <athenak> -B <build> -D Kokkos_ENABLE_SYCL=ON -D Kokkos_ARCH_INTEL_PVC=ON \
      -D CMAKE_CXX_COMPILER=icpx -D Athena_ENABLE_MPI=ON
```

Only the serial and MPI CPU lines were compiled for this reference. The GPU lines follow the
Kokkos option names and the upstream build docs; check them on the target machine.

## Machine files

There are no machine/toolchain files upstream: no `cmake/` directory and no presets. The
"Notes for Specific Machines" in the online docs
(https://ias-astrophysics.github.io/athenak-docs) and the `hpc-skills` machine skills cover
the site environment. Older machine notes may ask you to `git checkout` a Kokkos tag (e.g.
4.5.01 for SYCL). The bundled 4.7.2 is newer: keep the submodule at the commit AthenaK pins.

## Regression tests

`<athenak>/tst/run_test_suite.py` (needs `pytest`) builds in `<athenak>/tst/build` and runs
from `<athenak>/tst`: `--cpu`, `--mpicpu`, `--gpu` (always adds `Kokkos_ENABLE_CUDA=On`:
NVIDIA only), `--style`, `--test <file|dir> ...`.
- Extra CMake flags go in **one quoted string**:
  `--gpu "-DKokkos_ARCH_AMPERE80=On -DCMAKE_CXX_COMPILER=<athenak>/kokkos/bin/nvcc_wrapper"`
  (a single flag can also be given as `--cpu=-DX=ON`).
- With `--test`, always give the device flag(s) you can build: without one it enables every
  type present, including the CUDA build.

## Quick checks after building

```bash
<build>/src/athena -c                         # backend-independent config summary
<build>/src/athena -i <athenak>/inputs/hydro/sod.athinput -d <rundir>   # ~1 s on a CPU
```

The `--kokkos-print-configuration` flag (it goes through to Kokkos) shows the enabled
backends and archs at run time.
