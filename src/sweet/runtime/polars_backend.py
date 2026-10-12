"""Executes logical plans on Polars lazy frames. Polars objects never leave the runtime package."""
from __future__ import annotations

import polars as pl

from ..ir import plan_nodes as P
from . import io
from .expression_compiler import to_polars


class PolarsBackend:
    def __init__(self):
        # Only explicit collect() results are cached; nothing is cached implicitly.
        self._collected = {}

    def lazy(self, plan) -> pl.LazyFrame:
        if isinstance(plan, P.Scan):
            return io.scan(plan.path, plan.options)
        if isinstance(plan, P.Collected):
            df = self._collected.get(plan)
            if df is None:
                df = self.lazy(plan.input).collect()
                self._collected[plan] = df
            return df.lazy()
        if isinstance(plan, P.Join):
            return self.lazy(plan.left).join(
                self.lazy(plan.right), on=list(plan.keys), how=plan.how, coalesce=True
            )
        child = self.lazy(plan.input)
        if isinstance(plan, P.Filter):
            return child.filter(to_polars(plan.predicate))
        if isinstance(plan, P.Project):
            return child.select(list(plan.columns))
        if isinstance(plan, P.Derive):
            return child.with_columns(to_polars(plan.expr).alias(plan.name))
        if isinstance(plan, P.Sort):
            return child.sort(
                [c for c, _ in plan.keys], descending=[d for _, d in plan.keys],
                nulls_last=True, maintain_order=True,
            )
        if isinstance(plan, P.Limit):
            return child.head(plan.n)
        if isinstance(plan, P.Tail):
            return child.tail(plan.n)
        if isinstance(plan, P.DropMissing):
            return child.drop_nulls(subset=list(plan.columns) if plan.columns else None)
        if isinstance(plan, P.Aggregate):
            return child.group_by(list(plan.keys), maintain_order=True).agg(
                [to_polars(e).alias(n) for n, e in plan.aggs]
            )
        raise TypeError(f"cannot execute {plan!r}")

    def collect(self, plan) -> pl.DataFrame:
        return self.lazy(plan).collect()
