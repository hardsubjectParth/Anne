"""Converts a Lark parse tree into Anne AST nodes (the only module that knows about Lark trees)."""
from __future__ import annotations

import json

from lark import Token

from . import ast_nodes as A

_BIN = {
    "or_op": "or", "and_op": "and", "eq": "==", "ne": "!=", "lt": "<", "le": "<=", "gt": ">",
    "ge": ">=", "add": "+", "sub": "-", "mul": "*", "div": "/", "mod": "%",
}


def _tok(tok):
    return dict(line=tok.line, col=tok.column, length=max(1, len(tok)))


def _span(tree):
    toks = list(tree.scan_values(lambda v: isinstance(v, Token)))
    if not toks:
        return {}
    a, b = toks[0], toks[-1]
    length = (b.end_column - a.column) if a.line == b.end_line else len(a)
    return dict(line=a.line, col=a.column, length=max(1, length))


def _unescape(tok):
    raw = str(tok)[1:-1]
    try:
        return json.loads('"' + raw + '"')
    except ValueError:
        return raw


def build_expr(n):
    d, c = n.data, n.children
    if d == "int_lit":
        return A.IntLit(int(c[0]), **_tok(c[0]))
    if d == "float_lit":
        return A.FloatLit(float(c[0]), **_tok(c[0]))
    if d == "str_lit":
        return A.StrLit(_unescape(c[0]), **_tok(c[0]))
    if d == "true_lit":
        return A.BoolLit(True, **_tok(c[0]))
    if d == "false_lit":
        return A.BoolLit(False, **_tok(c[0]))
    if d == "name_ref":
        return A.NameRef(str(c[0]), **_tok(c[0]))
    if d == "call":
        args = build_args(c[1]) if len(c) > 1 else ()
        return A.Call(str(c[0]), args, **_span(n))
    if d == "list_lit":
        return A.ListLit(tuple(build_expr(x) for x in c), **_span(n))
    if d == "neg":
        return A.Unary("-", build_expr(c[0]), **_span(n))
    if d == "not_op":
        return A.Unary("not", build_expr(c[0]), **_span(n))
    if d in _BIN:
        return A.Binary(_BIN[d], build_expr(c[0]), build_expr(c[1]), **_span(n))
    raise AssertionError(f"unhandled expression node {d}")


def build_args(tree):
    out = []
    for a in tree.children:
        if a.data == "kwarg":
            out.append(A.Arg(str(a.children[0]), build_expr(a.children[1]), **_span(a)))
        else:
            out.append(A.Arg(None, build_expr(a.children[0]), **_span(a)))
    return tuple(out)


def build_chain(tree):
    c = tree.children
    base = A.NameRef(str(c[0]), **_tok(c[0]))
    calls = tuple(
        A.MethodCall(
            str(m.children[0]),
            build_args(m.children[1]) if len(m.children) > 1 else (),
            **_tok(m.children[0]),
        )
        for m in c[1:]
    )
    return A.Chain(base, calls, **_span(tree))


def build_read(tree):
    c = tree.children
    path = A.StrLit(_unescape(c[0]), **_tok(c[0]))
    options = ()
    if len(c) > 1 and c[1].children:
        options = build_args(c[1].children[0])
    return A.ReadExpr(path, options, **_span(tree))


def build_statement(tree):
    inner = tree.children[0]
    if inner.data == "data_decl":
        name_tok, source = inner.children
        value = build_read(source) if source.data == "read_expr" else build_chain(source)
        return A.DataDecl(str(name_tok), value, **_tok(name_tok))
    chain = build_chain(inner.children[0])
    return A.ActionStmt(chain, line=chain.line, col=chain.col, length=chain.length)


def build_program(tree):
    return A.Program(tuple(build_statement(s) for s in tree.children))
