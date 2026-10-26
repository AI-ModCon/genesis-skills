#!/usr/bin/env python3
"""Check that a lenstronomy script uses the values of a parameter set.

Parses the script with ``ast`` (it is never run), recovers the lenstronomy
inputs it builds, and compares them field by field with the parameter-set
JSON that ``validate_params.py`` accepts.

Resolution rules, in order:
* literals, including unary minus and constant folding of + - * / ** on
  resolved operands, so ``10**3`` and ``-0.1`` work;
* names, through a symbol table of simple ``name = value`` assignments;
* constant subscripts of resolved dicts and lists, e.g. ``cfg["fwhm"]``.
Anything else (function calls, loop variables, attribute reads) is reported
as UNRESOLVED: never guessed, and an unresolved value does not pass.

Where each field is looked for:
* ``lens_model_list`` / ``source_model_list``: a ``lens_model_list=`` /
  ``light_model_list=`` call keyword, or an assignment to that name
  (``light_model_list`` is accepted for the source too);
* ``kwargs_lens`` / ``kwargs_source``: the arguments of the last
  ``ImageModel.image(...)`` call, positional or by keyword, since that is what
  is rendered; without such a call, assignments to those names;
* ``numPix`` / ``deltaPix``: the first two arguments of
  ``data_configure_simple(...)``, positional or by keyword in either the 1.9.2
  (``numPix``) or 1.14+ (``num_pix``) spelling, falling back to assignments
  to either name;
* ``exposure_time`` / ``background_rms``: keywords of that call, falling back
  to same-named assignments;
* PSF ``fwhm``: the ``fwhm=`` keyword of a ``PSF(...)`` call.

Usage:
    python3 check_code_params.py simulate.py params.json

Exit status: 0 = every checked field matched; 1 = a field diverged, is
missing or is unresolved, or the script does not parse; 2 = usage error or
unreadable input.

Standard library only (Python 3.10+). Ported from ML4SCI/DeepLense-AI-Scientist
(src/dlens/tools/_code_param_check.py).
"""

from __future__ import annotations

import argparse
import ast
import json
from typing import Any

UNRESOLVED = "<unresolved>"

_REL_TOL = 1e-6

# data_configure_simple's grid arguments: lenstronomy 1.9.2 spelling, 1.14+ spelling.
_GRID_ALIASES = (("numPix", "num_pix"), ("deltaPix", "delta_pix"))


class _Extracted:
    """What the AST walk recovered from the script (None = not found)."""

    def __init__(self) -> None:
        self.lens_model_list: Any = None
        self.source_model_list: Any = None
        self.kwargs_lens: Any = None
        self.kwargs_source: Any = None
        self.numPix: Any = None
        self.deltaPix: Any = None
        self.exposure_time: Any = None
        self.background_rms: Any = None
        self.psf_fwhm: Any = None


def _resolve(node: ast.AST, symbols: dict[str, Any]) -> Any:
    """Resolve a node to a Python value, UNRESOLVED, or containers thereof."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        val = _resolve(node.operand, symbols)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return -val if isinstance(node.op, ast.USub) else val
        return UNRESOLVED
    if isinstance(node, ast.Name):
        return symbols.get(node.id, UNRESOLVED)
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
    ):
        left, right = _resolve(node.left, symbols), _resolve(node.right, symbols)
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (left, right)):
            try:
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    return left / right
                return left**right
            except (ZeroDivisionError, OverflowError):
                return UNRESOLVED
        return UNRESOLVED
    if isinstance(node, ast.Subscript):
        # Still fully static: a dict or list literal reached through a name and
        # indexed by a constant, e.g. kwargs_data["exposure_time"].
        base = _resolve(node.value, symbols)
        key = _resolve(node.slice, symbols)
        if isinstance(base, dict) and isinstance(key, (str, int, float)) and key in base:
            return base[key]
        if (
            isinstance(base, list)
            and isinstance(key, int)
            and not isinstance(key, bool)
            and 0 <= key < len(base)
        ):
            return base[key]
        return UNRESOLVED
    if isinstance(node, ast.List):
        return [_resolve(el, symbols) for el in node.elts]
    if isinstance(node, ast.Dict):
        out: dict[Any, Any] = {}
        for k, v in zip(node.keys, node.values):
            if k is None:
                # **mapping: merged in order, so it can override an earlier key.
                mapping = _resolve(v, symbols)
                if not isinstance(mapping, dict):
                    return UNRESOLVED
                out.update(mapping)
                continue
            key = _resolve(k, symbols)
            if key == UNRESOLVED or not isinstance(key, (str, int, float, bool, type(None))):
                return UNRESOLVED  # an unknown key could override any of the others
            out[key] = _resolve(v, symbols)
        return out
    return UNRESOLVED


def _call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _in_source_order(tree: ast.AST):
    """Yield every node depth-first in source order (``ast.walk`` is breadth-first)."""
    stack = [tree]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(reversed(list(ast.iter_child_nodes(node))))


def extract_lenstronomy_inputs(code: str) -> _Extracted:
    """Walk the script and recover the lenstronomy input values."""
    tree = ast.parse(code)
    symbols: dict[str, Any] = {}
    found = _Extracted()
    rendered: dict[str, Any] = {}

    # Source order matters: a later assignment must replace an earlier one.
    for node in _in_source_order(tree):
        # Symbol table from simple single-target assignments.
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
            node.targets[0], ast.Name
        ):
            name = node.targets[0].id
            value = _resolve(node.value, symbols)
            symbols[name] = value
            if name == "lens_model_list":
                found.lens_model_list = value
            elif name in ("source_model_list", "light_model_list"):
                found.source_model_list = value
            elif name == "kwargs_lens":
                found.kwargs_lens = value
            elif name == "kwargs_source":
                found.kwargs_source = value

        if isinstance(node, ast.Call):
            cname = _call_name(node)
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            if "lens_model_list" in kw and found.lens_model_list is None:
                found.lens_model_list = _resolve(kw["lens_model_list"], symbols)
            if "light_model_list" in kw and found.source_model_list is None:
                found.source_model_list = _resolve(kw["light_model_list"], symbols)
            if cname == "data_configure_simple":
                # Positional, or by keyword in 1.9.2 (numPix) or 1.14+ (num_pix) spelling.
                for i, (attr, snake) in enumerate(_GRID_ALIASES):
                    arg = node.args[i] if len(node.args) > i else kw.get(attr, kw.get(snake))
                    if arg is not None:
                        setattr(found, attr, _resolve(arg, symbols))
                if "exposure_time" in kw:
                    found.exposure_time = _resolve(kw["exposure_time"], symbols)
                if "background_rms" in kw:
                    found.background_rms = _resolve(kw["background_rms"], symbols)
            if cname == "PSF" and "fwhm" in kw:
                found.psf_fwhm = _resolve(kw["fwhm"], symbols)
            # ImageModel.image(kwargs_lens, kwargs_source, ...): what is rendered.
            if (cname == "image" and isinstance(node.func, ast.Attribute)
                    and (len(node.args) >= 2 or {"kwargs_lens", "kwargs_source"} & set(kw))):
                for i, attr in enumerate(("kwargs_lens", "kwargs_source")):
                    arg = node.args[i] if len(node.args) > i else kw.get(attr)
                    if arg is not None:
                        rendered[attr] = _resolve(arg, symbols)

    # The arguments of the last image() call outrank same-named assignments.
    for attr, value in rendered.items():
        setattr(found, attr, value)

    # Fallbacks to plain assignments for the data block.
    for attr, alias in (*_GRID_ALIASES, ("exposure_time", None), ("background_rms", None)):
        if getattr(found, attr) is None:
            if attr in symbols:
                setattr(found, attr, symbols[attr])
            elif alias in symbols:
                setattr(found, attr, symbols[alias])
    return found


def _numbers_match(expected: float, actual: Any) -> bool:
    if not isinstance(actual, (int, float)) or isinstance(actual, bool):
        return False
    return abs(float(actual) - float(expected)) <= _REL_TOL * max(1.0, abs(float(expected)))


def compare_code_to_params(code: str, params: dict[str, Any]) -> dict[str, Any]:
    """Diff the script's lenstronomy inputs against a parameter set.

    Only the parameter set's own fields are checked (extra keys the script
    adds are fine). ``passed`` requires every checked field to match:
    diverged, missing and unresolved all block, so a script that computes a
    value at runtime cannot silently pass.
    """
    try:
        found = extract_lenstronomy_inputs(code)
    except SyntaxError as exc:
        return {"passed": False, "matched": [], "diverged": [], "missing": ["<script>"],
                "unresolved": [], "messages": [f"script is not parseable: {exc}"]}

    matched: list[str] = []
    diverged: list[dict[str, Any]] = []
    missing: list[str] = []
    unresolved: list[str] = []

    def record(field: str, expected: Any, actual: Any) -> None:
        if actual is None:
            missing.append(field)
        elif actual == UNRESOLVED:
            unresolved.append(field)
        elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
            if _numbers_match(expected, actual):
                matched.append(field)
            else:
                diverged.append({"field": field, "expected": expected, "actual": actual})
        elif expected == actual:
            matched.append(field)
        else:
            diverged.append({"field": field, "expected": expected, "actual": actual})

    record("lens_model_list", params["lens_model_list"], found.lens_model_list)
    record("source_model_list", params["source_model_list"], found.source_model_list)

    for label, expected_kwargs, actual_kwargs in (
        ("kwargs_lens", params["kwargs_lens"], found.kwargs_lens),
        ("kwargs_source", params["kwargs_source"], found.kwargs_source),
    ):
        if actual_kwargs is None:
            missing.append(label)
            continue
        if not isinstance(actual_kwargs, list):
            unresolved.append(label)
            continue
        for i, exp_dict in enumerate(expected_kwargs):
            if i < len(actual_kwargs) and actual_kwargs[i] == UNRESOLVED:
                unresolved.append(f"{label}[{i}]")
                continue
            if i >= len(actual_kwargs) or not isinstance(actual_kwargs[i], dict):
                missing.append(f"{label}[{i}]")
                continue
            for key, exp_val in exp_dict.items():
                record(f"{label}[{i}].{key}", exp_val, actual_kwargs[i].get(key))

    data = params["kwargs_data"]
    record("numPix", data["numPix"], found.numPix)
    record("deltaPix", data["deltaPix"], found.deltaPix)
    if data.get("exposure_time") is not None:
        record("exposure_time", data["exposure_time"], found.exposure_time)
    if data.get("background_rms") is not None:
        record("background_rms", data["background_rms"], found.background_rms)
    fwhm = params.get("kwargs_psf", {}).get("fwhm")
    if fwhm is not None:
        record("psf_fwhm", fwhm, found.psf_fwhm)

    messages: list[str] = []
    for d in diverged:
        messages.append(f"{d['field']}: script uses {d['actual']!r} but the parameter set "
                        f"has {d['expected']!r}; use the parameter-set value exactly.")
    for f in missing:
        messages.append(f"{f}: not found in the script; write it explicitly (raw "
                        "lenstronomy with the parameter-set values, not a wrapper that "
                        "hides them).")
    for f in unresolved:
        messages.append(f"{f}: value is computed at runtime and cannot be verified; write "
                        "the parameter-set value as a literal.")

    return {
        "passed": not (diverged or missing or unresolved),
        "matched": sorted(matched),
        "diverged": diverged,
        "missing": sorted(missing),
        "unresolved": sorted(unresolved),
        "messages": messages,
    }


def load_params(raw: Any) -> dict[str, Any]:
    """Read the fields this check needs; ``num_pix``/``delta_pix`` are accepted."""
    if not isinstance(raw, dict):
        raise ValueError("the parameter set must be a JSON object")
    try:
        data = dict(raw["kwargs_data"])
        for camel, snake in (("numPix", "num_pix"), ("deltaPix", "delta_pix")):
            if camel not in data:
                data[camel] = data[snake]
        return {
            "lens_model_list": raw["lens_model_list"],
            "source_model_list": raw["source_model_list"],
            "kwargs_lens": raw["kwargs_lens"],
            "kwargs_source": raw["kwargs_source"],
            "kwargs_data": data,
            "kwargs_psf": raw.get("kwargs_psf") or {},
        }
    except (KeyError, TypeError) as exc:
        raise ValueError(f"parameter set is missing or has a malformed field ({exc}); "
                         "run validate_params.py on it first") from None


def _jsonable(value: Any) -> Any:
    """Make recovered script values printable as JSON (keys become strings)."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check a lenstronomy script against a parameter set; prints a JSON report.")
    parser.add_argument("script", help="the lenstronomy Python script to check (not executed)")
    parser.add_argument("params", help="parameter-set JSON file")
    args = parser.parse_args(argv)

    try:
        with open(args.script, encoding="utf-8") as fh:
            code = fh.read()
        with open(args.params, encoding="utf-8") as fh:
            params = load_params(json.load(fh))
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2

    report = compare_code_to_params(code, params)
    print(json.dumps(_jsonable(report), indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
