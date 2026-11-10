# Tao data, variables, and fitting

A Tao fit connects **data**, which describe the desired or measured behavior,
to **variables**, which control the model. Define both in initialization
namelists, select the data and variables for the task, run an optimizer, and
inspect the resulting residuals and settings.

Contents: [data](#data-are-named-observables),
[variables](#variables-connect-the-optimizer-to-lattice-attributes),
[selection](#select-the-fit), [running a fit](#run-and-examine-the-fit),
[merit function](#what-the-merit-function-means),
[saving settings](#save-fitted-settings),
[matching example](#bundled-matching-example),
and [further details](#further-details-and-examples).

## Data are named observables

A **datum** specifies a calculation, its location, and how it participates in
the fit. For an optics match, data can specify beta and alpha at a beamline end.
For orbit correction, they can represent measured BPM positions.

| Component | Meaning |
| --- | --- |
| `data_type` | Quantity to calculate, such as `beta.a`, `alpha.b`, or `orbit.x` |
| `data_source` | `lat` for lattice calculations; `beam` for bunch-tracking results |
| `ele_name` | Lattice element at which to evaluate it |
| `model`, `design`, `base` | Values calculated from the three lattice states |
| `meas` | Measured value, or a desired value supplied for lattice design |
| `ref` | Reference measurement used in correction/comparison modes |
| `merit_type` | How disagreement contributes to the objective |
| `weight` | Scale of that contribution |

Tao groups data in two levels: a `d2_data` group contains one or more `d1_data`
arrays, which contain individual data points. For example, define a group named
`twiss` and an array named `a` with two target values:

```fortran
&tao_d2_data
  d2_data%name = 'twiss'
  n_d1_data = 1
/

&tao_d1_data
  ix_d1_data = 1
  d1_data%name = 'a'
  datum(1) = 'beta.a'  '' '' 'END' 'target' 12.0 1e1
  datum(2) = 'alpha.a' '' '' 'END' 'target' -0.4 1e2
/
```

The positional columns are `data_type`, `ele_ref_name`, `ele_start_name`,
`ele_name`, `merit_type`, `meas`, and `weight`. The empty strings leave the
reference/range endpoints unspecified. Default evaluation is at the element
end. Component assignments such as `datum(1)%data_type = 'beta.a'` are an
alternative when explicit field names are clearer. Each `tao_d2_data` block is
followed immediately by its associated `tao_d1_data` blocks.

In `twiss.a[1]`, `twiss` is the group, `a` is the array, and `[1]` selects its
first datum. These names are chosen by the user; `data_type` determines the
calculation. Set `n_d1_data` to the number of arrays and give each array its own
`ix_d1_data` when defining additional groups of observables.

`twiss.a[1]|model` and `twiss.a[1]|meas` refer to different values of the same
datum. `2@twiss.a[1]|model` selects universe 2. A datum index is an index in its
data array, not a lattice element index.

Source: [Data][data], “Data Organization” (`s:data.org`), “Anatomy of a Datum”
(`s:data.anatomy`), and “Datum values” (`s:datum.values`).

## Variables connect the optimizer to lattice attributes

A variable controls a lattice attribute, such as `q1[k1]`. Variables are grouped
in named `v1_var` arrays. Choose attributes corresponding to the physical controls
available for the task, such as quadrupole strengths for optics matching or
steering kicks for orbit correction.

For example, this block creates a variable array named `quad` from all
quadrupoles in the loaded lattice and varies their `k1` attributes:

```fortran
&tao_var
  v1_var%name = 'quad'
  search_for_lat_eles = 'Quad::*'
  default_attribute = 'k1'
  default_step = 1e-4
  default_merit_type = 'limit'
  default_low_lim = -50
  default_high_lim = 50
  default_weight = 1
  ix_min_var = 1
/
```

`search_for_lat_eles` creates a variable for each matching element. For explicit
selection, use assignments such as `var(1)%ele_name = 'q1'` and
`var(1)%attribute = 'k1'`. The variable's `model` value is the current setting;
its `step` sets a small perturbation used in derivative calculations.

A variable can link the same setting across several universes. Bmad overlays
or groups can also be used as the controlled element when a knob should change
several underlying magnets. See [Bmad controllers](../bmad/controllers.md).

Source: [Variables][variables], “Overview” (`s:var.overview`) and “Anatomy of a
Variable” (`s:var.anatomy`).

## Select the fit

Data and variable definitions establish what can participate in a fit. Select
the sets appropriate to the calculation before running an optimizer:

```text
use data twiss
use var quad
```

Replace `twiss` and `quad` with the names defined for the model. `use` selects
the specified data or variable set and vetoes the others of that kind.
`restore` removes a veto on selected items without replacing the entire
selection, and `veto` excludes items. These commands change `good_user`; Tao
also checks whether the data are calculable and variables usable before setting
their effective `useit_opt` flags.

Inspect data with `show data twiss` and controls with `show variable quad`.
For a session that should start with a particular selection, put the `use`
commands in a [startup file](initialization.md#run-startup-commands).

Source: [Command reference][commands], `s:use`, `s:restore`, and `s:veto`.

## Run and examine the fit

After loading the model and selecting data and variables, run an optimizer and
inspect the result:

```text
run_optimizer lm
show merit
show constraints
show data twiss
show variable quad
```

The data table compares calculated and target values; the variable table shows
the resulting controls. Check residuals, variable penalties, and calculation
validity when assessing a fit.

To change a target and repeat the fit:

```text
set data twiss.a[1]|meas = 14
run_optimizer lm
```

The local optimizer `lm` is useful for small optics matches. Tao also provides
`lmdif`, `geodesic_lm`, `svd`, and the global-search optimizer `de`; their behavior
and parameters are described in [Optimization][optimization], `s:tao.opti`.
[PyTao](../pytao.md#scans-and-fitting) exposes the same fitting commands from
Python.

## What the merit function means

Tao minimizes a weighted sum of squared data residuals and variable penalties.
For a target fit, the data residual is `model - meas`. A weight of
`1 / tolerance**2` makes a one-tolerance deviation contribute one to the sum.
Weights therefore also balance observables with different units.

`merit_type = 'limit'` on a variable adds a penalty outside its `low_lim` and
`high_lim`; those numbers are penalty limits, not a guarantee that an optimizer
will never evaluate outside them. Datum merit types such as `max` and `min`
express inequalities instead of target equalities.

`show merit` identifies the largest contributions. `show constraints` displays
the constraints and current values. A failed optics calculation is represented
through datum validity and invalid-data penalties, not a physical measurement
of zero. The defaults for a simple design fit differ from correction setups
that use reference measurements or base differences; see `s:del.d`, `s:del.v`,
and `s:lat.correction` in [Optimization][optimization].

## Save fitted settings

Save the controlled attributes as Bmad assignments:

```text
write variable fitted.out
```

Apply these assignments after the original lattice definitions. For example,
a lattice file can load the layout, expand it, and then apply the saved settings:

```bmad
call, file = lattice.bmad
expand_lattice
call, file = fitted.out
```

See [export formats](commands-and-scripts.md#save-results) for Tao command
files and complete model snapshots.

## Bundled matching example

The bundled [initialization file](../../assets/matching/tao.init) combines these
concepts for an optics match. Its [lattice](../../assets/matching/lat.bmad) has
six quadrupoles in an open line. Entrance beta functions are 10 m; the data
target beta = 12 m and alpha = -0.4 for both transverse modes at `END`.

The `twiss` group has two arrays, `a` and `b`, and the `quad` variables control
the quadrupole strengths. The [startup file](../../assets/matching/setup.tao)
selects those data and variables after initialization. Keep the three files
together so their relative paths resolve. This session can be used to explore
the selection, fitting, and inspection commands above.

## Further details and examples

| Need | Official source and search target |
| --- | --- |
| All datum types and supported sources | [Data][data], `s:data.table`, `s:data.types` |
| Evaluation locations and ranges | [Data][data], `s:dat.eval`, `s:data.lat.ele` |
| Full data and variable namelists | [Initialization][init], `s:init.data`, `s:init.var` |
| Shared variables and slave-value mismatch | [Variables][variables], `s:var.anatomy`, `s:var.mismatch` |
| Merit functions and optimizer settings | [Optimization][optimization], `s:opt.main`, `s:tao.opti` |
| Saving variable settings | [Command reference][commands], `s:write.variable` |

The official [Twiss-correction example][correction] extends the ideas to multiple
universes and simulated measurements. [Optics matching][matching] adds more
extensive target, limit, and plotting configuration.

[data]: https://github.com/bmad-sim/bmad-ecosystem/blob/main/tao/doc/data.tex
[variables]: https://github.com/bmad-sim/bmad-ecosystem/blob/main/tao/doc/variables.tex
[optimization]: https://github.com/bmad-sim/bmad-ecosystem/blob/main/tao/doc/optimization.tex
[init]: https://github.com/bmad-sim/bmad-ecosystem/blob/main/tao/doc/initialization.tex
[commands]: https://github.com/bmad-sim/bmad-ecosystem/blob/main/tao/doc/command-list.tex
[correction]: https://github.com/bmad-sim/bmad-ecosystem/tree/main/bmad-doc/tutorial_bmad_tao/lattice_files/twiss_correction
[matching]: https://github.com/bmad-sim/bmad-ecosystem/tree/main/bmad-doc/tao_examples/optics_matching
