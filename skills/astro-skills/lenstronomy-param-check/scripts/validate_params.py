#!/usr/bin/env python3
"""Validate a lenstronomy lensing-simulation parameter set (JSON in, JSON out).

Deterministic checks, with no LLM and no lenstronomy import: redshifts, model
list / kwargs pairing, per-profile parameter names, Einstein radius,
ellipticity, Sersic shape, pixel grid, noise, PSF, and (with
``--preset deeplense``) the DeepLenseSim recipe masses and peak SNR. Every
failed check comes with a message saying what to change.

Usage:
    python3 validate_params.py params.json [--preset general|deeplense] [--set NAME=VALUE ...]
    python3 validate_params.py - < params.json

Exit status: 0 = every check passed; 1 = a check failed or the parameter set
is malformed; 2 = usage error or unreadable JSON.

Standard library only (Python 3.10+). Ported from ML4SCI/DeepLense-AI-Scientist
(src/dlens/tools/_param_validator.py).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from dataclasses import dataclass, field
from typing import Any

# Per-profile parameter names (lenstronomy ``param_names``), introspected from
# lenstronomy 1.9.2 and 1.14.2, which agree for every profile listed here.
PROFILE_PARAMS: dict[str, tuple[str, ...]] = {
    # lens mass profiles
    "SIE": ("theta_E", "e1", "e2", "center_x", "center_y"),
    "SIS": ("theta_E", "center_x", "center_y"),
    "EPL": ("theta_E", "gamma", "e1", "e2", "center_x", "center_y"),
    "SHEAR": ("gamma1", "gamma2", "ra_0", "dec_0"),
    "NFW": ("Rs", "alpha_Rs", "center_x", "center_y"),
    # source light profiles
    "SERSIC": ("amp", "R_sersic", "n_sersic", "center_x", "center_y"),
    "SERSIC_ELLIPSE": ("amp", "R_sersic", "n_sersic", "e1", "e2", "center_x", "center_y"),
    "GAUSSIAN": ("amp", "sigma", "center_x", "center_y"),
}

# The arguments each profile's ``function`` takes without a default, from the
# same introspection; the remaining names (centres, shear origin) default to 0.
REQUIRED_PARAMS: dict[str, tuple[str, ...]] = {
    "SIE": ("theta_E", "e1", "e2"),
    "SIS": ("theta_E",),
    "EPL": ("theta_E", "gamma", "e1", "e2"),
    "SHEAR": ("gamma1", "gamma2"),
    "NFW": ("Rs", "alpha_Rs"),
    "SERSIC": ("amp", "R_sersic", "n_sersic"),
    "SERSIC_ELLIPSE": ("amp", "R_sersic", "n_sersic", "e1", "e2"),
    "GAUSSIAN": ("amp", "sigma"),
}


@dataclass
class Ranges:
    """Bounds for one preset. A ``None`` bound disables that check.

    See references/presets.md for where each value comes from.
    """

    z_lens_max: float
    z_source_max: float
    theta_e_min: float
    theta_e_max: float
    ellipticity_max: float
    n_sersic_min: float
    n_sersic_max: float
    numpix_min: int
    numpix_max: int
    deltapix_min: float
    deltapix_max: float
    halo_mass_min: float | None = None
    halo_mass_max: float | None = None
    axion_mass_min: float | None = None
    axion_mass_max: float | None = None
    vortex_mass_min: float | None = None
    vortex_mass_max: float | None = None
    snr_min: float | None = None
    snr_max: float | None = None
    lensing_boost: float = 5.9
    # Preset-specific advice appended to failure messages.
    hints: dict[str, str] = field(default_factory=dict)


PRESETS: dict[str, Ranges] = {
    # Sanity rails for any galaxy- or cluster-scale simulation: they catch unit
    # slips, typos and swapped values, not unusual science.
    "general": Ranges(
        z_lens_max=5.0,
        z_source_max=20.0,
        theta_e_min=0.01,
        theta_e_max=60.0,
        ellipticity_max=0.8,
        n_sersic_min=0.36,
        n_sersic_max=8.0,
        numpix_min=16,
        numpix_max=4096,
        deltapix_min=0.001,
        deltapix_max=1.0,
        hints={
            "theta_e": "galaxy-scale lenses are typically 0.5-3 arcsec, clusters tens of arcsec.",
            "numpix": "check that numPix counts pixels per side, not total pixels.",
            "deltapix": "deltaPix is arcsec per pixel, e.g. HST 0.04-0.13, Euclid VIS 0.1.",
        },
    ),
    # The DeepLenseSim Model_I recipe (github.com/mwt5345/DeepLenseSim), with
    # its masses and the peak SNR measured on images generated from it.
    "deeplense": Ranges(
        z_lens_max=5.0,
        z_source_max=10.0,
        theta_e_min=0.12,
        theta_e_max=13.0,
        ellipticity_max=0.5,
        n_sersic_min=0.36,
        n_sersic_max=8.0,
        numpix_min=16,
        numpix_max=1024,
        deltapix_min=0.01,
        deltapix_max=0.5,
        halo_mass_min=1e10,
        halo_mass_max=1e14,
        axion_mass_min=1e-24,
        axion_mass_max=1e-22,
        vortex_mass_min=1e9,
        vortex_mass_max=1e12,
        snr_min=14.0,
        snr_max=60.0,
        lensing_boost=5.9,
        hints={
            "z_lens": "typical DeepLense lenses sit near z=0.5.",
            "z_source": "typical DeepLense sources sit near z=1.0.",
            "theta_e": "the canonical DeepLense configuration is about 1 arcsec.",
            "numpix": "DeepLense recipes use 150 (Model_I) or 64 (Model_II/III).",
            "deltapix": "Model_I uses 0.05, HST 0.08, Euclid 0.101.",
            "halo_mass": "the canonical DeepLense value is 1e12.",
            "vortex_mass": "the canonical value is 3e10.",
        },
    ),
}


class InputError(ValueError):
    """The parameter set is structurally malformed; ``problems`` lists why."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def load_params(raw: Any) -> dict[str, Any]:
    """Check the structure of a parameter set and return a normalized copy.

    ``kwargs_data`` accepts lenstronomy 1.9.2's ``numPix``/``deltaPix`` or the
    1.14+ ``num_pix``/``delta_pix``; the result always uses the camelCase keys.
    """
    problems: list[str] = []
    if not isinstance(raw, dict):
        raise InputError(["the parameter set must be a JSON object"])

    out: dict[str, Any] = {}
    for key in ("z_lens", "z_source"):
        if key not in raw:
            problems.append(f"missing required field '{key}'")
        elif not _is_number(raw[key]):
            problems.append(f"'{key}' must be a number")
        else:
            out[key] = raw[key]

    for models_key, kwargs_key in (("lens_model_list", "kwargs_lens"),
                                   ("source_model_list", "kwargs_source")):
        models = raw.get(models_key)
        if models is None:
            problems.append(f"missing required field '{models_key}'")
        elif not isinstance(models, list) or not all(isinstance(m, str) for m in models):
            problems.append(f"'{models_key}' must be a list of profile-name strings")
        else:
            out[models_key] = list(models)
        kwargs = raw.get(kwargs_key)
        if kwargs is None:
            problems.append(f"missing required field '{kwargs_key}'")
        elif not isinstance(kwargs, list) or not all(isinstance(kw, dict) for kw in kwargs):
            problems.append(f"'{kwargs_key}' must be a list of one object per profile")
        else:
            for i, kw in enumerate(kwargs):
                for name, value in kw.items():
                    if not _is_number(value):
                        problems.append(f"{kwargs_key}[{i}].{name} must be a number")
            out[kwargs_key] = [dict(kw) for kw in kwargs]

    data = raw.get("kwargs_data")
    if data is None:
        problems.append("missing required field 'kwargs_data'")
    elif not isinstance(data, dict):
        problems.append("'kwargs_data' must be an object")
    else:
        norm: dict[str, Any] = {}
        for camel, snake in (("numPix", "num_pix"), ("deltaPix", "delta_pix")):
            if camel in data and snake in data and data[camel] != data[snake]:
                problems.append(f"kwargs_data gives both {camel} and {snake} with different values")
            value = data.get(camel, data.get(snake))
            if value is None:
                problems.append(f"missing required field 'kwargs_data.{camel}'")
            elif not _is_number(value):
                problems.append(f"kwargs_data.{camel} must be a number")
            else:
                norm[camel] = value
        if "numPix" in norm:
            if float(norm["numPix"]).is_integer():
                norm["numPix"] = int(norm["numPix"])
            else:
                problems.append("kwargs_data.numPix must be a whole number of pixels")
        for key in ("exposure_time", "background_rms"):
            value = data.get(key)
            if value is not None and not _is_number(value):
                problems.append(f"kwargs_data.{key} must be a number or null")
            norm[key] = value
        out["kwargs_data"] = norm

    psf = raw.get("kwargs_psf", {"psf_type": "GAUSSIAN"})
    if not isinstance(psf, dict):
        problems.append("'kwargs_psf' must be an object")
    else:
        psf_type = psf.get("psf_type", "GAUSSIAN")
        if not isinstance(psf_type, str):
            problems.append("kwargs_psf.psf_type must be a string")
        norm_psf: dict[str, Any] = {"psf_type": psf_type}
        for key in ("fwhm", "pixel_size"):
            value = psf.get(key)
            if value is not None and not _is_number(value):
                problems.append(f"kwargs_psf.{key} must be a number or null")
            norm_psf[key] = value
        out["kwargs_psf"] = norm_psf

    for key in ("halo_mass", "axion_mass", "vortex_mass"):
        value = raw.get(key)
        if value is not None and not _is_number(value):
            problems.append(f"'{key}' must be a number or null")
        out[key] = value

    if problems:
        raise InputError(problems)
    return out


def _estimate_snr(params: dict[str, Any], boost: float) -> float | None:
    """Peak-pixel SNR of the lensed image, calibrated on DeepLenseSim Model_I.

    peak counts ~ amp * deltaPix^2 * exposure_time * ``boost``, where ``boost``
    is the measured amplification of the observed peak by SIE lensing and the
    PSF. The calibration assumes the recipe's exponential (n_sersic ~ 1)
    source, which is why only the deeplense preset uses it.
    """
    data = params["kwargs_data"]
    exposure, rms = data["exposure_time"], data["background_rms"]
    if exposure is None or rms is None:
        return None
    if exposure <= 0 or rms <= 0:
        return None  # covered by their own checks
    amps = [kw["amp"] for kw in params["kwargs_source"] if "amp" in kw]
    if not amps:
        return None
    peak_counts = max(amps) * data["deltaPix"] ** 2 * exposure * boost
    noise = (peak_counts + (rms * exposure) ** 2) ** 0.5
    return peak_counts / noise if noise > 0 else None


def validate_parameters(params: dict[str, Any], ranges: Ranges) -> dict[str, Any]:
    """Run every computable check on a normalized parameter set.

    Checks whose inputs are absent (no exposure time, no masses) are omitted
    rather than failed.
    """
    r = ranges
    checks: dict[str, bool] = {}
    messages: list[str] = []

    def hint(key: str) -> str:
        return f" {r.hints[key]}" if key in r.hints else ""

    def fail(name: str, msg: str) -> None:
        checks[name] = False
        messages.append(msg)

    def ok(name: str) -> None:
        # A check can run once per profile; one failure must stick.
        checks.setdefault(name, True)

    # --- redshifts ---------------------------------------------------------
    z_lens, z_source = params["z_lens"], params["z_source"]
    if 0 < z_lens < r.z_lens_max:
        ok("z_lens_range")
    else:
        fail("z_lens_range", f"z_lens={z_lens} outside (0, {r.z_lens_max}).{hint('z_lens')}")
    if 0 < z_source < r.z_source_max:
        ok("z_source_range")
    else:
        fail("z_source_range",
             f"z_source={z_source} outside (0, {r.z_source_max}).{hint('z_source')}")
    if z_lens < z_source:
        ok("redshift_order")
    else:
        fail("redshift_order", f"z_lens={z_lens} must be strictly less than "
             f"z_source={z_source}: the source must sit behind the lens.")

    # --- model list / kwargs pairing and profile keys ----------------------
    for label in ("lens", "source"):
        models = params[f"{label}_model_list"]
        kwargs = params[f"kwargs_{label}"]
        if len(models) == len(kwargs) and len(models) > 0:
            ok(f"{label}_pairing")
        else:
            fail(f"{label}_pairing",
                 f"{label}_model_list has {len(models)} profiles but kwargs_{label} has "
                 f"{len(kwargs)} dicts; lenstronomy pairs them positionally, one dict "
                 "per profile.")
            continue
        for i, (name, kw) in enumerate(zip(models, kwargs)):
            known = PROFILE_PARAMS.get(name)
            if known is None:
                fail(f"{label}_profile_{i}_known",
                     f"Unknown {label} profile '{name}'; supported: {sorted(PROFILE_PARAMS)}.")
                continue
            unknown_keys = sorted(set(kw) - set(known))
            if unknown_keys:
                fail(f"{label}_profile_{i}_keys",
                     f"{name} kwargs contain unknown key(s) {unknown_keys}; lenstronomy "
                     f"accepts exactly {list(known)}. Check for names from another version "
                     "or another profile.")
            missing_keys = [k for k in REQUIRED_PARAMS[name] if k not in kw]
            if missing_keys:
                fail(f"{label}_profile_{i}_keys",
                     f"{name} kwargs are missing required key(s) {missing_keys}; "
                     f"lenstronomy needs {list(REQUIRED_PARAMS[name])} and defaults the "
                     "rest to 0.")
            ok(f"{label}_profile_{i}_keys")

    # --- Einstein radius ----------------------------------------------------
    for i, kw in enumerate(params["kwargs_lens"]):
        if "theta_E" not in kw:
            continue
        t = kw["theta_E"]
        if r.theta_e_min <= t <= r.theta_e_max:
            ok("einstein_radius")
        else:
            fail("einstein_radius",
                 f"kwargs_lens[{i}] theta_E={t} arcsec outside [{r.theta_e_min}, "
                 f"{r.theta_e_max}];{hint('theta_e') or ' check the units are arcsec.'}")

    # --- ellipticity (lens + source e1/e2) ----------------------------------
    all_kwargs = params["kwargs_lens"] + params["kwargs_source"]
    e_bad = [
        (label, k, kw[k])
        for label in ("lens", "source")
        for kw in params[f"kwargs_{label}"]
        for k in ("e1", "e2")
        if k in kw and abs(kw[k]) > r.ellipticity_max
    ]
    if any("e1" in kw or "e2" in kw for kw in all_kwargs):
        if e_bad:
            label, k, v = e_bad[0]
            fail("ellipticity",
                 f"{label} {k}={v} exceeds |e|<={r.ellipticity_max} (the axis ratio would "
                 "be extreme); derive e1/e2 from an axis ratio and angle, e.g. "
                 "lenstronomy's param_util.phi_q2_ellipticity.")
        else:
            ok("ellipticity")

    # --- Sersic index / radius ----------------------------------------------
    for kw in params["kwargs_source"]:
        if "n_sersic" in kw:
            n = kw["n_sersic"]
            if r.n_sersic_min <= n <= r.n_sersic_max:
                ok("sersic_index")
            else:
                fail("sersic_index",
                     f"n_sersic={n} outside [{r.n_sersic_min}, {r.n_sersic_max}] "
                     "(1 = exponential disk, 4 = de Vaucouleurs; below about 0.36 the "
                     "profile is numerically invalid in lenstronomy).")
        if "R_sersic" in kw:
            if kw["R_sersic"] > 0:
                ok("sersic_radius")
            else:
                fail("sersic_radius", f"R_sersic={kw['R_sersic']} must be positive (arcsec).")

    # --- data / instrument block ---------------------------------------------
    data = params["kwargs_data"]
    if r.numpix_min <= data["numPix"] <= r.numpix_max:
        ok("numpix")
    else:
        fail("numpix", f"numPix={data['numPix']} outside [{r.numpix_min}, "
             f"{r.numpix_max}].{hint('numpix')}")
    if r.deltapix_min <= data["deltaPix"] <= r.deltapix_max:
        ok("deltapix")
    else:
        fail("deltapix", f"deltaPix={data['deltaPix']} arcsec outside [{r.deltapix_min}, "
             f"{r.deltapix_max}].{hint('deltapix')}")
    if data["exposure_time"] is not None:
        if data["exposure_time"] > 0:
            ok("exposure_time")
        else:
            fail("exposure_time", f"exposure_time={data['exposure_time']} must be positive "
                 "seconds (HST F160W: 5400; Euclid VIS: 565), or null for noiseless.")
    if data["background_rms"] is not None:
        if data["background_rms"] > 0:
            ok("background_rms")
        else:
            fail("background_rms", f"background_rms={data['background_rms']} must be "
                 "positive, or null for noiseless.")

    # --- PSF ------------------------------------------------------------------
    psf = params["kwargs_psf"]
    if psf["psf_type"] == "GAUSSIAN":
        if psf["fwhm"] is not None and psf["fwhm"] > 0:
            ok("psf_fwhm")
        else:
            fail("psf_fwhm", f"GAUSSIAN PSF requires a positive fwhm (got {psf['fwhm']}); "
                 "lenstronomy's PSF has no 'sigma' argument.")
    if psf["pixel_size"] is not None:
        if abs(psf["pixel_size"] - data["deltaPix"]) < 1e-9:
            ok("psf_pixel_size")
        else:
            fail("psf_pixel_size", f"PSF pixel_size={psf['pixel_size']} != grid "
                 f"deltaPix={data['deltaPix']}; they must match.")

    # --- DeepLense recipe masses (deeplense preset only) ----------------------
    for key, unit in (("halo_mass", "M_sun"), ("axion_mass", "eV"), ("vortex_mass", "M_sun")):
        value = params[key]
        lo, hi = getattr(r, f"{key}_min"), getattr(r, f"{key}_max")
        if value is None or lo is None or hi is None:
            continue
        if lo <= value <= hi:
            ok(key)
        else:
            fail(key, f"{key}={value:g} {unit} outside [{lo:g}, {hi:g}].{hint(key)}")

    # --- peak SNR (deeplense preset only) -------------------------------------
    snr = None
    if r.snr_min is not None and r.snr_max is not None:
        snr = _estimate_snr(params, r.lensing_boost)
    if snr is not None:
        if r.snr_min <= snr <= r.snr_max:
            ok("snr")
        elif snr < r.snr_min:
            fail("snr", f"estimated peak SNR {snr:.1f} < {r.snr_min:g} (DeepLenseSim "
                 "Model_I images measure median 18, p5 15); raise the source amp roughly "
                 "proportionally, increase exposure_time, or lower background_rms.")
        else:
            fail("snr", f"estimated peak SNR {snr:.1f} > {r.snr_max:g}, implausibly "
                 "bright for DeepLenseSim images (p95 = 22); the source amp is likely "
                 "runaway. Lower it.")

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "messages": messages,
        "snr_estimate": None if snr is None else round(snr, 3),
    }


def _apply_overrides(ranges: Ranges, overrides: list[str]) -> Ranges:
    numeric = {f.name: f for f in dataclasses.fields(Ranges) if f.name != "hints"}
    changes: dict[str, Any] = {}
    for item in overrides:
        name, sep, text = item.partition("=")
        if not sep or name not in numeric:
            raise ValueError(f"--set expects NAME=VALUE with NAME one of {sorted(numeric)}; "
                             f"got {item!r}")
        try:
            value = float(text)
        except ValueError:
            raise ValueError(f"--set {name}: {text!r} is not a number") from None
        changes[name] = int(value) if name.startswith("numpix") else value
    return dataclasses.replace(ranges, **changes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a lenstronomy parameter set; prints a JSON report.")
    parser.add_argument("params", help="parameter-set JSON file, or - for stdin")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="general",
                        help="range preset (default: general)")
    parser.add_argument("--set", dest="overrides", action="append", default=[],
                        metavar="NAME=VALUE", help="override one range bound, e.g. "
                        "theta_e_max=5 (repeatable)")
    args = parser.parse_args(argv)

    try:
        ranges = _apply_overrides(PRESETS[args.preset], args.overrides)
        if args.params == "-":
            raw = json.load(sys.stdin)
        else:
            with open(args.params, encoding="utf-8") as fh:
                raw = json.load(fh)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2

    try:
        params = load_params(raw)
    except InputError as exc:
        report = {"passed": False, "checks": {"schema": False},
                  "messages": exc.problems, "snr_estimate": None}
    else:
        report = validate_parameters(params, ranges)
    print(json.dumps({"preset": args.preset, **report}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
