# Tao commands and scripts

Tao commands act on the session described in [Tao concepts](../tao.md). They can
be entered at the prompt, read from a command file, or sent with
`tao.cmd("...")` through [PyTao](../pytao.md). `help set element`, for example,
shows the installed program's syntax for that operation.

Contents: [inspection](#inspect-a-model),
[selection](#select-elements-and-configurations),
[model changes](#change-the-working-lattice),
[scripts and aliases](#write-a-command-file-or-alias),
[plotting and tracking](#plot-and-track), and [export](#save-results).

## Inspect a model

`show lattice` lists elements and calculated quantities, `show element`
inspects one element, and `show value` evaluates an expression. For a lattice
with a quadrupole named `q`:

```text
show lattice
show element q
show lattice -attribute k1 quadrupole::*
show value lat::beta.a[END]
show value ele::q[k1]
```

Lattice-table quantities normally refer to element exits; `-beginning` and
`-middle` select other locations. `-design` and `-base` select the reference
states instead of the model.

The expression prefixes identify what is being accessed:

| Expression | Meaning |
| --- | --- |
| `ele::q[k1]` | A Bmad attribute on an element |
| `ele::q[beta_a]` | A Bmad optics quantity at the element exit |
| `lat::beta.a[END]` | A Tao lattice quantity, evaluated without defining a datum |
| `data::twiss.a[1]\|model` | The calculated value of a defined Tao datum |
| `var::quad[1]\|model` | The current value of a defined Tao variable |

Use element, data, and variable names from the loaded model. The bundled
[beamline](../../assets/beamline/lattice.bmad) supplies `q`; the
[matching session](../../assets/matching/tao.init) supplies `twiss` and `quad`.
Tao data names use forms such as `beta.a`; Bmad attributes use forms such as
`beta_a`. These are different naming conventions for related quantities.

For numerical processing, PyTao's parsed methods and arrays avoid splitting
human-readable `show` output. The raw `pipe` interface is documented separately;
its records are specific to the subcommand.

## Select elements and configurations

| Selector | Meaning |
| --- | --- |
| `Q3` | Element named Q3; list-taking commands can match repeated names |
| `Q3##2` | Second occurrence of Q3 in the selected branch |
| `134` | Element index 134 |
| `1>>Q3` | Q3 in branch 1 |
| `2@1>>Q3` | Q3 in branch 1 of universe 2 |
| `quadrupole::*` | All quadrupoles |
| `Q1:Q8` | Range of elements from Q1 through Q8 |

An omitted universe uses the default universe. `set default universe = 2`
changes it; `set default branch = 1` changes the default branch used by commands
that consult that setting. Explicit branch and occurrence selectors are useful
when names repeat.

Tao command words are case sensitive; Bmad element names are generally case
insensitive. `*` matches any number of characters and `%` matches one character.
An element list can combine selectors with commas.

Source: [Syntax][syntax], `s:ele.name` and `s:ele.list.format`.

## Change the working lattice

Use `set` to assign an absolute value and the unprefixed `change` form to add
an increment. These commands update the model lattice in the current session:

```text
set element q k1 = 0.3
change element q k1 0.01
show element q
```

Here `q[k1]` becomes `0.31`. The source `.bmad` file retains its original
settings; use [export commands](#save-results) to save the modified model.

The base lattice can hold a comparison point:

```text
set lattice base = model
set element q k1 = 0.4
show lattice -base
show lattice
```

`set lattice model = base` returns to that snapshot, while
`set lattice model = design` resets to the loaded design. A shared Tao variable
can propagate a parameter change to linked universes, so a universe-specific
reset is not necessarily independent of those links.

Tao normally recalculates after a lattice change. `set global lattice_calc_on = F`
defers calculation while batching changes; results then remain from the last
calculation. Universe-specific `on/off`, `twiss_calc`, and `track_calc` switches
are independent of that global switch. `show universe` displays them.

Source: [Command reference][commands], `s:change`, `s:set.lattice`, and
`s:set.universe`.

## Write a command file or alias

A `.tao` command file contains the same commands used at the prompt. For example,
this parameterized file changes a selected quadrupole and prints downstream
optics:

```text
! File: inspect_quad.tao
set element [[1]] k1 = [[2]]
show element [[1]]
show value lat::beta.a[END]
```

Run it with `call inspect_quad.tao q 0.3`. The arguments replace `[[1]]` and
`[[2]]`. A nested `call` with a relative path resolves beside the calling command
file. `!` starts a comment, `;` separates commands, and a trailing `&` continues
a command onto the next line.

For a short command sequence, an alias is convenient:

```text
alias inspect_quad show element [[1]]; show lattice
inspect_quad q
```

The [FODO `SetBetas.tao` example][alias-example] demonstrates a parameterized
fitting alias: it selects fit data and variables, sets two beta targets,
runs the optimizer, and prints the resulting magnet settings.

Command files also support integer loops:

```text
do j = 0, 4
  set particle_start pz = 1e-3 * [[j]]
  show lattice -orbit
enddo
```

Here `[[j]]` substitutes the loop index. This changes the starting momentum
deviation of each calculation; it leaves the final value in the session.
See [command reference][commands] sections `s:alias`, `s:call`, and `s:do` for
argument forms, nesting, and loops.

## Plot and track

A native Tao plot is placed into a **region** of the plot page. A plot contains
graphs, which contain curves. A template such as `beta` supplies the graph and
curve definitions:

```text
place r13 beta
scale r13 0 30
x_scale r13 0 2
```

These commands use Tao's native plotting, which the startup option `-noplot`
disables. For Python-managed Matplotlib or Bokeh figures, use
[PyTao plotting](../pytao.md#plotting).

Single-particle calculations and bunch tracking use different tracking modes.
For a session with a configured bunch, `set global track_type = beam` enables
beam tracking; `set global track_type = single` returns to single-particle mode.
The official [beam-tracking tutorial][beam-example] supplies the bunch
initialization, saved locations, and plots. [Initialization](initialization.md)
explains those fields.

## Save results

| Goal | Command |
| --- | --- |
| Write the model as a Bmad lattice | `write bmad model.bmad` |
| Save fitted variable settings in Bmad assignment syntax | `write variable fitted.out` |
| Save fitted variable settings as Tao commands | `write variable -tao_format fitted.tao` |

A written model contains current settings; it does not preserve the author's
original organization into includes and expressions. A variable-settings file
is useful when the original lattice should remain the starting point. See
[data and fitting](data-and-fitting.md) for applying the saved settings.

For exhaustive options, search [the command source][commands] for the command's
section heading or its label, for example `s:show.lattice`, `s:show.value`,
`s:write.bmad`, or `s:write.variable`. Expression definitions are in
[Syntax][syntax], sections `s:arithmetic.exp`, `s:lat.token`, and `s:ele.token`.

[commands]: https://github.com/bmad-sim/bmad-ecosystem/blob/main/tao/doc/command-list.tex
[syntax]: https://github.com/bmad-sim/bmad-ecosystem/blob/main/tao/doc/syntax.tex
[alias-example]: https://github.com/bmad-sim/bmad-ecosystem/blob/main/bmad-doc/tao_examples/fodo/SetBetas.tao
[beam-example]: https://github.com/bmad-sim/bmad-ecosystem/tree/main/bmad-doc/tutorial_bmad_tao/lattice_files/beam_tracking
