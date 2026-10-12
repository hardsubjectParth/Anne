from __future__ import annotations

import math
import operator

from ..ir.expressions import Agg, Bin, Lit, Neg, Not

_NO = object()
_ARITH = {"+": operator.add, "-": operator.sub, "*": operator.mul}
_CMP = {"==": operator.eq, "!=": operator.ne, "<": operator.lt, "<=": operator.le,
        ">": operator.gt, ">=": operator.ge}


def _num(v):
    return type(v) in (int, float)


def _ok(v):
    if type(v) is int:
        return -(2 ** 63) <= v < 2 ** 63
    if type(v) is float:
        return math.isfinite(v)
    return True


def _eval(op, a, b):
    try:
        if _num(a) and _num(b):
            if op in _ARITH:
                v = _ARITH[op](a, b)
            elif op == "/":
                if b == 0:
                    return _NO
                v = a / b
            elif op in _CMP:
                return _CMP[op](a, b)
            else:
                return _NO
            return v if _ok(v) else _NO
        if type(a) is str and type(b) is str:
            if op == "+":
                return a + b
            if op in _CMP:
                return _CMP[op](a, b)
        if type(a) is bool and type(b) is bool:
            if op == "and":
                return a and b
            if op == "or":
                return a or b
            if op in ("==", "!="):
                return _CMP[op](a, b)
    except ArithmeticError:
        pass
    return _NO


def _bool_lit(e):
    return isinstance(e, Lit) and type(e.value) is bool


def fold_expr(e):
    if isinstance(e, Neg):
        o = fold_expr(e.operand)
        if isinstance(o, Lit) and _num(o.value):
            return Lit(-o.value)
        return Neg(o)
    if isinstance(e, Not):
        o = fold_expr(e.operand)
        if _bool_lit(o):
            return Lit(not o.value)
        return Not(o)
    if isinstance(e, Agg):
        return Agg(e.func, fold_expr(e.arg) if e.arg is not None else None)
    if isinstance(e, Bin):
        l, r = fold_expr(e.left), fold_expr(e.right)
        if isinstance(l, Lit) and isinstance(r, Lit):
            v = _eval(e.op, l.value, r.value)
            if v is not _NO:
                return Lit(v)
        if e.op == "and":
            if _bool_lit(l):
                return r if l.value else l
            if _bool_lit(r):
                return l if r.value else r
        if e.op == "or":
            if _bool_lit(l):
                return l if l.value else r
            if _bool_lit(r):
                return r if r.value else l
        return Bin(e.op, l, r)
    return e
