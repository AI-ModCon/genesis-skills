"""Regression tests for card-eval-updater run selection."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "skills"
    / "baseeval-skills"
    / "card-eval-updater"
    / "scripts"
    / "parse_eval_results.py"
)

SPEC = importlib.util.spec_from_file_location("card_eval_parse", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class CardEvalRunSelectionTests(unittest.TestCase):
    def test_lm_eval_parent_with_two_runs_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            for name in ("run-a", "run-b"):
                write_json(
                    root / name / f"results_{name}.json",
                    {"lm_eval_version": "0.4.0"},
                )

            with self.assertRaisesRegex(PARSER.ParseError, "contains 2 valid"):
                PARSER.parse_lm_eval(root)

    def test_eval_factory_parent_with_two_run_roots_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            for run_name in ("run-a", "run-b"):
                artifacts = root / run_name / "task" / "artifacts"
                artifacts.mkdir(parents=True)
                (artifacts / "run_config.yml").write_text("framework_name: demo\n")

            with self.assertRaisesRegex(PARSER.ParseError, "from 2 Eval Factory runs"):
                PARSER.parse_eval_factory(root)

    def test_nemo_skills_parent_with_two_runs_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            payload = {"bench": {"pass@1": {"symbolic_correct": 50.0}}}
            write_json(root / "run-a" / "metrics.json", payload)
            write_json(root / "run-b" / "metrics.json", payload)

            with self.assertRaisesRegex(PARSER.ParseError, "contains 2 NeMo-Skills"):
                PARSER.parse_nemo_skills(root)

    def test_nemo_robust_eval_variant_metrics_count_as_one_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            aggregate = root / "metrics.json"
            detail = (
                root
                / "bench"
                / "variant-a"
                / "eval-results"
                / "bench"
                / "metrics.json"
            )
            write_json(
                aggregate,
                {
                    "bench": {
                        "variant-a": {"avg": 50.0},
                        "aggregated": {"avg": 50.0, "num_runs": 1},
                    }
                },
            )
            write_json(
                detail,
                {"bench": {"pass@1": {"symbolic_correct": 50.0}}},
            )

            self.assertEqual(PARSER._nemo_skills_files(root), [aggregate])

    def test_robust_aggregate_does_not_hide_unrelated_nested_eval_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            write_json(
                root / "metrics.json",
                {
                    "bench": {
                        "variant-a": {"avg": 50.0},
                        "aggregated": {"avg": 50.0, "num_runs": 1},
                    }
                },
            )
            write_json(
                root / "other-run" / "eval-results" / "bench" / "metrics.json",
                {"bench": {"pass@1": {"symbolic_correct": 60.0}}},
            )

            matches = PARSER._nemo_skills_files(root)
            self.assertEqual(len(matches), 2)

    def test_nemo_direct_aggregate_does_not_hide_nested_independent_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            write_json(
                root / "metrics.json",
                {"bench": {"pass@1": {"symbolic_correct": 50.0}}},
            )
            write_json(
                root / "nested-run" / "metrics.json",
                {"bench": {"pass@1": {"symbolic_correct": 60.0}}},
            )

            matches = PARSER._nemo_skills_files(root)
            self.assertEqual(len(matches), 2)
            with self.assertRaisesRegex(PARSER.ParseError, "contains 2 NeMo-Skills"):
                PARSER.parse_nemo_skills(root)


if __name__ == "__main__":
    unittest.main()
