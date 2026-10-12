from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import expressions as E
from . import plan_nodes as P


@dataclass(frozen=True)
class ActionStmt:
    kind: str  # show schema describe columns shape explain save
    plan: P.PlanNode
    schema: tuple
    args: tuple
    line: int = 0
    col: int = 0
    length: int = 1


@dataclass(frozen=True)
class LogicalProgram:
    statements: tuple


def format_expr(e) -> str:
    if isinstance(e, E.Col):
        return e.name
    if isinstance(e, E.Lit):
        v = e.value
        if isinstance(v, bool):
            return "true" if v else "false"
        return json.dumps(v) if isinstance(v, str) else repr(v)
    if isinstance(e, E.Neg):
        return f"-{format_expr(e.operand)}"
    if isinstance(e, E.Not):
        return f"not {format_expr(e.operand)}"
    if isinstance(e, E.Bin):
        return f"({format_expr(e.left)} {e.op} {format_expr(e.right)})"
    if isinstance(e, E.Agg):
        return f"{e.func}({format_expr(e.arg) if e.arg is not None else ''})"
    raise TypeError(e)


def _describe(n) -> str:
    if isinstance(n, P.Scan):
        opts = ", ".join(f"{k}={v}" for k, v in n.options)
        return f"Scan({Path(n.path).name}{', ' + opts if opts else ''})"
    if isinstance(n, P.Filter):
        return f"Filter({format_expr(n.predicate)})"
    if isinstance(n, P.Project):
        return f"Project({', '.join(n.columns)})"
    if isinstance(n, P.Derive):
        return f"Derive({n.name} = {format_expr(n.expr)})"
    if isinstance(n, P.Sort):
        return "Sort(" + ", ".join(f"{c} {'DESC' if d else 'ASC'}" for c, d in n.keys) + ")"
    if isinstance(n, P.Limit):
        return f"Limit({n.n})"
    if isinstance(n, P.Tail):
        return f"Tail({n.n})"
    if isinstance(n, P.DropMissing):
        return f"DropMissing({', '.join(n.columns) if n.columns else 'all columns'})"
    if isinstance(n, P.Aggregate):
        aggs = ", ".join(f"{k} = {format_expr(v)}" for k, v in n.aggs)
        return f"Aggregate(keys=[{', '.join(n.keys)}], {aggs})"
    if isinstance(n, P.Join):
        return f"Join(how={n.how}, on=[{', '.join(n.keys)}])"
    if isinstance(n, P.Collected):
        return "Collected"
    raise TypeError(n)


def format_plan(node, indent: int = 0) -> str:
    lines = ["  " * indent + _describe(node)]
    for name in ("input", "left", "right"):
        child = getattr(node, name, None)
        if child is not None:
            lines.append(format_plan(child, indent + 1))
    return "\n".join(lines)
