"""Anne's type system and expression type checker."""
from __future__ import annotations

import polars as pl

from ..diagnostics.errors import SweetSemanticError, suggest
from ..ir.expressions import Agg, Bin, Col, Lit, Neg, Not

INTEGER, FLOAT, STRING, BOOLEAN = "INTEGER", "FLOAT", "STRING", "BOOLEAN"
DATE, DATETIME, OTHER = "DATE", "DATETIME", "OTHER"
NUMERIC = frozenset({INTEGER, FLOAT})
TEMPORAL = frozenset({DATE, DATETIME})
ARITH_OPS = frozenset({"+", "-", "*", "/", "%"})
CMP_OPS = frozenset({"==", "!=", "<", "<=", ">", ">="})


def from_polars(dtype) -> str:
    if dtype.is_integer():
        return INTEGER
    if dtype.is_float() or getattr(dtype, "is_decimal", lambda: False)():
        return FLOAT
    if dtype == pl.String:
        return STRING
    if dtype == pl.Boolean:
        return BOOLEAN
    if dtype == pl.Date:
        return DATE
    if dtype == pl.Datetime:
        return DATETIME
    return OTHER


def lit_type(v) -> str:
    if isinstance(v, bool):
        return BOOLEAN
    if isinstance(v, int):
        return INTEGER
    if isinstance(v, float):
        return FLOAT
    return STRING


def unknown_column(name, available):
    hint = suggest(name, available) or ("available columns: " + ", ".join(available))
    return SweetSemanticError(f"unknown column '{name}'", hint=hint)


def comparable(a, b) -> bool:
    if OTHER in (a, b) or a == b:
        return True
    if a in NUMERIC and b in NUMERIC:
        return True
    if a in TEMPORAL and b in TEMPORAL:
        return True
    return (a in TEMPORAL and b == STRING) or (b in TEMPORAL and a == STRING)


def infer(e, schema, *, group_keys=None, _in_agg=False) -> str:
    """Return the Anne type of `e` under `schema`, or raise SweetSemanticError.

    group_keys=None  -> aggregate functions are not allowed (filter/derive/...).
    group_keys=set() -> summarize context: bare columns must be group keys.
    """
    cols = dict(schema)
    rec = lambda x, **kw: infer(x, schema, group_keys=group_keys, _in_agg=kw.get("_in_agg", _in_agg))
    if isinstance(e, Lit):
        return lit_type(e.value)
    if isinstance(e, Col):
        t = cols.get(e.name)
        if t is None:
            raise unknown_column(e.name, list(cols))
        if group_keys is not None and not _in_agg and e.name not in group_keys:
            raise SweetSemanticError(
                f"column '{e.name}' must be inside an aggregate or be a group key",
                hint=f"for example: sum({e.name})",
            )
        return t
    if isinstance(e, Neg):
        t = rec(e.operand)
        if t not in NUMERIC and t != OTHER:
            raise SweetSemanticError(f"cannot negate a {t} value")
        return t
    if isinstance(e, Not):
        t = rec(e.operand)
        if t not in (BOOLEAN, OTHER):
            raise SweetSemanticError(f"'not' needs a BOOLEAN value, got {t}")
        return BOOLEAN
    if isinstance(e, Bin):
        a, b, op = rec(e.left), rec(e.right), e.op
        if op in ARITH_OPS:
            if op == "+" and a == b == STRING:
                return STRING
            if a in NUMERIC | {OTHER} and b in NUMERIC | {OTHER}:
                if OTHER in (a, b):
                    return OTHER
                return FLOAT if (op == "/" or FLOAT in (a, b)) else INTEGER
            raise SweetSemanticError(f"cannot apply '{op}' to {a} and {b}")
        if op in CMP_OPS:
            if not comparable(a, b):
                raise SweetSemanticError(f"cannot compare {a} with {b} using '{op}'")
            return BOOLEAN
        if op in ("and", "or"):
            if a not in (BOOLEAN, OTHER) or b not in (BOOLEAN, OTHER):
                raise SweetSemanticError(f"'{op}' needs BOOLEAN operands, got {a} and {b}")
            return BOOLEAN
        raise SweetSemanticError(f"unknown operator '{op}'")
    if isinstance(e, Agg):
        if group_keys is None:
            raise SweetSemanticError(
                f"aggregate function '{e.func}' is only allowed inside summarize()",
                hint="use group_by(...).summarize(name = " + e.func + "(column))",
            )
        if _in_agg:
            raise SweetSemanticError("aggregate functions cannot be nested")
        t = rec(e.arg, _in_agg=True) if e.arg is not None else None
        if e.func == "count":
            return INTEGER
        if e.func in ("sum", "mean", "median"):
            if t not in NUMERIC and t != OTHER:
                raise SweetSemanticError(f"{e.func}() needs a numeric column, got {t}")
            return t if e.func == "sum" else FLOAT
        if t == BOOLEAN:
            raise SweetSemanticError(f"{e.func}() does not support BOOLEAN")
        return t
    raise TypeError(f"unknown expression {e!r}")
