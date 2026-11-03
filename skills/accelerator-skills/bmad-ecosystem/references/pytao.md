# PyTao: using Tao from Python

A `Tao` object loads a model, accepts Tao commands, and returns calculated
quantities as Python objects and arrays. The examples use the bundled
[beamline](../assets/beamline/lattice.bmad) and
[matching setup](../assets/matching/tao.init). Run the snippets from the
`bmad-ecosystem` skill directory; paths are relative to that directory.
Upstream notebooks provide further examples and longer analyses.

Contents: [session](#create-a-tao-session),
[commands and results](#commands-and-calculated-results),
[element models](#element-and-lattice-models), [scans](#scans-and-fitting),
[plots](#plotting), [particles](#beam-tracking-and-particles),
[configuration](#configuration-and-saved-state),
[independent sessions](#independent-sessions-and-diagnostics).

## Create a Tao session

```python
from pytao import Tao

tao = Tao(
    lattice_file="assets/beamline/lattice.bmad",
    noinit=True,
    noplot=True,
)
```

`lattice_file` selects the Bmad lattice, and `noinit=True` skips the default
initialization file. A session with data, variables, and startup commands uses
`init_file`; the [fitting example](#scans-and-fitting) below loads that setup.

Tao startup options are exposed as constructor keywords. `noplot=True`
suppresses the native plot window; Python plotting uses `plot="mpl"` or
`plot="bokeh"` instead. PyTao needs a working Tao shared library in addition
to the Python package. See [installation](installation.md) for package setup
and library discovery, and [usage](https://bmad-sim.github.io/pytao/usage/) for
startup options and notebook integration.

## Commands and calculated results

`cmd` sends one Tao command and returns a list of output lines. It is useful
both for changing the model and for inspecting the same output a user sees
at the Tao prompt:

```python
print("\n".join(tao.cmd("show lattice")))
before = tao.ele_twiss("END")
tao.cmd("set element q k1 = 0.3")
after = tao.ele_twiss("END")
print(before["beta_a"], after["beta_a"])
```

The beamline contains a quadrupole named `q`. Commands change the running model;
subsequent queries return its calculated results. `cmds([...])` sends a sequence
of commands. [Export commands](tao/commands-and-scripts.md#save-results) save
model settings to files.

PyTao provides several ways to retrieve results:

| Interface | What it supplies | Typical use |
| --- | --- | --- |
| `tao.cmd("show ...")` | Human-readable text lines | Inspect a command's output or diagnostic |
| `tao.ele_twiss(...)`, `tao.ele_orbit(...)` | Parsed dictionaries | Retrieve one kind of result at an element |
| `tao.lat_list(...)` | Arrays or lists across selected elements | Build a plot, table, or numerical calculation |
| `tao.evaluate(...)` | Numerical values of a Tao expression | Evaluate a derived quantity or data expression |
| `tao.ele(...)`, `tao.eles(...)` | Structured `Element` models | Explore several kinds of element information together |

For example:

```python
s = tao.lat_list("*", "ele.s")
beta_a_along_lattice = tao.lat_list("*", "ele.a.beta")
names = tao.lat_list("*", "ele.name")
```

`lat_list` returns numerical arrays for numerical quantities and a list of
strings for names. Its default flags select tracking elements; other flags
can change the selected objects and ordering. Use the same selection when
combining position and optics arrays. `evaluate` can return an array even
when an expression selects a single value.

Optics quantities follow [Bmad's conventions](bmad/physics-conventions.md#optics-and-dispersion).
Element queries normally refer to the downstream end; selectors and lattice states follow
[Tao's addressing rules](tao/commands-and-scripts.md#select-elements-and-configurations).

The parsed methods use Tao's machine interface internally. Raw `cmd_real` and
`cmd_integer` access numerical buffers populated by specific Tao commands.
The [Basics notebook](https://bmad-sim.github.io/pytao/examples/basic/)
has sections on `lat_list`, method commands, and `pipe` internals. The
[Tao API](https://bmad-sim.github.io/pytao/api/tao/) documents Python conveniences
such as `ele`, `plot`, and `track_beam`. For an inherited command method not
listed there, use its docstring or search the
[generated command interface](https://github.com/bmad-sim/pytao/blob/master/pytao/interface_commands.py)
for its definition, such as `def ele_twiss` or `def lat_list`.

## Element and lattice models

`tao.ele()` gathers an element's metadata, attributes, optics, orbit, and other
information into an `Element` object. `tao.eles()` accepts a selection of
elements, including ranges, wildcards, and element types:

```python
ele = tao.ele("q")
print(ele.name, ele.key, ele.twiss.beta_a)
print(ele.attrs["K1"].data, ele.attrs["K1"].units)

quads = tao.eles("quad::*", defaults=False, twiss=True, attrs=True)
```

The `.attrs` entries include values, units, and whether an attribute can be
changed. `.attribs` is a convenience view of their values. These objects
contain snapshots of queried data. Apply model changes through Tao commands,
then query again for updated results.

For a large lattice, requesting just the needed fields avoids querying all
available element information. The `Lattice` model collects `Element`
objects and provides lookup by name, type, or index, plus serialization.
The official [Elements and Lattices notebook](https://bmad-sim.github.io/pytao/examples/elements/)
demonstrates both models, field selection, and saving/loading. See the
[Element and Lattice API](https://bmad-sim.github.io/pytao/api/element/)
for the individual fields.

## Scans and fitting

A Python scan changes a lattice attribute or Tao variable, queries an
observable, and collects the results. Each point updates the current model;
preserve the starting values for a temporary scan. Calculation switches and
lattice states follow [Tao command semantics](tao/commands-and-scripts.md#change-the-working-lattice).

The bundled matching setup defines the `twiss` targets and `quad` variables;
its startup file selects them for fitting:

```python
tao = Tao(init_file="assets/matching/tao.init", noplot=True)
tao.cmd("run_optimizer lm")
print("\n".join(tao.cmd("show merit")))
twiss = tao.ele_twiss("END")
```

The [fitting guide](tao/data-and-fitting.md) explains its targets, variable
bounds, and merit function. The upstream
[FODO optics notebook](https://bmad-sim.github.io/pytao/examples/fodo/)
provides further examples of quadrupole scans, fitting, and beam tracking.

## Plotting

PyTao renders Tao plot templates using Matplotlib or Bokeh. For the bundled
beamline:

```python
tao = Tao(
    lattice_file="assets/beamline/lattice.bmad",
    noinit=True,
    plot="mpl",
)
tao.plot("beta", save="beta.png", include_layout=False)
```

Templates such as `beta`, `dispersion`, `orbit`, and `floor_plan` define what
to plot. PyTao supplies the Python rendering and options for layout and
appearance. Arrays from `lat_list` can also be plotted directly with Python
plotting tools.

Use the [Matplotlib notebook](https://bmad-sim.github.io/pytao/examples/plot-matplotlib/)
for stacked plots, fields, figure customization, and saving figures, or the
[Bokeh notebook](https://bmad-sim.github.io/pytao/examples/plot-bokeh/)
for interactive plots. A startup file that issues native plotting commands
may need a version without those commands when using Python plotting; see
[plotting and startup scripts](https://bmad-sim.github.io/pytao/usage/#pytao-plotting-and-startup-scripts).

## Beam tracking and particles

[Beam initialization](tao/initialization.md#beam-initialization) defines the
particle distribution and saved locations. For a configured session,
`tao.track_beam(use_progress_bar=False)` runs the bunch calculation.

`bunch_params` supplies statistics, while `bunch1` supplies individual particle
coordinates in Bmad's convention. Full particle access requires the beam to
have been saved at the requested element. `particles` returns an
`openPMD-beamphysics` `ParticleGroup`; its momenta use eV/c rather than Bmad's
reference-normalized momentum coordinates. `bunch_data` supplies the
corresponding dictionary of arrays. See [physics conventions](bmad/physics-conventions.md)
when translating between these representations.

The [Bunch Commands notebook](https://bmad-sim.github.io/pytao/examples/bunch/)
shows statistics, particle arrays, initial-particle access, and cumulative
beam data. The [beam tracking notebook](https://bmad-sim.github.io/pytao/examples/beam_track_progress_bar/)
shows how to configure a Gaussian distribution and track it with progress
reporting.

## Configuration and saved state

`TaoConfig` represents startup settings, common physics settings, beam
initialization, tracking settings, globals, and element overrides. It can
generate Tao commands or apply its settings back to a session:

```python
config = tao.get_config()
config.beam_init.a_emit = 2e-8
config.beam_init.set(tao, only_changed=True)
config.write("beam_configuration.json")
```

Changing the Python configuration object and applying it are separate actions.
A saved configuration is also distinct from the lattice it refers to.
`tao.archive("my_archive")` writes a lattice snapshot, a Tao settings command
file, and a shell launcher together. The official
[TaoConfig notebook](https://bmad-sim.github.io/pytao/examples/config/)
covers changing, saving, and loading configurations and creating an archive;
the [configuration API](https://bmad-sim.github.io/pytao/api/config/)
describes individual settings models.

## Independent sessions and diagnostics

There is one native Tao state per Python process. Constructing another `Tao`
object reinitializes that state. `SubprocessTao` runs an independent session
in its own process:

```python
from pytao import SubprocessTao

with SubprocessTao(
    init_file="assets/matching/tao.init", noplot=True
) as other:
    optics = other.ele_twiss("END")
```

The context manager closes the process on exit. See
[SubprocessTao usage](https://bmad-sim.github.io/pytao/usage/#subprocesstao-tao-in-a-subprocess)
for lifetime management.

Tao errors normally raise Python exceptions. Their messages retain the Tao
diagnostic. `raises=False` returns raw error output for inspection. The usage
guide also documents
[Python logging](https://bmad-sim.github.io/pytao/usage/#logging).
Avoid `quiet=True` as a general logging control: the upstream usage guide
notes that it can interfere with PyTao behavior.
