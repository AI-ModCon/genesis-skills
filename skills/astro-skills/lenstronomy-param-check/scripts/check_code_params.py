#!/usr/bin/env python3
"""Check that a lenstronomy script uses the values of a parameter set.

Parses the script with ``ast`` (it is never run), recovers the lenstronomy
inputs it builds, and compares them field by field with the parameter-set
JSON that ``validate_params.py`` accepts.

Resolution rules, in order:
* literals, including unary minus and constant folding of + - * / ** on
  resolved operands, so ``10**3`` and ``-0.1`` work;
* names, through a symbol table of ``name = value`` assignments, including
  annotated (``name: int = value``) and augmented (``name += value``) ones;
* constant subscripts of resolved dicts and lists, e.g. ``cfg["fwhm"]``, and
  ``**`` expansions of resolved dicts, applied in order;
* the lenstronomy objects a name holds: ``LensModel``, ``LightModel``, ``PSF``,
  ``data_configure_simple``, ``ImageData`` and ``ImageModel`` calls are followed
  through assignments.
Anything else (other calls, loop variables, attribute reads) is reported as
UNRESOLVED: never guessed, and an unresolved value does not pass. A None the
script passes, explicitly or as lenstronomy's default, is compared like any
other value; a field is missing only when nothing in the script sets it.

The script is followed the way it runs. A branch whose condition is known
statically (``if False:``, ``if DEBUG:`` with ``DEBUG = True``, ``if __name__ ==
"__main__":``) contributes only the side that runs; a function body counts
only where the function is called, in its own scope, and nothing after a return,
break, continue or sys.exit() runs (a path that raises renders nothing, so it is
dropped). When the path depends on runtime values (another condition, a loop, an
exception), a value that differs between the possible paths is UNRESOLVED.

Where each field is looked for:
* ``kwargs_lens`` / ``kwargs_source``: the arguments of the last
  ``ImageModel.image(...)`` call, positional or by keyword, since that is what
  is rendered (an argument the call leaves out is missing); without such a
  call, assignments to those names;
* ``lens_model_list`` / ``source_model_list``: the ``LensModel`` / ``LightModel``
  passed to the ``ImageModel`` that renders (UNRESOLVED if that argument, or the
  ImageModel itself, cannot be followed); with no ImageModel at all, the only one
  the script builds, else an assignment to that name (``light_model_list`` is
  accepted for the source too);
* ``numPix`` / ``deltaPix`` / ``exposure_time`` / ``background_rms``: the
  arguments of the ``data_configure_simple(...)`` behind the ``ImageData(**...)``
  given to that ``ImageModel`` (same rules), positional or by keyword in either
  the 1.9.2 (``numPix``) or 1.14+ (``num_pix``) spelling, falling back to
  assignments to either name;
* PSF ``psf_type`` / ``fwhm`` / ``pixel_size``: the ``PSF(...)`` passed to that
  ``ImageModel``, under the same rules. lenstronomy's default ``psf_type`` is
  ``'NONE'``, so leaving it out counts as ``'NONE'``.

Usage:
    python3 check_code_params.py simulate.py params.json

Exit status: 0 = every checked field matched; 1 = a field diverged, is
missing or is unresolved, or the script does not parse; 2 = usage error or
unreadable input, including a malformed parameter set (reported as
``{"error": ...}``).

Standard library only (Python 3.10+); reads the parameter set with
validate_params.py from the same directory. Ported from
ML4SCI/DeepLense-AI-Scientist (src/dlens/tools/_code_param_check.py).
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _load_validator() -> Any:
    """validate_params.py, next to this script: the parameter-set schema lives there."""
    path = Path(__file__).resolve().with_name("validate_params.py")
    spec = importlib.util.spec_from_file_location("_lenstronomy_param_check_validator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # its dataclasses look the module up while it loads
    spec.loader.exec_module(module)
    return module


_validator = _load_validator()

UNRESOLVED = "<unresolved>"

_REL_TOL = 1e-6

# data_configure_simple's grid arguments: lenstronomy 1.9.2 spelling, 1.14+ spelling.
_GRID_ALIASES = (("numPix", "num_pix"), ("deltaPix", "delta_pix"))

# The leading parameters of the calls the check follows (identical in 1.9.2 and 1.14).
_PARAMETERS = {
    "LensModel": ("lens_model_list",),
    "LightModel": ("light_model_list",),
    "PSF": ("psf_type", "fwhm", "truncation", "pixel_size"),
    "ImageModel": ("data_class", "psf_class", "lens_model_class", "source_model_class"),
    "data_configure_simple": ("numPix", "deltaPix", "exposure_time", "background_rms"),
    "image": ("kwargs_lens", "kwargs_source"),
}
_PSF_DEFAULT_TYPE = "NONE"
# The calls whose results the check follows through names.
_BUILDERS = ("LensModel", "LightModel", "PSF", "ImageModel", "ImageData", "data_configure_simple")

# Names whose assignments stand in for a field when nothing more direct is found.
_CONVENTIONAL = {"lens_model_list": "lens_model_list", "source_model_list": "source_model_list",
                 "light_model_list": "source_model_list", "kwargs_lens": "kwargs_lens",
                 "kwargs_source": "kwargs_source"}

_ABSENT = object()  # marks a key missing on one control-flow path


class _Missing:
    def __repr__(self) -> str:
        return "<missing>"


# Not found in the script (or not given to the rendering ImageModel), as distinct from
# an explicit None, which is a value the script passes and is compared like any other.
_MISSING = _Missing()
_MAX_CALL_DEPTH = 20


@dataclass
class _Built:
    """A lenstronomy object the script builds, with the arguments the check follows."""

    kind: str
    fields: dict[str, Any]


@dataclass(frozen=True)
class _Render:
    """What an ``ImageModel.image(...)`` call rendered: copies of its inputs as they were then."""

    kwargs_lens: Any
    kwargs_source: Any
    image_model: Any


class _Extracted:
    """What the AST walk recovered from the script (_MISSING = not found)."""

    def __init__(self) -> None:
        self.lens_model_list: Any = _MISSING
        self.source_model_list: Any = _MISSING
        self.kwargs_lens: Any = _MISSING
        self.kwargs_source: Any = _MISSING
        self.numPix: Any = _MISSING
        self.deltaPix: Any = _MISSING
        self.exposure_time: Any = _MISSING
        self.background_rms: Any = _MISSING
        self.psf_type: Any = _MISSING
        self.psf_fwhm: Any = _MISSING
        self.psf_pixel_size: Any = _MISSING


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _unknown(value: Any) -> bool:
    return isinstance(value, str) and value == UNRESOLVED


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


_FOLDED = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
           ast.Div: lambda a, b: a / b, ast.Pow: lambda a, b: a ** b}


def _fold(op: ast.operator, left: Any, right: Any) -> Any:
    """Constant folding of + - * / ** on numbers; anything else is UNRESOLVED."""
    if type(op) not in _FOLDED or not (_is_number(left) and _is_number(right)):
        return UNRESOLVED
    if isinstance(op, ast.Pow) and isinstance(left, int) and isinstance(right, int) and abs(right) > 4096:
        return UNRESOLVED  # 2**10**10 would take forever to compute
    try:
        return _FOLDED[type(op)](left, right)
    except (ZeroDivisionError, OverflowError):
        return UNRESOLVED


def _index(base: Any, key: Any) -> Any:
    """base[key] for a resolved dict or list and a constant key, else UNRESOLVED."""
    if isinstance(base, dict) and isinstance(key, (str, int, float)) and key in base:
        return base[key]
    if isinstance(base, (list, tuple)) and isinstance(key, int) and not isinstance(key, bool) \
            and 0 <= key < len(base):
        return base[key]
    return UNRESOLVED


_COMPARISONS = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b,
                ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
                ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b,
                ast.Is: lambda a, b: a is b, ast.IsNot: lambda a, b: a is not b}
_SCALARS = (str, int, float, bool, type(None))


def _compare(ops: list[ast.cmpop], values: list[Any]) -> Any:
    """A comparison of scalars, chained as Python does; UNRESOLVED otherwise."""
    if any(_unknown(v) or not isinstance(v, _SCALARS) for v in values):
        return UNRESOLVED
    for op, a, b in zip(ops, values, values[1:]):
        if type(op) not in _COMPARISONS:
            return UNRESOLVED
        try:
            if not _COMPARISONS[type(op)](a, b):
                return False
        except TypeError:
            return UNRESOLVED
    return True


def _truth(value: Any) -> bool | None:
    """The truth value of a resolved value, or None when it is not known statically."""
    if _unknown(value) or not isinstance(value, (*_SCALARS, list, tuple, dict)):
        return None
    return bool(value)


# --- objects, and edits to them -------------------------------------------------
#
# A value the script holds is a Python scalar, a tuple, a list or dict, a _Built
# lenstronomy object, or UNRESOLVED. Lists, dicts and _Built objects are mutable,
# so identity matters: two names that share one hold the same object, and an edit
# through either changes both. The check never edits an object in place. It makes a
# copy in which the edited part is UNRESOLVED and swaps it in for the original
# everywhere on that control-flow path (see _Walker.swap). Other paths, and earlier
# snapshots, keep the original.

_MUTABLE = (list, dict, _Built)


def _children(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, _Built):
        return list(value.fields.values())
    return []


def _reachable(value: Any) -> list[Any]:
    """Every mutable object reachable from a value, the value itself included."""
    out: list[Any] = []
    seen: set[int] = set()
    stack = [value]
    while stack:
        item = stack.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        if isinstance(item, _MUTABLE):
            out.append(item)
        stack.extend(_children(item))
    return out


def _has_unknown(value: Any) -> bool:
    """Whether some part of the value is UNRESOLVED (and so may be any object)."""
    return _unknown(value) or any(_has_unknown(child) for child in _children(value))


def _same(a: Any, b: Any) -> bool:
    """Whether two control-flow paths hold the same value: for a mutable one, the same object."""
    if a is b:
        return True
    if isinstance(a, _MUTABLE) or isinstance(b, _MUTABLE) or type(a) is not type(b):
        return False
    if isinstance(a, tuple):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return bool(a == b)


def _snapshot(value: Any) -> Any:
    """A copy that later edits to the script's objects cannot reach."""
    if isinstance(value, list):
        return [_snapshot(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_snapshot(v) for v in value)
    if isinstance(value, dict):
        return {k: _snapshot(v) for k, v in value.items()}
    if isinstance(value, _Built):
        return _Built(value.kind, {k: _snapshot(v) for k, v in value.fields.items()})
    return value


class _Replacer:
    """Rebuilds values with some objects swapped, sharing every part that does not change.

    A container holding a swapped object is copied, and the copy is swapped in for it
    too, so names that shared the container still share the copy. A lenstronomy
    object built from a swapped list or dict gets UNRESOLVED in that field instead:
    it may still use the value it was built with.
    """

    def __init__(self, swaps: dict[int, Any]) -> None:
        self.memo: dict[int, Any] = dict(swaps)
        self.copies: list[tuple[Any, Any]] = []  # (old, new) for every container rebuilt

    def __call__(self, value: Any) -> Any:
        if not isinstance(value, (*_MUTABLE, tuple)):
            return value
        key = id(value)
        if key in self.memo:
            return self.memo[key]
        new: Any = value
        if isinstance(value, (list, tuple)):
            parts = [self(v) for v in value]
            if any(p is not v for p, v in zip(parts, value)):
                new = parts if isinstance(value, list) else tuple(parts)
        elif isinstance(value, dict):
            items = {k: self(v) for k, v in value.items()}
            if any(items[k] is not v for k, v in value.items()):
                new = items
        else:
            fields = {}
            for k, v in value.fields.items():
                n = self(v)
                fields[k] = n if n is v or _unknown(n) or isinstance(n, _Built) else UNRESOLVED
            if any(fields[k] is not v for k, v in value.fields.items()):
                new = _Built(value.kind, fields)
        self.memo[key] = new
        if new is not value:
            self.copies.append((value, new))
        return new


@dataclass
class _Args:
    """The evaluated arguments of a call."""

    positional: list[Any]  # up to the first * expansion the check cannot resolve
    keywords: dict[str, Any]  # explicit keywords, and ** expansions of resolved dicts
    expansions: list[Any]  # every ** value, in order
    spread: list[Any]  # every * value that could not be expanded
    opaque: bool  # a * or ** expansion the check cannot resolve may pass more arguments

    def values(self) -> list[Any]:
        return [*self.positional, *self.keywords.values(), *self.expansions, *self.spread]

    def bind(self, names: tuple[str, ...]) -> dict[str, Any]:
        """Bound to the callee's leading parameter ``names``; keywords keep their own names.

        An argument the call does not pass is absent, or UNRESOLVED when an
        expansion that cannot be resolved might be passing it.
        """
        out = dict(zip(names, self.positional))
        out.update(self.keywords)
        if self.opaque:
            for name in names:
                out.setdefault(name, UNRESOLVED)
        return out


def _build(name: str, args: _Args) -> _Built:
    """The lenstronomy object a builder call makes, with the arguments the check follows."""
    if name == "ImageData":
        # Followed when built as ImageData(**kwargs_data) from data_configure_simple.
        config = args.expansions[0] if len(args.expansions) == 1 and not args.positional else UNRESOLVED
        is_config = isinstance(config, _Built) and config.kind == "data_configure_simple"
        return _Built("ImageData", {"config": config if is_config else UNRESOLVED})
    bound = args.bind(_PARAMETERS[name])
    if name == "data_configure_simple":
        for camel, snake in _GRID_ALIASES:
            if snake in bound:
                bound[camel] = bound.pop(snake)
        # numPix and deltaPix are required; exposure_time and background_rms default to None.
        return _Built(name, {k: bound.get(k, _MISSING if k in ("numPix", "deltaPix") else None)
                             for k in _PARAMETERS[name]})
    if name == "PSF":
        return _Built("PSF", {"psf_type": bound.get("psf_type", _PSF_DEFAULT_TYPE),
                              "fwhm": bound.get("fwhm"), "pixel_size": bound.get("pixel_size")})
    if name == "ImageModel":
        return _Built("ImageModel", {"data": bound.get("data_class"), "psf": bound.get("psf_class"),
                                     "lens": bound.get("lens_model_class"),
                                     "source": bound.get("source_model_class")})
    return _Built(name, {"models": bound.get(_PARAMETERS[name][0], _MISSING)})


# Calls the check does not follow but knows cannot change their arguments. The
# "capturing" ones return something that shares them (an iterator, a view, one of
# the arguments), so what they are given can afterwards be reached unseen.
_PURE_BUILTINS = {"print", "len", "repr", "str", "format", "isinstance", "issubclass", "type", "id",
                  "hash", "bool", "int", "float", "abs", "round", "callable", "ascii", "ord", "chr",
                  "bin", "hex", "oct", "divmod", "pow", "any", "all", "range"}
_CAPTURING_BUILTINS = {"list", "tuple", "dict", "set", "frozenset", "sorted", "reversed", "iter",
                       "enumerate", "zip", "min", "max", "sum", "next", "filter", "map", "getattr"}
_PURE_MODULE_CALLS = {"json.dumps", "json.dump", "copy.deepcopy", "pprint.pprint"}
_CAPTURING_MODULE_CALLS = {"copy.copy"}
# Methods of dicts and lists that do not change them; those marked * return a value
# that shares their contents.
_DICT_READS = {"get": True, "keys": False, "values": True, "items": True, "copy": True}
_LIST_READS = {"index": False, "count": False, "copy": True}
# lenstronomy methods that compute from an object without changing it.
_LENSTRONOMY_READS = {"ray_shooting", "alpha", "hessian", "kappa", "potential", "magnification",
                      "fermat_potential", "arrival_time", "surface_brightness", "total_flux",
                      "source_surface_brightness", "lens_surface_brightness"}


def _names_bound(target: ast.AST) -> list[str]:
    """Every plain name an assignment target, loop variable or pattern binds."""
    names = [n.id for n in ast.walk(target) if isinstance(n, ast.Name)]
    names += [n.name for n in ast.walk(target) if isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name]
    names += [n.rest for n in ast.walk(target) if isinstance(n, ast.MatchMapping) and n.rest]
    return names


def _root(node: ast.AST) -> ast.AST:
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node


class _Dead(Exception):
    """A call never returns: the path it is on ends there."""


class _State:
    """The names bound on one control-flow path, and what that path built and rendered."""

    def __init__(self, symbols: dict[str, Any] | None = None,
                 found: dict[str, Any] | None = None) -> None:
        self.symbols: dict[str, Any] = dict(symbols or {})
        self.found: dict[str, Any] = dict(found or {})

    def copy(self) -> _State:
        return _State(self.symbols, self.found)

    def take(self, other: _State) -> None:
        self.symbols, self.found = other.symbols, other.found


def _merge(paths: list[_State], dropped: list[Any] | None = None) -> _State:
    """Join control-flow paths: anything that differs between them is UNRESOLVED.

    The values that differ are appended to ``dropped``: what they hold can now be
    reached only through an UNRESOLVED value.
    """
    merged = _State()
    for attr in ("symbols", "found"):
        tables = [getattr(p, attr) for p in paths]
        out = getattr(merged, attr)
        for key in {k for t in tables for k in t}:
            values = [t.get(key, _ABSENT) for t in tables]
            if values[0] is not _ABSENT and all(v is not _ABSENT and _same(v, values[0]) for v in values[1:]):
                out[key] = values[0]
            else:
                out[key] = UNRESOLVED
                if dropped is not None:
                    dropped.extend(v for v in values if v is not _ABSENT)
    return merged


def _same_state(a: _State, b: _State) -> bool:
    return all(t1.keys() == t2.keys() and all(_same(t1[k], t2[k]) for k in t1)
               for t1, t2 in ((a.symbols, b.symbols), (a.found, b.found)))


class _Walker:
    """Follows the script statement by statement, the way it runs.

    ``block`` and ``statement`` return True when control cannot fall through: after a
    return, raise, break or continue, or a call that never returns. A return keeps
    its path's state for the function's caller, a break or continue for the loop's
    exit, and sys.exit() for the end of the program. A raise drops its path: a script
    that raises renders nothing. Expressions are evaluated by ``eval``, which follows
    the calls in them in evaluation order and raises _Dead from a call that never
    returns.

    An edit to an object the check can identify (``kwargs_lens[0]["theta_E"] = 2.5``,
    ``.update()``, ``del``, a function it follows changing an argument) makes the
    edited key UNRESOLVED, or the whole object when the edit is not a known key. An
    object that may be edited where the check cannot see is made UNRESOLVED: one
    handed to a call it does not follow, and every object that has *escaped* (become
    reachable through a value the check does not know, such as a loop variable)
    when something unknown is edited or called.
    """

    def __init__(self) -> None:
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        self.active: list[str] = []
        self.returns: list[list[_State]] = []  # one list per running function
        self.loop_exits: list[list[_State]] = []  # one list per running loop
        self.program_exits: list[_State] = []
        self.swaps: list[tuple[Any, Any]] = []  # every (old, new) object swap, in order
        self.escaped: dict[int, Any] = {}  # objects reachable through a value the check does not know

    # --- objects ------------------------------------------------------------------

    def swap(self, state: _State, swaps: list[tuple[Any, Any]]) -> None:
        """Put each new object in place of its old one, everywhere this path refers to it."""
        replacer = _Replacer({id(old): new for old, new in swaps})
        for table in (state.symbols, state.found):
            for key, value in list(table.items()):
                new = replacer(value)
                if new is not value:
                    table[key] = new
        for old, new in [*swaps, *replacer.copies]:
            self.swaps.append((old, new))
            if id(old) in self.escaped and isinstance(new, _MUTABLE):
                self.escaped[id(new)] = new

    def replay(self, state: _State, since: int) -> None:
        """Make the swaps done since ``since`` (in a called function) on this path too."""
        latest: dict[int, Any] = {}
        old_of: dict[int, Any] = {}
        for old, new in self.swaps[since:]:
            previous = latest.get(id(old), _ABSENT)
            latest[id(old)] = new if previous is _ABSENT or previous is new else UNRESOLVED
            old_of[id(old)] = old
        swaps = []
        for key, new in latest.items():
            seen: set[int] = set()
            while isinstance(new, _MUTABLE) and id(new) in latest and id(new) not in seen:
                seen.add(id(new))
                new = latest[id(new)]  # swapped again later
            swaps.append((old_of[key], new))
        if swaps:
            self.swap(state, swaps)

    def escape(self, value: Any) -> None:
        """What the value holds can now be reached through a value the check does not know."""
        for obj in _reachable(value):
            self.escaped[id(obj)] = obj

    def invalidate(self, state: _State, objects: list[Any]) -> None:
        """Every reference this path has to these objects becomes UNRESOLVED."""
        targets = list({id(o): o for o in objects if isinstance(o, _MUTABLE)}.values())
        if not targets:
            return
        for obj in targets:
            for child in _children(obj):
                self.escape(child)
        self.swap(state, [(obj, UNRESOLVED) for obj in targets])

    def mark(self, state: _State, container: Any, keys: list[Any]) -> None:
        """The container's values at these keys become UNRESOLVED (all of it for an unknown key)."""
        if isinstance(container, dict) and all(isinstance(k, _SCALARS) and not _unknown(k) for k in keys):
            new = dict(container)
            for key in keys:
                new[key] = UNRESOLVED
            self.swap(state, [(container, new)])
        elif isinstance(container, list) and all(_is_number(k) and isinstance(k, int)
                                                 and -len(container) <= k < len(container) for k in keys):
            new = list(container)
            for key in keys:
                new[key] = UNRESOLVED
            self.swap(state, [(container, new)])
        else:
            self.invalidate(state, [container])

    def module_like(self, node: ast.AST, state: _State) -> bool:
        """Rooted at a name the script never binds: a module, a builtin, or nothing."""
        root = _root(node)
        return isinstance(root, ast.Name) and root.id not in state.symbols

    def edit(self, state: _State, target: ast.Attribute | ast.Subscript, container: Any, key: Any,
             stored: Any = _ABSENT) -> None:
        """``target`` (``container[key]``, or an attribute) is assigned, deleted or changed in place."""
        if isinstance(container, (list, dict)) and isinstance(target, ast.Subscript):
            self.escape(stored)  # it is now held at a key whose value is unknown
            self.mark(state, container, [key])
        elif isinstance(container, _MUTABLE):
            self.escape(stored)
            self.invalidate(state, [container])
        else:
            # An object the check does not track: whatever is stored in it may be changed
            # unseen later, and the object itself may be any that escaped.
            unknown = [] if self.module_like(target.value, state) else list(self.escaped.values())
            self.invalidate(state, [*_reachable(stored), *unknown])

    def unknown_call(self, state: _State, args: _Args, receiver: Any, reaches_script: bool) -> None:
        """A call the check does not follow may change whatever it is given or can reach."""
        given = args.values() + ([] if receiver is _ABSENT else [receiver])
        objects = [obj for value in given for obj in _reachable(value)]
        if reaches_script or args.opaque or any(_has_unknown(v) for v in given):
            objects += list(self.escaped.values())  # an unknown value may be any of these
        self.invalidate(state, objects)

    # --- statements ------------------------------------------------------------

    def block(self, stmts: list[ast.stmt], state: _State) -> bool:
        for stmt in stmts:
            if self.statement(stmt, state):
                return True  # the rest of the block never runs
        return False

    def statement(self, node: ast.stmt, state: _State) -> bool:
        try:
            return self._statement(node, state)
        except _Dead:
            return True

    def _statement(self, node: ast.stmt, state: _State) -> bool:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.functions[node.name] = node  # the body runs only where it is called
            state.symbols[node.name] = UNRESOLVED
            return False
        if isinstance(node, ast.ClassDef):
            state.symbols[node.name] = UNRESOLVED
            return False
        if isinstance(node, ast.If):
            value = _truth(self.eval(node.test, state))
            if value is not None:
                return self.block(node.body if value else node.orelse, state)
            return self.branches([(node.body, state.copy()), (node.orelse, state.copy())], state)
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            return self.loop(node, state)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                self.escape(self.eval(item.context_expr, state))  # `as` may bind it, or part of it
                if item.optional_vars is not None:
                    self.bind(item.optional_vars, UNRESOLVED, state)
            return self.block(node.body, state)
        if isinstance(node, ast.Try) or type(node).__name__ == "TryStar":
            return self.attempt(node, state)
        if isinstance(node, ast.Match):
            self.escape(self.eval(node.subject, state))  # the patterns may bind parts of it
            cases = []
            for case in node.cases:
                path = state.copy()
                for name in _names_bound(case.pattern):
                    path.symbols[name] = UNRESOLVED
                cases.append((case.body, path))
            return self.branches([*cases, ([], state.copy())], state)  # or no case matches
        if isinstance(node, ast.Expr):
            self.eval(node.value, state)
        elif isinstance(node, ast.Assign):
            value = self.eval(node.value, state)
            for target in node.targets:
                self.bind(target, value, state)
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None:  # a bare annotation binds nothing
                self.bind(node.target, self.eval(node.value, state), state)
        elif isinstance(node, ast.AugAssign):
            self.augmented(node, state)
        elif isinstance(node, ast.Return):
            if node.value is not None:
                self.escape(self.eval(node.value, state))  # return values are not followed
            if self.returns:
                self.returns[-1].append(state.copy())
            return True
        elif isinstance(node, ast.Raise):
            for part in (node.exc, node.cause):
                if part is not None:
                    self.eval(part, state)
            return True
        elif isinstance(node, (ast.Break, ast.Continue)):
            if self.loop_exits:
                self.loop_exits[-1].append(state.copy())
            return True
        elif isinstance(node, ast.Assert):
            self.eval(node.test, state)
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                self.delete(target, state)
        return False

    def augmented(self, node: ast.AugAssign, state: _State) -> None:
        target = node.target
        if isinstance(target, ast.Name):
            value = self.eval(node.value, state)
            current = state.symbols.get(target.id, UNRESOLVED)
            if isinstance(current, _MUTABLE):
                # list += ..., dict |= ...: changed in place, so every name sharing it sees it.
                self.escape(value)
                self.invalidate(state, [current])
                self.bind(target, UNRESOLVED, state)
            else:  # x += v on a number is x = x + v
                self.bind(target, _fold(node.op, current, value), state)
            return
        if not isinstance(target, (ast.Attribute, ast.Subscript)):
            self.eval(node.value, state)
            return
        container = self.eval(target.value, state)
        key = self.eval(target.slice, state) if isinstance(target, ast.Subscript) else _ABSENT
        value = self.eval(node.value, state)
        current = _index(container, key) if isinstance(target, ast.Subscript) else UNRESOLVED
        self.edit(state, target, container, key, value)
        if isinstance(current, _MUTABLE):
            self.invalidate(state, [current])  # += on a list element extends that list in place

    def delete(self, target: ast.AST, state: _State) -> None:
        if isinstance(target, ast.Name):
            self.bind(target, UNRESOLVED, state)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for el in target.elts:
                self.delete(el, state)
        elif isinstance(target, (ast.Attribute, ast.Subscript)):
            container = self.eval(target.value, state)
            key = self.eval(target.slice, state) if isinstance(target, ast.Subscript) else _ABSENT
            self.edit(state, target, container, key)

    def merge(self, paths: list[_State]) -> _State:
        dropped: list[Any] = []
        merged = _merge(paths, dropped)
        for value in dropped:
            self.escape(value)
        return merged

    def branches(self, paths: list[tuple[list[ast.stmt], _State]], state: _State) -> bool:
        """Run alternative blocks, each from its own copy of the state; join the ones that fall through."""
        through = [path for body, path in paths if not self.block(body, path)]
        if not through:
            return True
        state.take(self.merge(through))
        return False

    def loop(self, node: ast.For | ast.AsyncFor | ast.While, state: _State) -> bool:
        """The body runs zero or more times: iterate until the joined state is stable."""
        if isinstance(node, ast.While):
            if _truth(self.eval(node.test, state)) is False:
                return self.block(node.orelse, state)
        else:
            self.escape(self.eval(node.iter, state))  # the loop variable holds its items
        entry = state.copy()
        for _ in range(3):
            body = entry.copy()
            if not isinstance(node, ast.While):
                self.bind(node.target, UNRESOLVED, body)
            self.loop_exits.append([])
            ended = self.block(node.body, body)
            exits = self.loop_exits.pop()
            joined = self.merge([state, *([] if ended else [body]), *exits])
            if _same_state(joined, entry):
                break
            entry = joined
        state.take(entry)
        return self.block(node.orelse, state)

    def attempt(self, node: ast.AST, state: _State) -> bool:
        """try/except: a handler may start from any point in the body."""
        before = state.copy()
        ended = self.block(node.body, state) or self.block(node.orelse, state)
        paths = [] if ended else [state.copy()]
        for handler in node.handlers:
            path = self.merge([before, state])
            if handler.name:
                path.symbols[handler.name] = UNRESOLVED
            if not self.block(handler.body, path):
                paths.append(path)
        if paths:
            state.take(self.merge(paths))
        return self.block(node.finalbody, state) or not paths

    def bind(self, target: ast.AST, value: Any, state: _State) -> None:
        if isinstance(target, ast.Name):
            state.symbols[target.id] = value
            if target.id in _CONVENTIONAL:
                state.found[f"assigned:{_CONVENTIONAL[target.id]}"] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            parts = list(value) if isinstance(value, (list, tuple)) else None
            starred = any(isinstance(el, ast.Starred) for el in target.elts)
            if parts is None or starred or len(parts) != len(target.elts):
                self.escape(value)  # its items go to names that are UNRESOLVED
                parts = [UNRESOLVED] * len(target.elts)
            for el, part in zip(target.elts, parts):
                self.bind(el.value if isinstance(el, ast.Starred) else el, part, state)
        elif isinstance(target, (ast.Attribute, ast.Subscript)):
            container = self.eval(target.value, state)
            key = self.eval(target.slice, state) if isinstance(target, ast.Subscript) else _ABSENT
            self.edit(state, target, container, key, value)
        else:
            self.effects(target, state)

    # --- expressions -------------------------------------------------------------

    def effects(self, node: ast.AST, state: _State, escaping: bool = True) -> None:
        """Follow the calls inside a node's parts, in evaluation order, ignoring their values.

        The parts' values are treated as escaping (the node's own value is unknown and
        may share them) unless ``escaping`` is False.
        """
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Lambda):
                self.lambda_(child, state)
            elif isinstance(child, ast.expr):
                value = self.eval(child, state)
                if escaping:
                    self.escape(value)
            else:
                self.effects(child, state, escaping)

    def lambda_(self, node: ast.Lambda, state: _State) -> None:
        """A lambda's body runs only when it is called, and may reach what it names."""
        for name in ast.walk(node.body):
            if isinstance(name, ast.Name):
                self.escape(state.symbols.get(name.id))

    def eval(self, node: ast.AST, state: _State) -> Any:
        """The value of an expression: a Python value, UNRESOLVED, or containers thereof."""
        method = getattr(self, f"_eval_{node.__class__.__name__}", None)
        if method is not None:
            return method(node, state)
        if isinstance(node, ast.Lambda):
            self.lambda_(node, state)
        else:
            self.effects(node, state, escaping=not isinstance(node, (ast.JoinedStr, ast.FormattedValue)))
        return UNRESOLVED

    def _eval_Constant(self, node: ast.Constant, state: _State) -> Any:
        return node.value

    def _eval_Name(self, node: ast.Name, state: _State) -> Any:
        return state.symbols.get(node.id, UNRESOLVED)

    def _eval_NamedExpr(self, node: ast.NamedExpr, state: _State) -> Any:
        value = self.eval(node.value, state)
        self.bind(node.target, value, state)
        return value

    def _eval_UnaryOp(self, node: ast.UnaryOp, state: _State) -> Any:
        value = self.eval(node.operand, state)
        if isinstance(node.op, ast.Not):
            truth = _truth(value)
            return UNRESOLVED if truth is None else not truth
        if _is_number(value) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return -value if isinstance(node.op, ast.USub) else value
        return UNRESOLVED

    def _eval_BinOp(self, node: ast.BinOp, state: _State) -> Any:
        left = self.eval(node.left, state)
        right = self.eval(node.right, state)
        value = _fold(node.op, left, right)
        if _unknown(value):  # e.g. list + list shares the items of both
            self.escape(left)
            self.escape(right)
        return value

    def alternatives(self, runs: list[Callable[[_State], Any]], state: _State) -> Any:
        """Exactly one of ``runs`` happens, which one is not known: follow each on its own copy.

        The paths that do not end are joined into ``state``; the value is theirs when they
        agree, else UNRESOLVED.
        """
        paths, values = [], []
        for run in runs:
            path = state.copy()
            try:
                values.append(run(path))
            except _Dead:
                continue
            paths.append(path)
        if not paths:
            raise _Dead
        state.take(self.merge(paths))
        if all(_same(v, values[0]) for v in values[1:]):
            return values[0]
        for value in values:
            self.escape(value)  # the result may be any of them
        return UNRESOLVED

    def _eval_BoolOp(self, node: ast.BoolOp, state: _State) -> Any:
        # Python stops at the first operand that decides the result (a true one for `or`,
        # a false one for `and`): the operands after it never run.
        decisive = isinstance(node.op, ast.Or)
        for i, operand in enumerate(node.values):
            value = self.eval(operand, state)
            if i == len(node.values) - 1:
                return value
            truth = _truth(value)
            if truth is decisive:
                return value
            if truth is None:  # the rest may or may not run
                rest = ast.BoolOp(op=node.op, values=node.values[i + 1:])
                return self.alternatives([lambda path: value, lambda path: self.eval(rest, path)], state)
        return UNRESOLVED  # not reached: a BoolOp has at least two operands

    def _eval_IfExp(self, node: ast.IfExp, state: _State) -> Any:
        test = _truth(self.eval(node.test, state))
        if test is not None:  # only the side that runs is followed
            return self.eval(node.body if test else node.orelse, state)
        return self.alternatives([lambda path: self.eval(node.body, path),
                                  lambda path: self.eval(node.orelse, path)], state)

    def _eval_Compare(self, node: ast.Compare, state: _State) -> Any:
        # a < b < c stops at the first comparison that is false: c is not evaluated.
        left = self.eval(node.left, state)
        for i, (op, comparator) in enumerate(zip(node.ops, node.comparators)):
            right = self.eval(comparator, state)
            result = _compare([op], [left, right])
            if result is False or i == len(node.ops) - 1:
                return result
            if _unknown(result):
                rest = ast.Compare(left=comparator, ops=node.ops[i + 1:], comparators=node.comparators[i + 1:])
                self.alternatives([lambda path: False, lambda path: self.eval(rest, path)], state)
                return UNRESOLVED
            left = right
        return UNRESOLVED  # not reached

    def comprehension(self, node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
                      state: _State) -> Any:
        """The first iterable is evaluated once; the rest runs once per item, or never.

        A generator expression is followed as if it were consumed right away.
        """
        first = node.generators[0]
        self.escape(self.eval(first.iter, state))  # the loop variables hold its items
        local = {name for gen in node.generators for name in _names_bound(gen.target)}
        outer = {name: state.symbols.get(name, _ABSENT) for name in local}

        def body(path: _State) -> Any:
            for i, gen in enumerate(node.generators):
                if i:
                    self.escape(self.eval(gen.iter, path))
                for name in _names_bound(gen.target):
                    path.symbols[name] = UNRESOLVED
                for condition in gen.ifs:
                    self.eval(condition, path)
            parts = (node.key, node.value) if isinstance(node, ast.DictComp) else (node.elt,)
            for part in parts:
                self.escape(self.eval(part, path))
            return UNRESOLVED

        for _ in range(3):  # each run may see what the one before it did
            before = state.copy()
            self.alternatives([lambda path: UNRESOLVED, body], state)
            for name, value in outer.items():  # its variables do not leak out (a walrus does)
                if value is _ABSENT:
                    state.symbols.pop(name, None)
                else:
                    state.symbols[name] = value
            if _same_state(before, state):
                break
        return UNRESOLVED

    _eval_ListComp = _eval_SetComp = _eval_DictComp = _eval_GeneratorExp = comprehension

    def _eval_Subscript(self, node: ast.Subscript, state: _State) -> Any:
        # Still fully static: a dict or list reached through a name and indexed by a
        # constant, e.g. kwargs_data["exposure_time"].
        base = self.eval(node.value, state)
        value = _index(base, self.eval(node.slice, state))
        if _unknown(value):
            self.escape(base)  # an unknown key or a slice may reach any of its items
        return value

    def _eval_Attribute(self, node: ast.Attribute, state: _State) -> Any:
        self.escape(self.eval(node.value, state))  # an attribute may share the object's parts
        return UNRESOLVED

    def _eval_List(self, node: ast.List, state: _State) -> Any:
        return [self.eval(el, state) for el in node.elts]

    def _eval_Tuple(self, node: ast.Tuple, state: _State) -> Any:
        return tuple(self.eval(el, state) for el in node.elts)

    def _eval_Starred(self, node: ast.Starred, state: _State) -> Any:
        self.escape(self.eval(node.value, state))
        return UNRESOLVED

    def _eval_Dict(self, node: ast.Dict, state: _State) -> Any:
        out: dict[Any, Any] = {}
        resolved = True
        for k, v in zip(node.keys, node.values):
            if k is None:
                # **mapping: merged in order, so it can override an earlier key.
                mapping = self.eval(v, state)
                if isinstance(mapping, dict):
                    out.update(mapping)
                else:
                    self.escape(mapping)
                    resolved = False
                continue
            key = self.eval(k, state)
            value = self.eval(v, state)
            if _unknown(key) or not isinstance(key, _SCALARS):
                self.escape(value)
                resolved = False  # an unknown key could override any of the others
            else:
                out[key] = value
        if not resolved:
            self.escape(out)
            return UNRESOLVED
        return out

    def _eval_Call(self, node: ast.Call, state: _State) -> Any:
        func = node.func
        receiver = self.eval(func.value, state) if isinstance(func, ast.Attribute) else _ABSENT
        if not isinstance(func, (ast.Attribute, ast.Name)):
            self.escape(self.eval(func, state))
        positional: list[Any] = []
        keywords: dict[str, Any] = {}
        expansions: list[Any] = []
        spread: list[Any] = []
        opaque = False
        for arg in node.args:
            if isinstance(arg, ast.Starred):
                value = self.eval(arg.value, state)
                if isinstance(value, (list, tuple)) and not opaque:
                    positional.extend(value)
                else:
                    spread.append(value)
                    opaque = True
                continue
            value = self.eval(arg, state)
            if opaque:
                spread.append(value)  # its position is unknown
            else:
                positional.append(value)
        for keyword in node.keywords:
            value = self.eval(keyword.value, state)
            if keyword.arg is not None:
                keywords[keyword.arg] = value
                continue
            expansions.append(value)
            if isinstance(value, dict):
                keywords.update({k: v for k, v in value.items() if isinstance(k, str)})
            else:
                opaque = True
        return self.call(node, receiver, _Args(positional, keywords, expansions, spread, opaque), state)

    def call(self, node: ast.Call, receiver: Any, args: _Args, state: _State) -> Any:
        """What a call returns, as far as the check follows it."""
        func, found = node.func, state.found
        name = _call_name(func)
        if name in _BUILDERS:
            built = _build(name, args)
            key = f"built:{name}"
            previous = found.get(key, ())
            found[key] = UNRESOLVED if previous == UNRESOLVED else previous + (built,)
            return built
        if name == "image" and isinstance(func, ast.Attribute):
            bound = args.bind(_PARAMETERS["image"])
            found["rendered"] = _Render(_snapshot(bound.get("kwargs_lens", _MISSING)),
                                        _snapshot(bound.get("kwargs_source", _MISSING)),
                                        _snapshot(receiver))
            return UNRESOLVED
        if _is_exit_call(node):
            self.program_exits.append(state.copy())
            raise _Dead
        if isinstance(func, ast.Name) and func.id in self.functions:
            return self.run(self.functions[func.id], args, state)
        if isinstance(receiver, (dict, list)):
            return self.container_method(receiver, name, args, state)
        if isinstance(receiver, _Built) and name in _LENSTRONOMY_READS:
            return UNRESOLVED
        if isinstance(func, ast.Name) and func.id not in state.symbols:
            if func.id in _PURE_BUILTINS:
                return UNRESOLVED
            if func.id in _CAPTURING_BUILTINS:
                for value in args.values():
                    self.escape(value)
                return UNRESOLVED
        module_call = self.module_like(func, state)
        if module_call and isinstance(func, ast.Attribute):
            dotted = ast.unparse(func)
            if dotted in _PURE_MODULE_CALLS:
                return UNRESOLVED
            if dotted in _CAPTURING_MODULE_CALLS:
                for value in args.values():
                    self.escape(value)
                return UNRESOLVED
        # A call the check does not follow. A module's function sees only its arguments; a
        # method of a script object, or a function the script holds, may reach any escaped one.
        self.unknown_call(state, args, _ABSENT if module_call else receiver, not module_call)
        return UNRESOLVED

    def container_method(self, container: dict | list, name: str, args: _Args, state: _State) -> Any:
        """A method call on a dict or list the script built."""
        reads = _DICT_READS if isinstance(container, dict) else _LIST_READS
        if name in reads:
            if reads[name]:
                for child in _children(container):
                    self.escape(child)  # the result shares them
            return UNRESOLVED
        # Anything else changes it: the keys it names become UNRESOLVED, else all of it.
        for value in args.values():
            self.escape(value)  # stored where the check cannot see
        for child in _children(container):
            self.escape(child)  # pop() and friends return them
        keys: list[Any] | None = None
        if isinstance(container, dict) and not args.opaque:
            if name in ("setdefault", "pop") and args.positional:
                keys = [args.positional[0]]
            elif name == "update" and len(args.positional) <= 1:
                source = args.positional[0] if args.positional else {}
                keys = [*source, *args.keywords] if isinstance(source, dict) else None
        if keys is None:
            self.invalidate(state, [container])
        else:
            self.mark(state, container, keys)
        return UNRESOLVED

    def run(self, fn: ast.FunctionDef | ast.AsyncFunctionDef, args: _Args, state: _State) -> Any:
        """Run a called function's body in its own scope; what it builds still counts.

        Raises _Dead when the function never returns (every path raises or exits).
        """
        if fn.name in self.active or len(self.active) >= _MAX_CALL_DEPTH:
            self.unknown_call(state, args, _ABSENT, True)
            return UNRESOLVED
        a = fn.args
        positional = [p.arg for p in (*a.posonlyargs, *a.args)]
        given = args.bind(tuple(positional))
        named = {*positional, *(k.arg for k in a.kwonlyargs)}
        for extra in [*args.positional[len(positional):], *args.spread,
                      *(v for k, v in args.keywords.items() if k not in named)]:
            self.escape(extra)  # it goes to *args or **kwargs, which are UNRESOLVED
        local = _State(state.symbols, state.found)
        defaults = dict(zip(positional[len(positional) - len(a.defaults):], a.defaults))
        defaults.update({p.arg: d for p, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None})
        for p in (*positional, *(k.arg for k in a.kwonlyargs)):
            if p in given:
                local.symbols[p] = given[p]
            elif p in defaults:
                try:
                    local.symbols[p] = self.eval(defaults[p], state.copy())
                except _Dead:
                    local.symbols[p] = UNRESOLVED
            else:
                local.symbols[p] = UNRESOLVED
        for extra in (a.vararg, a.kwarg):
            if extra is not None:
                local.symbols[extra.arg] = UNRESOLVED
        shared = {n for node in ast.walk(fn) if isinstance(node, ast.Global) for n in node.names}
        since = len(self.swaps)
        self.active.append(fn.name)
        self.returns.append([])
        ended = self.block(fn.body, local)
        paths = self.returns.pop() + ([] if ended else [local])
        self.active.pop()
        if not paths:
            self.replay(state, since)
            raise _Dead
        final = self.merge(paths)
        state.found = final.found
        for name in shared & set(final.symbols):
            state.symbols[name] = final.symbols[name]
        self.replay(state, since)  # what it changed in the objects it was given
        return UNRESOLVED


def _is_exit_call(call: ast.Call) -> bool:
    """sys.exit(), os._exit(), exit() or quit(): the program ends here."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id in ("exit", "quit")
    return (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
            and (func.value.id, func.attr) in (("sys", "exit"), ("os", "_exit")))


def _only(built: Any) -> Any:
    """The one object of a kind the script builds: None if none, UNRESOLVED if several differ."""
    if built is None or built == UNRESOLVED:
        return built
    distinct: list[Any] = []
    for b in built:
        if b not in distinct:
            distinct.append(b)
    return distinct[0] if len(distinct) == 1 else UNRESOLVED


def _component(image_model: Any, role: str, kind: str, found: dict[str, Any]) -> Any:
    """The ``kind`` object the rendering ImageModel was given as ``role``.

    Only a script that builds no ImageModel at all falls back to the one ``kind``
    object it builds. An argument the check cannot follow, or an ImageModel it
    cannot identify, leaves the component UNRESOLVED rather than guessing.
    """
    if isinstance(image_model, _Built):
        given = image_model.fields[role]
        if given is None:
            return _MISSING
        return given if isinstance(given, _Built) and given.kind == kind else UNRESOLVED
    if image_model == UNRESOLVED:
        return UNRESOLVED
    return _only(found.get(f"built:{kind}"))


def extract_lenstronomy_inputs(code: str) -> _Extracted:
    """Walk the script and recover the lenstronomy input values."""
    tree = ast.parse(code)
    state = _State({"__name__": "__main__"})  # the check is about the script run directly
    walker = _Walker()
    ended = walker.block(tree.body, state)
    # The script ends where it falls off the end or calls sys.exit(); if every path
    # raises, there is no successful run, so the state as walked is kept.
    paths = walker.program_exits + ([] if ended else [state])
    if paths:
        state = _merge(paths)
    symbols, f = state.symbols, state.found
    found = _Extracted()

    rendered = f.get("rendered")
    image_model: Any = None
    if _unknown(rendered):
        found.kwargs_lens = found.kwargs_source = image_model = UNRESOLVED
    elif isinstance(rendered, _Render):
        # The arguments of the last image() call outrank same-named assignments.
        found.kwargs_lens, found.kwargs_source = rendered.kwargs_lens, rendered.kwargs_source
        image_model = rendered.image_model
        if not (isinstance(image_model, _Built) and image_model.kind == "ImageModel"):
            image_model = UNRESOLVED  # the image() call's ImageModel cannot be identified
    else:
        found.kwargs_lens = f.get("assigned:kwargs_lens", _MISSING)
        found.kwargs_source = f.get("assigned:kwargs_source", _MISSING)
        image_model = _only(f.get("built:ImageModel"))

    for attr, role, kind in (("lens_model_list", "lens", "LensModel"),
                             ("source_model_list", "source", "LightModel")):
        model = _component(image_model, role, kind, f)
        if isinstance(model, _Built):
            setattr(found, attr, model.fields["models"])
        elif model == UNRESOLVED:
            setattr(found, attr, UNRESOLVED)
        elif model is None:
            setattr(found, attr, f.get(f"assigned:{attr}", _MISSING))

    psf = _component(image_model, "psf", "PSF", f)
    if isinstance(psf, _Built):
        found.psf_type, found.psf_fwhm = psf.fields["psf_type"], psf.fields["fwhm"]
        found.psf_pixel_size = psf.fields["pixel_size"]
    elif psf == UNRESOLVED:
        found.psf_type = found.psf_fwhm = found.psf_pixel_size = UNRESOLVED

    data = _component(image_model, "data", "ImageData", f)
    config = data.fields["config"] if isinstance(data, _Built) else data
    if config is None:  # no ImageModel or ImageData: the only data_configure_simple call
        config = _only(f.get("built:data_configure_simple"))
    for attr, alias in (*_GRID_ALIASES, ("exposure_time", None), ("background_rms", None)):
        if isinstance(config, _Built):
            value = config.fields[attr]  # an explicit or default None is what lenstronomy gets
        elif config is None:  # no call found: fall back to plain assignments
            value = symbols.get(attr, symbols.get(alias, _MISSING) if alias else _MISSING)
        elif config is _MISSING:
            value = _MISSING
        else:
            value = UNRESOLVED
        setattr(found, attr, value)
    return found


def _numbers_match(expected: float, actual: Any) -> bool:
    """Equal to within _REL_TOL of the expected value's magnitude; zero only matches zero.

    The tolerance is relative, so a nonzero value never matches zero, nor a value of
    the opposite sign: sigma=0 does not match a validated sigma=1e-7.
    """
    if not isinstance(actual, (int, float)) or isinstance(actual, bool):
        return False
    try:
        expected, actual = float(expected), float(actual)
    except OverflowError:  # an integer literal too large for a float
        return False
    if expected == 0.0 or actual == 0.0:
        return expected == actual
    return abs(actual - expected) <= _REL_TOL * abs(expected)


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
        if actual is _MISSING:
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
        if actual_kwargs is _MISSING:
            missing.append(label)
            continue
        if actual_kwargs == UNRESOLVED:
            unresolved.append(label)
            continue
        if not isinstance(actual_kwargs, (list, tuple)):
            diverged.append({"field": label, "expected": expected_kwargs, "actual": actual_kwargs})
            continue
        for i, exp_dict in enumerate(expected_kwargs):
            if i < len(actual_kwargs) and actual_kwargs[i] == UNRESOLVED:
                unresolved.append(f"{label}[{i}]")
                continue
            if i >= len(actual_kwargs) or not isinstance(actual_kwargs[i], dict):
                missing.append(f"{label}[{i}]")
                continue
            for key, exp_val in exp_dict.items():
                record(f"{label}[{i}].{key}", exp_val, actual_kwargs[i].get(key, _MISSING))

    data = params["kwargs_data"]
    record("numPix", data["numPix"], found.numPix)
    record("deltaPix", data["deltaPix"], found.deltaPix)
    # None (null or omitted) is the noiseless setting, compared like any other value.
    record("exposure_time", data["exposure_time"], found.exposure_time)
    record("background_rms", data["background_rms"], found.background_rms)
    psf = params.get("kwargs_psf", {})
    for field, key, actual in (("psf_type", "psf_type", found.psf_type),
                               ("psf_fwhm", "fwhm", found.psf_fwhm),
                               ("psf_pixel_size", "pixel_size", found.psf_pixel_size)):
        if psf.get(key) is not None:
            record(field, psf[key], actual)

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
    """Read the parameter set with validate_params.py's schema and return it normalized.

    The two scripts therefore see the same values: ``num_pix``/``delta_pix`` are
    accepted, a null or omitted exposure_time/background_rms is None, and an
    omitted ``psf_type`` is GAUSSIAN. A structural problem (``kwargs_lens: [1]``,
    a string where a number belongs, a missing field) raises ValueError listing
    every problem.
    """
    try:
        return _validator.load_params(raw)
    except _validator.InputError as exc:
        raise ValueError("malformed parameter set: " + "; ".join(exc.problems)
                         + ". Run validate_params.py on it first.") from None


def _jsonable(value: Any) -> Any:
    """Make recovered script values printable as JSON (keys become strings)."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
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
