"""Tests for the lenstronomy-param-check skill scripts (standard library only)."""

from __future__ import annotations

import copy
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "astro-skills" / "lenstronomy-param-check"
VALIDATE = SKILL / "scripts" / "validate_params.py"
CHECK = SKILL / "scripts" / "check_code_params.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look their module up while it loads
    spec.loader.exec_module(module)
    return module


V = _load("lenstronomy_validate_params", VALIDATE)
C = _load("lenstronomy_check_code_params", CHECK)

GOOD = json.loads((SKILL / "assets" / "example_params.json").read_text(encoding="utf-8"))
EXAMPLE = (SKILL / "assets" / "example_simulation.py").read_text(encoding="utf-8")


def _validate(params: dict, preset: str = "deeplense", **overrides) -> dict:
    ranges = V.PRESETS[preset]
    if overrides:
        ranges = V._apply_overrides(ranges, [f"{k}={v}" for k, v in overrides.items()])
    return V.validate_parameters(V.load_params(params), ranges)


def _good(**changes) -> dict:
    params = copy.deepcopy(GOOD)
    params.update(changes)
    return params


def _program(params: dict) -> str:
    """A script that writes the parameter set's values as literals."""
    data, psf = params["kwargs_data"], params["kwargs_psf"]
    return "\n".join(
        [
            "import numpy as np",
            f"numPix = {data['numPix']}",
            f"deltaPix = {data['deltaPix']}",
            f"exposure_time = {data['exposure_time']}",
            f"background_rms = {data['background_rms']}",
            f"lens_model_list = {params['lens_model_list']!r}",
            f"kwargs_lens = {params['kwargs_lens']!r}",
            f"source_model_list = {params['source_model_list']!r}",
            f"kwargs_source = {params['kwargs_source']!r}",
            f"psf_class = PSF(psf_type={psf['psf_type']!r}, fwhm={psf['fwhm']}, pixel_size=deltaPix)",
        ]
    ) + "\n"


def _compare(code: str, params: dict | None = None) -> dict:
    return C.compare_code_to_params(code, C.load_params(params or GOOD))


class ValidatorTests(unittest.TestCase):
    def test_example_passes_both_presets(self) -> None:
        res = _validate(GOOD, "deeplense")
        self.assertTrue(res["passed"], res["messages"])
        self.assertEqual(res["messages"], [])
        self.assertTrue(14.0 <= res["snr_estimate"] <= 60.0)

        res = _validate(GOOD, "general")
        self.assertTrue(res["passed"], res["messages"])
        self.assertIsNone(res["snr_estimate"])
        self.assertNotIn("snr", res["checks"])
        self.assertNotIn("halo_mass", res["checks"])

    def test_redshift_order(self) -> None:
        res = _validate(_good(z_lens=1.5, z_source=1.0))
        self.assertFalse(res["passed"])
        self.assertFalse(res["checks"]["redshift_order"])
        self.assertTrue(any("behind the lens" in m for m in res["messages"]))

    def test_einstein_radius(self) -> None:
        params = _good()
        params["kwargs_lens"][0]["theta_E"] = 40.0
        res = _validate(params)
        self.assertFalse(res["checks"]["einstein_radius"])
        self.assertTrue(any("theta_E=40.0" in m for m in res["messages"]))
        self.assertTrue(_validate(params, "general")["checks"]["einstein_radius"])

    def test_ellipticity_bound(self) -> None:
        params = _good()
        params["kwargs_lens"][0]["e1"] = 0.9
        for preset in ("deeplense", "general"):
            res = _validate(params, preset)
            self.assertFalse(res["checks"]["ellipticity"])
            self.assertTrue(any("e1=0.9" in m for m in res["messages"]))

    def test_sersic_index(self) -> None:
        params = _good()
        params["kwargs_source"][0]["n_sersic"] = 12.0
        self.assertFalse(_validate(params)["checks"]["sersic_index"])

    def test_exposure_and_background(self) -> None:
        res = _validate(_good(kwargs_data={"numPix": 64, "deltaPix": 0.08,
                                           "exposure_time": -5.0, "background_rms": 0.0}))
        self.assertFalse(res["checks"]["exposure_time"])
        self.assertFalse(res["checks"]["background_rms"])

    def test_grid_sanity(self) -> None:
        res = _validate(_good(kwargs_data={"numPix": 4, "deltaPix": 3.0,
                                           "exposure_time": 5400.0, "background_rms": 0.01}))
        self.assertFalse(res["checks"]["numpix"])
        self.assertFalse(res["checks"]["deltapix"])

    def test_psf_checks(self) -> None:
        res = _validate(_good(kwargs_psf={"psf_type": "GAUSSIAN", "fwhm": None, "pixel_size": 0.05}))
        self.assertFalse(res["checks"]["psf_fwhm"])
        self.assertFalse(res["checks"]["psf_pixel_size"])  # 0.05 != deltaPix 0.08
        self.assertTrue(any("no 'sigma'" in m for m in res["messages"]))

    def test_mass_ranges_only_under_deeplense(self) -> None:
        params = _good(halo_mass=1e16, axion_mass=1e-10, vortex_mass=1e6)
        res = _validate(params)
        for key in ("halo_mass", "axion_mass", "vortex_mass"):
            self.assertFalse(res["checks"][key])
        res = _validate(params, "general")
        self.assertTrue(res["passed"], res["messages"])

    def test_snr_band(self) -> None:
        dim = _good()
        dim["kwargs_source"][0]["amp"] = 0.001
        res = _validate(dim)
        self.assertFalse(res["checks"]["snr"])
        self.assertLess(res["snr_estimate"], 14.0)

        runaway = _good()
        runaway["kwargs_source"][0]["amp"] = 1e5
        res = _validate(runaway)
        self.assertFalse(res["checks"]["snr"])
        self.assertGreater(res["snr_estimate"], 60.0)
        self.assertTrue(any("runaway" in m for m in res["messages"]))

    def test_snr_skipped_when_noiseless(self) -> None:
        res = _validate(_good(kwargs_data={"numPix": 64, "deltaPix": 0.08}))
        self.assertNotIn("snr", res["checks"])
        self.assertIsNone(res["snr_estimate"])
        self.assertTrue(res["passed"], res["messages"])

    def test_snr_tracks_the_source_profile(self) -> None:
        # lenstronomy 1.9.2 renders of one lens at Model_I settings (150 px at 0.05",
        # Gaussian PSF FWHM 0.087", no supersampling, 1778 s, background_rms 0.01, the
        # recipe's noise), with amp set so each image measures SNR ~24: the median over
        # 50 noise draws of (brightest pixel - mean of the 10 px corners) /
        # sqrt(brightest pixel + their variance). Their amps span 25x, so amp alone
        # cannot predict the SNR.
        references = [
            ("SERSIC_ELLIPSE", {"amp": 76.0, "R_sersic": 0.3, "n_sersic": 0.5}, 25.3),
            ("SERSIC_ELLIPSE", {"amp": 32.0, "R_sersic": 0.3, "n_sersic": 1.0}, 24.2),
            ("SERSIC_ELLIPSE", {"amp": 10.0, "R_sersic": 0.3, "n_sersic": 2.0}, 23.3),
            ("SERSIC_ELLIPSE", {"amp": 3.1, "R_sersic": 0.3, "n_sersic": 4.0}, 23.6),
            ("GAUSSIAN", {"amp": 9.9, "sigma": 0.1}, 24.5),
        ]
        for source, kwargs, measured in references:
            with self.subTest(source=source, **kwargs):
                shape = {"e1": -0.05, "e2": 0.05} if source == "SERSIC_ELLIPSE" else {}
                params = _good(
                    kwargs_lens=[{"theta_E": 1.2, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}],
                    source_model_list=[source],
                    kwargs_source=[{**kwargs, **shape, "center_x": 0.12, "center_y": 0.05}],
                    kwargs_data={"numPix": 150, "deltaPix": 0.05, "exposure_time": 1778.0,
                                 "background_rms": 0.01},
                    kwargs_psf={"psf_type": "GAUSSIAN", "fwhm": 0.087, "pixel_size": 0.05},
                )
                res = _validate(params)
                self.assertTrue(res["checks"]["snr"], res["messages"])
                self.assertLess(abs(res["snr_estimate"] / measured - 1), 0.15)

    def test_snr_is_not_estimated_from_a_nonpositive_amp(self) -> None:
        # A negative amp used to make the estimate take the square root of a negative
        # number; it now fails its own check and the estimate is skipped.
        params = _good()
        params["kwargs_source"][0]["amp"] = -100.0
        res = _validate(params)
        self.assertFalse(res["checks"]["source_amp"])
        self.assertNotIn("snr", res["checks"])
        self.assertIsNone(res["snr_estimate"])

    def test_source_amp_must_be_positive_in_every_preset(self) -> None:
        for preset in ("general", "deeplense"):
            for amp in (-12.0, 0.0):
                with self.subTest(preset=preset, amp=amp):
                    params = _good()
                    params["kwargs_source"][0]["amp"] = amp
                    res = _validate(params, preset)
                    self.assertFalse(res["passed"])
                    self.assertFalse(res["checks"]["source_amp"])
                    self.assertTrue(any(f"amp={amp}" in m and "must be positive" in m
                                        for m in res["messages"]))
            gaussian = _good(source_model_list=["GAUSSIAN"],
                             kwargs_source=[{"amp": -12.0, "sigma": 0.1}])
            self.assertFalse(_validate(gaussian, preset)["checks"]["source_amp"])
            self.assertTrue(_validate(GOOD, preset)["checks"]["source_amp"])

    def test_psf_type_must_be_one_lenstronomy_accepts(self) -> None:
        params = _good()
        params["kwargs_psf"]["psf_type"] = "GAUSIAN"
        res = _validate(params, "general")
        self.assertFalse(res["checks"]["psf_type"])
        self.assertTrue(any("GAUSIAN" in m and "NONE" in m for m in res["messages"]))
        self.assertTrue(_validate(GOOD, "general")["checks"]["psf_type"])

    def test_profiles_are_checked_against_their_own_component(self) -> None:
        params = _good(source_model_list=["SIE"],
                       kwargs_source=[{"theta_E": 1.0, "e1": 0.1, "e2": 0.0}])
        res = _validate(params, "general")
        self.assertFalse(res["checks"]["source_profile_0_known"])
        self.assertTrue(any("'SIE' is a lens profile" in m for m in res["messages"]))

        params = _good(lens_model_list=["SERSIC"],
                       kwargs_lens=[{"amp": 1.0, "R_sersic": 0.3, "n_sersic": 1.0}])
        res = _validate(params, "general")
        self.assertFalse(res["checks"]["lens_profile_0_known"])

    def test_combined_ellipticity_must_stay_below_one(self) -> None:
        # Each component is within the general preset's 0.8, but |e| = 1.13 has no axis ratio.
        degenerate = _good()
        degenerate["kwargs_lens"][0].update(e1=0.8, e2=0.8)
        res = _validate(degenerate, "general")
        self.assertFalse(res["checks"]["ellipticity"])
        self.assertTrue(any("sqrt(e1^2 + e2^2) = 1.13" in m for m in res["messages"]))

        strong = _good()
        strong["kwargs_lens"][0].update(e1=0.6, e2=0.6)  # |e| = 0.85, q = 0.08: extreme but valid
        self.assertTrue(_validate(strong, "general")["checks"]["ellipticity"])

    def test_snr_skipped_for_a_nonpositive_pixel_scale(self) -> None:
        params = _good(kwargs_data={"numPix": 64, "deltaPix": 0, "exposure_time": 5400.0,
                                    "background_rms": 0.01},
                       kwargs_psf={"psf_type": "NONE", "fwhm": None, "pixel_size": None})
        res = _validate(params)
        self.assertFalse(res["checks"]["deltapix"])
        self.assertIsNone(res["snr_estimate"])
        self.assertNotIn("snr", res["checks"])

    def test_non_finite_numbers_are_schema_errors(self) -> None:
        # json.loads turns 1e400 into inf and accepts NaN; a 400-digit int overflows a float.
        for path, value in ((("kwargs_lens", 0, "center_x"), float("inf")),
                            (("kwargs_lens", 0, "e1"), float("nan")),
                            (("kwargs_source", 0, "amp"), 10 ** 400),
                            (("kwargs_data", "exposure_time"), float("inf"))):
            with self.subTest(field=path):
                params = _good()
                target = params
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(V.InputError) as raised:
                    V.load_params(params)
                self.assertTrue(any("finite" in p for p in raised.exception.problems))
        self.assertEqual(V.load_params(json.loads(json.dumps(GOOD)))["z_lens"], 0.5)

    def test_gaussian_source_width_must_be_positive(self) -> None:
        for preset in ("general", "deeplense"):
            with self.subTest(preset=preset):
                params = _good(source_model_list=["GAUSSIAN"],
                               kwargs_source=[{"amp": 9.9, "sigma": 0.0, "center_x": 0.05, "center_y": 0.05}])
                res = _validate(params, preset)
                self.assertFalse(res["checks"]["gaussian_sigma"])
                params["kwargs_source"][0]["sigma"] = 0.1
                self.assertTrue(_validate(params, preset)["checks"]["gaussian_sigma"])

    def test_pixel_psf_needs_a_kernel(self) -> None:
        psf = {"psf_type": "PIXEL", "fwhm": None, "pixel_size": 0.08}
        res = _validate(_good(kwargs_psf=psf), "general")
        self.assertFalse(res["checks"]["psf_kernel"])
        self.assertTrue(any("kernel_point_source" in m for m in res["messages"]))

        kernel = [[0.0, 0.1, 0.0], [0.1, 0.6, 0.1], [0.0, 0.1, 0.0]]
        self.assertTrue(_validate(_good(kwargs_psf=dict(psf, kernel_point_source=kernel)), "general")["passed"])
        zero = [[0.0] * 3] * 3
        self.assertFalse(_validate(_good(kwargs_psf=dict(psf, kernel_point_source=zero)), "general")["checks"]["psf_kernel"])
        with self.assertRaises(V.InputError):
            V.load_params(_good(kwargs_psf=dict(psf, kernel_point_source=[[1.0, 2.0], [3.0]])))

    def test_snr_is_not_estimated_from_an_invalid_source_shape(self) -> None:
        # n_sersic = 0.001 fails its own check; the estimate used to overflow on it.
        params = _good()
        params["kwargs_source"][0]["n_sersic"] = 0.001
        res = _validate(params)
        self.assertFalse(res["checks"]["sersic_index"])
        self.assertNotIn("snr", res["checks"])
        self.assertIsNone(res["snr_estimate"])

        # A tiny but positive R_sersic is valid, so it is estimated, without overflowing.
        params = _good()
        params["kwargs_source"][0].update(R_sersic=1e-300, n_sersic=0.5)
        self.assertFalse(_validate(params)["checks"]["snr"])

    def test_snr_is_not_estimated_for_several_sources(self) -> None:
        # Two copies of the same source add up to twice the peak; the brightest-one
        # estimate would not see it, so no estimate is made.
        params = _good(source_model_list=["SERSIC_ELLIPSE"] * 2)
        params["kwargs_source"] = params["kwargs_source"] * 2
        res = _validate(params)
        self.assertNotIn("snr", res["checks"])
        self.assertIsNone(res["snr_estimate"])
        self.assertTrue(res["passed"], res["messages"])

    def test_snr_is_not_estimated_from_an_out_of_range_pixel_scale(self) -> None:
        # deltaPix=1e-300 squares to 0 and used to raise ZeroDivisionError; a huge one overflowed.
        for delta in (1e-300, 1e200):
            with self.subTest(deltaPix=delta):
                params = _good(kwargs_data={"numPix": 64, "deltaPix": delta, "exposure_time": 5400.0,
                                            "background_rms": 0.01},
                               kwargs_psf={"psf_type": "NONE", "fwhm": None, "pixel_size": None})
                res = _validate(params)
                self.assertFalse(res["checks"]["deltapix"])
                self.assertNotIn("snr", res["checks"])
                self.assertIsNone(res["snr_estimate"])

    def test_an_overflowing_snr_estimate_fails_as_json(self) -> None:
        # amp=1e308 overflows the estimate; the report used to print NaN, which is not JSON.
        params = _good()
        params["kwargs_source"][0]["amp"] = 1e308
        res = _validate(params)
        self.assertFalse(res["checks"]["snr"])
        self.assertIsNone(res["snr_estimate"])
        self.assertTrue(any("overflows" in m for m in res["messages"]))
        json.loads(json.dumps(res, allow_nan=False))

    def test_snr_is_not_estimated_for_a_pixel_psf(self) -> None:
        # A PIXEL PSF has no fwhm; the estimate used to treat it as no blur at all, so two
        # very different kernels got the same estimate.
        sharp = [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.0]]
        wide = [[1.0] * 3] * 3
        for kernel in (sharp, wide):
            with self.subTest(kernel=kernel):
                res = _validate(_good(kwargs_psf={"psf_type": "PIXEL", "pixel_size": 0.08,
                                                  "kernel_point_source": kernel}))
                self.assertNotIn("snr", res["checks"])
                self.assertIsNone(res["snr_estimate"])
                self.assertTrue(res["passed"], res["messages"])

    def test_blurred_centre_matches_the_gaussian_closed_form(self) -> None:
        # A Gaussian of width s blurred by widths (sr, st) peaks at s^2 / sqrt((s^2+sr^2)(s^2+st^2)).
        for s, sr, st in ((0.1, 0.04, 0.04), (0.05, 0.08, 0.002), (0.3, 0.02, 0.01)):
            exact = s * s / math.sqrt((s * s + sr * sr) * (s * s + st * st))
            got = V._blurred_centre(lambda r, s=s: math.exp(-r * r / (2 * s * s)), sr, st)
            self.assertAlmostEqual(got / exact, 1.0, delta=1e-4)

    def test_unknown_profile_and_keys(self) -> None:
        params = _good(lens_model_list=["SIE_FANCY"])
        self.assertFalse(_validate(params)["checks"]["lens_profile_0_known"])

        blended = _good()
        blended["kwargs_source"][0]["sigma"] = 0.2  # a GAUSSIAN key on SERSIC_ELLIPSE
        res = _validate(blended)
        self.assertFalse(res["checks"]["source_profile_0_keys"])
        self.assertTrue(any("unknown key(s) ['sigma']" in m for m in res["messages"]))

    def test_pairing_mismatch(self) -> None:
        res = _validate(_good(lens_model_list=["SIE", "SHEAR"]))  # one kwargs dict
        self.assertFalse(res["checks"]["lens_pairing"])
        self.assertTrue(any("positionally" in m for m in res["messages"]))

    def test_bounds_can_be_overridden(self) -> None:
        res = _validate(GOOD, theta_e_max=0.5)  # canonical theta_E=1.0 now fails
        self.assertFalse(res["checks"]["einstein_radius"])
        with self.assertRaises(ValueError):
            V._apply_overrides(V.PRESETS["general"], ["no_such_bound=1"])


class ValidatorRegressionTests(unittest.TestCase):
    def test_a_later_pass_does_not_hide_an_earlier_failure(self) -> None:
        # DeepLense-AI-Scientist issue #10: with two Sersic sources, a bad
        # n_sersic or R_sersic followed by a good profile used to pass.
        good = GOOD["kwargs_source"][0]
        for key, bad_value in (("n_sersic", 12.0), ("R_sersic", -0.5)):
            bad = dict(good, **{key: bad_value})
            for profiles in ([bad, good], [good, bad]):
                params = _good(source_model_list=["SERSIC_ELLIPSE"] * 2,
                               kwargs_source=copy.deepcopy(profiles))
                res = _validate(params)
                with self.subTest(key=key, bad_first=profiles[0] is bad):
                    self.assertFalse(res["passed"])
                    self.assertTrue(any(key in m for m in res["messages"]))

    def test_every_lens_profile_einstein_radius_is_checked(self) -> None:
        good = GOOD["kwargs_lens"][0]
        params = _good(lens_model_list=["SIE", "SIE"],
                       kwargs_lens=[dict(good), dict(good, theta_E=500.0)])
        for preset in ("general", "deeplense"):
            res = _validate(params, preset)
            with self.subTest(preset=preset):
                self.assertFalse(res["checks"]["einstein_radius"])
                self.assertTrue(any("kwargs_lens[1]" in m and "theta_E=500.0" in m
                                    for m in res["messages"]))

    def test_missing_required_profile_keys_fail(self) -> None:
        no_theta = _good()
        del no_theta["kwargs_lens"][0]["theta_E"]
        res = _validate(no_theta, "general")
        self.assertFalse(res["checks"]["lens_profile_0_keys"])
        self.assertTrue(any("missing required key(s) ['theta_E']" in m for m in res["messages"]))

        no_gamma2 = _good(lens_model_list=["SIE", "SHEAR"],
                          kwargs_lens=[GOOD["kwargs_lens"][0], {"gamma1": 0.02}])
        res = _validate(no_gamma2, "general")
        self.assertFalse(res["checks"]["lens_profile_1_keys"])

        # Centres default to 0 in lenstronomy, so leaving them out is fine.
        centred = _good()
        for kw in centred["kwargs_lens"] + centred["kwargs_source"]:
            del kw["center_x"], kw["center_y"]
        res = _validate(centred, "general")
        self.assertTrue(res["passed"], res["messages"])


class LoadParamsTests(unittest.TestCase):
    def test_snake_case_grid_keys_are_accepted(self) -> None:
        params = _good(kwargs_data={"num_pix": 64, "delta_pix": 0.08})
        self.assertEqual(V.load_params(params)["kwargs_data"]["numPix"], 64)
        self.assertEqual(C.load_params(params)["kwargs_data"]["deltaPix"], 0.08)

    def test_structural_problems_are_all_reported(self) -> None:
        params = _good(z_lens="0.5", kwargs_data={"numPix": 64.5, "deltaPix": 0.08,
                                                  "delta_pix": 0.1})
        del params["kwargs_source"]
        with self.assertRaises(V.InputError) as caught:
            V.load_params(params)
        problems = " | ".join(caught.exception.problems)
        for text in ("'z_lens' must be a number", "'kwargs_source'", "whole number",
                     "both deltaPix and delta_pix"):
            self.assertIn(text, problems)


class CodeCheckTests(unittest.TestCase):
    def test_exact_match_passes(self) -> None:
        comp = _compare(_program(GOOD))
        self.assertTrue(comp["passed"], comp["messages"])
        self.assertIn("kwargs_lens[0].theta_E", comp["matched"])
        self.assertIn("numPix", comp["matched"])
        self.assertIn("psf_fwhm", comp["matched"])

    def test_example_script_matches_example_params(self) -> None:
        code = (SKILL / "assets" / "example_simulation.py").read_text(encoding="utf-8")
        comp = _compare(code)
        self.assertTrue(comp["passed"], comp["messages"])

    def test_diverged_field_reports_both_values(self) -> None:
        tampered = _good()
        tampered["kwargs_lens"][0]["theta_E"] = 2.5
        comp = _compare(_program(tampered))
        self.assertFalse(comp["passed"])
        diverged = {d["field"]: d for d in comp["diverged"]}
        self.assertEqual(diverged["kwargs_lens[0].theta_E"]["expected"], 1.0)
        self.assertEqual(diverged["kwargs_lens[0].theta_E"]["actual"], 2.5)

    def test_missing_block_reported(self) -> None:
        program = "".join(
            line + "\n" for line in _program(GOOD).splitlines()
            if not line.startswith(("kwargs_lens", "psf_class"))
        )
        comp = _compare(program)
        self.assertFalse(comp["passed"])
        self.assertIn("kwargs_lens", comp["missing"])
        self.assertIn("psf_fwhm", comp["missing"])

    def test_unresolved_value_does_not_pass(self) -> None:
        program = _program(GOOD).replace(
            "kwargs_lens = [{'theta_E': 1.0,",
            "theta_E = compute_einstein_radius()\nkwargs_lens = [{'theta_E': theta_E,",
        )
        comp = _compare(program)
        self.assertFalse(comp["passed"])
        self.assertIn("kwargs_lens[0].theta_E", comp["unresolved"])
        self.assertTrue(any("cannot be verified" in m for m in comp["messages"]))

    def test_resolution_through_names_expressions_and_subscripts(self) -> None:
        program = (
            "numPix = 64\n"
            "deltaPix = 0.08\n"
            "cfg = {'background_rms': 1e-2, 'fwhm': 0.15}\n"
            "t_exp = 54 * 10**2\n"
            "kwargs_data = data_configure_simple(numPix, deltaPix, "
            "exposure_time=t_exp, background_rms=cfg['background_rms'])\n"
            "lens_model_list = ['SIE']\n"
            "kwargs_lens = [{'theta_E': 1.0, 'e1': 0.1, 'e2': 0.0, "
            "'center_x': 0.0, 'center_y': 0.0}]\n"
            "source_model_list = ['SERSIC_ELLIPSE']\n"
            "kwargs_source = [{'amp': 12.0, 'R_sersic': 0.3, 'n_sersic': 1.5, "
            "'e1': 0.1, 'e2': -0.0, 'center_x': 0.05, 'center_y': 0.05}]\n"
            "psf_class = PSF(psf_type='GAUSSIAN', fwhm=cfg['fwhm'], pixel_size=deltaPix)\n"
        )
        comp = _compare(program)
        self.assertTrue(comp["passed"], comp["messages"])
        for field in ("exposure_time", "background_rms", "psf_fwhm"):
            self.assertIn(field, comp["matched"])

    def test_unparseable_script(self) -> None:
        comp = _compare("kwargs_lens = [\n")
        self.assertFalse(comp["passed"])
        self.assertEqual(comp["missing"], ["<script>"])


class CodeCheckRegressionTests(unittest.TestCase):
    def test_assignments_are_read_in_source_order(self) -> None:
        # ast.walk is breadth-first, so a correct kwargs_lens nested in a block
        # used to win over a later, wrong top-level reassignment.
        wrong = copy.deepcopy(GOOD["kwargs_lens"])
        wrong[0]["theta_E"] = 2.5
        program = _program(GOOD).replace(
            f"kwargs_lens = {GOOD['kwargs_lens']!r}\n",
            f"if True:\n    kwargs_lens = {GOOD['kwargs_lens']!r}\nkwargs_lens = {wrong!r}\n",
        )
        comp = _compare(program)
        self.assertFalse(comp["passed"])
        diverged = {d["field"]: d["actual"] for d in comp["diverged"]}
        self.assertEqual(diverged.get("kwargs_lens[0].theta_E"), 2.5)

    def test_grid_size_may_be_passed_by_keyword_in_either_spelling(self) -> None:
        # lenstronomy 1.9.2 names the arguments numPix/deltaPix, 1.14 num_pix/delta_pix.
        base = "".join(line + "\n" for line in _program(GOOD).splitlines()
                       if not line.startswith(("numPix", "deltaPix")))
        base = base.replace("pixel_size=deltaPix", "pixel_size=0.08")  # deltaPix is no longer a name
        call = ("kwargs_data = data_configure_simple({n}=64, {d}=0.08, "
                "exposure_time=exposure_time, background_rms=background_rms)\n")
        for n, d in (("numPix", "deltaPix"), ("num_pix", "delta_pix")):
            with self.subTest(spelling=n):
                comp = _compare(base + call.format(n=n, d=d))
                self.assertTrue(comp["passed"], comp["messages"])
                self.assertIn("numPix", comp["matched"])
                wrong = _compare(base + call.format(n=n, d=d).replace("=64", "=128"))
                self.assertIn("numPix", [x["field"] for x in wrong["diverged"]])

    def test_the_kwargs_passed_to_image_are_the_ones_checked(self) -> None:
        # A correct kwargs_lens that is defined but not rendered must not pass.
        wrong = copy.deepcopy(GOOD["kwargs_lens"])
        wrong[0]["theta_E"] = 2.5
        base = _program(GOOD) + f"kwargs_lens_render = {wrong!r}\n"
        for call in ("image_model.image(kwargs_lens=kwargs_lens_render, kwargs_source=kwargs_source)",
                     "image_model.image(kwargs_lens_render, kwargs_source)"):
            with self.subTest(call=call):
                comp = _compare(base + f"image = {call}\n")
                self.assertFalse(comp["passed"])
                diverged = {d["field"]: d["actual"] for d in comp["diverged"]}
                self.assertEqual(diverged.get("kwargs_lens[0].theta_E"), 2.5)

        comp = _compare(_program(GOOD) + "image = image_model.image(kwargs_lens=make_lens(), "
                        "kwargs_source=kwargs_source)\n")
        self.assertIn("kwargs_lens", comp["unresolved"])

    def _example(self) -> str:
        return (SKILL / "assets" / "example_simulation.py").read_text(encoding="utf-8")

    def test_dict_unpacking_is_applied_in_order(self) -> None:
        lens = 'kwargs_lens = [{"theta_E": 1.0,'
        comp = _compare(self._example().replace(lens, 'kwargs_lens = [{"theta_E": 1.0, **{"theta_E": 2.5},'))
        self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]}, {"kwargs_lens[0].theta_E": 2.5})

        comp = _compare(self._example().replace(lens, 'key = pick()\nkwargs_lens = [{key: 2.5, "theta_E": 1.0,'))
        self.assertIn("kwargs_lens[0]", comp["unresolved"])

        base = 'base = {"e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}\n'
        comp = _compare(self._example().replace(
            'kwargs_lens = [{"theta_E": 1.0, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]',
            base + 'kwargs_lens = [{**base, "theta_E": 1.0}]'))
        self.assertTrue(comp["passed"], comp["messages"])

    def test_code_that_does_not_run_does_not_count(self) -> None:
        wrong = 'kwargs_lens = [{"theta_E": 2.5, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]\n'
        lens = 'kwargs_lens = [{"theta_E": 1.0'
        for wrapper in ("if False:\n    ", "def unused():\n    "):
            with self.subTest(wrapper=wrapper.split(":")[0]):
                comp = _compare(self._example().replace(lens, wrong + wrapper + lens))
                diverged = {d["field"]: d["actual"] for d in comp["diverged"]}
                self.assertEqual(diverged.get("kwargs_lens[0].theta_E"), 2.5)

        # A branch that depends on runtime values: either kwargs_lens may be rendered.
        comp = _compare(self._example().replace(lens, wrong + "if len(sys.argv) > 2:\n    " + lens))
        self.assertIn("kwargs_lens", comp["unresolved"])

        # A function counts where it is called, here under the __main__ guard.
        code = self._example()
        head, body = code.split("numPix = 64")
        body = "".join(f"    {line}\n" if line.strip() else "\n" for line in ("numPix = 64" + body).splitlines())
        script = head + "def main():\n" + body + "\nif __name__ == '__main__':\n    main()\n"
        self.assertTrue(_compare(script)["passed"], _compare(script)["messages"])
        self.assertIn("kwargs_lens", _compare(script.replace("    main()", "    pass"))["missing"])

    def test_code_after_return_or_exit_does_not_count(self) -> None:
        call = "image = image_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source)"
        wrong = 'wrong = [{"theta_E": 2.5, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]\n'
        render = ("def render():\n"
                  "    image = image_model.image(kwargs_lens=wrong, kwargs_source=kwargs_source)\n"
                  "    return image\n"
                  "    image = image_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source)\n"
                  "image = render()")
        exits = ("image = image_model.image(kwargs_lens=wrong, kwargs_source=kwargs_source)\n"
                 "sys.exit(0)\n" + call)
        for name, replacement in (("return", render), ("sys.exit", exits)):
            with self.subTest(after=name):
                comp = _compare(self._example().replace(call, wrong + replacement))
                self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]}, {"kwargs_lens[0].theta_E": 2.5})

        # A path that raises renders nothing, so a guard does not make the result unresolved,
        # and sys.exit(main()) still runs main().
        guarded = self._example().replace(call, 'if len(sys.argv) > 5:\n    raise SystemExit("usage")\n' + call)
        self.assertTrue(_compare(guarded)["passed"], _compare(guarded)["messages"])
        head, body = self._example().split("numPix = 64")
        body = "".join(f"    {line}\n" if line.strip() else "\n" for line in ("numPix = 64" + body).splitlines())
        script = head + "def main():\n" + body + "    return 0\n\nif __name__ == '__main__':\n    sys.exit(main())\n"
        self.assertTrue(_compare(script)["passed"], _compare(script)["messages"])

        # A break ends the loop body: the assignment after it never runs.
        looped = self._example().replace(call, "for _ in range(3):\n    break\n    " + wrong + call)
        self.assertTrue(_compare(looped)["passed"], _compare(looped)["messages"])

    def test_the_model_classes_built_outrank_list_assignments(self) -> None:
        comp = _compare(self._example().replace(
            "LensModel(lens_model_list=lens_model_list)", "LensModel(lens_model_list=['SIS'])"))
        self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]}, {"lens_model_list": ["SIS"]})

        # The LightModel given to ImageModel as the source is the one checked, even when a
        # lens-light LightModel is built too; the lens light itself is not in the parameter set,
        # so it is reported.
        code = self._example().replace(
            "image_model = ImageModel(", "lens_light = LightModel(light_model_list=['SERSIC'])\n"
            "image_model = ImageModel(").replace(
            "kwargs_numerics=", "lens_light_model_class=lens_light, kwargs_numerics=")
        comp = _compare(code)
        self.assertIn("source_model_list", comp["matched"])
        self.assertEqual([(d["field"], d["expected"]) for d in comp["diverged"]],
                         [("ImageModel.lens_light_model_class", None)])

    def test_an_argument_the_check_cannot_follow_is_unresolved(self) -> None:
        # The expected PSF and LensModel are built, but ImageModel is given something else.
        for old, new, field in (
            ("    psf_class,\n    lens_model_class", "    get_psf(),\n    lens_model_class", "psf_fwhm"),
            ("lens_model_class=LensModel(lens_model_list=lens_model_list)",
             "lens_model_class=make_lens_model(LensModel(lens_model_list=lens_model_list))", "lens_model_list"),
        ):
            with self.subTest(field=field):
                comp = _compare(self._example().replace(old, new))
                self.assertIn(field, comp["unresolved"])

        # The ImageModel that renders cannot be identified: the one built earlier is not assumed.
        call = "image = image_model.image("
        comp = _compare(self._example().replace(call, "image_model = choose_image_model()\n" + call))
        for field in ("lens_model_list", "source_model_list", "psf_type"):
            self.assertIn(field, comp["unresolved"])

    def test_the_grid_is_read_from_the_imagedata_that_renders(self) -> None:
        config = "kwargs_data = sim_util.data_configure_simple(\n    numPix, deltaPix, exposure_time=5400.0, background_rms=0.01\n)"
        self.assertIn(config, self._example())
        used_128 = config.replace("numPix, deltaPix", "128, deltaPix")
        unused_64 = "\ndata_class = ImageData(**kwargs_data)\nunused = sim_util.data_configure_simple(64, 0.08)"
        code = self._example().replace(config, used_128).replace("\ndata_class = ImageData(**kwargs_data)", unused_64)
        self.assertEqual({d["field"]: d["actual"] for d in _compare(code)["diverged"]}, {"numPix": 128})

        # An ImageData the check cannot follow leaves the grid unresolved.
        code = self._example().replace("ImageData(**kwargs_data)", "ImageData(image_data=np.zeros((64, 64)))")
        self.assertIn("numPix", _compare(code)["unresolved"])

    def test_an_explicit_none_is_kept(self) -> None:
        # The assignments match, but data_configure_simple is passed None, which lenstronomy uses.
        code = _program(GOOD) + ("kwargs_data = data_configure_simple(numPix, deltaPix, "
                                 "exposure_time=None, background_rms=None)\n")
        comp = _compare(code)
        self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]},
                         {"exposure_time": None, "background_rms": None})
        # Left out, they default to None in lenstronomy too.
        comp = _compare(_program(GOOD) + "kwargs_data = data_configure_simple(numPix, deltaPix)\n")
        self.assertEqual({d["field"] for d in comp["diverged"]}, {"exposure_time", "background_rms"})

    def test_annotated_and_augmented_assignments_are_followed(self) -> None:
        grid = "numPix = 64\n"
        for added, expected in (("numPix: int = 128\n", {"numPix": 128}),
                                ("numPix += 64\n", {"numPix": 128})):
            with self.subTest(added=added.strip()):
                comp = _compare(self._example().replace(grid, grid + added))
                self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]}, expected)
        comp = _compare(self._example().replace(grid, grid + "numPix //= 1\n"))  # not folded: unresolved
        self.assertIn("numPix", comp["unresolved"])
        self.assertTrue(_compare(self._example().replace(grid, "numPix: int = 64\n"))["passed"])

    def test_arguments_left_out_of_image_are_missing(self) -> None:
        call = "image_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source)"
        comp = _compare(self._example().replace(call, "image_model.image(kwargs_lens=kwargs_lens)"))
        self.assertEqual(comp["missing"], ["kwargs_source"])
        comp = _compare(self._example().replace(call, "image_model.image()"))
        self.assertEqual(comp["missing"], ["kwargs_lens", "kwargs_source"])

    def test_psf_type_and_pixel_size_are_compared(self) -> None:
        psf = 'PSF(psf_type="GAUSSIAN", fwhm=0.15, pixel_size=deltaPix)'
        for changed, field, actual in (
            ('PSF(psf_type="NONE", fwhm=0.15, pixel_size=deltaPix)', "psf_type", "NONE"),
            ("PSF(fwhm=0.15, pixel_size=deltaPix)", "psf_type", "NONE"),  # lenstronomy's default
            ('PSF(psf_type="GAUSSIAN", fwhm=0.15, pixel_size=0.05)', "psf_pixel_size", 0.05),
        ):
            with self.subTest(psf=changed):
                comp = _compare(self._example().replace(psf, changed))
                self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]}, {field: actual})
        comp = _compare(self._example())
        self.assertIn("psf_type", comp["matched"])
        self.assertIn("psf_pixel_size", comp["matched"])

    def test_a_nonzero_value_never_matches_zero(self) -> None:
        # The tolerance was an absolute 1e-6 below 1, so a validated Gaussian sigma=1e-7 matched
        # a script's sigma=0, an invalid zero-width source.
        params = _good(source_model_list=["GAUSSIAN"],
                       kwargs_source=[{"amp": 12.0, "sigma": 1e-7, "center_x": 0.05, "center_y": 0.05}])
        self.assertTrue(_validate(params, "general")["passed"])
        for script_sigma, verdict in (("0", "diverged"), ("0.0", "diverged"), ("2e-7", "diverged"),
                                      ("-1e-7", "diverged"), ("1e-7", "matched"),
                                      ("1.0000001e-7", "matched"), ("10**400", "diverged")):
            with self.subTest(sigma=script_sigma):
                program = _program(params).replace("'sigma': 1e-07", f"'sigma': {script_sigma}")
                comp = _compare(program, params)
                fields = comp["matched"] if verdict == "matched" else [d["field"] for d in comp["diverged"]]
                self.assertIn("kwargs_source[0].sigma", fields)
                self.assertEqual(comp["passed"], verdict == "matched")
        self.assertTrue(C._numbers_match(0.0, 0))
        self.assertTrue(C._numbers_match(0.0, -0.0))
        self.assertFalse(C._numbers_match(0.0, 1e-300))
        self.assertTrue(C._numbers_match(5400.0, 5400.000001))

    def test_a_noiseless_parameter_set_is_compared_too(self) -> None:
        # A null exposure_time/background_rms means noiseless; the check skipped them, so the
        # example's noisy 5400 s / 0.01 configuration passed against a noiseless parameter set.
        for data in ({"numPix": 64, "deltaPix": 0.08, "exposure_time": None, "background_rms": None},
                     {"numPix": 64, "deltaPix": 0.08}):
            with self.subTest(kwargs_data=data):
                params = _good(kwargs_data=data)
                comp = _compare(EXAMPLE, params)
                self.assertEqual({d["field"]: (d["expected"], d["actual"]) for d in comp["diverged"]},
                                 {"exposure_time": (None, 5400.0), "background_rms": (None, 0.01)})
                noiseless = EXAMPLE.replace("numPix, deltaPix, exposure_time=5400.0, background_rms=0.01",
                                            "numPix, deltaPix")
                comp = _compare(noiseless, params)
                self.assertTrue(comp["passed"], comp["messages"])
                self.assertIn("exposure_time", comp["matched"])

    def test_an_omitted_psf_type_is_gaussian_as_in_the_validator(self) -> None:
        # The validator reads a kwargs_psf without psf_type as GAUSSIAN; the check skipped the
        # comparison, so PSF(psf_type="NONE") passed.
        params = _good(kwargs_psf={"fwhm": 0.15, "pixel_size": 0.08})
        self.assertTrue(_validate(params, "general")["passed"])
        psf = 'PSF(psf_type="GAUSSIAN", fwhm=0.15, pixel_size=deltaPix)'
        comp = _compare(EXAMPLE.replace(psf, 'PSF(psf_type="NONE", fwhm=0.15, pixel_size=deltaPix)'), params)
        self.assertEqual(comp["diverged"], [{"field": "psf_type", "expected": "GAUSSIAN", "actual": "NONE"}])
        self.assertIn("psf_type", _compare(EXAMPLE, params)["matched"])

    RENDER = "image = image_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source)"

    def _before_render(self, code: str) -> dict:
        self.assertIn(self.RENDER, EXAMPLE)
        return _compare(EXAMPLE.replace(self.RENDER, code + "\n" + self.RENDER))

    def test_in_place_edits_before_the_render_are_unresolved(self) -> None:
        # The review's case: this line before the render used to pass with theta_E "matched".
        comp = self._before_render('kwargs_lens[0]["theta_E"] = 2.5')
        self.assertFalse(comp["passed"])
        self.assertEqual(comp["unresolved"], ["kwargs_lens[0].theta_E"])
        self.assertIn("kwargs_lens[0].e1", comp["matched"])  # only the edited value

        edits = {
            "augmented": ('kwargs_lens[0]["theta_E"] += 1.5', "kwargs_lens[0].theta_E"),
            "del": ('del kwargs_lens[0]["theta_E"]', "kwargs_lens[0].theta_E"),
            "update keyword": ("kwargs_lens[0].update(theta_E=2.5)", "kwargs_lens[0].theta_E"),
            "update dict": ('kwargs_lens[0].update({"theta_E": 2.5})', "kwargs_lens[0].theta_E"),
            "setdefault": ('kwargs_lens[0].setdefault("theta_E", 2.5)', "kwargs_lens[0].theta_E"),
            "pop": ('kwargs_lens[0].pop("theta_E")', "kwargs_lens[0].theta_E"),
            "update unknown": ("kwargs_lens[0].update(load_overrides())", "kwargs_lens[0]"),
            "item replaced": ('kwargs_lens[0] = {"theta_E": 2.5}', "kwargs_lens[0]"),
            "append": ('kwargs_lens.append({"theta_E": 2.5})', "kwargs_lens"),
            "list +=": ('kwargs_lens += [{"theta_E": 2.5}]', "kwargs_lens"),
            "clear": ("kwargs_source[0].clear()", "kwargs_source[0]"),
            "scaled": ('kwargs_source[0]["amp"] *= 2', "kwargs_source[0].amp"),
            "through an alias": ('lens = kwargs_lens[0]\nlens["theta_E"] = 2.5', "kwargs_lens[0].theta_E"),
            "through a loop variable": ('for kw in kwargs_lens:\n    kw["theta_E"] = 2.5', "kwargs_lens[0].theta_E"),
            "through an iterator": ('for kw in iter(kwargs_lens):\n    kw["theta_E"] = 2.5', "kwargs_lens"),
            "in a function": ('def tweak(k):\n    k[0]["theta_E"] = 2.5\ntweak(kwargs_lens)',
                              "kwargs_lens[0].theta_E"),
            "by a call the check does not follow": ("tweak(kwargs_lens)", "kwargs_lens"),
            "attribute of the PSF": ("psf_class.fwhm = 0.3", "psf_fwhm"),
        }
        for name, (code, field) in edits.items():
            with self.subTest(name):
                comp = self._before_render(code)
                self.assertFalse(comp["passed"])
                self.assertIn(field, comp["unresolved"])
                self.assertFalse([m for m in comp["matched"] if m.startswith(field + ".")
                                  or m == field])

    def test_edits_that_cannot_change_the_render_still_pass(self) -> None:
        after = EXAMPLE.replace(self.RENDER, self.RENDER + '\nkwargs_lens[0]["theta_E"] = 2.5')
        self.assertTrue(_compare(after)["passed"], _compare(after)["messages"])  # rendered already
        for code in ('other = {"a": 1}\nother["a"] = 2', "print(kwargs_lens)",
                     "for kw in kwargs_lens:\n    print(kw)", "np.random.seed(0)",
                     'json.dumps(kwargs_lens)', 'kwargs_lens[0].get("theta_E")'):
            with self.subTest(code):
                comp = self._before_render(code)
                self.assertTrue(comp["passed"], comp["messages"])

    def test_operands_python_skips_do_not_count(self) -> None:
        # A wrong render, then a correct one Python never evaluates: the check used to visit
        # every call in the expression, so the skipped render overwrote the real one.
        wrong = ('wrong = [{"theta_E": 2.5, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]\n'
                 "image = image_model.image(kwargs_lens=wrong, kwargs_source=kwargs_source)\n")
        good = "image_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source)"
        for skipped in (f"False and {good}", f"x = {good} if False else None", f"True or {good}",
                        f"x = None if True else {good}", f"x = 1 > 2 > {good}", f"x = 0 or 1 or {good}"):
            with self.subTest(skipped):
                comp = _compare(EXAMPLE.replace(self.RENDER, wrong + skipped))
                self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]},
                                 {"kwargs_lens[0].theta_E": 2.5})
        # An operand that may or may not run leaves either render possible.
        for maybe in (f"flag = len(sys.argv) > 1\nflag and {good}", f"x = {good} if sys.argv else None"):
            with self.subTest(maybe):
                comp = _compare(EXAMPLE.replace(self.RENDER, wrong + maybe))
                self.assertIn("kwargs_lens", comp["unresolved"])
        # The side that runs still counts.
        comp = _compare(EXAMPLE.replace(self.RENDER, wrong + f"x = None if False else {good}"))
        self.assertTrue(comp["passed"], comp["messages"])

    def test_a_loop_else_runs_only_without_a_break(self) -> None:
        # The loop's else block was applied even after a break, so an else that assigns the
        # expected kwargs certified a render of the wrong ones.
        lens = 'kwargs_lens = [{"theta_E": 1.0, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]'
        wrong = lens.replace('"theta_E": 1.0', '"theta_E": 2.5')
        self.assertIn(lens, EXAMPLE)
        for loop in ("while True:\n    break", "for _ in range(3):\n    break",
                     "for _ in sys.argv:\n    break", "while len(sys.argv) > 1:\n    break"):
            with self.subTest(loop):
                code = EXAMPLE.replace(lens, wrong + "\n" + loop + "\nelse:\n    " + lens)
                comp = _compare(code)
                diverged = {d["field"]: d["actual"] for d in comp["diverged"]}
                if "sys.argv" in loop:  # may run zero times, so the else may run: either value
                    self.assertIn("kwargs_lens", comp["unresolved"])
                else:
                    self.assertEqual(diverged, {"kwargs_lens[0].theta_E": 2.5})
        # Without a break (a continue does not count) the else runs.
        for loop in ("for _ in range(2):\n    continue", "for _ in []:\n    pass", "while False:\n    pass"):
            with self.subTest(loop):
                comp = _compare(EXAMPLE.replace(lens, wrong + "\n" + loop + "\nelse:\n    " + lens))
                self.assertTrue(comp["passed"], comp["messages"])
        # `while True` without a break never ends, so the wrong render after it never runs.
        comp = _compare(EXAMPLE.replace(self.RENDER, self.RENDER + "\nwhile True:\n    pass\n" + wrong
                                        + "\nimage = image_model.image(kwargs_lens=kwargs_lens, "
                                        "kwargs_source=kwargs_source)"))
        self.assertTrue(comp["passed"], comp["messages"])

    def test_an_except_handler_may_start_anywhere_in_the_try_body(self) -> None:
        # Bad kwargs, an exception, then good kwargs: the handler sees the bad ones, but the
        # check joined only the states before and after the whole body, which both had good ones.
        lens = 'kwargs_lens = [{"theta_E": 1.0, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]'
        wrong = lens.replace('"theta_E": 1.0', '"theta_E": 2.5')
        indent = lambda code: "".join(f"    {line}\n" for line in code.splitlines())
        cases = {
            "in the body": (lens, lens + "\ntry:\n" + indent(wrong + "\n1 / 0\n" + lens)
                            + "except ZeroDivisionError:\n    pass", "kwargs_lens"),
            "a number in the body": ("numPix = 64\n", "numPix = 64\ntry:\n    numPix = 128\n    1 / 0\n"
                                     "    numPix = 64\nexcept ZeroDivisionError:\n    pass\n", "numPix"),
            "in a function it calls": (
                self.RENDER, self.RENDER + "\ndef risky():\n" + indent(
                    wrong + "\nimage_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source)"
                    "\nmaybe_fail()\n" + lens + "\n" + self.RENDER)
                + "try:\n    risky()\nexcept Exception:\n    pass", "kwargs_lens"),
            "a global set in a function": (
                "numPix = 64\n", "numPix = 64\ndef setup():\n    global numPix\n    numPix = 128\n"
                "    maybe_fail()\n    numPix = 64\ntry:\n    setup()\nexcept Exception:\n    pass\n", "numPix"),
        }
        for name, (old, new, field) in cases.items():
            with self.subTest(name):
                self.assertIn(old, EXAMPLE)
                comp = _compare(EXAMPLE.replace(old, new, 1))
                self.assertIn(field, comp["unresolved"])
        # A handler that re-raises or exits ends its path, so it does not matter.
        guarded = EXAMPLE.replace(lens, "try:\n    " + lens + "\nexcept Exception:\n    raise")
        self.assertTrue(_compare(guarded)["passed"], _compare(guarded)["messages"])

    def test_finally_runs_on_the_paths_that_leave_its_try(self) -> None:
        # A return inside try used to be saved before finally ran, so a render in finally was
        # missing from the returned path and the earlier, expected render was certified.
        wrong = 'wrong = [{"theta_E": 2.5, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]\n'
        render = "image_model.image(kwargs_lens={}, kwargs_source=kwargs_source)"
        cases = {
            "return": ("def render():\n    try:\n        return " + render.format("kwargs_lens")
                       + "\n    finally:\n        " + render.format("wrong") + "\nimage = render()"),
            "break": ("while True:\n    try:\n        " + render.format("kwargs_lens")
                      + "\n        break\n    finally:\n        " + render.format("wrong")),
            "sys.exit()": ("try:\n    " + render.format("kwargs_lens") + "\n    sys.exit(0)\nfinally:\n    "
                           + render.format("wrong")),
            "sys.exit() in a function": ("def main():\n    " + render.format("kwargs_lens")
                                         + "\n    sys.exit(0)\ntry:\n    main()\nfinally:\n    "
                                         + render.format("wrong")),
        }
        for name, code in cases.items():
            with self.subTest(name):
                comp = _compare(EXAMPLE.replace(self.RENDER, wrong + code))
                self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]},
                                 {"kwargs_lens[0].theta_E": 2.5}, comp["messages"])
        # A return in finally swallows an exception from anywhere in the try: either render may
        # be the last one, where the check used to drop the path that raised.
        code = ("def render():\n    try:\n        " + render.format("wrong") + "\n        raise RuntimeError"
                "\n    finally:\n        return\n" + render.format("kwargs_lens") + "\nrender()")
        self.assertIn("kwargs_lens", _compare(EXAMPLE.replace(self.RENDER, wrong + code))["unresolved"])
        # A finally that does not render leaves the result alone.
        code = "def render():\n    try:\n        return " + render.format("kwargs_lens") + "\n    finally:\n" \
               "        print('done')\nimage = render()"
        self.assertTrue(_compare(EXAMPLE.replace(self.RENDER, code))["passed"])

    def test_a_function_reads_the_names_of_the_scope_it_is_defined_in(self) -> None:
        # Functions were run with their caller's names, so render() reading the wrong global
        # kwargs_lens passed when its caller had a local kwargs_lens with the expected values.
        lens = 'kwargs_lens = [{"theta_E": 1.0, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]'
        wrong = lens.replace('"theta_E": 1.0', '"theta_E": 2.5')
        render = "image_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source)"
        global_render = ("def render():\n    return " + render + "\n"
                         "def main():\n    " + lens + "\n    render()\nmain()")
        comp = _compare(EXAMPLE.replace(self.RENDER, wrong + "\n" + global_render))
        self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]}, {"kwargs_lens[0].theta_E": 2.5})

        # A nested function sees the call that defines it, and a local function shadows a global one.
        closure = ("def render():\n    " + render.replace("kwargs_lens=kwargs_lens", "kwargs_lens=[]") + "\n"
                   "def main():\n    " + lens + "\n    def render():\n        " + render + "\n    render()\nmain()")
        comp = _compare(EXAMPLE.replace(self.RENDER, wrong + "\n" + closure))
        self.assertTrue(comp["passed"], comp["messages"])

        # A name a function assigns is local throughout it, even before the assignment.
        unbound = "def main():\n    " + render + "\n    " + lens + "\nmain()"
        comp = _compare(EXAMPLE.replace(self.RENDER, unbound))
        self.assertIn("kwargs_lens", comp["unresolved"])

    def test_default_arguments_are_evaluated_when_the_function_is_defined(self) -> None:
        # Defaults were resolved with the names at the call, so rebinding default_lens to the
        # expected kwargs after `def render(actual=default_lens)` certified the wrong default.
        wrong = '[{"theta_E": 2.5, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]'
        render = "image_model.image(kwargs_lens=actual, kwargs_source=kwargs_source)"
        code = (f"default_lens = {wrong}\ndef render(actual=default_lens):\n    {render}\n"
                "default_lens = kwargs_lens\nrender()")
        comp = _compare(EXAMPLE.replace(self.RENDER, code))
        self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]}, {"kwargs_lens[0].theta_E": 2.5})
        comp = _compare(EXAMPLE.replace(self.RENDER, code.replace("render()", "render(kwargs_lens)")))
        self.assertTrue(comp["passed"], comp["messages"])

        # A default list is one object shared by every call: an edit in one call is seen by the next.
        good = '[{"theta_E": 1.0, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]'
        shared = f"def render(actual={good}):\n    {render}\n    actual[0]['theta_E'] = 2.5\nrender()"
        self.assertTrue(_compare(EXAMPLE.replace(self.RENDER, shared))["passed"])  # edited after rendering
        comp = _compare(EXAMPLE.replace(self.RENDER, shared + "\nrender()"))
        self.assertEqual(comp["unresolved"], ["kwargs_lens[0].theta_E"])

    def test_pixel_psf_kernels_are_compared(self) -> None:
        # kernel_point_source was not followed, so any kernel, or one computed at runtime,
        # passed against a PIXEL parameter set.
        kernel = [[0.0, 0.1, 0.0], [0.1, 0.6, 0.1], [0.0, 0.1, 0.0]]
        params = _good(kwargs_psf={"psf_type": "PIXEL", "pixel_size": 0.08, "kernel_point_source": kernel})
        self.assertTrue(_validate(params, "general")["passed"])
        psf = 'PSF(psf_type="GAUSSIAN", fwhm=0.15, pixel_size=deltaPix)'
        pixel = 'PSF(psf_type="PIXEL", kernel_point_source={}, pixel_size=deltaPix)'
        other = [[0.0, 0.2, 0.0], [0.2, 0.2, 0.2], [0.0, 0.2, 0.0]]
        for written, verdict in ((repr(kernel), "matched"), (f"np.array({kernel!r})", "matched"),
                                 (repr(other), "diverged"), (repr(kernel[:2]), "diverged"),
                                 ("np.ones((3, 3)) / 9", "unresolved"), ("make_kernel()", "unresolved")):
            with self.subTest(kernel=written):
                comp = _compare(EXAMPLE.replace(psf, pixel.format(written)), params)
                fields = {"matched": comp["matched"], "unresolved": comp["unresolved"],
                          "diverged": [d["field"] for d in comp["diverged"]]}[verdict]
                self.assertIn("psf_kernel", fields)
                self.assertEqual(comp["passed"], verdict == "matched")
        comp = _compare(EXAMPLE.replace(psf, 'PSF(psf_type="PIXEL", pixel_size=deltaPix)'), params)
        self.assertEqual([d["field"] for d in comp["diverged"]], ["psf_kernel"])  # no kernel at all

    def test_the_text_of_the_unresolved_marker_is_an_ordinary_string(self) -> None:
        # The marker for an unknown value was the string "<unresolved>", so a script passing that
        # text was treated as unknown, and len() of an unknown value was 12.
        psf = 'PSF(psf_type="GAUSSIAN", fwhm=0.15, pixel_size=deltaPix)'
        comp = _compare(EXAMPLE.replace(psf, psf.replace('"GAUSSIAN"', '"<unresolved>"')))
        self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]}, {"psf_type": "<unresolved>"})
        comp = _compare(EXAMPLE.replace("numPix = 64", "numPix = 64 if len(sys.argv) == 12 else 128"))
        self.assertIn("numPix", comp["unresolved"])

    def test_redshifts_given_to_lens_model_are_compared(self) -> None:
        # The loader dropped z_lens and z_source, so a multi-plane LensModel at redshifts 0.9
        # and 3.0 passed against a parameter set at 0.5 and 1.0.
        lens = "LensModel(lens_model_list=lens_model_list)"
        self.assertIn(lens, EXAMPLE)
        multi = "LensModel(lens_model_list=lens_model_list, lens_redshift_list={}, z_source={}, multi_plane=True)"
        comp = _compare(EXAMPLE.replace(lens, multi.format("[0.9]", "3.0")))
        self.assertFalse(comp["passed"])
        self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]},
                         {"lens_redshift_list": [0.9], "z_source": 3.0})

        cases = {
            multi.format("[0.5]", "1.0"): ("matched", ["lens_redshift_list", "z_source"]),
            multi.format("[0.5]", "get_z()"): ("unresolved", ["z_source"]),
            "LensModel(lens_model_list, 0.5, 1.0)": ("matched", ["z_lens", "z_source"]),
            "LensModel(lens_model_list=lens_model_list, z_lens=0.4, z_source=1.0)": ("diverged", ["z_lens"]),
            "LensModel(lens_model_list=lens_model_list, z_source_convention=2.0)": ("diverged", ["z_source_convention"]),
            "LensModel(lens_model_list=lens_model_list, multi_plane=True)": ("missing", ["lens_redshift_list", "z_source"]),
            "LensModel(lens_model_list=lens_model_list, multi_plane=flag)": ("unresolved", ["multi_plane"]),
            "LensModel(lens_model_list=lens_model_list, **options)": ("unresolved", ["z_source", "z_source_convention"]),
        }
        for changed, (verdict, fields) in cases.items():
            with self.subTest(changed):
                comp = _compare(EXAMPLE.replace(lens, changed))
                listed = [d["field"] for d in comp["diverged"]] if verdict == "diverged" else comp[verdict]
                for field in fields:
                    self.assertIn(field, listed)
                self.assertEqual(comp["passed"], verdict == "matched", comp["messages"])
        self.assertTrue(_compare(EXAMPLE)["passed"])  # single plane, no redshifts given

    def test_profile_keys_the_parameter_set_leaves_out_are_checked(self) -> None:
        # Only the parameter set's keys were compared, so a script passing center_x=100 passed
        # against a parameter set that leaves center_x at lenstronomy's default of 0.
        params = _good()
        del params["kwargs_lens"][0]["center_x"], params["kwargs_lens"][0]["center_y"]
        self.assertTrue(_validate(params, "general")["passed"])
        lens = '"center_x": 0.0, "center_y": 0.0}]'
        self.assertIn(lens, EXAMPLE)
        comp = _compare(EXAMPLE.replace(lens, '"center_x": 100.0, "center_y": 0.0}]'), params)
        self.assertEqual(comp["diverged"], [{"field": "kwargs_lens[0].center_x", "expected": 0.0, "actual": 100.0}])
        self.assertIn("kwargs_lens[0].center_y", comp["matched"])  # 0, the default
        self.assertTrue(_compare(EXAMPLE, params)["passed"])

        del params["kwargs_source"][0]["center_x"]  # the example's source is at 0.05, not the default
        self.assertEqual([d["field"] for d in _compare(EXAMPLE, params)["diverged"]], ["kwargs_source[0].center_x"])

        # A key the profile does not take, and an extra profile entry, are reported too.
        comp = _compare(EXAMPLE.replace('"theta_E": 1.0,', '"theta_E": 1.0, "theta_e": 1.0,'))
        self.assertEqual([d["field"] for d in comp["diverged"]], ["kwargs_lens[0].theta_e"])
        self.assertTrue(any("not in the parameter set" in m for m in comp["messages"]))
        comp = _compare(EXAMPLE.replace(lens, lens[:-1] + ', {"theta_E": 0.1, "e1": 0.0, "e2": 0.0}]'))
        self.assertEqual([d["field"] for d in comp["diverged"]], ["kwargs_lens[1]"])

    def test_lenstronomy_arguments_the_parameter_set_does_not_describe(self) -> None:
        # Arguments outside the parameter set were ignored, so unconvolved=True, a shifted grid
        # or a truncated PSF passed. Each must be lenstronomy's default, which the parameter set
        # assumes; numerics and likelihood-only arguments are allowed.
        cases = {
            ("image_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source)",
             "image_model.image(kwargs_lens=kwargs_lens, kwargs_source=kwargs_source, unconvolved=True)"):
                ("image.unconvolved", False),
            ("fwhm=0.15, pixel_size=deltaPix)", "fwhm=0.15, pixel_size=deltaPix, truncation=3)"):
                ("PSF.truncation", 5),
            ("numPix, deltaPix, exposure_time", "numPix, deltaPix, center_ra=1.0, exposure_time"):
                ("data_configure_simple.center_ra", 0),
            ("ImageData(**kwargs_data)", "ImageData(**kwargs_data, ra_shift=0.5)"): ("ImageData.ra_shift", 0),
            ("LensModel(lens_model_list=lens_model_list)",
             "LensModel(lens_model_list=lens_model_list, decouple_multi_plane=True)"):
                ("LensModel.decouple_multi_plane", False),
            ("LightModel(light_model_list=source_model_list)",
             "LightModel(light_model_list=source_model_list, surprise=1)"): ("LightModel.surprise", C._NOT_IN_PARAMS),
        }
        for (old, new), (field, expected) in cases.items():
            with self.subTest(field):
                self.assertIn(old, EXAMPLE)
                comp = _compare(EXAMPLE.replace(old, new))
                self.assertEqual([(d["field"], d["expected"]) for d in comp["diverged"]], [(field, expected)])
        for old, new in (("fwhm=0.15, pixel_size=deltaPix)", "fwhm=0.15, pixel_size=deltaPix, truncation=5)"),
                         ('{"supersampling_factor": 1}', '{"supersampling_factor": 3}')):
            with self.subTest(new):
                self.assertTrue(_compare(EXAMPLE.replace(old, new))["passed"])  # the default; numerics
        comp = _compare(EXAMPLE.replace("fwhm=0.15, pixel_size=deltaPix)", "fwhm=0.15, pixel_size=deltaPix, truncation=t)"))
        self.assertIn("PSF.truncation", comp["unresolved"])

    def test_code_the_check_cannot_follow_leaves_everything_unresolved(self) -> None:
        # The script's own code that runs at a time the check cannot know (a callback, a
        # decorator, a lambda, a generator, a method, recursion) and code that changes Python or
        # lenstronomy itself can render or edit anything, so nothing can be certified.
        wrong = 'wrong = [{"theta_E": 2.5, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]\n'
        bad = "image_model.image(kwargs_lens=wrong, kwargs_source=kwargs_source)"
        cases = {
            "a callback": f"def late():\n    {bad}\natexit.register(late)",
            "a returned closure": f"def make():\n    def render():\n        {bad}\n    return render\nmake()()",
            "a decorator": f"@register\ndef render():\n    {bad}",
            "a lambda": f"render = lambda: {bad}\nrender()",
            "a generator kept for later": f"later = ({bad} for _ in range(1))\nlist(later)",
            "a generator function": f"def frames():\n    yield {bad}\nfor _ in frames():\n    pass",
            "a method": f"class Sim:\n    def run(self):\n        {bad}\nSim().run()",
            "recursion": f"def again(n):\n    if n:\n        again(n - 1)\n    {bad}\nagain(2)",
            "exec": f"exec({bad!r})",
            "globals()": "globals()['kwargs_lens'] = wrong",
            "patching lenstronomy": "sim_util.data_configure_simple = lambda *a, **k: {}",
            "patching numpy": "np.exp = abs",
            "setattr on lenstronomy": "setattr(sim_util, 'data_configure_simple', None)",
            "mock.patch": "unittest.mock.patch('lenstronomy.ImSim.image_model.ImageModel.image').start()",
        }
        for name, code in cases.items():
            with self.subTest(name):
                comp = _compare(EXAMPLE.replace(self.RENDER, wrong + code + "\n" + self.RENDER))
                self.assertFalse(comp["passed"])
                self.assertIn("kwargs_lens", comp["unresolved"])
                self.assertTrue(comp["messages"][0].startswith("The check cannot follow this script"))

        # Their harmless forms still pass.
        for code in ("order = sorted(kwargs_lens, key=lambda kw: kw['theta_E'])",
                     "class Config:\n    def __init__(self, n):\n        self.n = n\nConfig(1)",
                     "def pairs():\n    yield 1\nfor _ in pairs():\n    pass",
                     "total = sum(kw['theta_E'] for kw in kwargs_lens)",
                     "plt.rcParams['font.size'] = 12"):
            with self.subTest(code):
                comp = _compare(EXAMPLE.replace(self.RENDER, code + "\n" + self.RENDER))
                self.assertTrue(comp["passed"], comp["messages"])

    def test_exit_status_names_imports_and_context_managers(self) -> None:
        render = "image_model.image(kwargs_lens={}, kwargs_source=kwargs_source)"
        wrong = 'wrong = [{"theta_E": 2.5, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]\n'
        # sys.exit(1) is a failed run, like a raise, so a guard around the render that exits does
        # not leave it unresolved; raise SystemExit(0) is a successful end, like sys.exit(0).
        guarded = EXAMPLE.replace(self.RENDER, "try:\n    " + self.RENDER
                                  + "\nexcept Exception as exc:\n    print(exc)\n    sys.exit(1)")
        self.assertTrue(_compare(guarded)["passed"], _compare(guarded)["messages"])
        code = wrong + render.format("wrong") + "\nraise SystemExit(0)\n" + self.RENDER
        comp = _compare(EXAMPLE.replace(self.RENDER, code))
        self.assertEqual({d["field"]: d["actual"] for d in comp["diverged"]}, {"kwargs_lens[0].theta_E": 2.5})

        # A name the script defines or imports from elsewhere is not lenstronomy's, nor a builtin.
        psf = 'psf_class = PSF(psf_type="GAUSSIAN", fwhm=0.15, pixel_size=deltaPix)'
        for prelude, field in (("def PSF(**kwargs):\n    return None\n", "psf_type"),
                               ("from mylib import PSF\n", "psf_type"),
                               ("from mylib import *\n", "psf_type")):  # it may rebind any name
            with self.subTest(prelude):
                comp = _compare(EXAMPLE.replace(psf, prelude + psf))
                self.assertFalse(comp["passed"])
                self.assertIn(field, comp["unresolved"] + comp["missing"])
        code = "def exit():\n    pass\nexit()\n" + self.RENDER  # the script's own exit() does not end it
        self.assertTrue(_compare(EXAMPLE.replace(self.RENDER, code))["passed"])
        comp = _compare(EXAMPLE.replace(self.RENDER, "from mylib import print\nprint(kwargs_lens)\n" + self.RENDER))
        self.assertIn("kwargs_lens", comp["unresolved"])  # not the builtin, so it may change its argument

        # Imports inside a function stay modules.
        code = EXAMPLE.split('"""\n', 1)[1]  # everything after the docstring, imports included
        indented = "".join(f"    {line}\n" for line in code.splitlines())
        comp = _compare("def main():\n" + indented + "\nmain()\n")
        self.assertTrue(comp["passed"], comp["messages"])

        # A context manager that may swallow an exception leaves what its block did unresolved.
        code = (wrong + "with contextlib.suppress(Exception):\n    " + render.format("wrong")
                + "\n    maybe_fail()\n    " + render.format("kwargs_lens"))
        self.assertIn("kwargs_lens", _compare(EXAMPLE.replace(self.RENDER, code))["unresolved"])
        code = "with open('log.txt', 'w') as log:\n    " + self.RENDER
        self.assertTrue(_compare(EXAMPLE.replace(self.RENDER, code))["passed"])

        # A *expansion of unknown length leaves the positions of the items after it unknown.
        comp = _compare(EXAMPLE.replace("kwargs_lens = [{", "kwargs_lens = [*extra, {"))
        self.assertIn("kwargs_lens", comp["unresolved"])

    def test_scripts_python_would_reject_or_that_nest_too_deep(self) -> None:
        comp = _compare(EXAMPLE + "\nreturn 1\n")
        self.assertEqual(comp["missing"], ["<script>"])
        self.assertIn("not parseable", comp["messages"][0])
        comp = _compare(EXAMPLE.replace("numPix = 64", "numPix = " + "1 + " * 20000 + "1"))
        self.assertFalse(comp["passed"])

    def test_an_import_replaces_the_value_a_name_had(self) -> None:
        # The review's case: an import only recorded the module, so deltaPix kept 0.08 and
        # passed although Python hands pi to both builders.
        grid = "deltaPix = 0.08\n"
        for name, code in (("from-import", "from math import pi as deltaPix\n"),
                           ("import as", "import math as deltaPix\n"),
                           ("in a function, into a global",
                            "def load():\n    global deltaPix\n    from math import pi as deltaPix\nload()\n")):
            with self.subTest(name):
                comp = _compare(EXAMPLE.replace(grid, grid + code))
                self.assertFalse(comp["passed"])
                self.assertEqual(comp["unresolved"], ["deltaPix", "psf_pixel_size"])
        # The fallback to a conventional name's assignment, used when nothing renders, too.
        comp = _compare(EXAMPLE.replace(self.RENDER, "from config import kwargs_lens"))
        self.assertIn("kwargs_lens", comp["unresolved"])
        # Imports of names the script has not bound are modules, as before.
        comp = _compare(EXAMPLE.replace(grid, grid + "import numpy as np\nfrom math import pi\n"))
        self.assertTrue(comp["passed"], comp["messages"])

    def test_match_guards_run_before_their_case(self) -> None:
        # The review's case: guards were never evaluated, so a walrus in one rebound the lens
        # kwargs unseen. A false guard's effects also reach the cases after it.
        wrong = 'wrong = [{"theta_E": 2.5, "e1": 0.1, "e2": 0.0, "center_x": 0.0, "center_y": 0.0}]\n'
        for name, code in (("walrus in a guard", wrong + "match 0:\n    case _ if (kwargs_lens := wrong):\n        pass"),
                           ("edit in a false guard", "match 0:\n    case _ if kwargs_lens[0].update(theta_E=2.5):\n"
                                                     "        pass\n    case _:\n        pass")):
            with self.subTest(name):
                comp = self._before_render(code)
                self.assertFalse(comp["passed"])
                self.assertIn("kwargs_lens", comp["unresolved"])
        code = "match numPix:\n    case 64 if numPix > 0:\n        print('ok')\n    case [first] if first:\n        pass"
        self.assertTrue(self._before_render(code)["passed"])  # a guard without effects

class CommandLineTests(unittest.TestCase):
    def _run(self, *args: str, stdin: str | None = None) -> tuple[int, dict]:
        completed = subprocess.run(
            [sys.executable, *args], input=stdin, capture_output=True, text=True, check=False
        )
        return completed.returncode, json.loads(completed.stdout)

    def test_validate_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.json"
            good.write_text(json.dumps(GOOD), encoding="utf-8")
            bad = Path(tmp) / "bad.json"
            bad.write_text(json.dumps(_good(z_lens=2.0)), encoding="utf-8")
            broken = Path(tmp) / "broken.json"
            broken.write_text("{not json", encoding="utf-8")

            code, report = self._run(str(VALIDATE), str(good))
            self.assertEqual((code, report["passed"], report["preset"]), (0, True, "general"))
            code, report = self._run(str(VALIDATE), str(bad), "--preset", "deeplense")
            self.assertEqual((code, report["passed"]), (1, False))
            code, report = self._run(str(VALIDATE), str(broken))
            self.assertEqual(code, 2)
            self.assertIn("error", report)
            code, report = self._run(str(VALIDATE), str(good), "--set", "bogus=1")
            self.assertEqual(code, 2)

    def test_validate_reads_stdin_and_reports_schema_problems(self) -> None:
        code, report = self._run(str(VALIDATE), "-", stdin=json.dumps({"z_lens": 0.5}))
        self.assertEqual(code, 1)
        self.assertEqual(report["checks"], {"schema": False})
        self.assertTrue(report["messages"])

    def test_check_exit_codes(self) -> None:
        example = SKILL / "assets" / "example_simulation.py"
        params = SKILL / "assets" / "example_params.json"
        code, report = self._run(str(CHECK), str(example), str(params))
        self.assertEqual((code, report["passed"]), (0, True))
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "sim.py"
            script.write_text(_program(GOOD).replace("'theta_E': 1.0", "'theta_E': 3.0"),
                              encoding="utf-8")
            code, report = self._run(str(CHECK), str(script), str(params))
            self.assertEqual((code, report["passed"]), (1, False))
            code, report = self._run(str(CHECK), str(script), str(Path(tmp) / "missing.json"))
            self.assertEqual(code, 2)

    def test_check_reports_a_malformed_parameter_set_as_json(self) -> None:
        # kwargs_lens: [1] used to raise AttributeError with a traceback.
        malformed = {
            "kwargs_lens: [1]": {"kwargs_lens": [1]},
            "kwargs_lens not a list": {"kwargs_lens": {"theta_E": 1.0}},
            "string value": {"kwargs_source": [{"amp": "12"}]},
            "nested list in kwargs": {"kwargs_source": [[12.0]]},
            "model name not a string": {"lens_model_list": [1]},
            "kwargs_data not an object": {"kwargs_data": [64, 0.08]},
            "numPix not a number": {"kwargs_data": {"numPix": "64", "deltaPix": 0.08}},
            "kwargs_psf not an object": {"kwargs_psf": ["GAUSSIAN"]},
            "ragged kernel": {"kwargs_psf": {"psf_type": "PIXEL", "kernel_point_source": [[1.0], [1.0, 2.0]]}},
            "missing z_source": {"z_source": None},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "params.json"
            for name, change in malformed.items():
                with self.subTest(name):
                    params = {k: v for k, v in _good(**change).items() if v is not None}
                    path.write_text(json.dumps(params), encoding="utf-8")
                    completed = subprocess.run([sys.executable, str(CHECK), str(SKILL / "assets" / "example_simulation.py"),
                                                str(path)], capture_output=True, text=True, check=False)
                    self.assertEqual(completed.returncode, 2, completed.stderr)
                    self.assertEqual(completed.stderr, "")
                    self.assertTrue(json.loads(completed.stdout)["error"].startswith("malformed parameter set"))
            path.write_text("[]", encoding="utf-8")
            code, report = self._run(str(CHECK), str(SKILL / "assets" / "example_simulation.py"), str(path))
            self.assertEqual(code, 2)
            self.assertIn("JSON object", report["error"])


if __name__ == "__main__":
    unittest.main()
