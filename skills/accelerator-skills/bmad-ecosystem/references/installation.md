# Installing Bmad, Tao, and PyTao

Bmad supplies the simulation libraries; Tao supplies the executable and shared
library used by PyTao. Choose a conda-forge environment for prebuilt packages,
or a source build for development and custom build settings. A facility-provided
installation can also supply Tao and its shared library.

Contents: [conda-forge](#prebuilt-packages-with-conda-forge),
[source builds](#build-bmad-and-tao-from-source),
[PyTao with an existing Bmad installation](#add-pytao-to-an-existing-bmad-installation),
and [verification](#verify-with-the-bundled-beamline).

## Prebuilt packages with conda-forge

Use a Linux or macOS shell with [Miniforge](https://conda-forge.org/download/).
On Windows, run Linux and its conda installation inside WSL2. Install the native
libraries, executable, and Python interface:

```bash
conda install -c conda-forge bmad pytao
```

Keep this runtime separate from a source-build environment: sourcing
`util/dist_source_me` while using the prebuilt packages can introduce conflicting
library paths. On macOS, native Tao plotting requires XQuartz; the verification
below uses `-noplot`.

See the [Bmad installation guide](https://wiki.classe.cornell.edu/ACC/ACL/OffsiteDoc)
for platform setup and conda options, and
[PyTao installation](https://bmad-sim.github.io/pytao/installation/) for Python
package installation.

## Build Bmad and Tao from source

Download the `bmad_dist.tar.gz` asset from a
[Bmad release](https://github.com/bmad-sim/bmad-ecosystem/releases). This archive
includes the external packages used by the build. GitHub's automatically
generated source archives contain only the repository contents. Developers using
a Git checkout also need `bmad-external-packages`; the
[repository README](https://github.com/bmad-sim/bmad-ecosystem#compile-from-source)
describes that arrangement and an optional conda-based build environment.

Install the platform prerequisites listed in the
[build guide](https://wiki.classe.cornell.edu/ACC/ACL/OffsiteDoc), then configure
the compiler and plotting backend in `util/dist_prefs`. For PyTao, enable shared
libraries with `ACC_ENABLE_SHARED="Y"` or `ACC_ENABLE_SHARED_ONLY="Y"`, as described
in the [PyTao installation requirements](https://bmad-sim.github.io/pytao/installation/).

From a Bash shell, substitute the unpacked release directory below:

```bash
export DIST_BASE_DIR="/path/to/bmad-release"
source "$DIST_BASE_DIR/util/dist_source_me"
cd "$DIST_BASE_DIR"
util/dist_build_production
```

Source `util/dist_source_me` in subsequent sessions to select that release.
`accinfo` displays its environment and compiler settings. The build guide covers
platform-specific resource limits and troubleshooting.

## Add PyTao to an existing Bmad installation

With the Bmad environment initialized and a Python environment active:

```bash
python -m pip install pytao
```

The Python package loads the separately installed Tao shared library. PyTao's
[library loader](https://github.com/bmad-sim/pytao/blob/master/pytao/core.py)
checks an explicit library path, then the release's
`$ACC_ROOT_DIR/production/lib`, then system library discovery.

`PYTAO_LIB_PATH` can identify the library file or its containing directory.
For a conda installation that needs an explicit path:

```bash
export PYTAO_LIB_PATH="$CONDA_PREFIX/lib"
```

For a source build, use the release's `production/lib` directory. The library
is typically `libtao.so` on Linux or `libtao.dylib` on macOS. Python and the native
library must use compatible architectures and runtime dependencies.

## Verify with the bundled beamline

Run these checks from the `bmad-ecosystem` skill directory with the selected
environment active. For a Python check, use PyTao:

```python
from pytao import Tao

tao = Tao(
    lattice_file="assets/beamline/lattice.bmad",
    noinit=True,
    noplot=True,
)
print(tao.ele_twiss("END"))
```

The Python check exercises library loading, lattice parsing, and an optics
query. The [PyTao guide](pytao.md) continues with model changes and plotting.

For a standalone Tao check, use an interactive terminal session when the
available tools support sending commands to a running process:

```bash
tao -lat assets/beamline/lattice.bmad -noinit -noplot
```

This command opens a Tao prompt and keeps running until `exit`. `-noplot`
disables plotting. Enter `show lattice` to inspect the beamline, then `exit` to
return to the shell.

| Symptom | Check |
| --- | --- |
| Shell cannot find `tao` | Activate the conda environment or source the release setup script. |
| Python cannot import `pytao` | Check `python -m pip show pytao` with the interpreter used by the script or notebook. |
| PyTao cannot find `libtao` | Check shared-library build settings and `PYTAO_LIB_PATH`; an old `ACC_ROOT_DIR` can select another release. |
| Loader reports a missing dependency or symbol | Check that Python, `libtao`, and its dependencies come from a compatible installation. |
| Tao reports a missing lattice file | Run from the skill directory or supply an absolute lattice path. |
