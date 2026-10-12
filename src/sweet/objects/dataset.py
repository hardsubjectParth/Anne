"""Language-level Dataset value: an immutable (logical plan, schema) pair."""
from __future__ import annotations

from dataclasses import dataclass

from ..diagnostics.errors import SweetSemanticError, suggest
from ..ir import plan_nodes as P
from ..semantic import types as T
from ..semantic.types import unknown_column

JOIN_TYPES = ("inner", "left", "full")


def _check_columns(schema, names):
    available = [n for n, _ in schema]
    for n in names:
        if n not in available:
            raise unknown_column(n, available)


def _unique(names, what):
    seen = set()
    for n in names:
        if n in seen:
            raise SweetSemanticError(f"column '{n}' is listed twice in {what}")
        seen.add(n)


@dataclass(frozen=True)
class Dataset:
    plan: P.PlanNode
    schema: tuple  # ((column, anne_type), ...)

    @property
    def columns(self) -> tuple:
        return tuple(n for n, _ in self.schema)

    def filter(self, predicate):
        t = T.infer(predicate, self.schema)
        if t not in (T.BOOLEAN, T.OTHER):
            raise SweetSemanticError(
                f"filter() condition must be a BOOLEAN expression, got {t}",
                hint="use a comparison such as price > 100",
            )
        return Dataset(P.Filter(self.plan, predicate), self.schema)

    def select(self, *names):
        if not names:
            raise SweetSemanticError("select() needs at least one column")
        _check_columns(self.schema, names)
        _unique(names, "select()")
        d = dict(self.schema)
        return Dataset(P.Project(self.plan, tuple(names)), tuple((n, d[n]) for n in names))

    def derive(self, name, expr):
        t = T.infer(expr, self.schema)
        if name in self.columns:
            schema = tuple((n, t if n == name else ty) for n, ty in self.schema)
        else:
            schema = self.schema + ((name, t),)
        return Dataset(P.Derive(self.plan, name, expr), schema)

    def sort(self, keys):
        if not keys:
            raise SweetSemanticError("sort() needs at least one column")
        _check_columns(self.schema, [c for c, _ in keys])
        return Dataset(P.Sort(self.plan, tuple(keys)), self.schema)

    def limit(self, n):
        if not isinstance(n, int) or n < 0:
            raise SweetSemanticError("limit() needs a non-negative integer")
        return Dataset(P.Limit(self.plan, n), self.schema)

    head = limit

    def tail(self, n):
        if not isinstance(n, int) or n < 0:
            raise SweetSemanticError("tail() needs a non-negative integer")
        return Dataset(P.Tail(self.plan, n), self.schema)

    def drop_missing(self, *names):
        _check_columns(self.schema, names)
        _unique(names, "drop_missing()")
        return Dataset(P.DropMissing(self.plan, tuple(names)), self.schema)

    def group_by(self, *names):
        from .grouped_dataset import GroupedDataset

        if not names:
            raise SweetSemanticError("group_by() needs at least one column")
        _check_columns(self.schema, names)
        _unique(names, "group_by()")
        return GroupedDataset(self, tuple(names))

    def join(self, other, keys, how="inner"):
        if how not in JOIN_TYPES:
            raise SweetSemanticError(
                f"unsupported join type '{how}'", hint="supported: " + ", ".join(JOIN_TYPES)
            )
        if not keys:
            raise SweetSemanticError("join() needs at least one key column")
        ld, rd = dict(self.schema), dict(other.schema)
        for k in keys:
            if k not in ld:
                raise SweetSemanticError(f"join key '{k}' not found in the left dataset",
                                         hint=suggest(k, ld) or "left columns: " + ", ".join(ld))
            if k not in rd:
                raise SweetSemanticError(f"join key '{k}' not found in the right dataset",
                                         hint=suggest(k, rd) or "right columns: " + ", ".join(rd))
            if ld[k] != rd[k] and T.OTHER not in (ld[k], rd[k]):
                raise SweetSemanticError(
                    f"join key '{k}' has incompatible types: {ld[k]} (left) vs {rd[k]} (right)")
        out = list(self.schema)
        taken = set(ld)
        for name, ty in other.schema:
            if name in keys:
                continue
            final = name + "_right" if name in taken else name
            if final in taken:
                raise SweetSemanticError(f"join would produce a duplicate column '{final}'")
            taken.add(final)
            out.append((final, ty))
        return Dataset(P.Join(self.plan, other.plan, tuple(keys), how), tuple(out))

    def collect(self):
        return Dataset(P.Collected(self.plan), self.schema)
