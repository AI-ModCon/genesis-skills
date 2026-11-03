# Controllers and lord/slave relationships

Controllers express relationships between elements. They are useful when one
power supply drives several magnets, a tuning knob changes a weighted set of
strengths, or magnets move together on a support.

A **lord** is an element that controls attributes of other elements, its
**slaves**. Bmad also uses lords to represent physical elements that have been
split for tracking or traversed multiple times. A lord can therefore exist
outside the ordered sequence of tracking elements.

Contents: [overlays](#overlay-define-attributes-from-a-knob),
[groups](#group-apply-a-change-to-existing-settings),
[girders](#girder-align-elements-as-a-supported-assembly),
[physical lords](#physical-lords-from-superposition-and-multipass),
and [Tao variables](#bmad-controllers-and-tao-variables).

## Overlay: define attributes from a knob

An `overlay` defines the values of slave attributes as functions of its
variables. The official
[controller example](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tutorial_bmad_tao/lattice_files/control.bmad)
contains:

```bmad
ov2: overlay = {q[k1]: 0.7, q[x_offset]: 0.1*hh}, var = {hh}, hh = 0.01
```

Here `q` is a previously defined quadrupole. The overlay sets its `k1` to
0.7 m^-2 and its `x_offset` to 0.001 m. Changing `ov2[hh]` changes the offset
through the expression. `hh` is an actual adjustable controller variable;
a lattice constant would only be substituted during parsing.

If several overlays control one attribute, their contributions are summed.
The original value written on the slave is not an extra contribution.
To change an actively controlled attribute, change the corresponding overlay
variable rather than trying to override the slave independently.

The full expression syntax names the target attribute explicitly:
`{element[attribute]: expression}`. This is easier to interpret than shorthand
that infers an attribute from the variable name.

**Official detail:** **Overlay**, `s:overlay` in
[elements.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/elements.tex),
and **Group, Overlay, and Ramper Element Syntax**, `s:go.syntax` in
[attributes.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/attributes.tex).

## Group: apply a change to existing settings

A `group` also maps variables to slave attributes, but applies the **difference**
between the expression's new and old values:

\[
  \Delta a = f(v_{\mathrm{new}})-f(v_{\mathrm{old}}).
\]

The difference is added to the slave's existing attribute. This makes groups
useful for trim knobs that should preserve a set of existing magnet settings.
The tutorial example uses:

```bmad
gr1: group = {b[k1]: 0.4*sqrt(z)}, var = {z}
```

Changing `gr1[z]` adds the change in `0.4*sqrt(z)` to the bend's quadrupole
component. The old controller value is tracked internally; an `old_z` value
can also be specified when defining the initial change.

Because a group adds increments, changing both a group variable and its slave
attribute can make the result depend on operation order. A fit should represent
the intended physical knobs rather than independently varying both descriptions
of the same adjustment.

**Official detail:** **Group**, `s:group` in
[elements.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/elements.tex).
The section gives worked present/old-value examples and discusses interaction
with direct slave changes.

## Girder: align elements as a supported assembly

A `girder` represents a mechanical support. Its offsets and rotations contribute
to the placement of supported elements. Individual element misalignments remain
distinct from the motion of the assembly.

The support list names elements or lines. A girder can itself be supported by
another girder. For an element split by superposition or multipass, support its
physical lord rather than a tracking slave.

**Official detail:** **Girder**, `s:girder` in
[elements.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/elements.tex),
and **Girder Orientation**, `s:girder.orient` in
[attributes.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/attributes.tex).

## Physical lords from superposition and multipass

| Relationship | Why Bmad creates it |
| --- | --- |
| `super_lord` / `super_slave` | A physical element overlaps another element or is split into tracking pieces. The lord retains the original element while the slaves describe the pieces traversed by the particle. |
| `multipass_lord` / `multipass_slave` | Several traversals share one physical element. The lord holds common hardware attributes; slaves describe individual passes, which can have different reference energies or RF phases. |

These relationships are constructed by lattice expansion. They are not
additional magnets to place in the beamline manually. When an expanded lattice
contains unexpected pieces or repeated names, the relationship often explains
where the physical element went.

See [superposition and multipass syntax](lattice-syntax.md#superposition-and-multipass)
for examples. **Lord and Slave Elements**, `s:lord.slave` in
[concepts.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/concepts.tex)
explains the tracking and lord sections of a lattice.

## Bmad controllers and Tao variables

A Bmad overlay/group encodes relationships **inside the lattice**. A Tao variable
identifies an adjustable quantity for the application's fitting and control
machinery. That quantity may be a direct magnet attribute or a controller
variable, such as `ov2[hh]`.

Using a controller can reduce a fit to the actual independent hardware knobs.
See [Tao](../tao.md) for the data/variable model and fitting setup.
