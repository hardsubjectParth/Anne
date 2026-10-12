from __future__ import annotations

from dataclasses import dataclass

from ..diagnostics.errors import SweetSemanticError
from ..ir import plan_nodes as P
from ..ir.expressions import contains_agg
from ..semantic import types as T
from .dataset import Dataset


@dataclass(frozen=True)
class GroupedDataset:
    dataset: Dataset
    keys: tuple

    def summarize(self, aggs):
        if not aggs:
            raise SweetSemanticError("summarize() needs at least one aggregate, e.g. total = sum(price)")
        d = dict(self.dataset.schema)
        out = [(k, d[k]) for k in self.keys]
        taken = set(self.keys)
        for name, expr in aggs:
            if name in taken:
                raise SweetSemanticError(f"output column '{name}' is defined twice (or clashes with a group key)")
            if not contains_agg(expr):
                raise SweetSemanticError(
                    f"'{name}' must use an aggregate function (sum, mean, median, min, max, count)")
            out.append((name, T.infer(expr, self.dataset.schema, group_keys=set(self.keys))))
            taken.add(name)
        return Dataset(P.Aggregate(self.dataset.plan, self.keys, tuple(aggs)), tuple(out))
