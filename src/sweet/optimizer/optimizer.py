"""Sweet's logical optimizer: constant folding and filter fusion.

Projection/predicate pushdown are intentionally NOT implemented here; Polars' lazy optimizer does them.
"""
from __future__ import annotations

from dataclasses import replace

from ..ir import plan_nodes as P
from ..ir.expressions import Lit
from .constant_folding import fold_expr
from .filter_fusion import fuse_filters


def _fold_node(node):
    if isinstance(node, P.Filter):
        pred = fold_expr(node.predicate)
        if isinstance(pred, Lit) and pred.value is True:
            return node.input  # filter(true) keeps every row
        return replace(node, predicate=pred)
    if isinstance(node, P.Derive):
        return replace(node, expr=fold_expr(node.expr))
    if isinstance(node, P.Aggregate):
        return replace(node, aggs=tuple((n, fold_expr(e)) for n, e in node.aggs))
    return node


def optimize(plan):
    plan = P.map_children(plan, optimize)
    plan = _fold_node(plan)
    return fuse_filters(plan)
