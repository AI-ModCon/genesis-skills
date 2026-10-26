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

    def test_snr_negative_amp_fails_instead_of_crashing(self) -> None:
        params = _good()
        params["kwargs_source"][0]["amp"] = -100.0
        res = _validate(params)
        self.assertFalse(res["checks"]["snr"])
        self.assertTrue(any("raise the source amp" in m for m in res["messages"]))

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


if __name__ == "__main__":
    unittest.main()
