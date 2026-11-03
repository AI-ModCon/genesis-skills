# Bmad lattice syntax

Use this guide to write or interpret a `.bmad` file. The
[Bmad overview](../bmad.md) explains the objects being defined.

Contents: [statements](#statements-and-definitions),
[expressions](#expressions-and-inheritance), [lines](#lines-and-expansion),
[selectors](#attributes-and-element-selectors), [includes](#splitting-a-lattice-into-files),
and [composition](#superposition-and-multipass).

## Statements and definitions

An element definition has the form `name: element_type, attribute = value, ...`.
For example, from the bundled
[beamline](../../assets/beamline/lattice.bmad):

```bmad
d: drift, l = 0.5
q: quadrupole, l = 0.6, k1 = 0.23
```

`!` begins a comment. Element names, keywords, and attributes are generally case
insensitive; filenames and some string values retain their case. Tao command
words follow Tao's separate, case-sensitive syntax.

A comma at the end of a line continues the statement. An explicit `&` also
continues it. Semicolons separate statements on one line:

```bmad
q1: quadrupole, l = 0.6,
    k1 = 0.23
q2: quadrupole, l = 0.6; q2[k1] = -0.23
```

Use names beginning with a letter and containing letters, digits, or underscores.
Bmad reserves punctuation for constructs such as tagged names, superposition
slaves, and element selectors.

**Official detail:** **File Example and Syntax** in
[lattice-file.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/lattice-file.tex);
search `Lattice Element Names` / `s:ele.names` for naming rules.

## Expressions and inheritance

Arithmetic expressions support `+ - * / ^`, functions such as `sqrt` and `sin`,
and constants such as `pi` and `c_light`. A named constant is assigned with `=`:

```bmad
quad_length = 0.6
qa: quadrupole, l = quad_length, k1 = 0.23
qb: qa, k1 = -qa[k1]
qa[k1] = 0.30
```

`qb: qa` copies the attributes of `qa` at that point in parsing. Here `qb[k1]`
remains -0.23 after `qa[k1]` changes. Lattice expressions are evaluated
immediately; they do not establish live relationships between attributes.
Constants and attributes used in an expression must already have their intended
values. Constants normally cannot be redefined.

For an adjustable relationship between several magnets, use an
[overlay or group](controllers.md), rather than expecting an earlier expression
to update itself.

**Official detail:** **Arithmetic Expressions**, `s:arith`, and **Statement
Order**, `s:state.order`, in
[lattice-file.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/lattice-file.tex).

## Lines and expansion

A line assembles elements and other lines. `use` selects the line or lines
that become lattice branches:

```bmad
cell: line = (qa, d, qb, d)
transport: line = (3*cell)
use, transport
```

Expansion produces twelve tracking elements here, plus `BEGINNING` and the
default `END` marker. Repeated entries retain their names: there are three
occurrences of `qa` and six of `d`.

| Construct | Meaning |
| --- | --- |
| `line = (a, subline, b)` | Insert the expanded subline between `a` and `b`. |
| `3*cell` | Repeat a line three times. |
| `-cell` | Reverse the order of a line; individual elements keep their orientation. |
| `--cell` | Reverse the line order and the orientation of every element. |
| `use, line_a, line_b` | Create multiple root branches. |

True orientation reversal is useful for counter-propagating paths through shared
elements. It changes the coordinate relationship at element boundaries; use the
manual's **Element Orientation Reversal** section for that case.

Bmad normally expands the lattice after parsing. `expand_lattice` requests
expansion at a particular point, enabling assignments to individual occurrences
and branch-qualified elements after that point. All definitions needed for the
expansion must already be available.

**Official detail:** [lines-and-lists.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/lines-and-lists.tex),
**Beam Lines and Lattice Expansion** (`s:lines.wo.arg`), **Element Orientation
Reversal** (`s:ele.reverse`), and **Use Statement** (`s:use`). The same chapter
explains replaceable arguments, replacement lists, and line tagging.

## Attributes and element selectors

Set an existing element's attribute with `element[attribute] = value`:

```bmad
qa[k1] = 0.25
quadrupole::*[x_offset] = 0.001
```

`*` matches any number of characters; `%` matches one character. Prefixing a
selector with `quadrupole::` restricts the match to that element type.
Assignments affect elements already defined when the statement is parsed.
A wildcard assignment before the definitions does not set defaults for later
elements.

After expansion, occurrence, index, and branch selectors are available:

```bmad
expand_lattice
qa##2[k1] = 0.27       ! Second occurrence named QA
0>>qa##3[k1] = 0.29    ! Third occurrence in branch 0
```

An occurrence selector depends on line order. Give physically different magnets
distinct names when they need independent settings; then extracting a subline
does not change the meaning of those settings.

**Official detail:** **Matching to Lattice Element Names**, `s:ele.match`, and
**Lattice Element Parameters**, `s:lat.attribs`, in
[lattice-file.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/lattice-file.tex).
These sections also cover ranges, offsets from an element, and matching by
`type`, `alias`, or `descrip`.

## Splitting a lattice into files

`call` reads another lattice file. A useful arrangement separates physical layout
from magnet settings:

```bmad
call, file = "layout.bmad"
call, file = "strengths.bmad"
```

Relative include paths resolve from the directory of the file containing the
`call` statement. Environment variables such as `$LATDIR` can appear in paths;
`$LATTICE_ROOT_DIR` identifies the directory of the top-level lattice file.
Because attribute assignments require existing elements, read the definitions
before a file that changes their attributes.

**Official detail:** **Call Statement**, `s:call`, in
[lattice-file.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/lattice-file.tex).

## Superposition and multipass

**Superposition** places an element relative to another element without manually
splitting the line. The official
[superposition example](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tutorial_bmad_tao/lattice_files/superimpose1.bmad)
places a marker inside a quadrupole:

```bmad
q: quadrupole, l = 1, k1 = 0.2
d: drift, l = 1
m1: marker, superimpose, ref = q, ref_origin = beginning, offset = 0.3
lat: line = (q, d)
use, lat
```

Here the marker is 0.3 m from the quadrupole's entrance. Bmad constructs the
tracking pieces needed for the overlap and preserves the physical element through
lord/slave relationships. See **Superposition Fundamentals**, `c:super.fund` in
[superposition.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/superposition.tex).

**Multipass** represents repeated traversal of the same physical hardware.
Line repetition makes repeated elements; `line[multipass]` additionally
ties corresponding passes to one physical lord. The official
[multipass example](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tutorial_bmad_tao/lattice_files/multipass.bmad)
uses:

```bmad
cavity: lcavity, l = 1, voltage = 10e6, rf_frequency = 1e9
linac: line[multipass] = (cavity)
erl: line = (linac, linac)
use, erl
expand_lattice
cavity\2[phi0_multipass] = 0.5
```

The second pass has an RF phase offset of half a cycle. Reference energies can
differ between passes through a shared cavity. See **Multipass Fundamentals**
(`c:multipass.fund`) and **Phi0_multipass** (`s:phi0.mp`) in
[multipass.tex](https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad/doc/multipass.tex).
The excerpt relies on the physical setup in the complete upstream example.
