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
  ellipticity, Sersic shape, pixel grid, noise and PSF.
- `scripts/check_code_params.py` reads a lenstronomy script with Python's `ast`
  module, without running it, and reports every value that differs from the
  parameter set, is missing, or is computed at runtime.

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
a check failed, and 2 when the input could not be read.

## Presets

| Preset | Use for | What changes |
|--------|---------|--------------|
| `general` (default) | Any galaxy- or cluster-scale simulation | Wide sanity bounds; no mass or SNR checks |
| `deeplense` | The DeepLenseSim Model_I recipe | The recipe's bounds, halo/axion/vortex mass checks, and a peak-SNR band of 14-60 |

Override one bound with `--set NAME=VALUE`, for example `--set theta_e_max=5`.
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
- Write values as literals. Values produced by helper functions, such as
  `param_util.phi_q2_ellipticity`, are reported as unresolved because the check
  cannot verify them without running the code. Compute them once and write the
  numbers into both the parameter set and the script.
- A pass means the inputs are plausible and consistent with each other, not that
  the simulation is scientifically right.

## Limitations

- Profiles covered: SIE, SIS, EPL, SHEAR and NFW for the lens; SERSIC,
  SERSIC_ELLIPSE and GAUSSIAN for light. Any other profile, or a profile in the
  wrong list, is reported as unknown. Parameter names were introspected from
  lenstronomy 1.9.2 and 1.14.2, which agree.
- The code check follows the calls that build the simulation (`LensModel`,
  `LightModel`, `PSF`, `ImageModel`, `data_configure_simple` and
  `ImageModel.image`) and falls back to the conventional names (`kwargs_lens`,
  `lens_model_list`, ...). It follows the script the way it runs: code in a
  branch that cannot run, or in a function that is never called, does not count.
  A value that depends on a runtime condition, a loop or an exception is
  reported as unresolved. It does not follow return values or in-place edits
  such as `kwargs_lens[0]["theta_E"] = 2`.

## References

- Birrer, S. & Amara, A. 2018, "lenstronomy: Multi-purpose gravitational lens
  modelling software package", Physics of the Dark Universe, 22, 189.
- DeepLenseSim, the source of the `deeplense` preset:
  <https://github.com/mwt5345/DeepLenseSim>
