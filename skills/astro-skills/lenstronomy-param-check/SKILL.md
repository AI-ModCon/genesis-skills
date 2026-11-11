---
name: lenstronomy-param-check
description: Check lenstronomy strong-lensing simulation parameters for physical and API mistakes, then verify that a lenstronomy script uses exactly those values. Use when writing, reviewing or debugging lenstronomy kwargs, or simulation code an agent generated.
license: MIT
compatibility: Python 3.10+ standard library only. Does not import or need lenstronomy, Docker, network access or API keys.
allowed-tools: Bash(python3 *) Read Write
metadata:
  author: Aatmaj Amol Salunke
  source: https://github.com/ML4SCI/DeepLense-AI-Scientist
---

# lenstronomy Parameter Check

Two deterministic checks for simulations built with lenstronomy (Birrer & Amara
2018). Neither one runs lenstronomy or calls a model, so they are fast and give
the same answer every time.

- `scripts/validate_params.py` checks a parameter set: redshifts, the pairing of
  each model list with its kwargs, profile parameter names, Einstein radius,
  ellipticity, Sersic shape, source brightness, pixel grid, noise and PSF.
- `scripts/check_code_params.py` reads a lenstronomy script with Python's `ast`
  module, without running it, and reports every value that differs from the
  parameter set, is missing, or cannot be proven to match it.

## Use This Skill When

- Writing a lenstronomy simulation from a description, especially when you are
  generating the code.
- Reviewing or debugging the lens, source, grid or PSF settings of an existing
  lenstronomy script.
- Producing a batch of simulations whose parameters must stay within known bounds.

## Workflow

Paths are relative to this skill's directory.

1. **Write the parameter set** as JSON. The format is in
   [references/parameter-format.md](references/parameter-format.md), and
   [assets/example_params.json](assets/example_params.json) is a complete example.
2. **Validate it:**

   ```bash
   python3 scripts/validate_params.py params.json
   ```

   Add `--preset deeplense` for the DeepLenseSim Model_I recipe. Fix what each
   message says, then rerun until the report shows `"passed": true`.
3. **Write the script** with the validated values as literals.
   [assets/example_simulation.py](assets/example_simulation.py) shows the shape
   the check expects.
4. **Check the script against the parameter set:**

   ```bash
   python3 scripts/check_code_params.py simulate.py params.json
   ```

   Fix each diverged, missing or unresolved field in the script, then rerun.
5. **Report** both results to the user, including any range you overrode.

Both scripts print a JSON report and exit with 0 when everything passed, 1 when
a check failed, and 2 when the input could not be read. A malformed parameter set
is a failed `schema` check for `validate_params.py` and an `{"error": ...}`
report with exit status 2 for `check_code_params.py`.

## Presets

| Preset | Use for | What changes |
|--------|---------|--------------|
| `general` (default) | Any galaxy- or cluster-scale simulation | Wide sanity bounds; no mass or SNR checks |
| `deeplense` | The DeepLenseSim Model_I recipe | The recipe's bounds, halo/axion/vortex mass checks, and a peak-SNR band of 14-60 |

Override one bound with `--set NAME=VALUE`, for example `--set theta_e_max=5`;
the value must be a finite number.
Every bound and its source is listed in [references/presets.md](references/presets.md).

## Output Format

A failed validation names each failed check and says what to change:

```json
{
  "preset": "general",
  "passed": false,
  "checks": {"z_lens_range": true, "z_source_range": true, "redshift_order": false},
  "messages": ["z_lens=1.5 must be strictly less than z_source=1.0: the source must sit behind the lens."],
  "snr_estimate": null
}
```

A failed code check lists each field with both values:

```json
{
  "passed": false,
  "matched": ["deltaPix", "kwargs_lens[0].e1"],
  "diverged": [{"field": "kwargs_lens[0].theta_E", "expected": 1.0, "actual": 2.5}],
  "missing": [],
  "unresolved": [],
  "messages": ["kwargs_lens[0].theta_E: script uses 2.5 but the parameter set has 1.0; use the parameter-set value exactly."]
}
```

## Guidelines

- Fix the parameters or the script, not the bounds. Override a bound only when
  the user's science needs it, and say so in the report.
- Do not change a script's values just to silence the code check. If the
  parameter set is wrong, fix it and validate it again.
- Write values as literals, and do not change them after writing them. Values
  produced by helper functions, such as `param_util.phi_q2_ellipticity`, and
  values edited in place afterwards are reported as unresolved because the check
  cannot verify them without running the code. Compute them once and write the
  numbers into both the parameter set and the script.
- A pass means the inputs are plausible and consistent with each other, not that
  the simulation is scientifically right.

## Limitations

The code check certifies only what it can prove from the source: **a value it
cannot statically prove to be the parameter set's is reported as unresolved,
never as matched**, and an unresolved value fails the check. A pass therefore
means the script, if it runs, renders the parameter set's values; it does not
mean the script runs.

- Profiles covered: SIE, SIS, EPL, SHEAR and NFW for the lens; SERSIC,
  SERSIC_ELLIPSE and GAUSSIAN for light. Any other profile, or a profile in the
  wrong list, is reported as unknown. Parameter names were introspected from
  lenstronomy 1.9.2 and 1.14.2, which agree.
- What is rendered is what `ImageModel.image(...)` is called with, and the
  `LensModel`, `LightModel`, `PSF`, `ImageData` and `data_configure_simple` that
  `ImageModel` is built from; only a script with no `ImageModel` falls back to
  the conventional names (`kwargs_lens`, `lens_model_list`, ...). Higher-level
  interfaces such as `SimAPI` or `sim_util.simulate_simple` are not followed.
  Every argument of those calls that the parameter set does not describe must be
  lenstronomy's default; `kwargs_numerics` and likelihood-only arguments are not
  checked. Lens light, point sources and extinction are not supported, so a
  script that adds them fails.
- Redshifts are compared when the script gives `LensModel` any (`z_lens`,
  `z_source`, `lens_redshift_list`, `z_source_convention`, which multi-plane
  needs). A single-plane `LensModel` given none renders the same image whatever
  the redshifts, since the supported profiles are in angles. A `PIXEL` kernel is
  compared element by element as written, not after lenstronomy normalizes it.
- The check follows the script the way it runs: branches whose condition is
  known, and/or and conditional expressions, loops (an `else` only without a
  `break`), `try`/`except`/`finally` (a handler may start anywhere in its body),
  `match` cases and their guards, function calls with Python's scoping and
  default arguments, imports that rebind a name, and in-place edits through any
  name or function that shares the object, including one made while a later
  argument is evaluated. Unresolved, as values: anything a function returns, a
  call other than the lenstronomy builders and a few helpers known not to
  change their arguments (`print`, `len`, `range`, `np.array` without a
  `dtype`, `dict.get`, ...), an object handed to such a call, a loop variable
  over something it cannot list, an attribute, and whatever a `with` block does
  when its context manager might swallow an exception (anything but `open()`
  and similar). A non-finite value (`1e400`) never matches, and the report
  shows it as the string `"inf"` or `"nan"`.
- Unresolved, as a whole script: code that runs at a time the check cannot know,
  namely a function handed to code it does not follow (a callback, a decorator,
  a returned closure), a lambda or method that calls code, a generator
  expression that calls code and is not consumed right away (by `list()`,
  `sum()`, `str.join()` and the like), a generator or async function, and
  recursion; `exec()`, `eval()` and
  `globals()`; a star import from a module other than lenstronomy; and changes
  to lenstronomy, numpy, scipy or astropy themselves. The report says which line.
- The `deeplense` preset's SNR estimate covers one source profile with a
  Gaussian or no PSF; with several sources, since overlapping sources add up, or
  with a `PIXEL` PSF, it is skipped.

## References

- Birrer, S. & Amara, A. 2018, "lenstronomy: Multi-purpose gravitational lens
  modelling software package", Physics of the Dark Universe, 22, 189.
- DeepLenseSim, the source of the `deeplense` preset:
  <https://github.com/mwt5345/DeepLenseSim>
