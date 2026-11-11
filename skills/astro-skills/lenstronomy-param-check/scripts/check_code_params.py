#!/usr/bin/env python3
"""Check that a lenstronomy script uses the values of a parameter set.

Parses the script with ``ast`` (it is never run), recovers the lenstronomy
inputs it builds, and compares them field by field with the parameter-set
JSON that ``validate_params.py`` accepts.

The rule: a value the check cannot prove, from the source alone, to be the
parameter set's is UNRESOLVED, never matched, and an unresolved value does not
pass. Values it can prove:
* literals, including unary minus and constant folding of + - * / ** on
  resolved operands, so ``10**3`` and ``-0.1`` work;
* names, through ``name = value`` assignments (annotated, augmented and walrus
  ones too), constant subscripts of resolved dicts and lists, ``**`` expansions
  of resolved dicts, ``len()``, short ``range()`` and ``np.array()`` of literals;
* the lenstronomy objects a name holds: ``LensModel``, ``LightModel``, ``PSF``,
  ``data_configure_simple``, ``ImageData`` and ``ImageModel`` calls, when the
  name is lenstronomy's (imported from it, or not bound at all).
A None the script passes, explicitly or as lenstronomy's default, is compared
like any other value; a field is missing only when nothing in the script sets it.

The script is followed the way it runs. A branch, conditional expression or
and/or operand whose condition is known statically contributes only the side
that runs; a function body counts only where it is called, with Python's
scoping (its locals, then the module's names, or the enclosing call's for a
nested function), and its default arguments are evaluated where it is defined;
nothing after a return, break, continue or sys.exit() runs, a loop's else runs
only without a break, finally runs on every way out of its try, and a path that
raises or exits with an error renders nothing, so it is dropped. When the path
depends on runtime values (a condition, a loop, an exception, which may stop a
try body anywhere), a value that differs between the possible paths is
UNRESOLVED. An edit in place (``kwargs_lens[0]["theta_E"] = 2.5``, ``del``,
``.update()``) makes the edited value UNRESOLVED wherever the object is shared,
as does handing an object to a call the check does not follow. Code that runs
at a time the check cannot know (callbacks, decorators, lambdas or methods that
call code, generators, recursion, exec(), changes to lenstronomy itself) makes
every value UNRESOLVED.

Where each field is looked for:
* ``kwargs_lens`` / ``kwargs_source``: the arguments of the last
  ``ImageModel.image(...)`` call, positional or by keyword, since that is what
  is rendered (an argument the call leaves out is missing); without such a
  call, assignments to those names. Every key is checked: an optional key the
  parameter set leaves out must be lenstronomy's default, 0;
* ``lens_model_list`` / ``source_model_list``: the ``LensModel`` / ``LightModel``
  passed to the ``ImageModel`` that renders (UNRESOLVED if that argument, or the
  ImageModel itself, cannot be followed); with no ImageModel at all, the only one
  the script builds, else an assignment to that name (``light_model_list`` is
  accepted for the source too);
* ``z_lens`` / ``z_source``: every redshift that LensModel is given
  (``z_lens``, ``z_source``, ``lens_redshift_list``, ``z_source_convention``;
  multi-plane needs them). A single-plane LensModel given none renders the same
  image whatever the redshifts, so there is nothing to compare;
* ``numPix`` / ``deltaPix`` / ``exposure_time`` / ``background_rms``: the
  arguments of the ``data_configure_simple(...)`` behind the ``ImageData(**...)``
  given to that ``ImageModel`` (same rules), positional or by keyword in either
  the 1.9.2 (``numPix``) or 1.14+ (``num_pix``) spelling, falling back to
  assignments to either name;
* PSF ``psf_type`` / ``fwhm`` / ``pixel_size``, and ``kernel_point_source`` for
  a PIXEL PSF: the ``PSF(...)`` passed to that ``ImageModel``, under the same
  rules. lenstronomy's default ``psf_type`` is ``'NONE'``, so leaving it out
  counts as ``'NONE'``; the parameter set's default is GAUSSIAN.
Every other argument of those calls must be lenstronomy's default, which the
parameter set assumes (numerics and likelihood-only arguments excepted).

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

class _Unresolved:
    """A value the check cannot determine without running the script."""

    def __repr__(self) -> str:
        return "<unresolved>"


UNRESOLVED = _Unresolved()

_REL_TOL = 1e-6

# data_configure_simple's grid arguments: lenstronomy 1.9.2 spelling, 1.14+ spelling.
_GRID_ALIASES = (("numPix", "num_pix"), ("deltaPix", "delta_pix"))

# The leading parameters of the calls the check follows, as far as lenstronomy 1.9.2 and
# 1.14 agree on their order; a positional argument beyond them is UNRESOLVED.
_PARAMETERS = {
    "LensModel": ("lens_model_list", "z_lens", "z_source", "lens_redshift_list", "cosmo", "multi_plane"),
    "LightModel": ("light_model_list", "deflection_scaling_list", "source_redshift_list"),
    "PSF": ("psf_type", "fwhm", "truncation", "pixel_size", "kernel_point_source"),
    "ImageModel": ("data_class", "psf_class", "lens_model_class", "source_model_class",
                   "lens_light_model_class", "point_source_class", "extinction_class", "kwargs_numerics"),
    "data_configure_simple": ("numPix", "deltaPix", "exposure_time", "background_rms", "center_ra",
                              "center_dec", "inverse"),
    "image": ("kwargs_lens", "kwargs_source", "kwargs_lens_light", "kwargs_ps", "kwargs_extinction",
              "kwargs_special", "unconvolved"),
    "ImageData": (),
}
# The arguments of each call that the parameter set describes; the others are checked
# against _DEFAULTS.
_FOLLOWED = {
    "LensModel": ("lens_model_list", "z_lens", "z_source", "lens_redshift_list", "multi_plane",
                  "z_source_convention", "z_lens_convention"),
    "LightModel": ("light_model_list",),
    "PSF": ("psf_type", "fwhm", "pixel_size", "kernel_point_source"),
    "ImageModel": ("data_class", "psf_class", "lens_model_class", "source_model_class"),
    "data_configure_simple": ("numPix", "num_pix", "deltaPix", "delta_pix", "exposure_time", "background_rms"),
    "image": ("kwargs_lens", "kwargs_source"),
    "ImageData": (),
}
_ANY = object()  # any value: the argument does not change the rendered image
# lenstronomy's defaults (1.9.2 and 1.14) for the other arguments: the parameter set
# assumes them, so a script must leave them alone. Arguments only the likelihood or
# numerical accuracy uses are _ANY; for ImageData, the ones data_configure_simple sets
# already come from it, and passing them again is an error.
_DEFAULTS: dict[str, dict[str, Any]] = {
    "LensModel": {"cosmo": _ANY, "numerical_alpha_class": None, "observed_convention_index": None,
                  "cosmo_interp": False, "z_interp_stop": None, "num_z_interp": 100, "kwargs_interp": None,
                  "profile_kwargs_list": None, "decouple_multi_plane": False,
                  "kwargs_multiplane_model": None, "distance_ratio_sampling": False,
                  "cosmology_sampling": False, "cosmology_model": "FlatLambdaCDM", "use_jax": False},
    "LightModel": {"deflection_scaling_list": None, "source_redshift_list": None, "smoothing": 0.001,
                   "sersic_major_axis": None, "profile_kwargs_list": None},
    "PSF": {"truncation": 5, "psf_error_map": _ANY, "psf_variance_map": _ANY,
            "point_source_supersampling_factor": 1, "kernel_point_source_init": None,
            "kernel_point_source_normalisation": True},
    "ImageModel": {"lens_light_model_class": None, "point_source_class": None, "extinction_class": None,
                   "kwargs_numerics": _ANY, "likelihood_mask": _ANY, "psf_error_map_bool_list": _ANY,
                   "kwargs_pixelbased": None},
    "image": {"kwargs_lens_light": None, "kwargs_ps": None, "kwargs_extinction": None,
              "kwargs_special": None, "unconvolved": False, "apply_primary_beam": True,
              "source_add": True, "lens_light_add": True, "point_source_add": True},
    "data_configure_simple": {"center_ra": 0, "center_dec": 0, "inverse": False},
    "ImageData": {"noise_map": _ANY, "gradient_boost_factor": _ANY, "log_likelihood_constant": _ANY,
                  "likelihood_method": _ANY, "ra_shift": 0, "dec_shift": 0, "phi_rot": 0,
                  "antenna_primary_beam": None, "flux_scaling": 1},
}
_PSF_DEFAULT_TYPE = "NONE"
# LensModel's arguments that place the deflectors and the source in redshift (1.14 adds
# z_lens_convention); None, their default, means not given.
_REDSHIFT_ARGUMENTS = ("z_lens", "z_source", "lens_redshift_list", "multi_plane",
                       "z_source_convention", "z_lens_convention")
# The calls whose results the check follows through names.
_BUILDERS = ("LensModel", "LightModel", "PSF", "ImageModel", "ImageData", "data_configure_simple")

# Names whose assignments stand in for a field when nothing more direct is found.
_CONVENTIONAL = {"lens_model_list": "lens_model_list", "source_model_list": "source_model_list",
                 "light_model_list": "source_model_list", "kwargs_lens": "kwargs_lens",
                 "kwargs_source": "kwargs_source"}

_ABSENT = object()  # marks a key missing on one control-flow path
_NOT_IN_PARAMS = "<not in the parameter set>"  # the expected value of something the script adds


class _Missing:
    def __repr__(self) -> str:
        return "<missing>"


# Not found in the script (or not given to the rendering ImageModel), as distinct from
# an explicit None, which is a value the script passes and is compared like any other.
_MISSING = _Missing()
_MAX_CALL_DEPTH = 20
_UNROLL = 16  # a loop over a known list this long or shorter is followed item by item
_MAX_ROUNDS = 1000  # loop bodies are re-run until the state is stable, which it always becomes


@dataclass(repr=False)
class _Built:
    """A lenstronomy object the script builds, with the arguments the check follows."""

    kind: str
    fields: dict[str, Any]

    def __repr__(self) -> str:
        models = self.fields.get("models")
        return f"<{self.kind} {models!r}>" if isinstance(models, list) else f"<{self.kind}>"


@dataclass(frozen=True)
class _Render:
    """What an ``ImageModel.image(...)`` call rendered: copies of its inputs as they were then."""

    kwargs_lens: Any
    kwargs_source: Any
    image_model: Any
    extras: dict[str, Any]  # its other arguments (see _extras)


class _Extracted:
    """What the AST walk recovered from the script (_MISSING = not found)."""

    def __init__(self) -> None:
        self.notes: list[str] = []  # why every value is unresolved, when it is
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
        self.psf_kernel: Any = _MISSING
        self.lens_redshifts: Any = _MISSING  # the rendering LensModel's redshift arguments
        self.extras: list[tuple[str, dict[str, Any]]] = []  # (call, arguments not followed)


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _unknown(value: Any) -> bool:
    return value is UNRESOLVED


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

@dataclass(eq=False)
class _Function:
    """A function the script defines: its definition, the call (scope) it was defined in,
    and its default argument values, evaluated once when the ``def`` ran."""

    node: ast.FunctionDef | ast.AsyncFunctionDef
    scope: int
    defaults: dict[str, Any]


_MUTABLE = (list, dict, _Built, _Function)


def _children(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, _Built):
        return list(value.fields.values())
    if isinstance(value, _Function):
        return list(value.defaults.values())
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
    return value  # a function is kept as it is


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
        elif isinstance(value, _Function):  # a default argument shared by every call
            defaults = {k: self(v) for k, v in value.defaults.items()}
            if any(defaults[k] is not v for k, v in value.defaults.items()):
                new = _Function(value.node, value.scope, defaults)
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


def _extras(name: str, args: _Args) -> dict[str, Any]:
    """The arguments of a call that the parameter set does not describe, by name.

    A positional argument past the ones whose order the versions agree on is listed
    as UNRESOLVED under "(argument N)".
    """
    bound = args.bind(_PARAMETERS[name])
    out = {k: v for k, v in bound.items() if k not in _FOLLOWED[name]}
    for i in range(len(_PARAMETERS[name]), len(args.positional)):
        out[f"(argument {i + 1})"] = UNRESOLVED
    return out


def _build(name: str, args: _Args) -> _Built:
    """The lenstronomy object a builder call makes, with the arguments the check follows."""
    built = _construct(name, args)
    built.fields["extras"] = _extras(name, args)
    return built


def _construct(name: str, args: _Args) -> _Built:
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
                              "fwhm": bound.get("fwhm"), "pixel_size": bound.get("pixel_size"),
                              "kernel": bound.get("kernel_point_source")})
    if name == "ImageModel":
        return _Built("ImageModel", {"data": bound.get("data_class"), "psf": bound.get("psf_class"),
                                     "lens": bound.get("lens_model_class"),
                                     "source": bound.get("source_model_class")})
    if name == "LensModel":
        redshifts = {k: bound.get(k) for k in _REDSHIFT_ARGUMENTS}
        if args.opaque:  # an expansion may be passing any of them
            redshifts = {k: UNRESOLVED if v is None else v for k, v in redshifts.items()}
        return _Built(name, {"models": bound.get("lens_model_list", _MISSING), "redshifts": redshifts})
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
# Builtins that iterate over a generator they are given before returning (as does str.join).
_EAGER_BUILTINS = {"list", "tuple", "set", "frozenset", "dict", "sorted", "sum", "min", "max",
                   "any", "all", "next"}
# numpy's array constructors: of a nested list of numbers, a copy of it (kept as lists).
_ARRAY_CALLS = {"np.array", "np.asarray", "numpy.array", "numpy.asarray"}
_CAPTURING_MODULE_CALLS = {"copy.copy"}
# Methods of dicts and lists that do not change them; those marked * return a value
# that shares their contents.
_DICT_READS = {"get": True, "keys": False, "values": True, "items": True, "copy": True}
_LIST_READS = {"index": False, "count": False, "copy": True}
# lenstronomy methods that compute from an object without changing it.
_LENSTRONOMY_READS = {"ray_shooting", "alpha", "hessian", "kappa", "potential", "magnification",
                      "fermat_potential", "arrival_time", "surface_brightness", "total_flux",
                      "source_surface_brightness", "lens_surface_brightness"}


def _builtin_value(name: str, args: _Args) -> Any:
    """len() of a known container and a short range() of known ints; else UNRESOLVED."""
    values = args.positional
    if args.opaque or args.keywords or any(_unknown(v) for v in values):
        return UNRESOLVED
    if name == "len" and len(values) == 1 and isinstance(values[0], (str, list, tuple, dict)):
        return len(values[0])
    if name == "range" and 1 <= len(values) <= 3 and all(isinstance(v, int) and not isinstance(v, bool)
                                                         for v in values):
        try:
            items = range(*values)
        except ValueError:  # a zero step
            return UNRESOLVED
        return list(items) if len(items) <= _UNROLL else UNRESOLVED
    return UNRESOLVED


def _array_value(args: _Args) -> Any:
    """np.array(x) of a nested list of numbers: a copy of x; anything else is UNRESOLVED."""
    def numeric(value: Any) -> bool:
        if isinstance(value, (list, tuple)):
            return all(numeric(v) for v in value)
        return _is_number(value)
    extra = set(args.keywords) - {"dtype"}
    if args.opaque or extra or len(args.positional) != 1 or not isinstance(args.positional[0], (list, tuple)) \
            or not numeric(args.positional[0]):
        return UNRESOLVED
    return _snapshot([*args.positional[0]])


def _names_bound(target: ast.AST) -> list[str]:
    """Every plain name an assignment target, loop variable or pattern binds."""
    names = [n.id for n in ast.walk(target) if isinstance(n, ast.Name)]
    names += [n.name for n in ast.walk(target) if isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name]
    names += [n.rest for n in ast.walk(target) if isinstance(n, ast.MatchMapping) and n.rest]
    return names


def _scope_imports(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """The names a function's body imports (not those of nested functions or classes)."""
    out: set[str] = set()

    def walk(n: ast.AST) -> None:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            out.update((a.asname or a.name).split(".")[0] for a in n.names if a.name != "*")
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            for child in ast.iter_child_nodes(n):
                walk(child)
    for stmt in fn.body:
        walk(stmt)
    return out


def _may_have_effects(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> bool:
    """Whether running a function could change what the check follows.

    It could when it calls anything, declares global or nonlocal names, or assigns or
    deletes through a subscript or attribute, except an attribute of its first
    argument (``self.x = x`` in a method).
    """
    args = node.args.posonlyargs + node.args.args
    first = args[0].arg if args and not isinstance(node, ast.Lambda) else None
    for sub in ast.walk(node.body if isinstance(node, ast.Lambda) else ast.Module(node.body, [])):
        if isinstance(sub, (ast.Call, ast.Global, ast.Nonlocal, ast.NamedExpr, ast.YieldFrom, ast.Await)):
            return True
        if isinstance(sub, (ast.Subscript, ast.Attribute)) and isinstance(sub.ctx, (ast.Store, ast.Del)):
            if not (isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == first):
                return True
    return False


def _is_generator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """A generator or coroutine function: calling it does not run its body."""
    if isinstance(node, ast.AsyncFunctionDef):
        return True

    def walk(n: ast.AST) -> bool:
        if isinstance(n, (ast.Yield, ast.YieldFrom)):
            return True
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return False
        return any(walk(c) for c in ast.iter_child_nodes(n))
    return any(walk(stmt) for stmt in node.body)


def _exit_status(args: _Args) -> bool | None:
    """Whether sys.exit(...) with these arguments ends the run successfully (None: unknown)."""
    if args.opaque or args.keywords:
        return None
    if not args.positional:
        return True
    code = args.positional[0]
    if _unknown(code):
        return None
    return code is None or (isinstance(code, int) and code == 0)


# Libraries whose own functions lenstronomy relies on: a script that changes them is not
# followed. Names it uses without importing them are taken to be lenstronomy's.
_PATCHED_ROOTS = {"lenstronomy", "numpy", "scipy", "astropy"}
# Code that runs or reaches Python source and namespaces the check cannot see.
_DYNAMIC_BUILTINS = {"exec", "eval", "globals", "locals", "vars", "breakpoint"}
# Context managers known not to swallow an exception raised in their with block.
_PLAIN_CONTEXTS = {"open", "io.open", "gzip.open", "bz2.open", "lzma.open", "tarfile.open",
                   "zipfile.ZipFile", "tempfile.TemporaryDirectory", "tempfile.NamedTemporaryFile",
                   "tempfile.TemporaryFile", "h5py.File", "numpy.errstate", "np.errstate",
                   "warnings.catch_warnings", "contextlib.nullcontext", "threading.Lock", "threading.RLock"}


def _redirects(stmts: list[ast.stmt]) -> bool:
    """Whether the block can return, or break or continue a loop that encloses it."""
    def walk(node: ast.AST, in_loop: bool) -> bool:
        if isinstance(node, ast.Return):
            return True
        if isinstance(node, (ast.Break, ast.Continue)):
            return not in_loop
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return False
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            # A break or continue in the body is this loop's; in its else, the enclosing one's.
            return any(walk(s, True) for s in node.body) or any(walk(s, in_loop) for s in node.orelse)
        return any(walk(child, in_loop) for child in ast.iter_child_nodes(node))
    return any(walk(stmt, False) for stmt in stmts)


def _root(node: ast.AST) -> ast.AST:
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node


class _Dead(Exception):
    """A call never returns: the path it is on ends there."""


@dataclass(frozen=True)
class _Frame:
    """The module (scope 0) or one call of a function: the names it declares, and its locals."""

    scope: int = 0
    shared: frozenset[str] = frozenset()  # declared global
    locals: frozenset[str] = frozenset()  # every name the function binds (its parameters too)


_MODULE = _Frame()


def _scope_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[frozenset[str], frozenset[str]]:
    """A function's ``global`` names and its local names, as Python decides them (names it
    only imports are left out: they stay modules, as the check treats them).

    A name the function binds anywhere in its body is local to it everywhere in the body,
    unless it is declared global or nonlocal; nested functions, classes, lambdas and
    comprehensions have their own scopes (a walrus in a comprehension binds here).
    """
    cached = getattr(fn, "_param_check_scope", None)
    if cached is not None:
        return cached
    declared_global: set[str] = set()
    declared_nonlocal: set[str] = set()
    imported: set[str] = set()
    bound = {p.arg for p in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs,
                             fn.args.vararg, fn.args.kwarg) if p is not None}

    def visit(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
            return
        if isinstance(node, ast.Lambda):
            return
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            bound.update(n.target.id for n in ast.walk(node)
                         if isinstance(n, ast.NamedExpr) and isinstance(n.target, ast.Name))
            return
        if isinstance(node, ast.Global):
            declared_global.update(node.names)
        elif isinstance(node, ast.Nonlocal):
            declared_nonlocal.update(node.names)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imported.update((a.asname or a.name).split(".")[0] for a in node.names if a.name != "*")
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
            bound.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            bound.add(node.rest)
        for child in ast.iter_child_nodes(node):
            visit(child)

    for stmt in fn.body:
        visit(stmt)
    result = (frozenset(declared_global), frozenset(bound - declared_global - declared_nonlocal - imported))
    fn._param_check_scope = result  # type: ignore[attr-defined]
    return result


class _State:
    """The names bound on one control-flow path, and what that path built and rendered.

    In a function's call, ``symbols`` holds every name its body can see (its locals,
    then the names of the scope it was defined in) and ``globals`` the module's names
    as that call sees them; in the module, ``globals`` is None and ``symbols`` holds them.
    """

    def __init__(self, symbols: dict[str, Any] | None = None, found: dict[str, Any] | None = None,
                 frame: _Frame = _MODULE, globals_: dict[str, Any] | None = None) -> None:
        self.symbols: dict[str, Any] = dict(symbols or {})
        self.found: dict[str, Any] = dict(found or {})
        self.frame = frame
        self.globals: dict[str, Any] | None = None if globals_ is None else dict(globals_)

    def copy(self) -> _State:
        return _State(self.symbols, self.found, self.frame, self.globals)

    def take(self, other: _State) -> None:
        self.symbols, self.found, self.globals = other.symbols, other.found, other.globals

    def tables(self) -> list[dict[str, Any]]:
        return [t for t in (self.symbols, self.found, self.globals) if t is not None]

    def global_names(self) -> dict[str, Any]:
        """The module's names as this path sees them."""
        return self.symbols if self.globals is None else self.globals


def _merge(paths: list[_State], dropped: list[Any] | None = None) -> _State:
    """Join control-flow paths: anything that differs between them is UNRESOLVED.

    The values that differ are appended to ``dropped``: what they hold can now be
    reached only through an UNRESOLVED value.
    """
    merged = _State(frame=paths[0].frame, globals_=None if paths[0].globals is None else {})
    for attr in ("symbols", "found", "globals"):
        tables = [getattr(p, attr) for p in paths]
        out = getattr(merged, attr)
        if out is None:
            continue
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
               for t1, t2 in zip(a.tables(), b.tables()))


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
        self.active: list[ast.AST] = []  # the functions being run
        self.returns: list[list[_State]] = []  # one list per running function
        self.loops: list[tuple[list[_State], list[_State]]] = []  # (breaks, continues) per running loop
        self.program_exits: list[_State] = []
        self.swaps: list[tuple[Any, Any]] = []  # every (old, new) object swap, in order
        self.escaped: dict[int, Any] = {}  # objects reachable through a value the check does not know
        self.writes: list[set[tuple[Any, ...]]] = []  # what each running try body has assigned
        self.scopes = 0
        self.wild: list[str] = []  # why the script cannot be followed, if it cannot
        self.consumed: set[int] = set()  # generator expressions passed straight to a call

    def go_wild(self, node: ast.AST, reason: str) -> None:
        """The script runs its own code at a time the check cannot know: nothing is certain."""
        note = f"line {getattr(node, 'lineno', '?')}: {reason}"
        if note not in self.wild:
            self.wild.append(note)

    # --- writes -------------------------------------------------------------------

    def set_symbol(self, state: _State, name: str, value: Any) -> None:
        state.symbols[name] = value
        frame = state.frame
        is_global = frame.scope == 0 or name in frame.shared
        if is_global and state.globals is not None:
            state.globals[name] = value
        if self.writes:
            self.logged(("global", name) if is_global else ("local", frame.scope, name), value)

    def set_global(self, state: _State, name: str, value: Any) -> None:
        """Rebind a module name, from a function this path called."""
        if state.globals is None:
            self.set_symbol(state, name, value)
            return
        state.globals[name] = value
        if name not in state.frame.locals:
            state.symbols[name] = value
        if self.writes:
            self.logged(("global", name), value)

    def set_found(self, state: _State, key: str, value: Any) -> None:
        state.found[key] = value
        if self.writes:
            self.logged(("found", key), value)

    def logged(self, entry: tuple[Any, ...], value: Any) -> None:
        for log in self.writes:
            log.add(entry)
        self.escape(value)  # a handler may see it under a name that is UNRESOLVED there

    # --- objects ------------------------------------------------------------------

    def swap(self, state: _State, swaps: list[tuple[Any, Any]]) -> None:
        """Put each new object in place of its old one, everywhere this path refers to it."""
        replacer = _Replacer({id(old): new for old, new in swaps})
        for table in state.tables():
            for key, value in list(table.items()):
                new = replacer(value)
                if new is not value:
                    table[key] = new
        for old, new in [*swaps, *replacer.copies]:
            self.swaps.append((old, new))
            if id(old) in self.escaped and isinstance(new, _MUTABLE):
                self.escaped[id(new)] = new

    def latest(self, since: int) -> list[tuple[Any, Any]]:
        """Each object swapped since ``since``, with what it has become (UNRESOLVED if paths differ)."""
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
        return swaps

    def replay(self, state: _State, since: int) -> None:
        """Make the swaps done since ``since`` (in a called function) on this path too."""
        swaps = self.latest(since)
        if swaps:
            self.swap(state, swaps)

    def fresh(self, since: int, values: list[Any]) -> list[Any]:
        """``values`` as they are now: evaluating a later expression may have edited objects in them."""
        if len(self.swaps) == since:
            return values
        replacer = _Replacer({id(old): new for old, new in self.latest(since)})
        return [replacer(value) for value in values]

    def escape(self, value: Any) -> None:
        """What the value holds can now be reached through a value the check does not know."""
        for obj in _reachable(value):
            self.escaped[id(obj)] = obj
            if isinstance(obj, _Function) and _may_have_effects(obj.node):
                self.go_wild(obj.node, f"{obj.node.name}() reaches code the check does not follow, "
                                       "which may call it at any time")

    def invalidate(self, state: _State, objects: list[Any]) -> None:
        """Every reference this path has to these objects becomes UNRESOLVED."""
        targets = list({id(o): o for o in objects if isinstance(o, _MUTABLE)}.values())
        if not targets:
            return
        for obj in targets:
            self.escape(obj)
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

    def qualname(self, node: ast.AST, state: _State) -> str | None:
        """The dotted name ``a.b.c`` refers to when ``a`` is a module (imported or not), else None."""
        parts: list[str] = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if not isinstance(node, ast.Name) or node.id in state.symbols:
            return None
        imported = state.found.get(f"import:{node.id}", _ABSENT)
        if _unknown(imported):
            return None  # imported differently on different paths
        return ".".join([node.id if imported is _ABSENT else imported, *reversed(parts)])

    def is_builtin(self, func: ast.AST, state: _State) -> str | None:
        """The name of the builtin a bare-name call is, when the script neither binds nor imports it."""
        if isinstance(func, ast.Name) and func.id not in state.symbols and f"import:{func.id}" not in state.found:
            return func.id
        return None

    def builder(self, func: ast.AST, state: _State) -> str | None:
        """The lenstronomy builder a call is, if any: by name, and from lenstronomy when imported."""
        name = _call_name(func)
        if name not in _BUILDERS or not isinstance(func, (ast.Name, ast.Attribute)) \
                or not self.module_like(func, state):
            return None  # e.g. the script's own function, or a method of an object it holds
        root = _root(func)
        assert isinstance(root, ast.Name)
        qualified = self.qualname(func, state)
        if qualified is None:
            return None
        if f"import:{root.id}" not in state.found:
            return name  # used without an import: taken to be lenstronomy's
        return name if qualified.split(".")[0] == "lenstronomy" else None

    def patches(self, target: ast.AST, state: _State) -> str | None:
        """The library name an assignment or call changes, when it is lenstronomy or one it uses."""
        qualified = self.qualname(target, state) if self.module_like(target, state) else None
        if qualified is None:
            return None
        root = qualified.split(".")[0]
        unimported = f"import:{_root(target).id}" not in state.found  # type: ignore[union-attr]
        if root in _PATCHED_ROOTS or (unimported and (root in _BUILDERS or root == "np")):
            return qualified
        return None

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
            patched = self.patches(target, state)
            if patched is not None:
                self.go_wild(target, f"the script changes {patched}, which lenstronomy relies on")
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
            # The body runs only where it is called, seeing the names of the scope it is defined
            # in; the default values are evaluated now, once. A decorator is handed the function
            # and may call it at any time, and the name holds whatever it returns.
            if node.decorator_list:
                for decorator in node.decorator_list:
                    self.eval(decorator, state)
                if _may_have_effects(node):
                    self.go_wild(node, f"{node.name}() is decorated, so the check cannot tell when it runs")
                self.set_symbol(state, node.name, UNRESOLVED)
                return False
            a = node.args
            positional = [p.arg for p in (*a.posonlyargs, *a.args)]
            defaults = {}
            for name, default in zip(positional[len(positional) - len(a.defaults):], a.defaults):
                defaults[name] = self.eval(default, state)
            for p, default in zip(a.kwonlyargs, a.kw_defaults):
                if default is not None:
                    defaults[p.arg] = self.eval(default, state)
            self.set_symbol(state, node.name, _Function(node, state.frame.scope, defaults))
            return False
        if isinstance(node, ast.ClassDef):
            # The class body runs now, in its own namespace; its methods run when called through
            # an instance, which the check does not follow.
            for expr in [*node.decorator_list, *node.bases, *(k.value for k in node.keywords)]:
                self.escape(self.eval(expr, state))
            namespace, since = state.copy(), len(self.swaps)
            if not self.block(node.body, namespace):
                state.found = namespace.found
                self.replay(state, since)
            for stmt in ast.walk(ast.Module(node.body, [])):
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and _may_have_effects(stmt):
                    self.go_wild(node, f"class {node.name} has methods that call code, which run "
                                       "whenever an instance's method is called")
                    break
                if isinstance(stmt, (ast.Global, ast.Nonlocal)):
                    self.go_wild(node, f"class {node.name} rebinds names outside itself")
            self.set_symbol(state, node.name, UNRESOLVED)
            return False
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                self.imported(state, name, alias.name if alias.asname else name)
            return False
        if isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            for alias in node.names:
                if alias.name == "*":
                    if module.split(".")[0] != "lenstronomy":
                        self.go_wild(node, f"from {module} import * may rebind any name")
                else:
                    self.imported(state, alias.asname or alias.name, f"{module}.{alias.name}")
            return False
        if isinstance(node, ast.If):
            value = _truth(self.eval(node.test, state))
            if value is not None:
                return self.block(node.body if value else node.orelse, state)
            return self.branches([(node.body, state.copy()), (node.orelse, state.copy())], state)
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            return self.loop(node, state)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            plain = True
            for item in node.items:
                self.escape(self.eval(item.context_expr, state))  # `as` may bind it, or part of it
                plain = plain and self.plain_context(item.context_expr, state)
                if item.optional_vars is not None:
                    self.bind(item.optional_vars, UNRESOLVED, state)
            if plain:
                return self.block(node.body, state)
            # Its __exit__ may swallow an exception raised anywhere in the body, as an except
            # handler that does nothing would.
            start, since = state.copy(), len(self.swaps)
            self.writes.append(set())
            ended = self.block(node.body, state)
            writes = self.writes.pop()
            state.take(self.merge(([] if ended else [state.copy()]) + [self.handler_entry(start, since, writes)]))
            return False
        if isinstance(node, ast.Try) or type(node).__name__ == "TryStar":
            return self.attempt(node, state)
        if isinstance(node, ast.Match):
            # Cases are tried in order. A case is reached when the ones before it did not match
            # (a failed pattern may have bound some of its names) or matched with a false guard,
            # whose effects stay; its guard runs before its body.
            self.escape(self.eval(node.subject, state))  # the patterns may bind parts of it
            cases = []
            rest = state.copy()
            for case in node.cases:
                for name in _names_bound(case.pattern):
                    self.set_symbol(rest, name, UNRESOLVED)
                if case.guard is None:
                    cases.append((case.body, rest.copy()))
                    continue
                path = rest.copy()
                try:
                    self.eval(case.guard, path)
                except _Dead:
                    continue
                cases.append((case.body, path))
                rest = self.merge([rest, path.copy()])
            return self.branches([*cases, ([], rest)], state)  # or no case matches
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
            exc = node.exc
            if isinstance(exc, ast.Call) and self.is_builtin(exc.func, state) == "SystemExit":
                code = [self.eval(a, state.copy()) for a in exc.args]
                if _exit_status(_Args(code, {}, [], [], False)) is not False:
                    self.program_exits.append(state.copy())  # raise SystemExit(0) ends the run
            elif isinstance(exc, ast.Name) and self.is_builtin(exc, state) == "SystemExit":
                self.program_exits.append(state.copy())
            return True
        elif isinstance(node, (ast.Break, ast.Continue)):
            if self.loops:
                self.loops[-1][isinstance(node, ast.Continue)].append(state.copy())
            return True
        elif isinstance(node, ast.Assert):
            self.eval(node.test, state)
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                self.delete(target, state)
        return False

    def imported(self, state: _State, name: str, source: str) -> None:
        """An import binds ``name`` to a module or something in one: a value the name held is gone."""
        if name in state.symbols or name in state.frame.shared or name in _CONVENTIONAL:
            self.bind(ast.Name(id=name, ctx=ast.Store()), UNRESOLVED, state)
        self.set_found(state, f"import:{name}", source)

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
        """The body runs zero or more times; ``else`` runs only when the loop ends without a break.

        The body is re-run from the join of every way of reaching the loop's head until
        that join is stable. A value can only go from known to UNRESOLVED, so it becomes
        stable. A loop over a short list the check knows is followed item by item.
        """
        if not isinstance(node, ast.While):
            iterable = self.eval(node.iter, state)
            if isinstance(iterable, (list, tuple)) and len(iterable) <= _UNROLL:
                return self.unrolled(node, list(iterable), state)
            self.escape(iterable)  # the loop variable holds its items
        breaks: list[_State] = []
        finished: _State | None = None  # the loop ends without a break: its condition is false
        entry = state.copy()
        for _ in range(_MAX_ROUNDS):
            head = entry.copy()
            truth: bool | None = None  # a for loop may have another item, or none
            if isinstance(node, ast.While):
                try:
                    truth = _truth(self.eval(node.test, head))
                except _Dead:
                    finished = None
                    break
            finished = None if truth is True else head.copy()  # `while True` only ends by break
            if truth is False:
                break
            body = head.copy()
            if not isinstance(node, ast.While):
                for name in _names_bound(node.target):
                    self.bind(ast.Name(id=name, ctx=ast.Store()), UNRESOLVED, body)
            self.loops.append(([], []))
            ended = self.block(node.body, body)
            round_breaks, continues = self.loops.pop()
            breaks.extend(round_breaks)
            joined = self.merge([entry, *([] if ended else [body]), *continues])
            if _same_state(joined, entry):
                break
            entry = joined
        else:  # never happens (see above), but never certify an unfinished analysis
            for table in (entry.symbols, entry.found):
                for key in table:
                    table[key] = UNRESOLVED
            finished = entry
        paths = breaks
        if finished is not None and not self.block(node.orelse, finished):
            paths.append(finished)
        if not paths:
            return True  # it never exits
        state.take(self.merge(paths))
        return False

    def unrolled(self, node: ast.For | ast.AsyncFor, items: list[Any], state: _State) -> bool:
        """A loop over a known list: the body runs once per item, with the variable bound to it."""
        breaks: list[_State] = []
        current: _State | None = state
        for item in items:
            assert current is not None
            self.bind(node.target, item, current)
            self.loops.append(([], []))
            ended = self.block(node.body, current)
            round_breaks, continues = self.loops.pop()
            breaks.extend(round_breaks)
            following = ([] if ended else [current]) + continues
            if not following:
                current = None
                break
            current = following[0] if len(following) == 1 else self.merge(following)
        paths = breaks
        if current is not None and not self.block(node.orelse, current):
            paths.append(current)
        if not paths:
            return True
        state.take(paths[0] if len(paths) == 1 else self.merge(paths))
        return False

    def attempt(self, node: ast.AST, state: _State) -> bool:
        """try/except/else/finally.

        An exception can stop the body anywhere, in a function it calls too, so a handler
        starts from the state before the body with everything the body assigned or built
        UNRESOLVED and every edit it made to an object kept (see ``handler_entry``). The
        finally block runs on every way out: falling through, and every return, break,
        continue and sys.exit() inside the statement.
        """
        before, since = state.copy(), len(self.swaps)
        exits = self.exits()
        exit_marks = [len(paths) for paths in exits]
        self.writes.append(set())  # the whole statement, for an exception finally may swallow
        self.writes.append(set())  # the body, for the handlers
        ended = self.block(node.body, state)
        body_writes = self.writes.pop()
        ended = ended or self.block(node.orelse, state)  # the handlers do not cover the else block
        paths = [] if ended else [state.copy()]
        for handler in node.handlers:
            path = self.handler_entry(before, since, body_writes)
            try:
                if handler.type is not None:
                    self.eval(handler.type, path)
            except _Dead:
                continue
            if handler.name:
                self.set_symbol(path, handler.name, UNRESOLVED)
            if not self.block(handler.body, path):
                paths.append(path)
        all_writes = self.writes.pop()
        if node.finalbody:
            for target, mark in zip(exits, exit_marks):
                leaving, target[mark:] = target[mark:], []
                for path in leaving:
                    if path.frame.scope != state.frame.scope:  # sys.exit() in a function the body called
                        exit_path = self.handler_entry(before, since, all_writes)
                        exit_path.found = dict(path.found)
                        path = exit_path
                    if not self.block(node.finalbody, path):
                        target.append(path)  # it leaves as it would have; else finally redirected it
            if _redirects(node.finalbody):
                # A return, break or continue in finally swallows any exception raised before it.
                self.block(node.finalbody, self.handler_entry(before, since, all_writes))
        if not paths:
            return True
        state.take(self.merge(paths))
        return self.block(node.finalbody, state)

    def exits(self) -> list[list[_State]]:
        """The paths leaving the code being walked so far: by return, break, continue or sys.exit()."""
        out = [self.program_exits]
        if self.returns:
            out.append(self.returns[-1])
        if self.loops:
            out.extend(self.loops[-1])
        return out

    def handler_entry(self, before: _State, since: int, writes: set[tuple[Any, ...]]) -> _State:
        """The state an except handler may start from: ``before`` with the body's edits to
        objects replayed and everything the body wrote UNRESOLVED."""
        entry = before.copy()
        self.replay(entry, since)
        for kind, *where in writes:
            key = where[-1]
            if kind == "found":
                tables = [entry.found]
            elif kind == "local":
                tables = [entry.symbols] if where[0] == entry.frame.scope else []  # else another call's
            else:
                tables = [t for t in (entry.globals, entry.symbols) if t is not None
                          and (t is not entry.symbols or entry.frame.scope == 0 or key not in entry.frame.locals)]
            for table in tables:
                self.escape(table.get(key))
                table[key] = UNRESOLVED
        return entry

    def bind(self, target: ast.AST, value: Any, state: _State) -> None:
        if isinstance(target, ast.Name):
            self.set_symbol(state, target.id, value)
            if target.id in _CONVENTIONAL:
                self.set_found(state, f"assigned:{_CONVENTIONAL[target.id]}", value)
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
        if _may_have_effects(node):
            self.go_wild(node, "a lambda that calls code, which runs whenever it is called")
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

        A generator expression passed straight to a builtin that consumes it (list(), sum(),
        str.join() and the like) is followed as if run right away; any other runs its body
        when it is consumed, which the check cannot see.
        """
        if isinstance(node, ast.GeneratorExp) and id(node) not in self.consumed \
                and any(isinstance(n, (ast.Call, ast.NamedExpr)) for n in ast.walk(node)):
            self.go_wild(node, "a generator expression that calls code and is kept for later")
        first = node.generators[0]
        self.escape(self.eval(first.iter, state))  # the loop variables hold its items
        local = {name for gen in node.generators for name in _names_bound(gen.target)}
        outer = {name: state.symbols.get(name, _ABSENT) for name in local}

        def body(path: _State) -> Any:
            for i, gen in enumerate(node.generators):
                if i:
                    self.escape(self.eval(gen.iter, path))
                for name in _names_bound(gen.target):
                    self.set_symbol(path, name, UNRESOLVED)
                for condition in gen.ifs:
                    self.eval(condition, path)
            parts = (node.key, node.value) if isinstance(node, ast.DictComp) else (node.elt,)
            for part in parts:
                self.escape(self.eval(part, path))
            return UNRESOLVED

        for _ in range(_MAX_ROUNDS):  # each run may see what the one before it did; it becomes stable
            before = state.copy()
            self.alternatives([lambda path: UNRESOLVED, body], state)
            for name, value in outer.items():  # its variables do not leak out (a walrus does)
                if value is _ABSENT:
                    state.symbols.pop(name, None)
                else:
                    self.set_symbol(state, name, value)
            if _same_state(before, state):
                break
        return UNRESOLVED

    _eval_ListComp = _eval_SetComp = _eval_DictComp = _eval_GeneratorExp = comprehension

    def _eval_Subscript(self, node: ast.Subscript, state: _State) -> Any:
        # Still fully static: a dict or list reached through a name and indexed by a
        # constant, e.g. kwargs_data["exposure_time"].
        since = len(self.swaps)
        base = self.eval(node.value, state)
        key = self.eval(node.slice, state)
        [base] = self.fresh(since, [base])  # the key's evaluation may have edited it
        value = _index(base, key)
        if _unknown(value):
            self.escape(base)  # an unknown key or a slice may reach any of its items
        return value

    def _eval_Attribute(self, node: ast.Attribute, state: _State) -> Any:
        self.escape(self.eval(node.value, state))  # an attribute may share the object's parts
        return UNRESOLVED

    def _eval_List(self, node: ast.List, state: _State) -> Any:
        items = self.items(node.elts, state)
        return UNRESOLVED if items is None else items

    def _eval_Tuple(self, node: ast.Tuple, state: _State) -> Any:
        items = self.items(node.elts, state)
        return UNRESOLVED if items is None else tuple(items)

    def items(self, elts: list[ast.expr], state: _State) -> list[Any] | None:
        """The items of a list or tuple display; None when a *expansion leaves them unknown."""
        since = len(self.swaps)
        out: list[Any] = []
        known = True
        for el in elts:
            if isinstance(el, ast.Starred):
                value = self.eval(el.value, state)
                if isinstance(value, (list, tuple)):
                    out.extend(value)
                    continue
                self.escape(value)
                known = False  # how many items it adds, and so where the rest go, is unknown
            else:
                out.append(self.eval(el, state))
        out = self.fresh(since, out)  # a later item's evaluation may have edited an earlier one
        if not known:
            self.escape(out)
            return None
        return out

    def _eval_Starred(self, node: ast.Starred, state: _State) -> Any:
        self.escape(self.eval(node.value, state))
        return UNRESOLVED

    def _eval_Dict(self, node: ast.Dict, state: _State) -> Any:
        since = len(self.swaps)
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
        out = dict(zip(out, self.fresh(since, list(out.values()))))  # as for a list display
        if not resolved:
            self.escape(out)
            return UNRESOLVED
        return out

    def _eval_Call(self, node: ast.Call, state: _State) -> Any:
        func = node.func
        since = len(self.swaps)
        receiver = self.eval(func.value, state) if isinstance(func, ast.Attribute) else _ABSENT
        if isinstance(func, ast.Name):
            callee = state.symbols.get(func.id, _ABSENT)
        elif isinstance(func, ast.Attribute):
            callee = _ABSENT
        else:
            callee = self.eval(func, state)  # e.g. handlers[0](...)
        positional: list[Any] = []
        keywords: dict[str, Any] = {}
        expansions: list[Any] = []
        spread: list[Any] = []
        opaque = False
        eager = self.is_builtin(func, state) in _EAGER_BUILTINS \
            or (isinstance(func, ast.Attribute) and func.attr == "join" and isinstance(receiver, str))
        for arg in node.args:
            if isinstance(arg, ast.GeneratorExp) and eager:
                self.consumed.add(id(arg))  # run now; any other call may keep it for later
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
        # Evaluating a later argument may have edited an object an earlier one, or the receiver, holds.
        receiver, callee, positional, keywords, expansions, spread = self.fresh(
            since, [receiver, callee, positional, keywords, expansions, spread])
        return self.call(node, callee, receiver, _Args(positional, keywords, expansions, spread, opaque), state)

    def call(self, node: ast.Call, callee: Any, receiver: Any, args: _Args, state: _State) -> Any:
        """What a call returns, as far as the check follows it."""
        func = node.func
        name = _call_name(func)
        builder = self.builder(func, state) if callee is _ABSENT else None
        if builder is not None:
            built = _build(name, args)
            key = f"built:{name}"
            previous = state.found.get(key, ())
            self.set_found(state, key, UNRESOLVED if previous == UNRESOLVED else previous + (built,))
            return built
        if name == "image" and isinstance(func, ast.Attribute):
            bound = args.bind(_PARAMETERS["image"])
            self.set_found(state, "rendered", _Render(_snapshot(bound.get("kwargs_lens", _MISSING)),
                                                      _snapshot(bound.get("kwargs_source", _MISSING)),
                                                      _snapshot(receiver), _snapshot(_extras("image", args))))
            return UNRESOLVED
        qualified = self.qualname(func, state) if callee is _ABSENT else None
        if qualified in ("sys.exit", "os._exit", "exit", "quit"):
            if _exit_status(args) is not False:  # sys.exit(1) or sys.exit("message") is a failed run
                self.program_exits.append(state.copy())
            raise _Dead
        if qualified is not None and (qualified in _DYNAMIC_BUILTINS
                                      or qualified.split(".")[0] in ("unittest", "mock")
                                      or (qualified in ("setattr", "delattr") and node.args
                                          and self.patches(node.args[0], state))):
            self.go_wild(node, f"{qualified}() changes code or names the check cannot see")
        if isinstance(callee, _Function):
            return self.run(callee, args, state)
        if not isinstance(func, (ast.Name, ast.Attribute)):
            self.escape(callee)
        if isinstance(receiver, (dict, list)):
            return self.container_method(receiver, name, args, state)
        if isinstance(receiver, _Built) and name in _LENSTRONOMY_READS:
            return UNRESOLVED
        builtin = self.is_builtin(func, state)
        if builtin in _PURE_BUILTINS:
            return _builtin_value(builtin, args)
        if builtin in _CAPTURING_BUILTINS:
            for value in args.values():
                self.escape(value)
            return UNRESOLVED
        module_call = self.module_like(func, state)
        if module_call and isinstance(func, ast.Attribute):
            dotted = qualified or ""
            if dotted in _ARRAY_CALLS:
                return _array_value(args)
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

    def plain_context(self, expr: ast.expr, state: _State) -> bool:
        """A context manager known not to swallow exceptions: open() and a few like it."""
        if not isinstance(expr, ast.Call):
            return False
        if isinstance(expr.func, ast.Attribute) and expr.func.attr == "open":
            return True  # e.g. Path(...).open()
        return self.qualname(expr.func, state) in _PLAIN_CONTEXTS

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

    def run(self, fn: _Function, args: _Args, state: _State) -> Any:
        """Run a called function's body in its own scope; what it builds still counts.

        The body sees its own locals (UNRESOLVED until assigned), then the names of the
        scope it was defined in: the module's, or for a nested function the call it was
        defined in, which must be the one calling it. Its global rebindings, and a nested
        function's rebinding of its enclosing names, come back to the caller, and so do its
        edits to objects. Raises _Dead when the function never returns.
        """
        node = fn.node
        nested = fn.scope != 0
        reason = None
        if node in self.active or len(self.active) >= _MAX_CALL_DEPTH:
            reason = f"{node.name}() calls itself, or calls nest too deep, which the check does not follow"
        elif nested and fn.scope != state.frame.scope:
            reason = f"{node.name}() is called outside the function that defines it"
        elif _is_generator(node):
            reason = f"{node.name}() is a generator or async function, whose body runs later"
        if reason is not None:
            if reason.startswith(f"{node.name}() is a generator") and not _may_have_effects(node):
                return UNRESOLVED
            self.go_wild(node, reason)
            self.unknown_call(state, args, _ABSENT, True)
            return UNRESOLVED
        declared_global, local_names = _scope_names(node)
        a = node.args
        positional = [p.arg for p in (*a.posonlyargs, *a.args)]
        given = args.bind(tuple(positional))
        named = {*positional, *(k.arg for k in a.kwonlyargs)}
        for extra in [*args.positional[len(positional):], *args.spread,
                      *(v for k, v in args.keywords.items() if k not in named)]:
            self.escape(extra)  # it goes to *args or **kwargs, which are UNRESOLVED
        module_names = state.global_names()
        self.scopes += 1
        frame = _Frame(self.scopes, declared_global, local_names)
        local = _State(state.symbols if nested else module_names, state.found, frame, module_names)
        for name in declared_global:
            if name in module_names:
                local.symbols[name] = module_names[name]
            else:
                local.symbols.pop(name, None)
        for name in local_names:
            local.symbols[name] = UNRESOLVED  # unbound until the body assigns it
        for name in _scope_imports(node):
            local.symbols.pop(name, None)  # an imported module is not one of the script's values
        for p in (*positional, *(k.arg for k in a.kwonlyargs)):
            self.set_symbol(local, p, given[p] if p in given else fn.defaults.get(p, UNRESOLVED))
        for extra in (a.vararg, a.kwarg):
            if extra is not None:
                self.set_symbol(local, extra.arg, UNRESOLVED)
        since = len(self.swaps)
        self.active.append(node)
        self.returns.append([])
        ended = self.block(node.body, local)
        paths = self.returns.pop() + ([] if ended else [local])
        self.active.pop()
        if not paths:
            self.replay(state, since)
            raise _Dead
        final = self.merge(paths)
        state.found = final.found
        assert final.globals is not None
        for name, value in final.globals.items():  # its global rebindings
            if not _same(value, module_names.get(name, _ABSENT)):
                self.set_global(state, name, value)
        if nested:  # its nonlocal rebindings
            for name, value in final.symbols.items():
                if name not in local_names and name not in declared_global \
                        and not _same(value, state.symbols.get(name, _ABSENT)):
                    self.set_symbol(state, name, value)
        self.replay(state, since)  # what it changed in the objects it was given or could reach
        return UNRESOLVED


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
    compile(tree, "<script>", "exec", dont_inherit=True)  # e.g. a return outside a function
    state = _State({"__name__": "__main__"})  # the check is about the script run directly
    walker = _Walker()
    ended = walker.block(tree.body, state)
    # The script ends where it falls off the end or calls sys.exit(); if every path
    # raises, there is no successful run, so the state as walked is kept.
    exits = [p if p.globals is None else _State(p.globals, p.found) for p in walker.program_exits]
    paths = exits + ([] if ended else [state])
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
        found.extras.append(("image", rendered.extras))
        image_model = rendered.image_model
        if not (isinstance(image_model, _Built) and image_model.kind == "ImageModel"):
            image_model = UNRESOLVED  # the image() call's ImageModel cannot be identified
    else:
        found.kwargs_lens = f.get("assigned:kwargs_lens", _MISSING)
        found.kwargs_source = f.get("assigned:kwargs_source", _MISSING)
        image_model = _only(f.get("built:ImageModel"))

    if isinstance(image_model, _Built) and image_model.kind == "ImageModel":
        found.extras.append(("ImageModel", image_model.fields["extras"]))
    for attr, role, kind in (("lens_model_list", "lens", "LensModel"),
                             ("source_model_list", "source", "LightModel")):
        model = _component(image_model, role, kind, f)
        if isinstance(model, _Built):
            setattr(found, attr, model.fields["models"])
            found.extras.append((kind, model.fields["extras"]))
            if kind == "LensModel":
                found.lens_redshifts = model.fields["redshifts"]
        elif model == UNRESOLVED:
            setattr(found, attr, UNRESOLVED)
        elif model is None:
            setattr(found, attr, f.get(f"assigned:{attr}", _MISSING))

    psf = _component(image_model, "psf", "PSF", f)
    if isinstance(psf, _Built):
        found.extras.append(("PSF", psf.fields["extras"]))
        found.psf_type, found.psf_fwhm = psf.fields["psf_type"], psf.fields["fwhm"]
        found.psf_pixel_size, found.psf_kernel = psf.fields["pixel_size"], psf.fields["kernel"]
    elif psf == UNRESOLVED:
        found.psf_type = found.psf_fwhm = found.psf_pixel_size = found.psf_kernel = UNRESOLVED

    data = _component(image_model, "data", "ImageData", f)
    if isinstance(data, _Built):
        found.extras.append(("ImageData", data.fields["extras"]))
    config = data.fields["config"] if isinstance(data, _Built) else data
    if config is None:  # no ImageModel or ImageData: the only data_configure_simple call
        config = _only(f.get("built:data_configure_simple"))
    if isinstance(config, _Built):
        found.extras.append(("data_configure_simple", config.fields["extras"]))
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
    if walker.wild:
        # The script runs its own code at points the check cannot see: nothing is certain.
        for attr, value in vars(found).items():
            if attr not in ("notes", "extras"):
                setattr(found, attr, UNRESOLVED)
        found.extras = []
        found.notes = walker.wild
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


def _match(expected: Any, actual: Any) -> bool | None:
    """True if the script's value is the parameter set's, False if it is not, None if unknown.

    Numbers match within _REL_TOL (see _numbers_match); lists (or tuples) match item by
    item. A value that is UNRESOLVED, or that has an UNRESOLVED part where everything
    else matches, is unknown: it is never reported as matching.
    """
    if _unknown(actual):
        return None
    if _is_number(expected):
        return _numbers_match(expected, actual)
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
            return False
        results = [_match(e, a) for e, a in zip(expected, actual)]
        return False if False in results else (None if None in results else True)
    return bool(expected == actual) and type(expected) is type(actual)


def compare_code_to_params(code: str, params: dict[str, Any]) -> dict[str, Any]:
    """Diff the script's lenstronomy inputs against a parameter set.

    Only the parameter set's own fields are checked (extra keys the script
    adds are fine). ``passed`` requires every checked field to match:
    diverged, missing and unresolved all block, so a script that computes a
    value at runtime cannot silently pass.
    """
    try:
        found = extract_lenstronomy_inputs(code)
    except (SyntaxError, ValueError) as exc:  # ValueError: e.g. a null byte in the source
        return {"passed": False, "matched": [], "diverged": [], "missing": ["<script>"],
                "unresolved": [], "messages": [f"script is not parseable: {exc}"]}
    except (RecursionError, MemoryError):
        return {"passed": False, "matched": [], "diverged": [], "missing": [], "unresolved": ["<script>"],
                "messages": ["<script>: nested too deeply for the check to follow; simplify it."]}

    matched: list[str] = []
    diverged: list[dict[str, Any]] = []
    missing: list[str] = []
    unresolved: list[str] = []
    unexpected: list[str] = []  # diverged: the script passes something the parameter set does not have

    def record(field: str, expected: Any, actual: Any) -> None:
        if actual is _MISSING:
            missing.append(field)
            return
        result = _match(expected, actual)
        if result is None:
            unresolved.append(field)
        elif result:
            matched.append(field)
        else:
            diverged.append({"field": field, "expected": expected, "actual": actual})

    record("lens_model_list", params["lens_model_list"], found.lens_model_list)
    record("source_model_list", params["source_model_list"], found.source_model_list)

    # Redshifts: every one the rendering LensModel is given. A single-plane LensModel
    # given none renders the same image whatever the redshifts (the profiles here are in
    # angles), so there is nothing to compare; multi-plane needs z_source and a redshift
    # for each deflector, all of which must be the parameter set's.
    redshifts = found.lens_redshifts
    if isinstance(redshifts, dict):
        z_lens, z_source = params["z_lens"], params["z_source"]
        expected_z = {"z_lens": z_lens, "z_source": z_source, "z_source_convention": z_source,
                      "z_lens_convention": z_lens,
                      "lens_redshift_list": [z_lens] * len(params["lens_model_list"])}
        multi_plane = redshifts["multi_plane"]
        if _unknown(multi_plane):
            unresolved.append("multi_plane")
        for name, expected in expected_z.items():
            value = redshifts[name]
            if value is not None:
                record(name, expected, value)
            elif multi_plane is True and name in ("z_source", "lens_redshift_list"):
                missing.append(name)  # lenstronomy's multi-plane mode requires it

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
        models = params["lens_model_list" if label == "kwargs_lens" else "source_model_list"]
        for i, exp_dict in enumerate(expected_kwargs):
            if i < len(actual_kwargs) and actual_kwargs[i] == UNRESOLVED:
                unresolved.append(f"{label}[{i}]")
                continue
            if i >= len(actual_kwargs) or not isinstance(actual_kwargs[i], dict):
                missing.append(f"{label}[{i}]")
                continue
            for key, exp_val in exp_dict.items():
                record(f"{label}[{i}].{key}", exp_val, actual_kwargs[i].get(key, _MISSING))
            # Keys the script passes that the parameter set leaves out: an optional one must
            # be lenstronomy's default (0), anything else is not a parameter of the profile.
            name = models[i] if i < len(models) else None
            optional = [k for k in _validator.PROFILE_PARAMS.get(name, ())
                        if k not in _validator.REQUIRED_PARAMS.get(name, ())]
            for key, value in actual_kwargs[i].items():
                if key in exp_dict:
                    continue
                field = f"{label}[{i}].{key}"
                if key in optional:
                    record(field, 0.0, value)
                else:
                    unexpected.append(field)
                    diverged.append({"field": field, "expected": _NOT_IN_PARAMS, "actual": value})
        for i in range(len(expected_kwargs), len(actual_kwargs)):
            unexpected.append(f"{label}[{i}]")
            diverged.append({"field": f"{label}[{i}]", "expected": _NOT_IN_PARAMS, "actual": actual_kwargs[i]})

    # The arguments of the calls that render which the parameter set does not describe:
    # lenstronomy's default is what the parameter set assumes.
    defaulted: set[str] = set()
    for call, extras in found.extras:
        for argument, value in extras.items():
            field = f"{call}{argument}" if argument.startswith("(") else f"{call}.{argument}"
            default = _DEFAULTS[call].get(argument, _NOT_IN_PARAMS)
            if default is _ANY:
                continue
            result = None if _has_unknown(value) else (
                False if default is _NOT_IN_PARAMS else _match(default, value))
            if result is None:
                unresolved.append(field)
            elif not result:
                if default is _NOT_IN_PARAMS:
                    unexpected.append(field)  # not an argument of this call in lenstronomy
                else:
                    defaulted.add(field)
                diverged.append({"field": field, "expected": default, "actual": value})

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
    if psf.get("psf_type") == "PIXEL":
        # The kernel, element by element as written: a runtime-computed one is UNRESOLVED.
        record("psf_kernel", psf["kernel_point_source"], found.psf_kernel)

    messages: list[str] = [f"The check cannot follow this script, so every value is unresolved: {note}."
                           for note in found.notes]
    for d in diverged:
        if d["field"] == "psf_kernel":
            messages.append("psf_kernel: the script's kernel_point_source is not the parameter "
                            "set's; use the parameter-set kernel exactly, as a literal.")
            continue
        if d["field"] in defaulted:
            messages.append(f"{d['field']}: the script passes {d['actual']!r}, but the parameter set "
                            f"assumes lenstronomy's default, {d['expected']!r}; leave the argument out.")
            continue
        if d["field"] in unexpected:
            messages.append(f"{d['field']}: the script passes {d['actual']!r}, which is not in the "
                            "parameter set; remove it, or add it to the parameter set and validate "
                            "that again.")
            continue
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
