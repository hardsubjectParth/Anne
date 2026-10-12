"""Typed, hashable expression IR. Anne expressions are NEVER evaluated with Python eval()."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Col:
    name: str


@dataclass(frozen=True)
class Lit:
    value: object  # int | float | str | bool


@dataclass(frozen=True)
class Neg:
    operand: object


@dataclass(frozen=True)
class Not:
    operand: object


@dataclass(frozen=True)
class Bin:
    op: str  # + - * / % == != < <= > >= and or
    left: object
    right: object


@dataclass(frozen=True)
class Agg:
    func: str  # sum mean median min max count
    arg: object | None = None


def contains_agg(e) -> bool:
    if isinstance(e, Agg):
        return True
    if isinstance(e, (Neg, Not)):
        return contains_agg(e.operand)
    if isinstance(e, Bin):
        return contains_agg(e.left) or contains_agg(e.right)
    return False
