# AthenaK Outputs and Analysis

Upstream docs: [Outputs](https://ias-astrophysics.github.io/athenak-docs/outputs.html), [analysis](https://ias-astrophysics.github.io/athenak-docs/analysis.html).

Checked against AthenaK commit c5a0d7f and plot-tools commit f29d3e6 (2026-11-09).
Output code lives in `<athenak>/src/outputs/`; `outputs.cpp` dispatches on `file_type`.

Routing:

| Data | Tool |
|------|------|
| `.bin` mesh dumps (2D, 3D, sliced, SMR/AMR) | plot-tools `athplot.load_ath_bin.BinaryData` (streams per MeshBlock) |
| Variables split across several `.bin` files | `athplot.group_data.GroupData` |
| `sph/*.vtk` spherical surfaces | `athplot.load_sph_vtk.SphericalData` |
| Compact-object tracker `<basename>.co_N.txt` | `athplot.tracker.Tracker` |
| `.hst`, `.tab` | `<athenak>/vis/python/athena_read.py` (`hst()`, `tab()`) |
| `.bin` -> ParaView/VisIt/yt | `<athenak>/vis/python/make_athdf.py` / `bin_convert.py` |
| `.cbin` | `vis/python/bin_convert.py` (BinaryData rejects it) |
| `cart/*.bin` | `vis/python/cartgrid.py` (`CartesianGridData`) |

## `<outputN>` blocks: common keys

One block per output; `N` is any integer, so blocks need not be consecutive. Block syntax:
`references/input-format.md`.

| Key | Default | Meaning |
|-----|---------|---------|
| `file_type` | required | one of the types below; anything else is fatal |
| `dt` | required unless `dcycle` | simulation time between dumps; block ignored if `dt <= 0` |
| `dcycle` | - | dump every N cycles; if present, `dt` is ignored |
| `variable` | required except `hst`, `rst`, `log` | variable or group (see below); `trk` also needs the line, but ignores its value |
| `id` | `variable` | string used in the file name (use it to keep two blocks with the same variable apart) |
| `file_number` | 0 | first dump number |
| `slice_x1`/`slice_x2`/`slice_x3` | none | write only the plane of cells containing that coordinate (no interpolation; each refinement level samples its own cell); must lie inside the mesh |
| `ghost_zones` | false | include ghost cells |
| `gid` | -1 | write only MeshBlock `gid` (fatal if the mesh has a single MeshBlock) |
| `single_file_per_rank` | false | `bin`, `cbin`, `rst` only: one file per MPI rank in `rank_XXXXXXXX/` subdirs |
| `data_format` | `%12.5e` | printf format for `hst`/`tab` columns |

Only one `hst`, one `rst` and one `log` block are allowed per run. `NNNNN` below is the
5-digit `file_number`; all paths are relative to the run directory (`-d`).

## Output types

| `file_type` | Contents | Type-specific keys | Files |
|-------------|----------|--------------------|-------|
| `hst` | volume-integrated sums each `dt`, one row per dump, `[n]=name` header | `user_hist_only` (default false). `.user.hst` needs `<problem>/user_hist = true` and a pgen that enrols a history function (e.g. `gr_torus`, `dyngr_tov`); `user_hist = true` without one aborts | `<basename>.hydro.hst`, `.mhd.hst`, `.user.hst`; Z4c: `<basename>.z4c.user.hst` |
| `tab` | ASCII 1D line: `gid`, index, coordinate, variables | must reduce to 1D: 2D needs `slice_x1` or `slice_x2`, 3D needs two `slice_x*` | `tab/<basename>.<id>.NNNNN.tab` |
| `bin` | binary MeshBlock dump: text header + full input-file dump, then per block indices, logical location, level, extent, float32 data | `slice_x*`, `ghost_zones`, `gid`, `single_file_per_rank` | `bin/<basename>.<id>.NNNNN.bin`; per rank: `bin/rank_XXXXXXXX/<basename>.<id>.NNNNN.bin` |
| `cbin` | `bin`-like, block-averaged by `coarsen_factor` | `coarsen_factor` (required; every MeshBlock dimension must be divisible by it, so 2D meshes abort), `compute_moments` (writes `<q>`..`<q^4>` as `<var>_1st`..`_4th`), `single_file_per_rank` | `cbin_<id>_<factor>/<basename>.<id>.NNNNN.cbin` (+ `rank_XXXXXXXX/`) |
| `vtk` | legacy VTK `STRUCTURED_POINTS` sized from the root grid (uniform meshes, or one block via `gid`) | `slice_x*`, `gid` | `vtk/<basename>.<id>[.<gid>].NNNNN.vtk` |
| `pvtk` | particle VTK | `variable = prtcl_all` | `pvtk/<basename>.<id>[.<gid>].NNNNN.part.vtk` |
| `trk` | tracked particles (tag < `nparticles`): float32 x,y,z,vx,vy,vz appended each dump | `nparticles` (required) | `trk/<basename>.trk` |
| `pdf` | ASCII histogram (1D or 2D) of one variable; groups like `hydro_w` are rejected | `bin_min`, `bin_max`, `nbin` (required); `logscale` (true), `mass_weighted` (false); 2D: `variable_2`, `bin2_min`, `bin2_max`, `nbin2`, `logscale2` | `pdf_<id>[_<variable_2>]/<basename>.NNNNN.pdf` + `<basename>.bins.pdf` |
| `cart` | interpolation onto a Cartesian box (own binary format) | `center_x/y/z` (0), `extent_x/y/z` (2.0), `numpoints_x/y/z` (32), `chebyshev` (false) | `cart/<basename>.<id>.NNNNN.bin` |
| `sph` | interpolation onto spherical shells, binary legacy VTK `STRUCTURED_GRID`, optional `weights` field (r^2 dOmega) | exactly one of `radius`, `radii = r1, r2, ...`, or `nradii` + `r_min` + `r_max` (+ `r_spacing` = `linear` (default) / `log`); `ntheta` (32), `nphi` (2*ntheta), `theta_spacing` (`uniform_costheta`/`uniform_theta`), `theta_centering` (`node`/`cell`), `xc`/`yc`/`zc` (0), `weights` (true) | `sph/<basename>.r=<R>.<id>.NNNNN.vtk`, or `r=<Rmin>-<Rmax>` for several shells (`%.2f`) |
| `rst` | restart dump (see `references/running.md`) | `single_file_per_rank` | `rst/<basename>.NNNNN.rst` or `rst/rank_XXXXXXXX/<basename>.NNNNN.rst` |
| `log` | event counters: `cycle eos_dfloor eos_efloor eos_tfloor eos_vceil eos_fail c2p_it fofc`; rows only when a counter is nonzero | - | `<basename>.log` |

History columns: `time dt mass 1-mom 2-mom 3-mom tot-E 1-KE 2-KE 3-KE` (+ `1-ME 2-ME 3-ME` for
MHD, + `scal-0`, `scal-1`, ... for passive scalars). No `tot-E` with an isothermal EOS. Z4c: `C-norm2 H-norm2 M-norm2 Z-norm2 ...
Volume`.

Compact-object trackers are not `<output>` blocks. They come from `<z4c>` `co_N_type = BH|NS`
(plus `co_N_x/y/z`, `co_N_out_every`, `tracker_mode`). Each writes `<basename>.co_N.txt` with
columns `iter time x y z vx vy vz`; set `<z4c>` `filename` to change the `co_` prefix.

### `variable` names

Defined in `src/outputs/outputs.hpp` (`var_choice`). An unknown name is fatal. Asking for a
module that was not built (e.g. `mhd_*` without `<mhd>`) is also fatal.

| Group | Single components | Notes |
|-------|-------------------|-------|
| `hydro_u`, `hydro_w` | `hydro_u_d/_m1/_m2/_m3/_e/_s`, `hydro_w_d/_vx/_vy/_vz/_e/_s` | conserved / primitive; `_s` = passive scalars |
| `mhd_u`, `mhd_w`, `mhd_bcc`, `mhd_u_bcc`, `mhd_w_bcc` | `mhd_u_*`, `mhd_w_*`, `mhd_bcc1/2/3` | `mhd_w_bcc` = primitives + cell-centred B; `mhd_t` (DynGRMHD temperature) |
| derived (computed at output time) | `hydro_wz`, `hydro_w2`, `mhd_wz`, `mhd_w2`, `mhd_jz`, `mhd_j2`, `mhd_curv`, `mhd_k_jxb`, `mhd_curv_perp`, `mhd_bmag`, `mhd_divb`, `mhd_jcon`, `mhd_dynamo_ks` | e.g. `mhd_jz` writes a field named `jz` |
| radiation | `rad_coord`, `rad_fluid`, `rad_coord_fluid`, `rad_hydro_*`, `rad_mhd_*` | needs `<radiation>` |
| `adm` | `adm_gxx`..`adm_gzz`, `adm_Kxx`..`adm_Kzz`, `adm_psi4`, `adm_alpha`, `adm_betax/y/z` | GR / NR |
| `z4c` | `z4c_chi`, `z4c_g*`, `z4c_Khat`, `z4c_A*`, `z4c_Gam*`, `z4c_Theta`, `z4c_alpha`, `z4c_beta*` | |
| `weyl`, `con`, `tmunu` | `weyl_rpsi4/ipsi4`; `con_C/H/M/Z/Mx/My/Mz`; `tmunu_E`, `tmunu_S*` | |
| other | `turb_force`, `grav_phi`, `hydro_sgs`, `mhd_sgs`, `prtcl_all`, `prtcl_d` | |

Field names inside files are short labels (`dens velx vely velz eint bcc1 bcc2 bcc3`, `adm_gxx`, ...).
Primitive output stores `eint`, not pressure. Read the actual list with `BinaryData(f).variable_names`.

Tips: write `slice_x3 = <z>` `bin` outputs for frequent movies, and full 3D dumps rarely.
Leave `ghost_zones` off for analysis. BinaryData still opens such files, but each block then
carries `nx+2*nghost` cells over the interior extent, so plots are shifted and sums double-count.

## Analysis part 1: plot-tools (`athplot`), primary tool for mesh data

plot-tools is GPL-3.0: install and call it, do not copy its code.

### Install

```bash
pip install git+https://github.com/jfields7/plot-tools.git            # latest main
pip install git+https://github.com/jfields7/plot-tools.git@f29d3e6754696b9b1f2ea764e4455283fd230437  # tested
pip install -e <plot-tools-clone>                                       # editable checkout
```

- Package name `athplot` (v0.2), Python >= 3.8, build backend `hatchling`.
- Dependencies (`pyproject.toml`): numpy, scipy, matplotlib, `vtk>=9.4` (large wheel), and
  `pycompose` from a GitHub URL (it also pulls in `h5py`). On an offline or firewalled login
  node, preinstall these or build a wheelhouse elsewhere.
- Minimal install for `.bin` work: `pip install numpy scipy matplotlib`, then
  `pip install --no-deps <plot-tools-clone>`. Without the optional packages these still import:
  `athplot`, `load_ath_bin`, `group_data`, `image`, `tracker`, `utils.units`.
  These fail: `load_sph_vtk` and `utils.sph_integrate` (need `vtk`), and `utils.eos` / `utils.ejecta`
  (need `h5py`; NQT tables also need PyCompOSE).
- Use a non-interactive backend on clusters: `MPLBACKEND=Agg` or `matplotlib.use("Agg")`.

### `BinaryData` (`athplot.load_ath_bin`)

The constructor reads only the header, the embedded input file and the MeshBlock index.
Field data stays on disk and is read one block at a time.

| Name | Notes |
|------|-------|
| `BinaryData(filename)` | raises `RuntimeError('Unrecognized data file format.')` / `'Could not read location size.'` on non-`bin` files |
| `.time`, `.cycle`, `.variable_names`, `.extent` (root domain), `.input_file[block][key]` (strings), `.blocks` (list of `MeshBlock`) | metadata, no data read |
| `.is_2d()` | true if any block dimension is 1 (2D runs, 1D runs, and `slice_x*` outputs) |
| `.get_block_data(var, slice_loc=None, block_filter=lambda b: True)` | generator of `(block, array)`. `var` may be a name, a list/tuple of names (yields a tuple of arrays), or a registered `"derived:..."` name. Arrays are `(nz, ny, nx)` in 3D, 2D otherwise. `slice_loc=('x'|'y'|'z', coord)` is 3D only and yields `MeshBlockSlice` objects |
| `.plot_slice(var, ax=None, cmap='viridis', norm=None, vmin=None, vmax=None, interpolation='none', origin='lower', slice_loc=None, rescale=1., unit_length=1.0)` | one `imshow` per block; returns the last image (use it for the colorbar). 3D data requires `slice_loc` |
| `.register_derived_variable(name, f, *varnames)` | `name` must start with `derived:`; `f(*arrays)` is called per block |

`MeshBlock` attributes: `size` `[nx, ny, nz]`, `level`, logical `i, j, k`, `coords`
`(x1min, x1max, x2min, x2max, x3min, x3max)`, and `dx` `[dx1, dx2, dx3]` (correct per level, so
`prod(dx)` is the cell volume under SMR/AMR). Methods: `get_extent()`, `get_coords()` (cell-centre 1D
arrays), `get_coord_blocks()` (meshgrids matching the data array), `is_2d()`, and `restrict()`
(index into a global unigrid array; uniform meshes only).

`MeshBlockSlice` (yielded with `slice_loc`) has `get_extent()`, `get_coord_blocks()` and
`restrict()`. Its `get_coords()` is broken at the tested commit for `y`/`z` slices (AttributeError).

Use the block iterator directly for anything that is not a picture: totals, histograms, profiles,
extrema, or selecting refinement levels (`block_filter=lambda b: b.level == L`). Memory stays at one
block, so it works on dumps larger than RAM.

### `GroupData`, `Image`, `SphericalData`, `Tracker`

| Class / method | Notes |
|----------------|-------|
| `athplot.group_data.GroupData(filenames)` | several `.bin` files from the same dump, e.g. `<basename>.adm.NNNNN.bin` + `<basename>.mhd_w_bcc.NNNNN.bin`. Checks block count, block size and dimensionality |
| `.register_derived_variable(name, f, *varnames)`, `.plot_slice(var, ax, cmap, norm, vmin, vmax, interpolation, origin, slice_loc, rescale)` | each name is looked up in whichever file has it. Derived variables work only on 2D/sliced data; on 3D data with `slice_loc` it raises `RuntimeError`, so write `slice_x*` outputs for such plots. `.datasets` holds the `BinaryData` objects |
| `athplot.image.Image(filename, extent, var, slice_loc=None)` | gathers the points of one variable from blocks inside `extent=[xmin, xmax, ymin, ymax]`, then interpolates with `scipy.griddata`. Slower than streaming |
| `.make_image_data(xres, yres, method='nearest', return_grid=False, transform=None)` | uniform 2D array, `[y, x]` order |
| `.make_var_data(xres, yres, var, extent, method='nearest', return_grid=False, transform=None, slice_loc=None)` | re-gathers for another variable or extent |
| `.plot_line(npoints, start, end, method='linear', var=None, extent=None, slice_loc=None)` | values along a straight line `(x0, y0)`->`(x1, y1)` (line-outs) |
| `.transform_coordinates(xtransform, ytransform)` | rescale coordinates in place |
| `athplot.load_sph_vtk.SphericalData(filename)` | `sph` output. Attributes: `time`, `cycle`, `radii`, `theta`, `phi` (`(nphi, ntheta)`), `field_names`, `fields3d[var]` `(nradii, nphi, ntheta)`, `fields` (single shell squeezed) |
| `.shell(var, iradius=0)`, `.radial_profile(var, reduction=np.mean)`, `.integrate(var)` | `integrate` sums `weights*var` per shell (needs `weights = true`, the default) |
| `.plot_data(var, ax, cmap='viridis', norm=None, vmin=None, vmax=None, iradius=0)` | 3D surface on a `projection='3d'` axis; returns `(surf, ScalarMappable)` |
| `athplot.tracker.Tracker(fname)` | reads `<basename>.co_N.txt`, drops duplicate times; `time it x y z vx vy vz`; `smooth_walk()` returns smoothed `(x, y)` for `tracker_mode = walk` (assumes motion in the x-y plane) |

`athplot.utils` (general-purpose parts only): `units` has unit systems (`cactus`, `cgs`, `metric`)
and `conv_*(ua, ub, value)` converters, e.g. G=c=Msun code units to CGS. `sph_integrate` has
`integrate_over_sphere` and `integrate_over_phi` for `(nphi, ntheta)` arrays. `eos.EquationOfState`
reads PyCompOSE HDF5 tables. `ejecta` is specific to NR outflow analysis.

### Limitations (restated from the plot-tools README)

- Streaming draws each block separately, so give `plot_slice` a fixed colour scale: `norm=LogNorm(vmin, vmax)`
  or `vmin`/`vmax`. Otherwise every block auto-scales and the image is a patchwork. If the range is unknown,
  do a cheap first pass over `get_block_data` for min/max.
- The README also warns that ranges spanning many decades get clipped to each block's data range
  (seams). The CHANGELOG lists a fix for log-scaled colorbars; if seams remain, narrow the range or use
  `Image` for a single interpolated array.
- 3D `slice_loc`: pick a coordinate at a cell centre. A coordinate on an interior cell face raises
  `ValueError: cannot reshape`. One on a MeshBlock face returns blocks from both sides, so reductions
  count them twice.

### Binary layouts (tested)

| Layout | `BinaryData` |
|--------|--------------|
| default `bin` (serial or MPI, uniform, SMR, AMR, 2D, 3D, `slice_x*`) | yes |
| `single_file_per_rank` `bin` | yes, per file. Each `bin/rank_XXXXXXXX/` file has a full header but only that rank's blocks: loop over all rank files |
| `ghost_zones = true` | opens, but blocks include ghosts (see above) |
| `cbin` (any layout) | no: `RuntimeError: Could not read location size.` (different header). Use `vis/python` |
| `cart/*.bin` | no: `Unrecognized data file format.`. Use `vis/python/cartgrid.py` |

### Bundled examples

`<plot-tools>/examples/` has `plot_slice.py`, `plot_derived.py`, `plot_group.py`,
`plot_image.py`, `plot_sph.py` and `plot_trackers.py`. They read `data/...`, so run them from
`examples/` (`cd examples && MPLBACKEND=Agg python plot_slice.py`). Use them as templates.

## Analysis part 2: AthenaK `vis/python`, only where plot-tools stops

Use it from the AthenaK checkout; do not copy it. Run scripts by path, or put
`<athenak>/vis/python` on `PYTHONPATH` / `sys.path` for imports. Needs numpy; `bin_convert`
and `athena_read.athdf` need `h5py`.

| Name | Use |
|------|-----|
| `athena_read.hst(filename, raw=False)` | dict column -> array. Each start or restart appends a new header, and `hst` reads **only the data after the last header** (warns "Multiple headers found"): on a restarted run it silently drops everything before the restart. Use `scripts/hst_summary.py` for the full history |
| `athena_read.tab(filename)` | dict: `time`, `cycle`, `i`, `x1v` (or `x2v`/`x3v`), variables |
| `athena_read.athdf(filename, ...)` | read converted `.athdf` |
| `plot_hst.py -i <file.hst> -v <column> [-xlog] [-ylog]` | quick look at one column vs time. Plots one column only (comma lists fail). An unknown name prints the valid columns, then raises. `-o <file>` saves nothing at the tested commit; it only switches to a non-interactive backend |
| `plot_tab.py -i <file.NNNNN.tab> -v <col> [-n N]` | interactive quick look, or an animation of N consecutive `.tab` files. One column only; `-o` saves nothing (it only switches to the Agg backend), so it is useless on headless nodes. Use `athena_read.tab` instead |
| `make_athdf.py <stem> [-v]` | converts every `<stem>*.bin` to `.athdf` + `.athdf.xdmf` beside it. The stem is a prefix: `bin/run.mhd_w` also matches `bin/run.mhd_w_bcc.*` |
| `bin_convert.py f1.bin [f2.bin ...]` / `bin_convert.convert_file(fname)` | same, per file |
| `bin_convert.read_binary`, `read_coarsened_binary`, `read_all_ranks_binary`, `read_all_ranks_coarsened_binary`, `write_athdf(name, filedata)`, `write_xdmf_for(xdmfname, athdf_basename, filedata)` | building blocks for `cbin` and per-rank layouts. The `read_all_ranks_*` functions take the `rank_00000000` file. They silently keep only the largest rank files: with unequal blocks per rank (tested: 3 blocks on 2 ranks) data is lost. Prefer default-layout `bin` for conversion |
| `cartgrid.CartesianGridData(fname)` | `cart` output: `.time`, `.cycle`, `.center`, `.extent`, `.numpoints`, `.variables[name]` |
| `plot_slice.py <file.bin> <var> <out.png> [-d x/y/z] [-l loc] [--vmin --vmax -n log ...]` | fallback slice plotter only. It has many GR/radiation `derived:` quantities (`derived:?` lists them) but does not read `cbin` |

`plot_hst.py` does not list columns, print first/last/min/max, or plot several columns. Use the
skill's `scripts/hst_summary.py` (standard library; matplotlib for `--plot`). It joins all
restart segments, drops rows a restart superseded, and flags NaNs:

```bash
python3 scripts/hst_summary.py <basename>.hydro.hst                 # columns + first/last/min/max
python3 scripts/hst_summary.py <basename>.hydro.hst --plot tot-E,mass -o hst.png --logy
python3 scripts/hst_summary.py <basename>.hydro.hst --csv > hst.csv
```

## Short worked examples

All tested on CPU against outputs from a serial and a 2-rank MPI build, and against plot-tools'
`examples/data`. `<basename>` comes from `<job>/basename`; run them in the run directory.

(a) 2D density slice with a fixed `LogNorm` (3D: pass a cell-centre `slice_loc`):

```python
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from athplot.load_ath_bin import BinaryData

d = BinaryData("bin/<basename>.mhd_w_bcc.00010.bin")   # header + block index only
kw = {} if d.is_2d() else {"slice_loc": ("z", 0.01)}
fig, ax = plt.subplots()
im = d.plot_slice("dens", ax=ax, cmap="inferno", norm=LogNorm(vmin=1e-2, vmax=1e1), **kw)
fig.colorbar(im, ax=ax, label=r"$\rho$")
ax.set_title(f"t = {d.time:.3g} (cycle {d.cycle})")
fig.savefig("dens.png", dpi=150)
```

(b) Derived variables, one file and two files:

```python
d = BinaryData("bin/<basename>.mhd_w_bcc.00010.bin")
d.register_derived_variable("derived:pmag", lambda b1, b2, b3: 0.5*(b1**2 + b2**2 + b3**2),
                            "bcc1", "bcc2", "bcc3")
im = d.plot_slice("derived:pmag", norm=LogNorm(vmin=1e-4, vmax=1e0))

from athplot.group_data import GroupData
from matplotlib.colors import SymLogNorm
g = GroupData(["bin/<basename>.mhd_w_bcc.00010.bin", "bin/<basename>.mhd_jz.00010.bin"])
g.register_derived_variable("derived:jz_rho", lambda jz, rho: jz/rho, "jz", "dens")
im = g.plot_slice("derived:jz_rho", cmap="RdBu_r",
                  norm=SymLogNorm(linthresh=1e-2, vmin=-1e2, vmax=1e2))
```

(c) Reduction over a large 3D dump, one MeshBlock in memory at a time (works with AMR):

```python
import numpy as np
from athplot.load_ath_bin import BinaryData

d = BinaryData("bin/<basename>.mhd_w_bcc.00010.bin")
edges = np.logspace(-3, 2, 51)
hist, mass, px = np.zeros(len(edges) - 1), 0.0, 0.0
for blk, (rho, vx) in d.get_block_data(["dens", "velx"]):
    dV = np.prod(blk.dx)
    mass += rho.sum() * dV
    px += (rho * vx).sum() * dV
    hist += np.histogram(rho, bins=edges, weights=np.full(rho.shape, dV))[0]
print(f"t={d.time:.4g} mass={mass:.6e} x-mom={px:.6e}")   # compare with hst mass, 1-mom
```

(d) Radial profile, surface integral and mass flux from a multi-shell `sph` dump:

```python
import numpy as np
from athplot.load_sph_vtk import SphericalData

s = SphericalData("sph/<basename>.r=0.10-0.40.mhd_w.00010.vtk")
rho_avg = s.radial_profile("dens")          # (nradii,)
m_shell = s.integrate("dens")               # sum(weights*rho); weights = r^2 dOmega
th, ph, f = s.theta, s.phi, s.fields3d
vr = (f["velx"]*np.sin(th)*np.cos(ph) + f["vely"]*np.sin(th)*np.sin(ph) + f["velz"]*np.cos(th))
mdot = (f["weights"]*f["dens"]*vr).sum(axis=(1, 2))   # per shell
```

(e) History column vs time (single-segment runs; for restarted runs use `scripts/hst_summary.py`, above):

```python
import sys
sys.path.insert(0, "<athenak>/vis/python")
import athena_read
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

h = athena_read.hst("<basename>.mhd.hst")
print(list(h))                               # available columns
plt.plot(h["time"], h["tot-E"]); plt.xlabel("time"); plt.ylabel("tot-E")
plt.savefig("totE.png", dpi=150)
```

(f) `.bin` series for ParaView/VisIt (open the `.athdf.xdmf` files):

```bash
python <athenak>/vis/python/make_athdf.py bin/<basename>.mhd_w_bcc -v
python <athenak>/vis/python/bin_convert.py bin/<basename>.mhd_w_bcc.00010.bin   # single file
```

For `cbin`: `fd = bin_convert.read_coarsened_binary(f)`, then `write_athdf(out, fd)` and
`write_xdmf_for(out + ".xdmf", os.path.basename(out), fd)`.
