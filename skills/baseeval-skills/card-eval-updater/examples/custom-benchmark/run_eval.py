#!/usr/bin/env python3
"""Run the custom benchmark against the custom model.

`--include_path` registers custom *tasks*, but a custom *model* has to be
imported before lm-eval builds its registry. This wrapper does that import and
then hands off to the ordinary lm-eval CLI, so every flag below is stock
lm-evaluation-harness and the output layout is the standard one.

    python3 run_eval.py [extra lm_eval flags...]
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "models"))

# The task YAML declares `data_files: data/beamline_qa.jsonl`, which HuggingFace
# datasets resolves against the current working directory, not against the YAML.
# Without this the example only runs from its own directory.
os.chdir(HERE)

import lexical_overlap  # noqa: F401,E402  - registers the "lexical-overlap" model
from lm_eval.__main__ import cli_evaluate  # noqa: E402

DEFAULT_ARGS = [
    "--model",
    "lexical-overlap",
    "--include_path",
    str(HERE / "tasks"),
    "--tasks",
    "beamline_qa",
    "--log_samples",
    "--output_path",
    str(HERE / "results" / "beamline_qa"),
]

if __name__ == "__main__":
    sys.argv = [sys.argv[0]] + (sys.argv[1:] or DEFAULT_ARGS)
    cli_evaluate()
