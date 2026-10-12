from __future__ import annotations

from ..ir.expressions import Bin
from ..ir.plan_nodes import Filter


def fuse_filters(node):
    """Filter(Filter(x, a), b) -> Filter(x, a and b)."""
    if isinstance(node, Filter) and isinstance(node.input, Filter):
        return Filter(node.input.input, Bin("and", node.input.predicate, node.predicate))
    return node
