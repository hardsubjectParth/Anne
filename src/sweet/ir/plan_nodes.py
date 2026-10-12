from __future__ import annotations

from dataclasses import dataclass, fields, replace


@dataclass(frozen=True)
class PlanNode:
    pass


@dataclass(frozen=True)
class Scan(PlanNode):
    path: str
    options: tuple = ()


@dataclass(frozen=True)
class Filter(PlanNode):
    input: PlanNode
    predicate: object


@dataclass(frozen=True)
class Project(PlanNode):
    input: PlanNode
    columns: tuple


@dataclass(frozen=True)
class Derive(PlanNode):
    input: PlanNode
    name: str
    expr: object


@dataclass(frozen=True)
class Sort(PlanNode):
    input: PlanNode
    keys: tuple  # ((column, descending), ...)


@dataclass(frozen=True)
class Limit(PlanNode):
    input: PlanNode
    n: int


@dataclass(frozen=True)
class Tail(PlanNode):
    input: PlanNode
    n: int


@dataclass(frozen=True)
class DropMissing(PlanNode):
    input: PlanNode
    columns: tuple  # empty tuple = all columns


@dataclass(frozen=True)
class Aggregate(PlanNode):
    input: PlanNode
    keys: tuple
    aggs: tuple  # ((name, expr), ...)


@dataclass(frozen=True)
class Join(PlanNode):
    left: PlanNode
    right: PlanNode
    keys: tuple
    how: str


@dataclass(frozen=True)
class Collected(PlanNode):
    """Explicit materialization point created by collect()."""
    input: PlanNode


def map_children(node, fn):
    changes = {f.name: fn(getattr(node, f.name)) for f in fields(node) if f.name in ("input", "left", "right")}
    return replace(node, **changes) if changes else node
