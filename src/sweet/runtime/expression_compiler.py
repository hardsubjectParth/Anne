"""Translates expression IR into Polars expressions (a controlled compiler, no eval)."""
from __future__ import annotations

import operator

import polars as pl

from ..ir.expressions import Agg, Bin, Col, Lit, Neg, Not

_OPS = {
    "+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv, "%": operator.mod,
    "==": operator.eq, "!=": operator.ne, "<": operator.lt, "<=": operator.le,
    ">": operator.gt, ">=": operator.ge, "and": operator.and_, "or": operator.or_,
}


def to_polars(e) -> pl.Expr:
    if isinstance(e, Col):
        return pl.col(e.name)
    if isinstance(e, Lit):
        return pl.lit(e.value)
    if isinstance(e, Neg):
        return -to_polars(e.operand)
    if isinstance(e, Not):
        return ~to_polars(e.operand)
    if isinstance(e, Bin):
        return _OPS[e.op](to_polars(e.left), to_polars(e.right))
    if isinstance(e, Agg):
        if e.arg is None:
            return pl.len()
        x = to_polars(e.arg)
        return {"sum": x.sum, "mean": x.mean, "median": x.median, "min": x.min,
                "max": x.max, "count": x.count}[e.func]()
    raise TypeError(f"cannot compile {e!r}")
