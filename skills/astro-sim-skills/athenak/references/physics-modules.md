# AthenaK Physics Modules (input-block map)

Upstream docs: [hydro](https://ias-astrophysics.github.io/athenak-docs/hydro.html), [MHD](https://ias-astrophysics.github.io/athenak-docs/mhd.html), [radiation](https://ias-astrophysics.github.io/athenak-docs/radiation.html), [particles](https://ias-astrophysics.github.io/athenak-docs/particles.html), [ion-neutral](https://ias-astrophysics.github.io/athenak-docs/ion_neutral.html), [numerical relativity](https://ias-astrophysics.github.io/athenak-docs/numerical_relativity.html), [dynamical GRMHD](https://ias-astrophysics.github.io/athenak-docs/dyngrmhd.html) and its [EOS](https://ias-astrophysics.github.io/athenak-docs/dyngrmhd_eos.html), [source terms](https://ias-astrophysics.github.io/athenak-docs/source_terms.html), [diffusion](https://ias-astrophysics.github.io/athenak-docs/diffusion.html), [shearing box](https://ias-astrophysics.github.io/athenak-docs/shearing_box.html), [cyclic zoom](https://ias-astrophysics.github.io/athenak-docs/cyclic_zoom.html), [units](https://ias-astrophysics.github.io/athenak-docs/units.html).

Checked against AthenaK commit c5a0d7f (2026-11-09). Modules are switched on by the
**presence of their block** in the input file (`src/mesh/meshblock_pack.cpp`, `AddPhysics`);
an empty block (e.g. `<adm>` with no keys) counts. At least one of `<hydro>`, `<mhd>`,
`<ion-neutral>`, `<radiation>`, `<z4c>`, `<particles>`, `<gravity>` is required.
Syntax and framework blocks: `references/input-format.md`.

Input files named below are under `<athenak>/inputs/`. Those without `<problem>/pgen_name`
(or naming a generator that is not built in) need a binary built with
`-D PROBLEM=<path under src/pgen, no .cpp>`; see `references/build.md`.

## Allowed combinations (enforced at startup)

| Blocks present | Result |
|---|---|
| `<hydro>` only / `<mhd>` only | single-fluid hydro / MHD |
| `<hydro>` + `<mhd>` | fatal unless `<ion-neutral>` is also present |
| `<ion-neutral>` | requires both `<hydro>` and `<mhd>` |
| `<radiation>` | requires `<coord>/general_rel = true`; at most one of `<hydro>`/`<mhd>` |
| `<z4c>` or `<adm>` + `<mhd>` | dynamical-spacetime GRMHD (DynGRMHD) |
| `<z4c>` or `<adm>` + `<hydro>` | fatal ("use MHD instead") |
| `<z4c>` | also builds the ADM variables; `<adm>` alone = ADM metric without Z4c evolution |

## Riemann solvers by regime

`rsolver` has no default. Valid values (others abort):

| Regime (`<coord>`, `<time>/evolution`) | `<hydro>/rsolver` | `<mhd>/rsolver` |
|---|---|---|
| Newtonian, `dynamic` | `llf`, `hlle`, `hllc` (ideal EOS only), `roe` | `llf`, `hlle`, `hlld` |
| Newtonian, `kinematic` | `advect` | `advect` |
| SR (`special_rel = true`), `dynamic` | `llf`, `hlle`, `hllc` | `llf`, `hlle` |
| GR (`general_rel = true`), `dynamic` | `llf`, `hlle` | `llf`, `hlle` |
| DynGRMHD (`<adm>`/`<z4c>` + `<mhd>`) | n/a | `llf`, `hlle` |

SR/GR reject `kinematic` evolution and `eos = isothermal`.

## Reconstruction (shared by `<hydro>`, `<mhd>`, `<radiation>`)

`reconstruct` = `dc` | `plm` (default) | `ppm4` | `ppmx` | `wenoz` | `teno`.
`ppm4/ppmx/wenoz/teno` need `<mesh>/nghost >= 3`. With `fofc = true` (first-order flux
correction, hydro/MHD): `plm` needs `nghost >= 3`, the others `>= 4`.

## `<hydro>` — Newtonian / SR / GR hydrodynamics

Evolves density, momentum, energy (+ `nscalars` passive scalars). SR/GR set by `<coord>`.
Example: `hydro/sod.athinput`, `srhydro/mb1.athinput`, `grhydro/gr_fm_torus_uniform.athinput`.

| Key | Notes |
|---|---|
| `eos` | required: `ideal` (needs `gamma`) or `isothermal` (needs `iso_sound_speed`; Newtonian only) |
| `reconstruct`, `rsolver`, `fofc` | see above; `fofc` default false |
| `nscalars` | passive scalars, default 0 |
| `dfloor`, `pfloor`, `tfloor`, `sfloor` | density / pressure / temperature / entropy floors (default FLT_MIN) |
| `gamma_max` | Lorentz-factor ceiling, SR/GR |
| `nu_iso`, `nu_aniso`, `viscosity_integrator` | viscosity (presence of a `nu_*` key enables it); integrator `explicit` (default) or `sts` |
| `alpha_iso`, `alpha_aniso`, `alpha_spitzer`, `conductivity_integrator` | thermal conduction (ideal EOS only); `q_limit` optional |

Viscosity example: `hydro/viscosity.athinput`. `sts` requires `<time>/sts_integrator = rkl2`.

## `<mhd>` — Newtonian / SR / GR MHD (constrained transport)

Evolves the fluid plus face-centred magnetic field. Same EOS, reconstruction, floors,
`nscalars`, `fofc`, viscosity and conduction keys as `<hydro>`, read from `<mhd>`.
Example: `mhd/orszag_tang.athinput`, `srmhd/mub1.athinput`, `grmhd/gr_fm_torus_sane_8_4.athinput`
(GR torus pgen: `fluids/gr_torus`).

| Extra key | Notes |
|---|---|
| `sigma_max` | magnetization ceiling (Newtonian ideal/isothermal, SR, GR) |
| `gamma_max` | Lorentz-factor ceiling, SR/GR |
| `eta_ohm`, `eta_ad`, `resistivity_integrator` | Ohmic / ambipolar diffusion; `explicit` or `sts`. Example `mhd/resistivity.athinput` |

## `<coord>` — relativity and metric

Not a physics module by itself; read whenever coordinates are built.

| Key | Default | Notes |
|---|---|---|
| `special_rel` | false | SR (flat) |
| `general_rel` | false | GR in Cartesian Kerr-Schild coordinates (stationary metric); not both SR and GR |
| `minkowski` | false | GR with flat metric (then `a`/excision not read) |
| `a` | required in GR unless `minkowski` | black-hole spin |
| `excise` | true | excise inside the horizon |
| `dexcise`, `pexcise` | required if `excise` | density / pressure set inside the excised region (DynGRMHD: `dexcise`, `texcise`) |
| `flux_excise_r` | 1.0 | flux-excision radius (fixed to the horizon radius when `<radiation>` is on) |
| `excision_scheme` | `fixed` | DynGRMHD only: `fixed` \| `lapse` (`excise_lapse`, 0.25) \| `horizon` (needs `<fastflow>`; `horizon_factor`) ; also `smooth_excision`, `tdamp` |

With `<adm>`/`<z4c>` + `<mhd>`, `special_rel`/`general_rel` are ignored (metric is dynamical).

## `<units>` — physical units

Present → unit object built (else code units). Keys: `length_cgs`, `mass_cgs`, `time_cgs`
(default 1), `mu` (mean molecular weight, 1). If `<coord>/general_rel = true`, instead
requires `bhmass_msun` and `density_cgs` (length = GM/c², time = GM/c³). Needed by radiation
Compton scattering and by the `ism_cooling` source term.
Example: `radiation/rad_fm_sane_8_4.athinput`.

## `<hydro_srcterms>`, `<mhd_srcterms>`, `<rad_srcterms>` — source terms

All flags default false.

| Flag | Extra keys |
|---|---|
| `const_accel` | `const_accel_val`, `const_accel_dir` (1–3). Example `hydro/rt2d.athinput` (pgen `fluids/rt`, which also reads `<hydro>/const_accel_val`; add it there) |
| `ism_cooling` | `hrate` (heating rate); uses `<units>` |
| `rel_cooling` | `crate_rel`, `cpower_rel` (default 1) |
| `rad_beam` | `dii_dt`, `pos_1..3`, `dir_1..3`, `width`, `spread`. Example `radiation/bh_beam.athinput` |
| `self_gravity` | couples to `<gravity>` (fatal if that block is absent) |

Problem-specific sources: `<problem>/user_srcs = true` + a pgen that enrolls them.

## `<ion-neutral>` — two-fluid ion–neutral MHD

`<mhd>` = ion fluid, `<hydro>` = neutral fluid, coupled by drag. Keys: `drag_coeff` (required),
`ionization_coeff`, `recombination_coeff` (default 0). `<time>/integrator` must be `imex2`,
`imex2+` or `imex3` (rk1–rk4 abort); STS is not supported.
Example: `ion-neutral/perp_cshock.athinput`.

## `<radiation>` — grey radiation transport (discrete ordinates)

Evolves specific intensities on a geodesic angular grid; requires GR (`minkowski = true`
for flat-space tests). Example: `radiation/hohlraum_1d.athinput`, `radiation/rad_fm_sane_8_4.athinput`.

| Key | Notes |
|---|---|
| `nlevel` | required: geodesic-grid level, `10·nlevel²+2` angles; fixed for a restart |
| `rotate_geo`, `angular_fluxes` | default true |
| `reconstruct` | as above (default `plm`) |
| `n_0_floor` | default 0.1 |
| `rad_source` | matter coupling; default true when `<hydro>`/`<mhd>` present |
| `kappa_s`; `kappa_a`, `kappa_p` | opacities (required when `rad_source`; `kappa_a/kappa_p` unless `power_opacity = true`) |
| `arad` | required when `rad_source` and no `<units>` |
| `compton` | needs `<units>` |
| `affect_fluid` (true), `fixed_fluid` (false) | feedback on / freeze of the fluid |

## `<particles>` — test particles

Keys: `particle_type` (required; only `cosmic_ray`), `pusher` (required; only `drift`),
`ppc` (particles per cell, default 1; may be < 1), `assign_tag` (`index_order` | `rank_order`).
2D/3D only. Example: `particles/random_particle_drift.athinput`.

## `<turb_driving>` — Ornstein–Uhlenbeck turbulence forcing

Drives hydro and/or MHD; forcing array and RNG state go into restarts. Keys: `nlow`, `nhigh`
(mode range, 1/2), `driving_type` (0 isotropic, 1 anisotropic), `expo` (5/3),
`exp_prp`, `exp_prl`, `dedt` (energy injection rate), `tcorr` (correlation time).
Example: `hydro/turb.athinput` (pgen `fluids/turb`).

## `<shearing_box>` — local rotating frame

Keys: `qshear`, `omega0` (required), `stratified` (false). Adds orbital advection; pairs with
`ix1_bc = ox1_bc = shear_periodic`. Not compatible with SMR/AMR. Stratified (`mri3d`):
`ix3_bc = ox3_bc = user`.
Example: `shearing_box/mri3d_unstratified.athinput`.

## `<gravity>` — multigrid self-gravity

Poisson solve for the potential; couple to the fluid with `<hydro_srcterms>/self_gravity = true`.
Keys: `four_pi_G` (must be set), `threshold`, `niteration`, `npresmooth`, `npostsmooth`,
`full_multigrid`, `fmg_ncycle`, `mg_bc` (`zerofixed` | `zerograd` | `multipole`; with
`multipole`: `mporder`, `auto_mporigin`, `nodipole`). Example: `tests/selfgravity.athinput`.

## `<z4c>` — numerical relativity (Z4c + moving-puncture gauge)

Evolves the Z4c spacetime variables; also creates `<adm>` variables. Finite-difference stencil
follows `<mesh>/nghost` (2, 3 or 4). Example: `tests/linear_wave_z4c.athinput`,
`z4c/z4c_boosted_puncture.athinput`.

| Keys | Purpose |
|---|---|
| `lapse_oplog`, `lapse_harmonic`, `lapse_harmonicf`, `lapse_advect`, `shift_eta`, `shift_Gamma`, `shift_advect`, `shift_alpha2Gamma`, `shift_H` (harmonic shift, default 0) | gauge |
| `damp_kappa1`, `damp_kappa2`, `diss` | constraint damping, Kreiss–Oliger dissipation |
| `chi_div_floor`, `chi_min_floor`, `floor_chi`, `eps_floor` | conformal-factor safety |
| `slow_start_lapse`, `ssl_damping_amp`, `ssl_damping_time`, `ssl_damping_index` | lapse slow start |
| `use_z4c` (true; false = BSSN), `chi_psi_power` (-4), `extrap_order` (2; outflow-BC extrapolation), `excise_chi` (history-only excision) | formulation / misc |
| `co_N_type` (`BH` \| `NS`), `co_N_x/y/z`, `co_N_radius`, ... | compact-object trackers, numbered consecutively from 0 (no count key) |
| `nrad_wave_extraction`, `extraction_radius_N`, `waveform_dt`, `extraction_nlev` (10) | Ψ₄ extraction |
| `enable_driftcontrol`, `dc_*` | drift control (needs a tracker) |

Related blocks: `<z4c_amr>` (`method` = `trivial` | `tracker` | `chi` (`chi_min`) | `dchi`
(`dchi_max`), `radius_N_rad`/`radius_N_reflevel`), used by puncture pgens through
`<amr_criterion0> method = user`; `<cce>` (`num_radii`, `cce_dt`); `<fastflow>`
(`num_horizons`, apparent-horizon finder).

## `<adm>` — ADM metric

Holds the 3+1 metric for matter on a given spacetime. With `<adm>` + `<mhd>` and no `<z4c>`,
the pgen sets the metric and matter evolves on it. Key: `dynamic` (default false); when true
(and no `<z4c>`), the ADM variables are re-set from the pgen's metric function every stage.
Example: `dyn_grmhd/sod.athinput` (empty `<adm>` + flat metric).

## Dynamical-spacetime GRMHD (DynGRMHD)

Enabled by `<mhd>` together with `<z4c>` (full NR) or `<adm>`. Uses the PrimitiveSolver
conservative-to-primitive library; `<mhd>/eos = ideal` plus `gamma` are still read.

| `<mhd>` key | Notes |
|---|---|
| `dyn_eos` | required: `ideal` \| `piecewise_poly` \| `compose` \| `hybrid` |
| `dyn_error` | required: `reset_floor` |
| `rsolver` | `llf` \| `hlle`; `fofc_method` `llf` (default) \| `hlle` |
| `dfloor`, `tfloor`, `dthreshold` (1.0) | atmosphere floors / threshold (`pfloor` unused) |
| `c2p_tol`, `c2p_iter`, `c2perrs` | C2P tolerance (1e-15), iterations (50), error cap |
| `gamma_max` (50), `max_bsq` (1e6) | velocity and magnetization caps |
| `sN_atmosphere` | atmosphere value of species `N` |
| `pwp_poly_rmd`, `pwp_density_pieces_N`, `pwp_gamma_pieces_N`, `gamma_thermal` | `piecewise_poly` |
| `table`, `units` (`geometric_solar` default \| `geometric_kilometer` \| `nuclear` \| `cgs`), `use_NQT` | `compose`, `hybrid` (tabulated); `hybrid` also `gamma_thermal` |
| `enforce_maximum` (true), `dmp_M` (1.2), `scalar_pplimiter` (true), `dyn_scratch` (0), `fixed` (false) | relaxed-DMP FOFC, limiter, kernel scratch level, freeze fluid |

Examples: `dyn_grmhd/whisky_tov.athinput`, `dyn_grmhd/mag_tov.athinput`, BNS initial-data
readers in `dyn_grmhd/` (external libraries; see `references/build.md`).

## `<cyclic_zoom>` — cyclic zoom refinement

Enabled by an `<amr_criterionN>` with `method = cyclic_zoom` under
`<mesh_refinement>/refinement = adaptive`; that criterion block holds the zoom geometry
(`nlevels`, `r_0`, `x1c..x3c`, ...). Optional `<cyclic_zoom>`: `verbose`, `read_rst`, `write_rst`,
`max_nzmb_per_dvce`/`max_nzmb_per_host` (≤ `max_nmb_per_rank`). One zoom criterion only; seed the
finest level with a `<refined_regionN>`.
3D hydro/MHD/radiation only; rejected with ion-neutral, particles, gravity, turbulence driving,
Z4c/ADM/DynGRMHD, and shearing box. Example: `zoom/zoom_bondi.athinput`.
