# GS2 Namelist Parameter Reference

GS2 input files use Fortran namelist syntax. Parameters not specified take their defaults.

## `&knobs` — Core Run Control

```fortran
&knobs
  delt = 0.01            ! initial timestep
  delt_option = 'default'! timestep control: 'default', 'set_by_hand', 'cfl'
  nstep = 5000           ! max number of timesteps
  tend = 100.0           ! end time (normalized units); overrides nstep if set
  beta = 0.0             ! ratio of plasma to magnetic pressure (0 = electrostatic)
  fapar = 0.0            ! 0=no A_par, 1=include A_par (electromagnetic)
  fbpar = 0.0            ! 0=no B_par, 1=include B_par
  woutunits = .false.    ! output in physical vs. normalized units
/
```

## `&species_parameters_N` — Species (one block per species)

```fortran
&species_parameters_1     ! ions
  z = 1.0                ! charge number
  mass = 1.0             ! mass (normalized to reference mass)
  dens = 1.0             ! density (normalized to reference density)
  temp = 1.0             ! temperature (normalized to reference temperature)
  tprim = 2.3            ! -d ln T / d ln r (temperature gradient drive)
  fprim = 0.8            ! -d ln n / d ln r (density gradient drive)
  vnewk = 0.01           ! collision frequency (normalized)
  type = 'ion'           ! 'ion' or 'electron' or 'beam'
/
&species_parameters_2     ! electrons
  z = -1.0
  mass = 0.000272        ! me/mi for deuterium
  dens = 1.0
  temp = 1.0
  tprim = 2.3
  fprim = 0.8
  vnewk = 0.04
  type = 'electron'
/
```

Set `nspec` in `&kt_grids_knobs` or GS2 infers from the number of `species_parameters_N` blocks.

## `&theta_grid_knobs` — Magnetic Geometry

```fortran
&theta_grid_knobs
  equilibrium_type = 's-alpha'  ! geometry model:
                                ! 's-alpha', 'miller', 'file', 'eik'
/
```

For `s-alpha`:
```fortran
&theta_grid_parameters
  ntheta = 32      ! poloidal grid points
  nperiod = 1      ! number of poloidal turns
  eps = 0.18       ! inverse aspect ratio r/R
  epsl = 0.36      ! 2*eps
  shat = 0.8       ! magnetic shear
  qinp = 1.4       ! safety factor q
  rhoc = 0.5       ! normalized minor radius
/
```

For `miller` geometry, replace with `&miller_parameters` containing `rmaj`, `rgeo`, `kappa`, `tri`, etc.

## `&fields_knobs` — Field Equations

```fortran
&fields_knobs
  field_option = 'implicit'  ! 'implicit' (recommended), 'explicit', 'local'
/
```

## `&dist_fn_knobs` — Distribution Function

```fortran
&dist_fn_knobs
  boundary_option = 'zero'    ! BC for dist. fn.: 'zero', 'linked', 'periodic'
  gridfac = 1.0               ! grid factor for velocity space
  g_exb = 0.0                 ! E×B shear rate (normalized)
/
```

## `&collisions_knobs` — Collision Operator

```fortran
&collisions_knobs
  collision_model = 'default'  ! 'default' (pitch-angle), 'lorentz',
                               ! 'full', 'ediffuse', 'none'
  heating = .false.            ! include collisional heating
/
```

## `&kt_grids_knobs` — Perpendicular Wavenumber Grid

```fortran
&kt_grids_knobs
  grid_option = 'box'          ! 'box' (nonlinear) or 'range' (linear)
/
```

For nonlinear box runs:
```fortran
&kt_grids_box_parameters
  nx = 32          ! number of kx modes (actual grid = 2*nx/3 after dealiasing)
  ny = 32          ! number of ky modes
  jtwist = 5       ! twist-and-shift BC parameter
  y0 = 10.0        ! box size parameter (~ 1/kymin)
/
```

For linear range (scan over ky):
```fortran
&kt_grids_range_parameters
  naky = 1         ! number of ky values
  aky_min = 0.3    ! minimum ky*rho_i
  aky_max = 0.3    ! maximum ky*rho_i
  nakx = 1         ! number of kx values
  akx_min = 0.0    ! minimum kx*rho_i
  akx_max = 0.0    ! maximum kx*rho_i
/
```

## `&init_g_knobs` — Initial Conditions

```fortran
&init_g_knobs
  ginit_option = 'noise'   ! 'noise', 'default', 'restart_many', 'kpar'
  phiinit = 1.0e-3         ! initial amplitude
  chop_side = .false.      ! initialize only one parallel parity
/
```

## `&gs2_diagnostics_knobs` — Output

```fortran
&gs2_diagnostics_knobs
  nwrite = 10              ! write output every N steps
  navg = 10                ! average over N steps for some diagnostics
  omegatol = 1.0e-3        ! convergence tolerance for frequency
  omegatinst = 500.0       ! time interval for frequency calculation
  save_for_restart = .true.! write restart files
  write_phi_over_time = .true.     ! include phi(t) in netcdf output
  write_apar_over_time = .false.
  write_ntot_over_time = .false.
/
```

## `&hyper_knobs` — Numerical Dissipation

```fortran
&hyper_knobs
  hyper_option = 'none'     ! 'none', 'visc_only', 'res_only', 'both'
  const_amp = .false.       ! constant vs. adaptive amplitude
  D_hypervisc = 0.1         ! hyperviscosity coefficient
/
```

## Normalized Units

GS2 uses gyrokinetic normalized units unless `woutunits = .true.`:
- Length: ion gyroradius ρ_i
- Time: a/v_ti (major radius / ion thermal speed)
- Temperature: reference ion temperature T_ref
- Density: reference density n_ref
