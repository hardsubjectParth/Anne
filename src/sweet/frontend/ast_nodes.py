"""Anne AST. Plain dataclasses: nothing here depends on Lark."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Node:
    line: int = field(default=0, kw_only=True, compare=False)
    col: int = field(default=0, kw_only=True, compare=False)
    length: int = field(default=1, kw_only=True, compare=False)


@dataclass(frozen=True)
class IntLit(Node):
    value: int


@dataclass(frozen=True)
class FloatLit(Node):
    value: float


@dataclass(frozen=True)
class StrLit(Node):
    value: str


@dataclass(frozen=True)
class BoolLit(Node):
    value: bool


@dataclass(frozen=True)
class NameRef(Node):
    name: str


@dataclass(frozen=True)
class ListLit(Node):
    items: tuple


@dataclass(frozen=True)
class Unary(Node):
    op: str
    operand: Node


@dataclass(frozen=True)
class Binary(Node):
    op: str
    left: Node
    right: Node


@dataclass(frozen=True)
class Arg(Node):
    name: str | None
    value: Node


@dataclass(frozen=True)
class Call(Node):
    name: str
    args: tuple


@dataclass(frozen=True)
class MethodCall(Node):
    name: str
    args: tuple


@dataclass(frozen=True)
class ReadExpr(Node):
    path: StrLit
    options: tuple


@dataclass(frozen=True)
class Chain(Node):
    base: NameRef
    calls: tuple


@dataclass(frozen=True)
class DataDecl(Node):
    name: str
    value: Node


@dataclass(frozen=True)
class ActionStmt(Node):
    chain: Chain


@dataclass(frozen=True)
class Program(Node):
    statements: tuple
