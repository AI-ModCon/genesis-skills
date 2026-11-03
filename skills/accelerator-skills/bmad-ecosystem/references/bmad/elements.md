# Bmad elements

An element's type selects its physical model. Attributes then describe its
length, strength, orientation, aperture, and calculation options. The following
tables cover common choices and the distinctions that matter when building a
lattice.

Contents: [passive elements](#passive-elements-and-observation-points),
[magnets](#magnets), [RF](#rf-and-acceleration),
[geometry and control](#geometry-control-and-maps), [photons](#photon-optics),
and [shared attributes](#attributes-shared-by-many-elements).

The official **Lattice Elements** chapter is in
[elements.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/elements.tex).
The search labels below identify its individual definitions. Complete attribute
names, units, and defaults are in
[list-element-attributes.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/list-element-attributes.tex);
search for the element name, for example `s:list.quadrupole`.

## Passive elements and observation points

| Type | Purpose | Common attributes | Manual label |
| --- | --- | --- | --- |
| `drift` | Propagation through a length of free space | `l` | `s:drift` |
| `marker` | A zero-length named location, such as an interaction point or optics observation point | — | `s:mark` |
| `monitor`, `instrument` | Label diagnostic devices; particle tracking is drift-like | `l` | `s:monitor` |
| `pipe` | Represent a beam-pipe section; particle tracking is drift-like | `l`, aperture settings | `s:monitor` |
| `ecollimator` | Drift-like transport with an elliptical aperture | `l`, `x_limit`, `y_limit` | `s:col` |
| `rcollimator` | Drift-like transport with a rectangular aperture | `l`, `x_limit`, `y_limit` | `s:col` |

A monitor names a place to calculate or compare an orbit; it does not by itself
simulate a measurement system. Tao data associate a measured or target quantity
with that location.

## Magnets

| Type | Purpose | Common attributes | Manual label |
| --- | --- | --- | --- |
| `quadrupole` | Linear focusing in one transverse plane and defocusing in the other | `l`, `k1` or `b1_gradient`, `tilt` | `s:quad` |
| `sbend` | Dipole described with sector geometry | `l`, `g` or `angle`, `dg`, `e1`, `e2` | `s:bend` |
| `rbend` | Dipole described with rectangular geometry; converted to an equivalent `sbend` internally | `l`, `angle`, `e1`, `e2` | `s:bend` |
| `sextupole` | Quadratic transverse field, often used for chromatic correction | `l`, `k2` or `b2_gradient` | `s:sex` |
| `octupole` | Cubic transverse field, used for nonlinear optics | `l`, `k3` or `b3_gradient` | `s:oct` |
| `solenoid` | Longitudinal magnetic field with coupled transverse motion | `l`, `ks` or `bs_field` | `s:sol` |
| `sol_quad` | Combined solenoid and quadrupole field | `l`, `ks`, `k1` | `s:sq` |
| `hkicker`, `vkicker` | Horizontal or vertical steering corrector | `l`, `kick` | `s:hvkicker` |
| `kicker` | Corrector with both transverse components | `l`, `hkick`, `vkick` | `s:kicker` |
| `ac_kicker` | Time-dependent kick | `amp_vs_time` or `frequencies` | `s:ac.kick` |
| `multipole` | Thin magnetic multipole kick, specified by integrated strengths and tilt angles | `k1l`, `k2l`, `t1`, `t2`, ... | `s:mult` |
| `ab_multipole` | Thin multipole representation using normal/skew coefficients | `a1`, `b1`, `a2`, `b2`, ... | `s:ab.m` |
| `wiggler`, `undulator` | Periodic magnetic structure | `l` and field/model-specific settings | `s:wiggler` |

The bundled [beamline](../../assets/beamline/lattice.bmad) contains these definitions:

```bmad
b: sbend, l = 0.5, g = 1, e1 = 0.1, dg = 0.001
q: quadrupole, l = 0.6, k1 = 0.23
```

For an untilted quadrupole, positive `k1` focuses horizontally and defocuses
vertically for the reference species. `k1` has units m^-2; `b1_gradient` is
the physical gradient in T/m. [Field conventions](physics-conventions.md#normalized-strengths-and-physical-fields)
explain which quantity remains fixed when the reference momentum changes.

In a bend, `g = 1/rho` is the design curvature and `angle = g*l` when `l` is
the arc length. `dg` adds a bending-field error relative to that design.
Changing `g` changes the reference layout; changing `dg` changes the orbit
relative to it. `e1` and `e2` specify face angles. `rbend` and `sbend` use
different length/face conventions, so copying the same numbers between them
does not generally preserve the magnet geometry.

Both finite-length magnets and thin multipoles can represent higher-order
fields. A `multipole` specifies an integrated kick; a `sextupole` or `octupole`
also has physical length and the associated transport. The symbols `an` and
`bn` on general elements use Bmad's multipole convention, which is not simply
interchangeable with `knl`. See **Magnetostatic Multipole Fields**,
`s:mag.field` in
[electromagnetic-fields.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/electromagnetic-fields.tex).

## RF and acceleration

| Type | Purpose | Common attributes | Manual label |
| --- | --- | --- | --- |
| `lcavity` | Accelerating cavity whose reference energy can change along the lattice | `l`, `voltage` or `gradient`, `rf_frequency`, `phi0` | `s:lcav` |
| `rfcavity` | Cavity with constant reference energy, commonly used in rings | `voltage`, `rf_frequency` or `harmon`, `phi0` | `s:rfcav` |
| `crab_cavity` | RF transverse deflection | `l`, `voltage`, `rf_frequency`, `phi0` | `s:crab` |
| `e_gun` | Electron-gun element, including emission from very low momentum | Field and voltage settings for the chosen model | `s:e.gun` |

The distinction between `lcavity` and `rfcavity` is the **reference energy**
convention, not whether an individual particle receives an energy kick.
Reference energy changes also change the normalization of particle coordinates
and magnetic strengths downstream.

The official [cavity tutorial](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tutorial_bmad_tao/lattice_files/cavity.bmad)
and [multipass tutorial](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tutorial_bmad_tao/lattice_files/multipass.bmad)
show RF setup. The latter uses:

```bmad
cavity: lcavity, l = 1, voltage = 10e6, rf_frequency = 1e9
```

RF phase attributes such as `phi0` are measured in cycles (radians divided by
`2*pi`), not radians. `phi0 = 0` is on crest for the standard `lcavity`
convention. RF timing, autoscaling, and pass-dependent phases have their own
definitions; follow the element's manual section when using those features.

## Geometry, control, and maps

| Type | Purpose | Manual label |
| --- | --- | --- |
| `patch` | Change the reference coordinates and time between adjoining parts of a lattice | `s:patch` |
| `floor_shift` | Change floor-coordinate placement without affecting particle tracking | `s:floor.ele` |
| `fiducial` | Establish a reference for floor placement | `s:fiducial` |
| `fork`, `photon_fork` | Connect a path to another branch, including an emitted-photon branch | `s:fork` |
| `overlay` | Set slave attributes as functions of control variables | `s:overlay` |
| `group` | Apply increments to slave attributes as control variables change | `s:group` |
| `girder` | Represent a support whose motion contributes to supported elements' alignment | `s:girder` |
| `ramper` | Apply a parameter ramp in an application that supports ramper elements | `s:ramper` |
| `taylor` | Supply a transfer map as a Taylor expansion | `s:taylor` |
| `match` | Supply a first-order map with specified optics transformation | `s:match` |
| `em_field` | Describe general electromagnetic fields using field maps | `s:em.field` |
| `custom` | Delegate an element's behavior to application-supplied routines | `s:custom` |

A `match` element is an idealized map; finding settings for actual magnets is a
Tao fitting task. [Controllers](controllers.md) explain the shared-parameter
elements. The curated
[patch](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tutorial_bmad_tao/lattice_files/patch.bmad)
and [fork](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tutorial_bmad_tao/lattice_files/fork.bmad)
examples show how geometry elements are used in complete lattices.

## Photon optics

| Type | Purpose | Manual label |
| --- | --- | --- |
| `photon_init` | Specify a photon source distribution | `s:photon.init` |
| `crystal` | Crystal diffraction and reflection | `s:crystal` |
| `mirror` | Reflect photons from a surface | `s:mirror` |
| `multilayer_mirror` | Reflection from a multilayer coating | `s:multilayer` |
| `diffraction_plate`, `mask` | Apertures and masks used in diffraction calculations | `s:diff.plate`, `s:mask` |
| `sample` | Represent a sample interacting with photons | `s:sample` |
| `detector` | Collect photon information at a detector surface | `s:detector` |

Photons use their own phase-space definitions and tracking models.
`parameter[photon_type]` selects coherent or incoherent treatment; selecting
a photon element does not establish all of the beam or coherence settings.
Start with the relevant element definition and the **Photon Phase Space
Coordinates** section (`s:photon.phase.space`) of
[phase-space.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/phase-space.tex).

## Attributes shared by many elements

Common attribute families live in the **Element Attributes** chapter,
[attributes.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/attributes.tex):

| Need | Attributes or concept | Section/search label |
| --- | --- | --- |
| Align a magnet | `x_offset`, `y_offset`, pitches, `tilt`; bend orientation has additional conventions | **Orientation**, `s:offset` |
| Set an aperture | Limits, shape, and the location at which it is applied | **Aperture and Limit Attributes**, `s:limit` |
| Add field errors | Magnetic/electric multipole coefficients | **Multipole Attributes**, `s:multip` |
| Load a field map | `cartesian_map`, `cylindrical_map`, `grid_field`, or generalized gradients | **Field Maps**, `s:fieldmap` |
| Model wake effects | Short- and long-range wake definitions | **Wakefields**, `s:wakes` |
| Choose edge fields | `fringe_at` and `fringe_type`, with element-specific parameters | **Fringe Fields**, `s:fringe` |

Attribute availability and behavior depend on the element and calculation
method. For example, a field map attached to an element is ignored by
`bmad_standard` particle tracking. The [calculation-method overview](physics-conventions.md#tracking-and-optics-are-different-calculations)
explains where those choices are made.
