# Bmad: the physical model and lattice language

A Bmad lattice describes elements, their arrangement, fields, reference
particle, and modeling choices.

## How a lattice is organized

- An **element** represents a magnet, cavity, drift, aperture, optical component,
  or a named location such as a marker. Its attributes specify length, strength,
  alignment, and other properties.
- A **line** is a lattice-file expression assembling elements and other lines.
  Bmad expands the selected lines into **branches**: ordered paths through the
  machine.
- A **lattice** contains one or more branches. A branch can describe a beamline,
  a storage ring, or one repeating period. Fork elements connect branches.
- A **lord** controls other elements, its **slaves**. This represents shared
  knobs, overlapping fields, or several passes through the same physical magnet.
  The physical elements and the elements used for tracking need not be identical.

Each branch starts with `BEGINNING` at element index 0. Bmad also appends an
`END` marker by default. Repeating a line can create multiple elements with the
same name; element names alone are therefore not always unique.

These objects are defined in the manual's **Bmad Concepts and Organization**
chapter ([source](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/concepts.tex),
labels `s:element.def`, `s:branch.def`, `s:lattice.def`, and `s:lord.slave`).

## Read a small lattice

The bundled [lattice](../assets/beamline/lattice.bmad) describes a small open
beamline. Its essential statements are:

```bmad
beginning[beta_a] = 10.
beginning[beta_b] = 10.
beginning[e_tot] = 10e6
parameter[geometry] = open
parameter[particle] = electron

d: drift, l = 0.5
b: sbend, l = 0.5, g = 1, e1 = 0.1, dg = 0.001
q: quadrupole, l = 0.6, k1 = 0.23

lat: line = (d, b, q)
use, lat
```

`beginning` supplies entrance conditions; here the two mode beta functions are
10 m and the reference total energy is 10 MeV. `parameter` supplies the species
and geometry. The next three statements define elements, `line` orders them,
and `use` selects the line that becomes the lattice.

The [element guide](bmad/elements.md) explains the bend and quadrupole attributes.

The [lattice syntax guide](bmad/lattice-syntax.md) covers definitions,
expressions, includes, and line expansion. [Physics conventions](bmad/physics-conventions.md)
cover reference quantities, geometry, coordinates, and optics.

## Capabilities beyond the basic lattice

| Capability | Meaning and official starting point |
| --- | --- |
| Field maps | Represent spatially varying fields rather than only idealized element strengths. **Field Maps**, `s:fieldmap` in [attributes.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/attributes.tex). |
| Tracking algorithms | Choose the particle integrator, transfer-matrix calculation, and spin method separately. **Tracking, Spin, and Transfer Matrix Calculation Methods**, `c:methods` in [methods.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/methods.tex). |
| Collective effects | Model interactions within a bunch, including space charge and coherent synchrotron radiation. Start with [multiparticle.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/multiparticle.tex) and the tutorial's [beam tracking example](https://github.com/bmad-sim/bmad-ecosystem/tree/main/bmad-doc/tutorial_bmad_tao/lattice_files/beam_tracking). |
| Wakes | Describe fields left by a bunch that act on following particles or bunches. **Wakefields**, `s:wakes` in [attributes.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/attributes.tex); theory in [wakefields.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/wakefields.tex). |
| Radiation and spin | Compute radiation effects and spin evolution using their own settings and algorithms. See [synchrotron-radiation.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/synchrotron-radiation.tex) and [spin.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/spin.tex). |
| Photon optics | Model emission and transport through crystals, mirrors, apertures, and other X-ray elements. See [elements](bmad/elements.md#photon-optics) and [xray-tracking.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/xray-tracking.tex). |
| Native applications | Call Bmad from a program through its lattice, element, and particle structures. Start with [programming.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/programming.tex) and the official [example program](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/example-program.tex). |

The [Bmad manual](https://www.classe.cornell.edu/bmad/manual.html) is the full
reference. Source links above name the chapter and, where useful, its TeX label
so a large file can be searched directly.
