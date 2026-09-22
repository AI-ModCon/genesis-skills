"""Smoke tests for the repository policy validator."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.skill_fixtures import write_skill, write_text
from tools.repo_inventory import build_readme_contributor_names, build_readme_tree_lines


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate_repo_policy.py"


def _write_valid_fixture(root: Path) -> None:
    write_text(root / "LICENSE", "Root license placeholder\n")
    write_text(
        root / "CONTRIBUTING.md",
        "\n".join(
            [
                "AI/LLM-assisted contributions are permitted when the author reviews and validates the result.",
                "For AI/LLM-assisted contributions, see [Guidelines for AI/LLM-Assisted Contributions](#guidelines-for-ai-llm-assisted-contributions) below.",
                "",
                "### Guidelines for AI/LLM-Assisted Contributions",
                "",
                "Placeholder policy text.",
                "",
            ]
        ),
    )
    write_text(root / "CODE_OF_CONDUCT.md", "Code of conduct placeholder\n")
    write_text(
        root / "NOTICE",
        "\n".join(
            [
                "Known third-party subtrees:",
                "",
                "  skills/amsc-skills/ATTRIBUTION.md",
                "  skills/basedata-skills/ATTRIBUTION.md",
                "  skills/baseeval-skills/LICENSE",
                "  skills/basesim-skills/LICENSE",
                "",
            ]
        ),
    )
    write_text(root / "docs" / "getting_started.md", "# Getting Started\n")
    write_text(root / "unpack.sh", "#!/usr/bin/env bash\n")
    write_skill(root / "skill-search", description="Discover the catalog of bundled skills")
    write_text(root / "skill-search" / "scripts" / "skill_search.py", "print('skill-search')\n")
    write_skill(root / "skills" / "academy", description="Academy skill")
    write_text(
        root / "skills" / "amsc-skills" / "ATTRIBUTION.md",
        "\n".join(
            [
                "# Attribution",
                "",
                "The skills in this directory were sourced from the **American Science Cloud Intelligent Interfaces Team**.",
                "",
                "**Source repository:** https://gitlab.com/amsc2/ai-services/intelligent-interfaces/agent-skills",
                "",
                "**Team:** American Science Cloud Intelligent Interfaces Team",
                "",
            ]
        ),
    )
    write_skill(root / "skills" / "amsc-skills" / "amsc-python-client", description="AmSC Python client skill")
    write_skill(root / "skills" / "amsc-skills" / "iri-api", description="IRI API skill")
    write_text(
        root / "skills" / "basedata-skills" / "ATTRIBUTION.md",
        "\n".join(
            [
                "# Attribution",
                "",
                "The skills in this directory were sourced from the **ModCon Base Data** project.",
                "",
                "**Original repository:** https://github.com/AI-ModCon/BaseData_Skills",
                "",
                "**Team:** ModCon Base Data (AI-ModCon): Shreyas Cholia (LBNL) [Lead], Jean Luca Bez (LBNL), Jong Choi (ORNL), Rohith Varikoti (PNNL), Kyle Parfrey (PPPL), Andrew Tritt (LBNL), Aaron Tuor (PNNL)",
                "",
            ]
        ),
    )
    write_skill(root / "skills" / "basedata-skills" / "croissant-validator", description="Croissant validation skill")
    write_skill(root / "skills" / "basedata-skills" / "skill-creator", description="Skill authoring helper")
    write_text(root / "skills" / "baseeval-skills" / "LICENSE", "Apache-2.0 license placeholder\n")
    write_text(
        root / "skills" / "baseeval-skills" / "README.md",
        "\n".join(
            [
                "# BaseEval Skills",
                "",
                "Agent skills for language-model evaluation workflows. The `skills/baseeval-skills/` subtree is licensed Apache-2.0; see [`LICENSE`](LICENSE).",
                "See [`lm-eval-harness-skills/ATTRIBUTION.md`](lm-eval-harness-skills/ATTRIBUTION.md).",
                "See [`perlmutter-ns-skills/ATTRIBUTION.md`](perlmutter-ns-skills/ATTRIBUTION.md).",
                "",
            ]
        ),
    )
    write_skill(root / "skills" / "baseeval-skills" / "card-eval-updater", description="Evaluation run to model card updater")
    write_text(
        root / "skills" / "baseeval-skills" / "lm-eval-harness-skills" / "ATTRIBUTION.md",
        "\n".join(
            [
                "# Attribution",
                "",
                "**Author:** Emily Saldanha, Pacific Northwest National Laboratory (PNNL)",
                "",
            ]
        ),
    )
    write_skill(
        root / "skills" / "baseeval-skills" / "lm-eval-harness-skills" / "configuration-creator",
        description="Create evaluation configurations",
    )
    write_text(
        root / "skills" / "baseeval-skills" / "perlmutter-ns-skills" / "ATTRIBUTION.md",
        "\n".join(
            [
                "# Attribution",
                "",
                "**Authors:**",
                "- Fernando Llorente, Brookhaven National Laboratory (BNL)",
                "- Eric Chagnon, Lawrence Berkeley National Laboratory (LBNL)",
                "",
            ]
        ),
    )
    write_skill(
        root / "skills" / "baseeval-skills" / "perlmutter-ns-skills" / "perlmutter-nemo-eval",
        description="Run NeMo-Skills evaluation on Perlmutter",
    )
    write_text(
        root / "skills" / "basesafe-skills" / "readme.md",
        "\n".join(
            [
                "Reusable AI / agentic \"skills\" for the safe development of frontier AI/ML models and agentic systems.",
                "",
                "# Attribution",
                "",
                "The ModCon BaseSafe Team:",
                "| Name              | Institution   |",
                "|-------------------|---------------|",
                "| Robin Cosbey      | PNNL          |",
                "| David Florey      | PNNL          |",
                "| Steven Goldenberg | JLab          |",
                "| Nathan Hodas      | PNNL          |",
                "| Natalie Isenberg  | PNNL          |",
                "| Olivera Kotevska  | ORNL          |",
                "| Reilly Raab       | PNNL          |",
                "| Malachi Schram    | PNNL          |",
                "",
            ]
        ),
    )
    write_skill(root / "skills" / "basesafe-skills" / "ai-fingerprint", description="AI fingerprinting skill")
    write_skill(root / "skills" / "basesafe-skills" / "uq-metrics-evaluator", description="UQ metrics evaluator")
    write_text(root / "skills" / "basesim-skills" / "LICENSE", "Apache-2.0 license placeholder\n")
    write_text(
        root / "skills" / "basesim-skills" / "README.md",
        "\n".join(
            [
                "# BaseSim Skills",
                "",
                "Agent skills for the apeiron continual-learning framework. The `skills/basesim-skills/` subtree is licensed Apache-2.0; see [`LICENSE`](LICENSE).",
                "See [`ATTRIBUTION.md`](ATTRIBUTION.md).",
                "",
            ]
        ),
    )
    write_text(
        root / "skills" / "basesim-skills" / "ATTRIBUTION.md",
        "\n".join(
            [
                "# Attribution",
                "",
                "The skills in this directory were sourced from the **BaseSim Framework (APEIRON)** project.",
                "",
                "**Original repository:** https://github.com/AI-ModCon/BaseSIM_APEIRON",
                "",
                "**Authors:**",
                "- Andrew Ayres, Oak Ridge National Laboratory (ORNL)",
                "- Ana Gainaru, Los Alamos National Laboratory (LANL)",
                "- Anna Quach, Idaho National Laboratory (INL)",
                "- Krishnan Raghavan, Argonne National Laboratory (ANL)",
                "- Alvaro Sanchez-Villar, Princeton Plasma Physics Laboratory (PPPL)",
                "- Rafael Zamora-Resendiz, Lawrence Berkeley National Laboratory (LBNL)",
                "",
            ]
        ),
    )
    write_skill(root / "skills" / "basesim-skills" / "install-apeiron", description="Install apeiron into a project")
    write_skill(
        root / "skills" / "basesim-skills" / "apeiron-choose-detector",
        description="Recommend and configure an apeiron drift detector",
    )
    write_skill(root / "skills" / "hpc-skills" / "aurora", description="Aurora HPC skill")
    write_skill(root / "skills" / "hpc-skills" / "slurm", description="Slurm HPC skill")
    write_skill(root / "skills" / "literature-search", description="Literature search skill")
    write_skill(root / "skills" / "multi-agent-systems", description="Multi-agent systems skill")
    write_skill(root / "skills" / "plasma-sim-skills" / "gs2", description="GS2 plasma simulation skill")
    write_skill(root / "skills" / "plasma-sim-skills" / "gkeyll", description="Gkeyll plasma simulation skill")

    tree = "\n".join(build_readme_tree_lines(root))
    contributors = "\n".join(f"- {name}" for name in build_readme_contributor_names(root))
    write_text(
        root / "README.md",
        "\n".join(
            [
                "# Genesis Skills",
                "",
                "## Repository Structure",
                "",
                "```",
                tree,
                "```",
                "",
                "## Contributors",
                "",
                "Individual skills and their directories contain specific attribution details. The catalog-level and skill contributors include the following:",
                "",
                contributors,
                "",
                "## License",
                "This product is licensed under the root [LICENSE](LICENSE) found at the root of this repository.",
                "Some skills under `skills/` are sourced from third parties. Where a `LICENSE` (or `LICENSE.txt`) file is present in a subdirectory, that license governs the contents of that subdirectory and supersedes the root license for that subtree.",
                "The repository-level summary of individual skill and third-party licensing details is in [NOTICE](NOTICE); see the attribution file in each identified subtree for the licensing information supplied with that content.",
                "",
                "## Acknowledgment",
                "This work was supported by the U.S. Department of Energy (DOE), Office of Science, Office of Advanced Scientific Computing Research in alignment with DOE's Genesis Mission.",
                "",
            ]
        ),
    )


class RepoPolicyValidatorTests(unittest.TestCase):
    def test_tree_inventory_discovers_new_skill_family(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_valid_fixture(root)
            write_skill(root / "skills" / "zeta-skills" / "alpha", description="Alpha skill")
            write_skill(root / "skills" / "zeta-skills" / "beta", description="Beta skill")

            tree_lines = build_readme_tree_lines(root)

            self.assertIn("│   └── zeta-skills/  # alpha, beta (2)", tree_lines)
            self.assertLess(tree_lines.index("│   └── zeta-skills/  # alpha, beta (2)"), tree_lines.index("├── CONTRIBUTING.md"))

    def test_validator_accepts_a_minimal_consistent_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_valid_fixture(root)

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("repo policy: OK", completed.stdout)

    def test_validator_reports_missing_readme_notice_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_valid_fixture(root)
            write_text(
                root / "README.md",
                "\n".join(
                    [
                        "# Genesis Skills",
                        "",
                        "See [LICENSE](LICENSE) only.",
                        "",
                    ]
                ),
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("README.md", completed.stdout)
            self.assertIn("NOTICE", completed.stdout)

    def test_validator_reports_missing_acknowledgment_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_valid_fixture(root)
            write_text(
                root / "README.md",
                "\n".join(
                    [
                        "# Genesis Skills",
                        "",
                        "See [LICENSE](LICENSE) and [NOTICE](NOTICE).",
                        "",
                    ]
                ),
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("README.md", completed.stdout)
            self.assertIn("Acknowledgment", completed.stdout)

    def test_validator_reports_missing_ai_assisted_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_valid_fixture(root)
            write_text(
                root / "CONTRIBUTING.md",
                "\n".join(
                    [
                        "AI/LLM-assisted contributions are permitted when the author reviews and validates the result.",
                        "",
                        "### Guidelines for AI/LLM-Assisted Contributions",
                        "",
                        "Placeholder policy text.",
                        "",
                    ]
                ),
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("CONTRIBUTING.md", completed.stdout)
            self.assertIn("Guidelines for AI/LLM-Assisted Contributions", completed.stdout)

    def test_validator_reports_stale_repository_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_valid_fixture(root)
            write_text(
                root / "README.md",
                (root / "README.md").read_text(encoding="utf-8").replace(
                    "└── skill_spec.md              # Agent Skills format specification\n",
                    "",
                ),
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("repository structure", completed.stdout)

    def test_validator_reports_stale_contributor_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            _write_valid_fixture(root)
            write_text(
                root / "README.md",
                (root / "README.md").read_text(encoding="utf-8").replace("- Jong Choi\n", ""),
            )

            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("contributors", completed.stdout)


if __name__ == "__main__":
    unittest.main()
