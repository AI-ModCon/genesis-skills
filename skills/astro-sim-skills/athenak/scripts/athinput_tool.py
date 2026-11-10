#!/usr/bin/env python3
"""Inspect AthenaK parameter files (athinput) without running AthenaK.

Standard library only. Reads a plain ``athinput`` file, or the parameter dump
embedded at the start of an AthenaK restart (``.rst``) or binary (``.bin``)
output, using the same rules as AthenaK's ``ParameterInput::LoadFromStream``:

* ``<block>`` on its own line starts (or re-opens) a block;
* ``name = value  # comment``; whitespace around ``=`` is optional;
* everything after ``#`` is a comment; tabs are removed;
* a repeated name in the same block overwrites the earlier value;
* ``<par_end>`` stops parsing.

Usage::

    athinput_tool.py FILE                       # summary
    athinput_tool.py FILE --get mesh/nx1 --get time/tlim
    athinput_tool.py FILE --dump                # normalized block/key = value
    athinput_tool.py FILE --json                # parsed blocks as JSON
    athinput_tool.py --diff A B                 # parameter-level diff
    athinput_tool.py FILE time/tlim=2.0 ...     # apply overrides as AthenaK would

Overrides follow AthenaK's command-line rule: the block and the parameter must
already exist in the file, otherwise AthenaK stops with a fatal error. This
tool reports the same error instead of silently adding the key.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PAR_END = "<par_end>"
PAR_DUMP_MARK = "PAR_DUMP"
MAX_HEADER_BYTES = 1 << 20  # AthenaK itself gives up after ~40 KB

# Block-name prefixes AthenaK accepts (ParameterInput::CheckBlockNames). AthenaK
# matches by prefix, so "output3" and "refined_region1" are valid.
KNOWN_BLOCK_PREFIXES = (
    "comment", "job",
    "mesh", "meshblock", "mesh_refinement", "refined_region", "amr_criterion",
    "coord", "adm", "shearing_box", "cyclic_zoom",
    "time", "problem", "output", "units",
    "hydro", "mhd", "ion-neutral", "radiation", "z4c", "z4c_amr", "cce",
    "rad_srcterms", "hydro_srcterms", "mhd_srcterms", "particles", "turb_driving",
    "gravity", "fastflow",
)

PHYSICS_BLOCKS = (
    "coord", "adm", "hydro", "mhd", "ion-neutral", "radiation", "z4c", "particles",
    "turb_driving", "gravity", "shearing_box", "cyclic_zoom", "units",
)


class AthinputError(Exception):
    """Raised for malformed input or invalid lookups."""


Blocks = dict[str, dict[str, str]]


def parse_text(text: str, warnings: list[str] | None = None) -> Blocks:
    """Parse athinput text into ``{block: {name: value}}`` (insertion ordered).

    Problems that AthenaK does not reject but mishandles are appended to
    ``warnings`` when a list is given.
    """

    blocks: Blocks = {}
    current: dict[str, str] | None = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.replace("\t", "")
        stripped = line.strip(" ")
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(PAR_END):
            break
        if stripped.startswith("<"):
            end = stripped.find(">")
            if end < 0:
                raise AthinputError(f"line {lineno}: block name not properly ended: {raw!r}")
            name = stripped[1:end].strip()
            if line[0] == " " and warnings is not None:
                # AthenaK extracts the name with an offset that assumes column 0,
                # so an indented header yields a mangled block name.
                warnings.append(f"line {lineno}: indented <{name}> header; AthenaK misreads indented block names")
            current = blocks.setdefault(name, {})
            continue
        if current is None:
            raise AthinputError(f"line {lineno}: parameter before first <block>: {raw!r}")
        body = stripped.split("#", 1)[0]
        if "=" not in body:
            raise AthinputError(f"line {lineno}: expected 'name = value': {raw!r}")
        key, value = body.split("=", 1)
        current[key.strip()] = value.strip()
    return blocks


def extract_parameter_text(data: bytes) -> str:
    """Return the athinput text from a plain file or an AthenaK .rst/.bin header."""

    head = data[:MAX_HEADER_BYTES]
    end = head.find(PAR_END.encode())
    if end >= 0:
        head = head[: end + len(PAR_END)]
    elif b"\0" in head:
        raise AthinputError("binary file without a '<par_end>' parameter header")
    text = head.decode("latin-1")
    mark = text.find(PAR_DUMP_MARK)
    if mark >= 0:
        # Skip binary-format header lines that precede the parameter dump.
        text = text[text.find("\n", mark) + 1:]
    return text


def load(path: str | Path, warnings: list[str] | None = None) -> Blocks:
    return parse_text(extract_parameter_text(Path(path).read_bytes()), warnings)


def apply_overrides(blocks: Blocks, overrides: list[str]) -> None:
    """Apply ``block/name=value`` overrides with AthenaK's semantics."""

    for item in overrides:
        if "/" not in item or "=" not in item:
            raise AthinputError(f"override must look like block/name=value: {item!r}")
        slash = item.index("/")
        equal = item.index("=")
        block, name, value = item[:slash], item[slash + 1:equal], item[equal + 1:]
        if block not in blocks:
            raise AthinputError(f"block '{block}' on command line not found (AthenaK would abort)")
        if name not in blocks[block]:
            raise AthinputError(
                f"parameter '{name}' in block '{block}' on command line not found (AthenaK would abort)"
            )
        blocks[block][name] = value


def get(blocks: Blocks, spec: str) -> str:
    if "/" not in spec:
        raise AthinputError(f"--get expects block/name, got {spec!r}")
    block, name = spec.split("/", 1)
    try:
        return blocks[block][name]
    except KeyError:
        raise AthinputError(f"{spec} not set") from None


def unknown_blocks(blocks: Blocks) -> list[str]:
    return [b for b in blocks if not any(b.startswith(p) for p in KNOWN_BLOCK_PREFIXES)]


def _int(blocks: Blocks, block: str, name: str, default: int | None = None) -> int | None:
    try:
        return int(float(blocks[block][name]))
    except (KeyError, ValueError):
        return default


def mesh_summary(blocks: Blocks) -> list[str]:
    lines: list[str] = []
    mesh = blocks.get("mesh", {})
    nx = [_int(blocks, "mesh", f"nx{i}", 1) for i in (1, 2, 3)]
    ndim = 1 + (nx[1] > 1) + (nx[2] > 1)
    lines.append(f"mesh: {' x '.join(str(n) for n in nx[:ndim])} ({ndim}D), nghost={mesh.get('nghost', '?')}")
    for i in range(1, ndim + 1):
        lo, hi = mesh.get(f"x{i}min", "?"), mesh.get(f"x{i}max", "?")
        bcs = mesh.get(f"ix{i}_bc", "?"), mesh.get(f"ox{i}_bc", "?")
        lines.append(f"  x{i}: [{lo}, {hi}]  bc: {bcs[0]} / {bcs[1]}")
    mb = [_int(blocks, "meshblock", f"nx{i}", n) for i, n in zip((1, 2, 3), nx)]
    count = 1
    divisible = True
    for n, m in zip(nx, mb):
        if m and n % m == 0:
            count *= n // m
        else:
            divisible = False
    mbtxt = " x ".join(str(m) for m in mb[:ndim])
    if divisible:
        lines.append(f"meshblock: {mbtxt} -> {count} MeshBlocks on the root level")
    else:
        lines.append(f"meshblock: {mbtxt} -> WARNING: mesh nx is not a multiple of meshblock nx")
    ref = blocks.get("mesh_refinement")
    if ref:
        desc = ", ".join(f"{k}={v}" for k, v in ref.items())
        lines.append(f"refinement: {desc}")
        regions = [b for b in blocks if b.startswith("refined_region")]
        criteria = [b for b in blocks if b.startswith("amr_criterion")]
        if regions:
            lines.append(f"  static regions: {', '.join(regions)}")
        if criteria:
            lines.append(f"  AMR criteria: {', '.join(criteria)}")
    else:
        lines.append("refinement: none (no <mesh_refinement> block)")
    return lines


def summary(blocks: Blocks) -> str:
    lines: list[str] = []
    job = blocks.get("job", {})
    lines.append(f"basename: {job.get('basename', '?')}")
    pgen = blocks.get("problem", {}).get("pgen_name")
    if pgen:
        lines.append(f"problem: pgen_name={pgen}")
    lines.extend(mesh_summary(blocks))
    time = blocks.get("time", {})
    keys = ("evolution", "integrator", "cfl_number", "tlim", "nlim", "ndiag")
    lines.append("time: " + ", ".join(f"{k}={time[k]}" for k in keys if k in time))
    physics = [b for b in PHYSICS_BLOCKS if b in blocks]
    lines.append("physics blocks: " + (", ".join(physics) if physics else "none"))
    for name in physics:
        params = blocks[name]
        if name == "coord":
            picks = list(params)  # small block: general_rel, special_rel, a, excision, ...
        else:
            picks = [k for k in ("eos", "gamma", "reconstruct", "rsolver", "dfloor", "pfloor")
                     if k in params]
        if picks:
            lines.append(f"  <{name}> " + ", ".join(f"{k}={params[k]}" for k in picks))
    outputs = sorted((b for b in blocks if b.startswith("output")), key=_output_order)
    lines.append(f"outputs: {len(outputs)}")
    for name in outputs:
        out = blocks[name]
        cadence = _cadence(out)
        var = f" variable={out['variable']}" if "variable" in out else ""
        lines.append(f"  <{name}> file_type={out.get('file_type', '?')}{var} {cadence}")
    bad = unknown_blocks(blocks)
    if bad:
        lines.append("WARNING: block names AthenaK will reject: " + ", ".join(bad))
    return "\n".join(lines)


def _cadence(out: dict[str, str]) -> str:
    """Describe an <outputN> cadence the way AthenaK's Outputs constructor reads it."""

    if "dcycle" in out:  # dcycle takes precedence over dt
        return f"dcycle={out['dcycle']}"
    if "dt" in out:
        try:
            disabled = float(out["dt"]) <= 0.0
        except ValueError:
            disabled = False
        return f"dt={out['dt']}" + (" (disabled: dt <= 0)" if disabled else "")
    return "no dt/dcycle (AthenaK aborts)"


def _output_order(name: str) -> tuple[int, str]:
    digits = name[len("output"):]
    return (int(digits), name) if digits.isdigit() else (sys.maxsize, name)


def dump(blocks: Blocks) -> str:
    return "\n".join(f"{b}/{k} = {v}" for b, params in blocks.items() for k, v in params.items())


def diff(a: Blocks, b: Blocks) -> list[str]:
    flat_a = {f"{blk}/{k}": v for blk, ps in a.items() for k, v in ps.items()}
    flat_b = {f"{blk}/{k}": v for blk, ps in b.items() for k, v in ps.items()}
    out: list[str] = []
    for key in sorted(flat_a.keys() | flat_b.keys()):
        va, vb = flat_a.get(key), flat_b.get(key)
        if va == vb:
            continue
        if va is None:
            out.append(f"+ {key} = {vb}")
        elif vb is None:
            out.append(f"- {key} = {va}")
        else:
            out.append(f"~ {key}: {va} -> {vb}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("file", nargs="?", help="athinput, .rst, or .bin file")
    parser.add_argument("overrides", nargs="*", help="block/name=value overrides (AthenaK semantics)")
    parser.add_argument("--get", action="append", default=[], metavar="BLOCK/NAME",
                        help="print one value (repeatable)")
    parser.add_argument("--dump", action="store_true", help="print every parameter as block/name = value")
    parser.add_argument("--json", action="store_true", help="print parsed blocks as JSON")
    parser.add_argument("--diff", nargs=2, metavar=("A", "B"), help="parameter-level diff of two files")
    args = parser.parse_args(argv)

    try:
        if args.diff:
            lines = diff(load(args.diff[0]), load(args.diff[1]))
            print("\n".join(lines) if lines else "no differences")
            return 1 if lines else 0
        if not args.file:
            parser.error("a file is required unless --diff is given")
        warnings: list[str] = []
        blocks = load(args.file, warnings)
        for message in warnings:
            print(f"athinput_tool: warning: {message}", file=sys.stderr)
        apply_overrides(blocks, args.overrides)
        if args.get:
            for spec in args.get:
                print(get(blocks, spec))
        elif args.json:
            print(json.dumps(blocks, indent=2))
        elif args.dump:
            print(dump(blocks))
        else:
            print(summary(blocks))
    except (AthinputError, OSError) as exc:
        print(f"athinput_tool: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
