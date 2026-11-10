# AthenaK Input File (`athinput`) Format

Upstream docs: [Input file](https://ias-astrophysics.github.io/athenak-docs/input_file.html), [uniform mesh](https://ias-astrophysics.github.io/athenak-docs/uniform_mesh.html), [SMR](https://ias-astrophysics.github.io/athenak-docs/smr.html), [AMR](https://ias-astrophysics.github.io/athenak-docs/amr.html).

Checked against AthenaK commit c5a0d7f (2026-11-09). Parser: `src/parameter_input.cpp`;
driver of the read order: `src/main.cpp`.

## Syntax

```
<blockname>              # block header: '<' must be the first non-blank char; keep it in column 1
name = value             # one parameter per line; spaces around '=' optional
name2 = value2 # comment # everything after the first '#' is a comment
# a full-line comment
<par_end>                # optional: parsing stops here (restart files end their header with it)
```

Rules (from the parser, not conventions):
- Blank lines and lines starting with `#` are skipped. Tab characters are deleted everywhere
  (not turned into spaces); use spaces.
- A `name = value` line before the first `<block>` is a fatal error.
- No line continuation: name, value and comment must fit on one line. A value cannot contain `#`.
- Leading/trailing spaces of the value are trimmed; the value is stored as a string and
  converted when the code reads it:
  - integer: C `atoi` (so `1e3` reads as `1`; write integers plainly);
  - real: C `atof` (`1.0e-3`, `0.5`, `-1`);
  - boolean: a value starting with `0` or `1` is read as an integer; otherwise
    `true`/`false` (case-insensitive). Use only these four spellings;
  - string: used verbatim (case-sensitive: `outflow`, not `Outflow`).
- Repeated parameter in a block: the later value silently overwrites the earlier one.
  A repeated block header re-opens the same block (allowed, not recommended).
- Block names are checked (only when an input file is given with `-i`) against the prefixes
  `comment job mesh meshblock mesh_refinement refined_region amr_criterion coord adm
  shearing_box cyclic_zoom time problem output units hydro mhd ion-neutral radiation z4c
  z4c_amr cce rad_srcterms hydro_srcterms mhd_srcterms particles turb_driving gravity fastflow`.
  A name matching none of them (e.g. `<foo>`) aborts. The check is prefix-only, so numbered
  blocks (`<output3>`, `<refined_region1>`, `<amr_criterion0>`) pass, but so do typos such as
  `<jobs>` or `<hydro_typo>`; their keys then show up only as "not used" warnings.
- Do not indent a `<block>` line: the name is extracted with an offset that assumes
  `<` in column 1; `  <hydro>` becomes a block named `hydro> ` and `<hydro>` is then missing.
- Required parameters missing → `### FATAL ERROR ... Parameter name '<x>' not found in block '<b>'`.
  Optional parameters take a built-in default and are added to the parameter list as
  `# Default value added at run time` (visible in restart dumps).
- Unused parameters: just before the main loop, rank 0 prints to stderr
  `### WARNING ... input parameter <block>/name = value was not used by the code (check for a typo)`.
  This is the only typo detection; `<comment>` is exempt. Run with `-v` to get it without running.

## Block map

| Block | Required? | Purpose |
|---|---|---|
| `<comment>` | no | free text; never read |
| `<job>` | yes | `basename` = prefix of all output files |
| `<mesh>` | yes | root grid, ghost cells, boundary conditions |
| `<meshblock>` | no | MeshBlock size (default: whole mesh = 1 block) |
| `<mesh_refinement>`, `<refined_regionN>`, `<amr_criterionN>` | no | SMR/AMR |
| `<time>` | yes | integrator, CFL, stop conditions |
| `<problem>` | pgen-dependent | `pgen_name` for built-in generators + problem parameters |
| `<outputN>` | no | outputs; see `references/outputs-and-analysis.md` |
| physics blocks | ≥1 needed | `<hydro>`, `<mhd>`, `<radiation>`, `<z4c>`, ...; see `references/physics-modules.md` |

`<problem>` keys read by the framework: `pgen_name` (built-in generator name; ignored if the
binary was built with `-D PROBLEM=...`), `user_srcs`, `user_hist` (booleans, default false;
enable source terms / history columns enrolled by a custom pgen). Everything else in
`<problem>` is defined by the problem generator source.

## `<job>`

| Key | Type | Notes |
|---|---|---|
| `basename` | string, required | used by every output and by Z4c trackers/horizon files |

## `<mesh>`

| Key | Type | Default | Notes |
|---|---|---|---|
| `nx1`, `nx2`, `nx3` | int | required | root-grid cells; ≥4 in each active dim. `nx2=1,nx3=1` → 1D; `nx3=1` → 2D; `nx2=1,nx3>1` is rejected |
| `x1min`…`x3max` | real | required | all six always required, even in 1D/2D; `max > min` |
| `nghost` | int | 2 | ≥2; even with SMR/AMR; ≥3 for `ppm4/ppmx/wenoz/teno`; +1 with `fofc` |
| `ix1_bc`, `ox1_bc` | string | required | |
| `ix2_bc`, `ox2_bc` | string | required in 2D/3D | not read in 1D (setting them only warns) |
| `ix3_bc`, `ox3_bc` | string | required in 3D | not read in 1D/2D (likewise `<meshblock>` `nx2`/`nx3`) |

Boundary flags: `reflect`, `outflow`, `inflow`, `diode`, `user`, `periodic`, `vacuum`,
`shear_periodic`, `undef`. Constraints enforced at startup:
- `periodic` must be set on both faces of a direction.
- `shear_periodic` only on both x1 faces, only in 2D/3D, and requires a `<shearing_box>` block.
- `user` requires the problem generator to enroll a boundary function (fatal otherwise).

## `<meshblock>`

`nx1`, `nx2`, `nx3` (int; default = corresponding `<mesh>` value). Each must divide the mesh
`nx`, be ≥4 in active dims, and be even when SMR/AMR is on. MeshBlocks are the unit of
MPI/GPU decomposition (see `references/running.md`).

## `<mesh_refinement>` and refinement blocks

| Key | Default | Notes |
|---|---|---|
| `refinement` | `none` | `none` \| `static` \| `adaptive` |
| `num_levels` | 1 | AMR only: number of levels counting the root |
| `max_nmb_per_rank` | — | **required with AMR**; sizes device arrays; must be ≥ root blocks per rank |
| `ncycle_check` | 1 | cycles between refinement checks |
| `refinement_interval` | 5 | min cycles between (de)refinements of a block |
| `prolong_primitives` | (off) | prolongate primitives instead of conserved variables |

`<refined_regionN>` (SMR, and initial refinement with AMR): `level` (≥1), `x1min`, `x1max`,
plus `x2min/x2max` in 2D/3D and `x3min/x3max` in 3D; must lie inside the root mesh.
With AMR they only seed the initial mesh; the criteria may derefine them. To keep a region
refined, add a `location` criterion.

`<amr_criterionN>` (AMR; at least one required when `refinement = adaptive`):

| Key | Notes |
|---|---|
| `method` | `min_max`, `slope`, `second_deriv`, `location`, `cyclic_zoom`, `user` |
| `variable` | required for `min_max`/`slope`/`second_deriv`: `hydro_u_d`, `hydro_w_d`, `mhd_u_d`, `mhd_w_d`, `rad_coord_e` |
| `value_min`, `value_max` | thresholds (defaults ∓FLT_MAX). `min_max`: refine if the block max > `value_max` or min < `value_min`, otherwise derefine. `slope` / `second_deriv`: refine if the max of \|Δq\|/q (\|Δ²q\|/q) > `value_max`, otherwise derefine (`value_min` unused). Derefining happens only if no other criterion flagged the block |
| `location_x1/x2/x3`, `location_rad` | `location`: refine blocks overlapping the cube of half-width `location_rad` (default 0) around `location_x*`, up to `num_levels`; never derefines |

`user` calls a function enrolled by the pgen (e.g. Z4c puncture pgens, which read `<z4c_amr>`).
Mesh refinement is incompatible with `<shearing_box>`.

Example (adapted from AthenaK `inputs/hydro/blast_hydro_amr.athinput`, BSD-3-Clause, abridged):
```
<mesh_refinement>
refinement          = adaptive
num_levels          = 2
refinement_interval = 3
max_nmb_per_rank    = 1024
<amr_criterion0>
method   = slope
variable = hydro_w_d
value_max = 0.1
```

## `<time>`

| Key | Default | Notes |
|---|---|---|
| `evolution` | required | `static` \| `kinematic` \| `dynamic`. `kinematic` only with Newtonian `rsolver = advect` |
| `integrator` | `rk2` | `rk1`, `rk2`, `rk3`, `rk4`, `imex2`, `imex2+`, `imex3` |
| `cfl_number` | required | not checked against the integrator's stability limit |
| `tlim` | required (non-static) | stop time |
| `nlim` | -1 | max cycles; -1 = unlimited |
| `ndiag` | 1 | cycles between stdout cycle lines |
| `start_time` | 0 | initial time (new runs only) |
| `sts_integrator` | `none` | `none` \| `rkl2` (super-time-stepping for diffusion) |
| `sts_max_dt_ratio` | -1 | -1 or >0 |

`sts_integrator = rkl2` requires ≥1 diffusion process with `*_integrator = sts`, and vice versa
(see `references/physics-modules.md`). STS supports only Newtonian hydro/MHD: it is rejected
with SR/GR/dynamical GRMHD, `<ion-neutral>`, `<radiation>`, and shearing box / orbital advection.

## `<outputN>` (summary)

One block per output stream; `N` is any integer. Common keys:

| Key | Notes |
|---|---|
| `file_type` | `hst`, `tab`, `bin`, `cbin`, `vtk`, `rst`, `log`, `trk`, `pdf`, `cart`, `sph`, ... |
| `dt` or `dcycle` | one is required (neither → fatal); `dcycle` wins if both are set. A block with `dt <= 0` (and no `dcycle`) is silently skipped |
| `variable` | required except for `hst`, `rst`, `log` (`trk` needs the line but ignores its value); e.g. `hydro_w`, `mhd_w_bcc` |
| `id` | file-name tag (default = `variable`) |
| `slice_x1/x2/x3`, `ghost_zones`, `gid`, `data_format` | slicing / layout options |
| `single_file_per_rank` | `bin`, `cbin`, `rst` only |
| `file_number`, `last_time` | bookkeeping written back by the code; leave unset |

Full list, file naming and readers: `references/outputs-and-analysis.md`.

## Command-line overrides

```
athena -i run.athinput time/tlim=2.0 mesh/nx1=512 output2/dt=0.1
```
- Any argument containing both `/` and `=` is parsed as `block/name=value` (no spaces).
- Applied **after** the input file (and after a restart file), so the command line wins.
- Can only change parameters already present: an unknown block or key is a fatal error
  (`... on command line not found`). To add a parameter, edit the file or use a partial `-i` file on restart.
- Arguments without both `/` and `=` that are not flags are ignored silently.
- `athena -i run.athinput -n` prints the merged parameter list (`PAR_DUMP`) and exits: the
  quickest check of what a run will see. `-v` builds everything on one MeshBlock, prints
  unused-parameter warnings, and exits.

## Restarts and parameters

Restart files (`file_type = rst`, written to `rst/<basename>.NNNNN.rst`) begin with a full
`PAR_DUMP` of the parameters in force (file + command line + run-time defaults, with each
output's `file_number`/`last_time` updated), terminated by `<par_end>`, then the binary state.

Read order with `-r`: (1) parameters from the restart header, (2) the `-i` file if also given,
merged on top (may override and add keys/blocks), (3) command-line `block/key=value`.

```
athena -r rst/Sod.00001.rst time/tlim=0.5                 # extend a run
athena -r rst/Sod.00001.rst -i changes.athinput           # partial file: only the changed keys
```

What the restart fixes vs. what you may change:

| Fixed by the restart (input values ignored or must match) | Taken from parameters (changeable) |
|---|---|
| root mesh size/extent, `nghost`, MeshBlock size, MeshBlock tree/refinement state, `time`, `dt`, `ncycle` | `tlim`, `nlim`, `ndiag`, `integrator`, `cfl_number` |
| set of physics modules and their array sizes (`nscalars`, radiation `nlevel`): a mismatch aborts with "restart file is broken" | outputs (add/remove blocks, cadence); numbering continues from the stored `file_number` |
| `start_time` (not read on restart) | floors, solver options, AMR limits (`num_levels`, `max_nmb_per_rank`) |

Do not edit `<mesh>`/`<meshblock>` on restart: dimensionality flags are still derived from the
parameter values while sizes come from the binary header. The MPI rank count may change for
a single-file restart (blocks are re-balanced). With `single_file_per_rank = true` each rank
reads `rst/rank_<8-digit rank>/<file>` for its own rank, so restart with the same rank count;
pass any one rank's path to `-r` (detected by the `/rank_` substring).

## Annotated minimal example

Adapted from AthenaK `inputs/hydro/sod.athinput` (BSD-3-Clause). Full annotated copy, tested
with the default (built-in) problem generators: `assets/minimal_hydro.athinput`.

```
<job>
basename = Sod
<mesh>
nghost = 2
nx1 = 256                       # 1D: nx2 = nx3 = 1
x1min = -0.5
x1max = 0.5
ix1_bc = outflow
ox1_bc = outflow
nx2 = 1
x2min = -0.5
x2max = 0.5
nx3 = 1
x3min = -0.5
x3max = 0.5
<meshblock>
nx1 = 64                        # 4 MeshBlocks
<time>
evolution = dynamic
integrator = rk2
cfl_number = 0.8
tlim = 0.25
<hydro>
eos = ideal
reconstruct = plm
rsolver = llf
gamma = 1.4
<problem>
pgen_name = shock_tube
shock_dir = 1
xshock = 0.0
dl = 1.0
pl = 1.0
ul = 0.0
vl = 0.0
wl = 0.0
dr = 0.125
pr = 0.1
ur = 0.0
vr = 0.0
wr = 0.0
<output1>
file_type = hst
dt = 0.01
```
