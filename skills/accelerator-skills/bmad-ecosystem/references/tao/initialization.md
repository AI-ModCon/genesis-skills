# Tao initialization

A session combines a Bmad lattice with the data, variables, plots, and particle
bunches needed for a calculation. Load a lattice directly for simple inspection,
or describe a reusable session in `tao.init` and related initialization files.

Contents: [starting a session](#start-a-session),
[namelist syntax](#namelist-syntax), [blocks and files](#what-goes-in-each-block),
[startup commands](#run-startup-commands), [universes](#multiple-universes),
[beam initialization](#beam-initialization), and [further details](#further-details).

## Start a session

To inspect a lattice using Tao's default session settings:

```sh
tao -lat lattice.bmad -noinit -noplot
```

To load a configured session:

```sh
tao -init_file tao.init -noplot
```

Substitute the paths for the model being used. `-noinit` skips the default
initialization file; `-init_file` chooses a particular initialization file.
`-noplot` suppresses native plotting windows. With an interactive terminal,
enter commands at the Tao prompt and finish with `exit`.

For a shell script, supply a command sequence ending in `exit`:

```sh
tao -init_file tao.init -noplot -command "show lattice; exit"
```

`-command` executes after startup-file commands. Semicolons separate the commands
inside the quoted argument. For longer workflows, call a
[command file](commands-and-scripts.md#write-a-command-file-or-alias) from that
sequence. [PyTao](../pytao.md) opens the same session with
`Tao(init_file="tao.init", noplot=True)` and provides Python access to its results.

Source: [Initialization][init], “Tao Initialization Command Line Arguments”
(`s:command.line`).

## Namelist syntax

Tao initialization uses Fortran **namelists**. `&name` starts a block, `/` ends
it, `%` accesses a structure component, and `(N)` selects an array entry.
Strings should be quoted; `!` introduces a comment. Logical values can be
written as `T` and `F`.

Unlike Bmad lattice expressions, namelist values are not arithmetic expressions.
Write a computed number such as `0.025`, not `1/40`: the slash would end the
namelist. Array assignment consumes the values supplied; one value does not
broadcast across a range. These distinctions matter when translating a Bmad
expression into an initialization setting.

Source: [Initialization][init], “Namelist Syntax” (`s:format`).

## What goes in each block

Select the lattice in a `tao_design_lattice` block. For example, a `tao.init`
beside `lattice.bmad` can contain:

```fortran
&tao_design_lattice
  n_universes = 1
  design_lattice(1)%file = "lattice.bmad"
/
```

Add initialization blocks according to the calculation:

| Namelist | Purpose |
| --- | --- |
| `tao_start` | Locate other initialization files and startup command files |
| `tao_design_lattice` | Select the lattice for each universe |
| `tao_params` | Set global Tao and Bmad calculation parameters |
| `tao_d2_data`, `tao_d1_data` | Define named data groups and individual observables/targets |
| `tao_var` | Define adjustable lattice parameters |
| `tao_beam_init` | Define the tracked bunch and where particle coordinates are saved |
| `tao_plot_page` | Place plots into regions on the native plot page |
| `tao_template_plot`, `tao_template_graph` | Define custom plots and their graphs/curves |

A small project can keep these blocks in `tao.init`. Larger projects can separate
them by role and use `tao_start` to locate them:

```fortran
&tao_start
  data_file = "data.init"
  var_file = "variables.init"
  plot_file = "plots.init"
  startup_file = "setup.tao"
/
```

Without an explicit `data_file`, `var_file`, `beam_file`, or `plot_file`, Tao
looks for those namelists in the root initialization file. Paths specified in
that file are relative to its directory. Paths passed on the command line are
relative to the process working directory, and command-line selections take
precedence.

One naming trap: `-lattice_file` on the command line selects a physical lattice.
The `lattice_file` field in `tao_start` selects the file containing the
`tao_design_lattice` namelist. The latter then names the `.bmad` files.

Source: [Initialization][init], “Beginning Initialization” (`s:init.begin`) and
“Lattice Initialization” (`s:init.lat`).

## Run startup commands

A startup file runs Tao commands after the lattice, data, and variables have
been initialized. Use it to establish the initial working state: select data
and controls for a fit, set calculation options, or define reusable aliases.
The `startup_file` setting above names `setup.tao`; the default name is
`tao.startup`.

For a session with data named `twiss` and variables named `quad`, a startup
file can select them for fitting:

```text
use data twiss
use var quad
```

Choose the names for the model and task. The `use` commands set the active
selection; [data and fitting](data-and-fitting.md#select-the-fit) explains how
selection affects optimization. The bundled [matching session](../../assets/matching/tao.init)
uses [setup.tao](../../assets/matching/setup.tao) for this purpose.

Use `-startup_file` to choose another command file, or `-nostartup` to skip
startup commands. With `-noplot`, startup commands still execute while native
plotting is disabled. Command-file syntax and aliases are described in
[commands and scripts](commands-and-scripts.md#write-a-command-file-or-alias).

## Multiple universes

Use multiple universes to represent different machine configurations or
measurement conditions within one session. Set `n_universes` and specify the
lattice loaded by each universe:

```fortran
&tao_design_lattice
  n_universes = 2
  design_lattice(1)%file = "lat1.bmad"
  design_lattice(2)%file = "lat2.bmad"
/
```

Each universe has its own data and model/design/base lattices. A Tao variable
can link the same adjustable attribute across universes, which is useful when
fitting several measurement conditions with one set of magnet parameters.
See [Tao concepts](../tao.md) and [data and fitting](data-and-fitting.md).
The [multiple-universes example][universes] supplies a complete configuration.

## Beam initialization

Define the particle distribution and saved locations in `tao_beam_init` when
using bunch tracking. For example:

```fortran
&tao_beam_init
  saved_at = "*"
  beam_init%n_particle = 1000
  beam_init%a_norm_emit = 1.0e-6
  beam_init%b_norm_emit = 1.0e-6
  beam_init%bunch_charge = 1e-9
  beam_init%sig_pz = 1e-3
  beam_init%sig_z = 0.00059958
/
```

The emittances here are normalized, `bunch_charge` is in coulombs, `sig_pz` is
the spread in Bmad's relative momentum coordinate, and `sig_z` is in meters.
`saved_at` chooses locations whose particle coordinates remain available after
tracking; `"*"` saves at every element and can be expensive for a large model.
Distribution choices are defined in the manual's `s:beam.init` section;
[Bmad conventions](../bmad/physics-conventions.md#charged-particle-phase-space)
define the coordinates. Use the [tracking commands](commands-and-scripts.md#plot-and-track)
to select bunch tracking after the session is configured.

The [beam-tracking example][beam] combines a lattice, beam initialization,
plot definitions, and command files.

## Further details

Search the following sections in [the initialization source][init]:

| Topic | Section label |
| --- | --- |
| Startup options | `s:command.line` |
| Global parameters | `s:globals` |
| Bunch distributions, Twiss parameters, species, and saved locations | `s:beam.init` |
| Variable definitions | `s:init.var` |
| Data definitions | `s:init.data` |
| Plot page and templates | `s:init.plot`, `s:plot.page`, `s:template` |

[init]: https://github.com/bmad-sim/bmad-ecosystem/blob/main/tao/doc/initialization.tex
[universes]: https://github.com/bmad-sim/bmad-ecosystem/tree/main/bmad-doc/tutorial_bmad_tao/lattice_files/multiple_universes
[beam]: https://github.com/bmad-sim/bmad-ecosystem/tree/main/bmad-doc/tutorial_bmad_tao/lattice_files/beam_tracking
