# Bmad physics conventions

Use this guide when interpreting a lattice, particle coordinates, field
strengths, or calculated optics. These conventions also apply when the values
are obtained through Tao or PyTao.

Contents: [reference quantities](#reference-particle-and-units),
[coordinates](#charged-particle-phase-space), [frames](#spatial-coordinate-frames),
[fields](#normalized-strengths-and-physical-fields),
[optics](#optics-and-dispersion), and [calculation methods](#tracking-and-optics-are-different-calculations).

## Reference particle and units

The reference species and momentum define the normalization used by a lattice.
The reference time gives the arrival-time origin at each longitudinal position.
A tracked particle can differ from this reference in position, momentum,
arrival time, and, when explicitly configured, species.

| Quantity | Bmad convention |
| --- | --- |
| Lengths, positions, beta functions | Metres |
| Geometric angles, betatron phase | Radians |
| `e_tot` | Total energy, including rest energy, in eV |
| `p0c` | Reference momentum multiplied by `c`, in eV |
| Magnetic field | Tesla |
| Voltage, frequency | Volts, Hz |
| RF phases such as `phi0` | Cycles: radians / `2*pi` |

`beginning[e_tot]` and `parameter[e_tot]` are alternative ways to set the same
entrance reference energy; likewise for `p0c`. Setting energy determines
momentum and vice versa. The MAD-compatible `beam, energy = ...` statement is
an exception to the eV convention: it uses GeV.

**Official detail:** **Units and Constants**, `s:constants` in
[lattice-file.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/lattice-file.tex);
**Reference Particle, Reference Energy, and Reference Time**, `s:ref.energy`
in [phase-space.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/phase-space.tex).

## Charged-particle phase space

For tracking with longitudinal position `s` as the independent variable,
the six coordinates are

\[
  (x,p_x,y,p_y,z,p_z), \qquad
  p_x=P_x/P_0,\quad p_y=P_y/P_0,\quad p_z=(P-P_0)/P_0.
\]

`x` and `y` are transverse positions in metres; `P` is the magnitude of the
particle momentum and `P0` is the local reference momentum. All three
momentum coordinates are dimensionless.

The longitudinal coordinate is

\[
  z=-\beta c(t-t_0),
\]

where `beta` is the **particle's** speed divided by `c`, and `t0` is the
reference arrival time at the same `s`. Thus an early particle has positive `z`.
This is an arrival-time coordinate, not the global longitudinal position.
`p_z` is relative momentum deviation, not longitudinal momentum and not,
in general, relative energy deviation.

Consequences for common conversions:

- Reconstruct momentum with the local `P0`. It can change along an accelerating
  lattice.
- `px` and `py` are normalized momenta, not slopes. In a straight section,
  `dx/ds = px / sqrt((1+pz)^2 - px^2 - py^2)`; the curved-frame relation
  also includes the reference curvature.
- Replacing `pz` by `delta_E/E0` or `beta` by 1 uses the ultrarelativistic
  approximation.
- Photon and time-based tracking use separate coordinate definitions.

**Official detail:** **Charged Particle Phase Space Coordinates**,
`s:phase.space`, in
[phase-space.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/phase-space.tex).
The slope relation is equation label `xpa1p`. The same file contains
`s:time.phase.space`, `s:photon.phase.space`, and the comparison with MAD.

## Spatial coordinate frames

The **local laboratory frame** follows the reference orbit along the lattice.
The **element body frame** follows the actual element, including its alignment
offsets and rotations. **Global**, or **floor**, coordinates describe the layout
in a fixed laboratory frame.

Moving a quadrupole with `x_offset` changes its alignment relative to the
reference orbit. Changing a bend's design curvature or inserting a `patch`
changes the reference layout itself. A computed particle orbit is another
object: it can depart from the reference orbit.

**Official detail:** **Coordinates and Physical Layout** in
[coordinates.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/coordinates.tex):
`s:local.coords`, `s:global`, and `s:lab.body.transform`.
The tutorial's [geometry](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tutorial_bmad_tao/lattice_files/geometry.bmad)
and [misalignment](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tutorial_bmad_tao/lattice_files/misalign.bmad)
examples illustrate the distinction.

## Normalized strengths and physical fields

Bmad can describe a magnet using a normalized strength or a physical field:

| Magnet | Normalized attribute | Physical attribute |
| --- | --- | --- |
| Quadrupole | `k1`, m^-2 | `b1_gradient`, T/m |
| Sextupole | `k2`, m^-3 | `b2_gradient`, T/m^2 |
| Octupole | `k3`, m^-4 | `b3_gradient`, T/m^3 |
| Solenoid | `ks`, m^-1 | `bs_field`, T |
| Bend | `g` and error `dg`, m^-1 | `b_field` and error `db_field`, T |

`field_master` decides which representation is independent. With
`field_master = F`, the normalized strengths are held fixed as the reference
momentum changes; the corresponding physical fields change. With
`field_master = T`, the physical fields are held fixed and the normalized
strengths change.

Setting a physical field attribute in the lattice selects the latter convention;
setting normalized strengths selects the former. Do not specify both kinds
for the same element. For example, these are two different ways to define
a quadrupole:

```bmad
q_norm: quadrupole, l = 0.6, k1 = 0.23
q_field: quadrupole, l = 0.6, b1_gradient = 9.0
```

The conversion also depends on reference species and charge. The settings are
not interchangeable merely because they describe the same magnet at one energy.

**Official detail:** **Field_Master and Normalized Vs. Unnormalized Field
Strengths**, `s:field.master` in
[attributes.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/attributes.tex);
the field normalization is defined in **Magnetostatic Multipole Fields**,
`s:mag.field` in
[electromagnetic-fields.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/electromagnetic-fields.tex).

## Optics and dispersion

`beta_a`, `alpha_a`, `beta_b`, and `alpha_b` describe the two transverse normal
modes. In the usual uncoupled case they correspond to horizontal and vertical
optics. With coupling, retain the mode interpretation rather than treating them
as independent x/y beam sizes.

| Quantity | Meaning | Units |
| --- | --- | --- |
| `beta_a`, `beta_b` | Twiss beta functions: beam-size scaling for a given mode emittance | m |
| `alpha_a`, `alpha_b` | Twiss alpha parameters: position-momentum correlation, associated with envelope convergence or divergence in uncoupled optics | Dimensionless |

For a matched, uncoupled beam without a dispersion contribution, the horizontal
rms size satisfies `sigma_x^2 = epsilon_x * beta_a`, where `epsilon_x` is the
geometric emittance. A beta function alone therefore does not specify a beam size.

For an open line, the entrance orbit and optics propagate downstream. Entrance
Twiss parameters are specified with `beginning[beta_a]`, `beginning[alpha_a]`,
`beginning[beta_b]`, and `beginning[alpha_b]`. For a closed lattice, the periodic
solution comes from the one-turn map.
Selecting closed geometry does not guarantee a stable periodic solution or
physical closure in floor coordinates.

Dispersion describes the orbit's dependence on relative momentum:
`eta_x = dx/dpz` and `eta_y = dy/dpz` at fixed `s`. Bmad's `etap_x` and `etap_y`
are **momentum dispersions**, `dpx/dpz` and `dpy/dpz`. They are not generally
identical to `deta_x_ds` and `deta_y_ds`.

**Official detail:** **Coupling and Normal Modes** (`s:coupling`),
**Dispersion Calculation** (`s:dispersion`), and **Twiss Calculation**
(`s:twiss.calc`) in
[optics.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/optics.tex).
Entrance conditions and global lattice settings are defined in
[param-statements.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/param-statements.tex),
`s:beginning` and `s:param`.

## Tracking and optics are different calculations

Each element can select separate methods:

| Attribute | What it controls |
| --- | --- |
| `tracking_method` | Advancing a particle through the element |
| `mat6_calc_method` | Calculating its first-order transfer matrix |
| `spin_tracking_method` | Advancing the particle's spin |

Common particle methods include `bmad_standard` (element-specific formulas),
`runge_kutta` (adaptive field integration), `symp_lie_ptc` (PTC Lie integration),
`linear` (first-order map), and `taylor` (Taylor map). Supported combinations
depend on the element.

In particular, `bmad_standard` ignores attached field maps. A field-map
calculation therefore needs a method that uses the field description.
The `linear` method cannot be paired with `mat6_calc_method = tracking`,
because each calculation would depend on the other.

Tracking a distribution, including wakes or collective forces, adds beam-level
settings beyond an element's single-particle integrator. Tao and PyTao expose
those calculations; the lattice file alone does not request a tracking run.

**Official detail:** **Particle Tracking Methods** (`s:tkm`), **Linear Transfer
Map (Mat6) Calculation Methods** (`s:xfer`), **Spin Tracking Methods**
(`s:spin.methods`), and the element/method compatibility tables in
[methods.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/methods.tex).
