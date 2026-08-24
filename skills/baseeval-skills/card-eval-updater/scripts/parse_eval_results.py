#!/usr/bin/env python3
"""Parse evaluation-harness output into a canonical eval bundle.

Supports three harnesses, auto-detected by signature:

  lm-evaluation-harness    results_<ISO>.json carrying a top-level lm_eval_version
  nemo-evaluator-launcher  a tree containing <task>/artifacts/results.yml
  nemo-skills              metrics.json from `ns eval` / `ns robust_eval`

Every number in the bundle is read directly out of a harness artifact and
carries the path it came from in `artifact_path`. Nothing here infers,
estimates, or reformulates a score.

Usage:
    parse_eval_results.py <path> [--model-id ID] [--allow-partial] [-o bundle.json]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    yaml = None

SCHEMA_VERSION = "1.0"

# Warnings raised mid-parse and attached to the bundle at the end.
_pending_warnings: list[str] = []

# Keys inside a NeMo-Skills metric block that describe the run rather than score it.
_NS_META_KEYS = {
    "num_entries",
    "avg_tokens",
    "gen_seconds",
    "no_answer",
    "min",
    "max",
    "avg",
    "std",
    "num_seeds",
    "num_runs",
    "prompt_sensitivity",
}


class ParseError(RuntimeError):
    """Raised when a path cannot be parsed as any known harness output."""


class PartialRunError(RuntimeError):
    """Raised when a run is limited/truncated and --allow-partial was not given."""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _read_yaml(path: Path) -> Any:
    if yaml is None:
        raise ParseError(f"pyyaml is required to read {path}")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _epoch_to_iso(value: Any) -> str | None:
    try:
        return (
            _dt.datetime.fromtimestamp(float(value), tz=_dt.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    """Coerce to str. YAML happily types an all-digit git hash as an int, and a
    bare `1.0` version as a float; the schema expects strings."""
    if value is None:
        return None
    return str(value)


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# Keys lm-eval derives a model name from (evaluation_tracker._get_model_name).
_LM_EVAL_NAME_KEYS = ("peft", "delta", "pretrained", "model", "path", "engine")
_RANDOM_NAME_RE = re.compile(r"^[a-z0-9]{8}$")

# lm-eval model *types* for which model_args genuinely identifies the weights.
# For any other type - notably a custom registered class - model_args is just
# ignored kwargs, and a leftover `pretrained=` from a wrapper script's defaults
# will silently name a model that never ran. Seen in the wild: running
# configuration-tester's test_config.sh with a custom model and no explicit
# model_args produced a results file naming mistralai/Mistral-7B-Instruct-v0.3.
_LM_EVAL_WEIGHT_BEARING_TYPES = {
    "hf",
    "hf-auto",
    "huggingface",
    "hf-multimodal",
    "hf-vlms",
    "hf-steered",
    "vllm",
    "vllm-vlm",
    "sglang",
    "sglang-generate",
    "gguf",
    "ggml",
    "nemo_lm",
    "mamba_ssm",
    "neuronx",
    "openvino",
    "ipex",
    "optimum-lm",
    "openai-completions",
    "openai-chat-completions",
    "local-completions",
    "local-chat-completions",
    "anthropic-completions",
    "anthropic-chat",
    "anthropic-chat-completions",
    "textsynth",
    "watsonx_llm",
    "ibm_watsonx_ai",
}


# `dataset_path` values that name a generic loader rather than a dataset. For
# these the real source is dataset_kwargs.data_files - the common shape for the
# custom tasks produced by the lm-eval-harness configuration skills.
_GENERIC_LOADERS = {"json", "csv", "parquet", "text", "arrow", "pandas", "generator"}


def _lm_eval_dataset_source(task_cfg: dict) -> str | None:
    """Resolve a task's data source, seeing through generic dataset loaders."""
    path = task_cfg.get("dataset_path")
    if path not in _GENERIC_LOADERS:
        return path
    data_files = (task_cfg.get("dataset_kwargs") or {}).get("data_files")
    if isinstance(data_files, dict):
        split = task_cfg.get("test_split") or "test"
        chosen = data_files.get(split) or next(iter(data_files.values()), None)
    else:
        chosen = data_files
    if isinstance(chosen, list):
        chosen = chosen[0] if chosen else None
    return str(chosen) if chosen else path


def _is_generated_model_name(name: Any, model_args: dict) -> bool:
    """True when lm-eval fell back to random_name_id() for the model name."""
    if not isinstance(name, str) or not _RANDOM_NAME_RE.match(name):
        return False
    return not any(key in (model_args or {}) for key in _LM_EVAL_NAME_KEYS)


def _blank_result() -> dict:
    """A result row with every optional field defaulted, so the schema always validates."""
    return {
        "benchmark": None,
        "variant": None,
        "task_yaml": None,
        "dataset_path": None,
        "dataset_name": None,
        "dataset_description": None,
        "metric": None,
        "value": None,
        "value_raw": None,
        "scale": "fraction",
        "stderr": None,
        "stddev": None,
        "higher_is_better": None,
        "num_fewshot": None,
        "num_samples": None,
        "num_samples_total": None,
        "is_partial": False,
        "temperature": None,
        "top_p": None,
        "max_new_tokens": None,
        "seeds": None,
        "num_runs": None,
        "prompt_sensitivity": None,
        "no_answer": None,
        "artifact_path": None,
    }


# --------------------------------------------------------------------------
# detection
# --------------------------------------------------------------------------


def _lm_eval_files(path: Path) -> list[Path]:
    """Return lm-eval results_*.json files under `path`, newest first."""
    if path.is_file():
        candidates = [path] if path.name.startswith("results_") else []
    else:
        candidates = sorted(path.rglob("results_*.json"))
    out = []
    for cand in candidates:
        try:
            data = _read_json(cand)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and "lm_eval_version" in data:
            out.append(cand)
    return sorted(out, key=lambda p: p.name, reverse=True)


def _eval_factory_tasks(path: Path) -> list[Path]:
    """Return Eval Factory task directories (those holding artifacts/run_config.yml)."""
    if path.is_file():
        path = path.parent
    seen: list[Path] = []
    for cfg in sorted(path.rglob("artifacts/run_config.yml")):
        seen.append(cfg.parent.parent)
    if (path / "artifacts" / "run_config.yml").exists() and path not in seen:
        seen.append(path)
    return seen


def _nemo_skills_file(path: Path) -> Path | None:
    """Return the top-level NeMo-Skills metrics.json, if this looks like one."""
    if path.is_file() and path.name == "metrics.json":
        candidates = [path]
    elif path.is_dir():
        direct = path / "metrics.json"
        candidates = [direct] if direct.exists() else sorted(path.rglob("metrics.json"))
    else:
        return None
    for cand in candidates:
        try:
            data = _read_json(cand)
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict) or "config" in data:
            continue  # `config` marks an Eval Factory metrics.json
        for block in data.values():
            if isinstance(block, dict) and any(isinstance(v, dict) for v in block.values()):
                return cand
    return None


def detect(path: Path) -> str:
    if _lm_eval_files(path):
        return "lm-evaluation-harness"
    if _eval_factory_tasks(path):
        return "nemo-evaluator-launcher"
    if _nemo_skills_file(path):
        return "nemo-skills"
    raise ParseError(
        f"{path} does not look like output from any supported harness "
        "(lm-evaluation-harness, nemo-evaluator-launcher, nemo-skills)."
    )


# --------------------------------------------------------------------------
# adapter: lm-evaluation-harness
# --------------------------------------------------------------------------


def parse_lm_eval(path: Path) -> dict:
    global _pending_warnings
    _pending_warnings = []
    files = _lm_eval_files(path)
    if not files:
        raise ParseError(f"no lm-evaluation-harness results_*.json under {path}")
    results_file = files[0]
    data = _read_json(results_file)

    cfg = data.get("config") or {}
    gen = cfg.get("gen_kwargs") or {}
    limit = cfg.get("limit")

    model_args = cfg.get("model_args") or {}
    if isinstance(model_args, str):  # older lm-eval serialises this as a string
        parsed = dict(kv.split("=", 1) for kv in model_args.split(",") if "=" in kv)
        model_args = parsed
    model_id = data.get("model_name") or model_args.get("pretrained")
    model_type = cfg.get("model")
    if model_id and model_type and model_type not in _LM_EVAL_WEIGHT_BEARING_TYPES:
        # A custom model class ran, so model_args did not select the weights and
        # the derived name cannot be trusted to describe what was evaluated.
        untrusted = model_id
        model_id = None
        _pending_warnings.append(
            f"lm-eval recorded model_name={untrusted!r}, but the model type was "
            f"{model_type!r} - a custom class for which model_args does not "
            "identify the weights. That name may be a leftover default naming a "
            "model that never ran, so it was discarded. Pass --model-id."
        )
    if _is_generated_model_name(model_id, model_args):
        # lm-eval derives model_name from peft/delta/pretrained/model/path/engine
        # in model_args and otherwise falls back to random_name_id() - 8 random
        # [a-z0-9] chars. Custom model classes with no model_args hit that path,
        # so the "name" is a per-run nonce. Writing it into a card as the model
        # identity would be worse than admitting we do not know.
        model_id = None

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "run_id": results_file.parent.name,
            "harness": "lm-evaluation-harness",
            "harness_version": data.get("lm_eval_version"),
            "framework": None,
            "git_hash": data.get("git_hash") or data.get("upper_git_hash"),
            "date": _epoch_to_iso(data.get("date")),
            "runtime_seconds": _as_float(data.get("total_evaluation_time_seconds")),
            "artifact_root": str(path.resolve()),
        },
        "model": {
            "id": model_id,
            "base_model": None,
            "num_parameters": _as_int(cfg.get("model_num_parameters")),
            "dtype": cfg.get("model_dtype"),
            "endpoint_url": model_args.get("base_url"),
            "api_type": None,
            "source": data.get("model_source") or cfg.get("model"),
            "id_provenance": "harness",
        },
        "compute": {
            "device": cfg.get("device"),
            "batch_size": cfg.get("batch_size"),
            "hardware_note": None,
        },
        "audit": {},
        "results": [],
    }

    if _pending_warnings:
        bundle.setdefault("_warnings", []).extend(_pending_warnings)

    judges = sorted(
        {
            p.name.split("_")[2]
            for p in results_file.parent.glob("llm_judge_*.jsonl")
            if len(p.name.split("_")) > 3
        }
    )
    if judges:
        bundle["audit"]["llm_judge_names"] = judges

    n_shot = data.get("n-shot") or {}
    n_samples = data.get("n-samples") or {}
    hib = data.get("higher_is_better") or {}
    configs = data.get("configs") or {}

    for task, block in (data.get("results") or {}).items():
        if not isinstance(block, dict):
            continue
        task_cfg = configs.get(task) or {}
        counts = n_samples.get(task) or {}
        effective = _as_int(counts.get("effective"))
        original = _as_int(counts.get("original"))
        partial = bool(limit is not None) or (
            effective is not None and original is not None and effective < original
        )

        for key, value in block.items():
            # keys look like "acc,none"; stderr arrives as a sibling "acc_stderr,none"
            if key == "alias" or not isinstance(value, (int, float)):
                continue
            name, _, filt = key.partition(",")
            if name.endswith("_stderr"):
                continue
            row = _blank_result()
            row.update(
                benchmark=task,
                metric=name,
                value=float(value),
                value_raw=float(value),
                scale="fraction",
                stderr=_as_float(block.get(f"{name}_stderr,{filt}")),
                higher_is_better=(hib.get(task) or {}).get(name),
                num_fewshot=_as_int(n_shot.get(task)),
                num_samples=effective,
                num_samples_total=original,
                is_partial=partial,
                dataset_path=_lm_eval_dataset_source(task_cfg),
                dataset_name=task_cfg.get("dataset_name"),
                dataset_description=(task_cfg.get("metadata") or {}).get("description"),
                temperature=_as_float(gen.get("temperature")),
                top_p=_as_float(gen.get("top_p")),
                max_new_tokens=_as_int(gen.get("max_gen_toks") or gen.get("max_new_tokens")),
                seeds=[
                    cfg[k]
                    for k in ("random_seed", "numpy_seed", "torch_seed")
                    if cfg.get(k) is not None
                ]
                or None,
                artifact_path=str(results_file),
            )
            bundle["results"].append(row)

    return bundle


# --------------------------------------------------------------------------
# adapter: nemo-evaluator-launcher (Eval Factory)
# --------------------------------------------------------------------------


def _walk_scores(metrics: dict) -> list[tuple[str, dict]]:
    """Flatten metrics.<M>.scores.<S> into (metric_name, score_block) pairs.

    The inner score key is NOT reliably the metric name: bigcode emits
    metrics.pass@1.scores.pass@1 while simple_evals emits
    metrics.score.scores.micro. Iterate generically.
    """
    out: list[tuple[str, dict]] = []
    for metric_name, metric_block in (metrics or {}).items():
        scores = (metric_block or {}).get("scores") or {}
        for score_key, score_block in scores.items():
            if not isinstance(score_block, dict):
                continue
            if score_key == metric_name or len(scores) == 1:
                label = metric_name
            else:
                label = f"{metric_name}[{score_key}]"
            out.append((label, score_block))
    return out


def parse_eval_factory(path: Path) -> dict:
    task_dirs = _eval_factory_tasks(path)
    if not task_dirs:
        raise ParseError(f"no Eval Factory task directories under {path}")

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "run_id": None,
            "harness": "nemo-evaluator-launcher",
            "harness_version": None,
            "framework": None,
            "git_hash": None,
            "date": None,
            "runtime_seconds": None,
            "artifact_root": str(path.resolve()),
        },
        "model": {
            "id": None,
            "base_model": None,
            "num_parameters": None,
            "dtype": None,
            "endpoint_url": None,
            "api_type": None,
            "source": None,
            "id_provenance": "harness",
        },
        "compute": {"device": None, "batch_size": None, "hardware_note": None},
        "audit": {},
        "results": [],
    }

    frameworks: set[str] = set()
    skipped: list[str] = []
    total_runtime = 0.0
    saw_runtime = False

    for task_dir in task_dirs:
        artifacts = task_dir / "artifacts"
        results_path = artifacts / "results.yml"
        run_config_path = artifacts / "run_config.yml"

        run_config = _read_yaml(run_config_path) if run_config_path.exists() else {}
        params = ((run_config.get("config") or {}).get("params")) or {}
        framework = _as_str(run_config.get("framework_name"))  # here, not in results.yml
        if framework:
            frameworks.add(framework)

        # Endpoint / model identity: run_config first, metadata.yaml as fallback.
        endpoint = ((run_config.get("target") or {}).get("api_endpoint")) or {}
        if not endpoint.get("model_id") and (artifacts / "metadata.yaml").exists():
            meta = _read_yaml(artifacts / "metadata.yaml") or {}
            endpoint = ((meta.get("launcher_resolved_config") or {}).get("target") or {}).get(
                "api_endpoint"
            ) or {}
        if endpoint.get("model_id") and not bundle["model"]["id"]:
            bundle["model"]["id"] = _as_str(endpoint.get("model_id"))
            bundle["model"]["endpoint_url"] = _as_str(endpoint.get("url"))
            bundle["model"]["api_type"] = _as_str(endpoint.get("type"))

        # Runtime + response statistics (auditing signal).
        efm_path = artifacts / "eval_factory_metrics.json"
        if efm_path.exists():
            efm = _read_json(efm_path)
            evaluation = efm.get("evaluation") or {}
            runtime = _as_float(evaluation.get("runtime_seconds"))
            if runtime is not None:
                total_runtime += runtime
                saw_runtime = True
            stats = efm.get("response_stats") or {}
            if stats:
                bundle["audit"].update(
                    {
                        k: v
                        for k, v in {
                            "avg_latency_ms": _as_float(stats.get("avg_latency_ms")),
                            "avg_completion_tokens": _as_float(stats.get("avg_completion_tokens")),
                            "finish_reason": stats.get("finish_reason") or None,
                            "status_codes": stats.get("status_codes") or None,
                            "successful_count": _as_int(stats.get("successful_count")),
                            "request_count": _as_int(stats.get("count")),
                        }.items()
                        if v is not None
                    }
                )

        if not results_path.exists():
            # Real and common: the task ran but scoring produced nothing.
            skipped.append(task_dir.name)
            continue

        results_yaml = _read_yaml(results_path) or {}
        versioning = ((results_yaml.get("metadata") or {}).get("versioning")) or {}
        bundle["run"]["harness_version"] = bundle["run"]["harness_version"] or _as_str(
            versioning.get("nemo_evaluator_launcher")
        )
        bundle["run"]["git_hash"] = bundle["run"]["git_hash"] or _as_str(
            results_yaml.get("git_hash")
        )
        if bundle["run"]["run_id"] is None:
            bundle["run"]["run_id"] = task_dir.parent.name

        limit_samples = _as_int(params.get("limit_samples"))
        tasks_block = (results_yaml.get("results") or {}).get("tasks") or {}

        for task_name, task_block in tasks_block.items():
            for metric_label, score_block in _walk_scores((task_block or {}).get("metrics") or {}):
                stats = score_block.get("stats") or {}
                value = _as_float(score_block.get("value"))
                if value is None:
                    continue
                # Eval Factory wraps 20+ harnesses. Most emit rates in [0,1], but
                # some emit perplexity, BLEU on 0-100, token counts or latency.
                # Presenting those as fractions would be a fabricated reading, so
                # they are marked 'raw' and rendered in the harness's own units.
                scale = "fraction" if 0.0 <= value <= 1.0 else "raw"
                row = _blank_result()
                row.update(
                    benchmark=task_name,
                    metric=metric_label,
                    value=value,
                    value_raw=value,
                    scale=scale,
                    stderr=_as_float(stats.get("stderr")),
                    stddev=_as_float(stats.get("stddev")),
                    num_samples=limit_samples,
                    is_partial=limit_samples is not None,
                    temperature=_as_float(params.get("temperature")),
                    top_p=_as_float(params.get("top_p")),
                    max_new_tokens=_as_int(params.get("max_new_tokens")),
                    artifact_path=str(results_path),
                )
                bundle["results"].append(row)

    if len(frameworks) == 1:
        bundle["run"]["framework"] = frameworks.pop()
    elif frameworks:
        bundle["run"]["framework"] = ", ".join(sorted(frameworks))
    if saw_runtime:
        bundle["run"]["runtime_seconds"] = total_runtime
    if skipped:
        bundle.setdefault("_warnings", []).extend(
            f"task '{name}' has no results.yml (scoring produced no output) - skipped"
            for name in skipped
        )
    if not bundle["results"]:
        raise ParseError(
            f"found Eval Factory task directories under {path} but none produced a "
            f"results.yml (skipped: {', '.join(skipped) or 'none'})"
        )
    return bundle


# --------------------------------------------------------------------------
# adapter: nemo-skills
# --------------------------------------------------------------------------


def _ns_metric_name(block: dict) -> str | None:
    """The scoring key inside a NeMo-Skills metric block (e.g. symbolic_correct)."""
    for key, value in block.items():
        if key in _NS_META_KEYS or key.endswith("_statistics"):
            continue
        if isinstance(value, (int, float)):
            return key
    return None


def _ns_recover_metric_name(root: Path, benchmark: str) -> str | None:
    """Recover the metric name from a per-variant metrics.json.

    The robust_eval aggregation records min/max/avg/std but drops the name of
    the thing being averaged. The per-variant files still carry it.
    """
    for cand in sorted(root.rglob("eval-results/*/metrics.json")):
        try:
            data = _read_json(cand)
        except (json.JSONDecodeError, OSError):
            continue
        block = data.get(benchmark)
        if not isinstance(block, dict):
            continue
        for mode_block in block.values():
            if isinstance(mode_block, dict):
                name = _ns_metric_name(mode_block)
                if name:
                    return name
    return None


def parse_nemo_skills(path: Path, model_id: str | None = None) -> dict:
    metrics_path = _nemo_skills_file(path)
    if metrics_path is None:
        raise ParseError(f"no NeMo-Skills metrics.json under {path}")
    data = _read_json(metrics_path)
    root = metrics_path.parent

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "run_id": root.name,
            "harness": "nemo-skills",
            "harness_version": None,
            "framework": None,
            "git_hash": None,
            "date": None,
            "runtime_seconds": None,
            "artifact_root": str(path.resolve()),
        },
        # NeMo-Skills records no model identity anywhere in its output.
        "model": {
            "id": model_id,
            "base_model": None,
            "num_parameters": None,
            "dtype": None,
            "endpoint_url": None,
            "api_type": None,
            "source": None,
            "id_provenance": "user" if model_id else "harness",
        },
        "compute": {"device": None, "batch_size": None, "hardware_note": None},
        "audit": {},
        "results": [],
    }

    for benchmark, block in data.items():
        if not isinstance(block, dict):
            continue
        is_robust = "aggregated" in block

        if is_robust:
            metric_name = _ns_recover_metric_name(root, benchmark) or "score"
            aggregated = block.get("aggregated") or {}
            for variant, vblock in block.items():
                if not isinstance(vblock, dict):
                    continue
                avg = _as_float(vblock.get("avg"))
                if avg is None:
                    continue
                is_agg = variant == "aggregated"
                row = _blank_result()
                row.update(
                    benchmark=benchmark,
                    variant=None if is_agg else variant,
                    metric=metric_name,
                    value=avg / 100.0,  # NeMo-Skills reports percentages
                    value_raw=avg,
                    scale="percent",
                    stddev=(_as_float(vblock.get("std")) or 0.0) / 100.0
                    if vblock.get("std") is not None
                    else None,
                    num_runs=_as_int(vblock.get("num_seeds") or vblock.get("num_runs")),
                    prompt_sensitivity=(
                        _as_float(aggregated.get("prompt_sensitivity")) if is_agg else None
                    ),
                    no_answer=(_as_float(vblock.get("no_answer")) or 0.0) / 100.0
                    if vblock.get("no_answer") is not None
                    else None,
                    higher_is_better=True,
                    artifact_path=str(metrics_path),
                )
                bundle["results"].append(row)
        else:
            for mode, mblock in block.items():
                if not isinstance(mblock, dict):
                    continue
                metric_name = _ns_metric_name(mblock)
                if metric_name is None:
                    continue
                raw = _as_float(mblock.get(metric_name))
                if raw is None:
                    continue
                label = metric_name if mode == "pass@1" else f"{metric_name}[{mode}]"
                row = _blank_result()
                row.update(
                    benchmark=benchmark,
                    metric=label,
                    value=raw / 100.0,
                    value_raw=raw,
                    scale="percent",
                    num_samples=_as_int(mblock.get("num_entries")),
                    no_answer=(_as_float(mblock.get("no_answer")) or 0.0) / 100.0
                    if mblock.get("no_answer") is not None
                    else None,
                    higher_is_better=True,
                    artifact_path=str(metrics_path),
                )
                bundle["results"].append(row)
                avg_tokens = _as_float(mblock.get("avg_tokens"))
                if avg_tokens is not None:
                    bundle["audit"].setdefault("avg_tokens", avg_tokens)

    if not bundle["results"]:
        raise ParseError(f"{metrics_path} contained no parseable metric blocks")

    no_answers = [r["no_answer"] for r in bundle["results"] if r["no_answer"] is not None]
    if no_answers:
        bundle["audit"].setdefault("no_answer_rate", max(no_answers))
    return bundle


# --------------------------------------------------------------------------
# top level
# --------------------------------------------------------------------------


def parse(path: Path, model_id: str | None = None, allow_partial: bool = False) -> dict:
    harness = detect(path)
    if harness == "lm-evaluation-harness":
        bundle = parse_lm_eval(path)
    elif harness == "nemo-evaluator-launcher":
        bundle = parse_eval_factory(path)
    else:
        bundle = parse_nemo_skills(path, model_id=model_id)

    if model_id and harness != "nemo-skills":
        bundle["model"]["id"] = model_id
        bundle["model"]["id_provenance"] = "user"

    partial = [r for r in bundle["results"] if r["is_partial"]]
    if partial and not allow_partial:
        detail = ", ".join(
            f"{r['benchmark']}/{r['metric']}"
            + (
                f" ({r['num_samples']}/{r['num_samples_total']} samples)"
                if r["num_samples"] and r["num_samples_total"]
                else f" (limited to {r['num_samples']} samples)"
                if r["num_samples"]
                else ""
            )
            for r in partial[:6]
        )
        raise PartialRunError(
            "this run is partial and must not be written into a card as a headline "
            f"result: {detail}. Re-run the eval without a sample limit, or pass "
            "--allow-partial to record it explicitly labelled as partial."
        )
    return bundle


def validate_bundle(bundle: dict, schema_path: Path | None = None) -> list[str]:
    """Validate against the bundle schema. Returns a list of error strings."""
    schema_path = schema_path or (
        Path(__file__).resolve().parent.parent / "references" / "eval-bundle.schema.json"
    )
    try:
        import jsonschema
    except ImportError:
        return []  # optional dependency; parsing already guarantees the shape
    if not schema_path.exists():
        return [f"schema not found at {schema_path}"]
    schema = _read_json(schema_path)
    payload = {k: v for k, v in bundle.items() if not k.startswith("_")}
    validator = jsonschema.Draft202012Validator(schema)
    return [
        f"{'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
        for err in validator.iter_errors(payload)
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("path", type=Path, help="harness run directory or results file")
    ap.add_argument(
        "--model-id",
        help="model identifier. Required for NeMo-Skills runs, which record none.",
    )
    ap.add_argument(
        "--allow-partial",
        action="store_true",
        help="permit sample-limited runs; they are labelled partial wherever rendered",
    )
    ap.add_argument("-o", "--output", type=Path, help="write bundle here (default: stdout)")
    ap.add_argument("--no-validate", action="store_true", help="skip schema validation")
    args = ap.parse_args(argv)

    try:
        bundle = parse(args.path, model_id=args.model_id, allow_partial=args.allow_partial)
    except PartialRunError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for warning in bundle.get("_warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    if bundle["model"]["id"] is None:
        print(
            "warning: no model identity found in the harness output. Pass --model-id "
            "so the card records which model was evaluated.",
            file=sys.stderr,
        )

    if not args.no_validate:
        errors = validate_bundle(bundle)
        if errors:
            print("error: bundle failed schema validation:", file=sys.stderr)
            for err in errors:
                print(f"  {err}", file=sys.stderr)
            return 3

    text = json.dumps(bundle, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(
            f"wrote {args.output} "
            f"({len(bundle['results'])} results, harness={bundle['run']['harness']})",
            file=sys.stderr,
        )
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
