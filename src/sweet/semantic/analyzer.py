"""Semantic analysis: AST -> Dataset objects -> logical actions."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from ..diagnostics.errors import SweetError, SweetSemanticError, suggest
from ..frontend import ast_nodes as A
from ..ir import expressions as E
from ..ir.logical_plan import ActionStmt, LogicalProgram
from ..ir.plan_nodes import Scan
from ..objects.dataset import JOIN_TYPES, Dataset
from ..objects.grouped_dataset import GroupedDataset
from ..runtime import io as sio
from . import types as T
from .symbols import SymbolTable

AGG_FUNCS = ("sum", "mean", "median", "min", "max", "count")
ACTIONS = ("show", "schema", "describe", "columns", "shape", "explain", "save")
DATASET_METHODS = ("filter", "select", "derive", "sort", "limit", "head", "tail",
                   "drop_missing", "group_by", "join", "collect")


class Analyzer:
    def __init__(self, base_dir=".", symbols=None):
        self.base_dir = Path(base_dir)
        self.symbols = symbols if symbols is not None else SymbolTable()

    # ------------------------------------------------------------ helpers
    @contextmanager
    def _at(self, node):
        try:
            yield
        except SweetError as e:
            e.at(node)
            raise

    def _err(self, message, node, hint=None):
        return SweetSemanticError(message, hint=hint).at(node)

    def _positional(self, call, lo, hi, usage):
        named = [a for a in call.args if a.name is not None]
        if named:
            raise self._err(f"{call.name}() does not take named arguments", named[0], f"usage: {usage}")
        n = len(call.args)
        if n < lo or (hi is not None and n > hi):
            want = f"{lo}" if lo == hi else f"{lo} to {hi}" if hi is not None else f"at least {lo}"
            raise self._err(f"{call.name}() expects {want} argument(s), got {n}", call, f"usage: {usage}")
        return [a.value for a in call.args]

    def _named(self, call, usage):
        pos = [a for a in call.args if a.name is None]
        if pos:
            raise self._err(f"{call.name}() arguments must be written name = expression", pos[0], f"usage: {usage}")
        if not call.args:
            raise self._err(f"{call.name}() needs at least one argument", call, f"usage: {usage}")
        seen = set()
        for a in call.args:
            if a.name in seen:
                raise self._err(f"'{a.name}' is given twice", a)
            seen.add(a.name)
        return [(a.name, a) for a in call.args]

    def _names(self, nodes, schema, what):
        out = []
        for n in nodes:
            if not isinstance(n, A.NameRef):
                raise self._err(f"{what} takes plain column names", n)
            if n.name not in dict(schema):
                with self._at(n):
                    raise T.unknown_column(n.name, [c for c, _ in schema])
            out.append(n.name)
        return out

    def _int(self, node, usage):
        if not isinstance(node, A.IntLit):
            raise self._err("expected a non-negative integer", node, f"usage: {usage}")
        return node.value

    # ------------------------------------------------------------ lowering
    def _lower(self, node, schema):
        if isinstance(node, A.IntLit | A.FloatLit | A.StrLit | A.BoolLit):
            return E.Lit(node.value)
        if isinstance(node, A.NameRef):
            cols = [c for c, _ in schema]
            if node.name not in cols:
                err = T.unknown_column(node.name, cols)
                if node.name in self.symbols.names():
                    err.hint = f"'{node.name}' is a dataset, not a column"
                raise err.at(node)
            return E.Col(node.name)
        if isinstance(node, A.Unary):
            inner = self._lower(node.operand, schema)
            return E.Neg(inner) if node.op == "-" else E.Not(inner)
        if isinstance(node, A.Binary):
            return E.Bin(node.op, self._lower(node.left, schema), self._lower(node.right, schema))
        if isinstance(node, A.Call):
            if node.name not in AGG_FUNCS:
                raise self._err(f"unknown function '{node.name}'", node,
                                suggest(node.name, AGG_FUNCS) or "functions: " + ", ".join(AGG_FUNCS))
            if any(a.name is not None for a in node.args):
                raise self._err(f"{node.name}() does not take named arguments", node)
            if node.name == "count" and len(node.args) > 1 or node.name != "count" and len(node.args) != 1:
                raise self._err(f"{node.name}() takes {'0 or 1' if node.name == 'count' else '1'} argument(s)", node)
            arg = self._lower(node.args[0].value, schema) if node.args else None
            return E.Agg(node.name, arg)
        if isinstance(node, A.ListLit):
            raise self._err("lists are only allowed in join(on = [a, b])", node)
        raise AssertionError(node)

    # ------------------------------------------------------------ statements
    def analyze(self, program: A.Program) -> LogicalProgram:
        snap = self.symbols.snapshot()
        out = []
        try:
            for st in program.statements:
                with self._at(st):
                    stmt = self._statement(st)
                if stmt is not None:
                    out.append(stmt)
        except BaseException:
            self.symbols.restore(snap)
            raise
        return LogicalProgram(tuple(out))

    def _statement(self, st):
        if isinstance(st, A.DataDecl):
            if isinstance(st.value, A.ReadExpr):
                value = self._read(st.value)
            else:
                value, _ = self._eval_chain(st.value, allow_action=False)
            self.symbols.define(st.name, value)
            return None
        value, action = self._eval_chain(st.chain, allow_action=True)
        if action is None:
            raise self._err("this statement has no effect", st.chain,
                            "end it with .show(), or assign it: data name = ...;")
        return self._action(value, action)

    def _read(self, node):
        opts = {}
        for a in node.options:
            if a.name is None or not isinstance(a.value, A.BoolLit | A.StrLit | A.IntLit):
                raise self._err("reader options are written name = value (true/false or a string)", a)
            opts[a.name] = a.value.value
        with self._at(node.path):
            fmt = sio.format_of(node.path.value)
            sio.validate_options(fmt, opts)
            full = sio.resolve(node.path.value, self.base_dir)
            options = tuple(sorted(opts.items()))
            schema = sio.schema_of(str(full), options)
        return Dataset(Scan(str(full), options), schema)

    def _eval_chain(self, chain, allow_action):
        with self._at(chain.base):
            value = self.symbols.lookup(chain.base.name)
        for i, call in enumerate(chain.calls):
            last = i == len(chain.calls) - 1
            if call.name in ACTIONS:
                if not allow_action:
                    raise self._err(f"{call.name}() does not produce a dataset, so it cannot be assigned", call,
                                    "assign a dataset: data name = other.filter(...);")
                if not last:
                    raise self._err(f"{call.name}() must be the last call in a statement", call)
                if isinstance(value, GroupedDataset):
                    raise self._err(f"cannot call {call.name}() on a grouped dataset", call,
                                    "call summarize(...) after group_by(...) first")
                return value, call
            value = self._apply(value, call)
        return value, None

    def _apply(self, value, call):
        name = call.name
        if isinstance(value, GroupedDataset):
            if name != "summarize":
                raise self._err(f"cannot call {name}() on a grouped dataset", call,
                                "call summarize(...) after group_by(...) first")
            return self._summarize(value, call)
        if name == "summarize":
            raise self._err("summarize() must follow group_by()", call,
                            "for example: data.group_by(region).summarize(total = sum(price))")
        if name not in DATASET_METHODS:
            raise self._err(f"unknown method '{name}()'", call,
                            suggest(name, DATASET_METHODS + ACTIONS) or "methods: " + ", ".join(DATASET_METHODS))
        return getattr(self, "_m_" + name)(value, call)

    # ------------------------------------------------------------ dataset methods
    def _m_filter(self, ds, call):
        (node,) = self._positional(call, 1, 1, "filter(condition)")
        expr = self._lower(node, ds.schema)
        with self._at(node):
            return ds.filter(expr)

    def _m_select(self, ds, call):
        nodes = self._positional(call, 1, None, "select(col1, col2, ...)")
        names = self._names(nodes, ds.schema, "select()")
        with self._at(call):
            return ds.select(*names)

    def _m_derive(self, ds, call):
        for name, arg in self._named(call, "derive(total = price * quantity)"):
            expr = self._lower(arg.value, ds.schema)
            with self._at(arg.value):
                ds = ds.derive(name, expr)
        return ds

    def _m_sort(self, ds, call):
        nodes = self._positional(call, 1, None, "sort(column, desc)")
        keys, dir_set = [], False
        for n in nodes:
            if not isinstance(n, A.NameRef):
                raise self._err("sort() takes column names and optional asc/desc", n)
            if n.name in ("asc", "desc"):
                if not keys or dir_set:
                    raise self._err(f"'{n.name}' must directly follow a column name", n)
                keys[-1] = (keys[-1][0], n.name == "desc")
                dir_set = True
                continue
            self._names([n], ds.schema, "sort()")
            keys.append((n.name, False))
            dir_set = False
        with self._at(call):
            return ds.sort(keys)

    def _m_limit(self, ds, call):
        (node,) = self._positional(call, 1, 1, "limit(n)")
        with self._at(call):
            return ds.limit(self._int(node, "limit(n)"))

    _m_head = _m_limit

    def _m_tail(self, ds, call):
        (node,) = self._positional(call, 1, 1, "tail(n)")
        with self._at(call):
            return ds.tail(self._int(node, "tail(n)"))

    def _m_drop_missing(self, ds, call):
        nodes = self._positional(call, 0, None, "drop_missing(col, ...)")
        names = self._names(nodes, ds.schema, "drop_missing()")
        with self._at(call):
            return ds.drop_missing(*names)

    def _m_group_by(self, ds, call):
        nodes = self._positional(call, 1, None, "group_by(col, ...)")
        names = self._names(nodes, ds.schema, "group_by()")
        with self._at(call):
            return ds.group_by(*names)

    def _m_collect(self, ds, call):
        self._positional(call, 0, 0, "collect()")
        return ds.collect()

    def _m_join(self, ds, call):
        usage = 'join(other, on = key, how = "left")'
        pos = [a for a in call.args if a.name is None]
        kws = {a.name: a for a in call.args if a.name is not None}
        if len(pos) != 1 or not isinstance(pos[0].value, A.NameRef):
            raise self._err("join() needs exactly one other dataset as its first argument", call, f"usage: {usage}")
        for k, a in kws.items():
            if k not in ("on", "how"):
                raise self._err(f"unknown join option '{k}'", a, "options: on, how")
        if "on" not in kws:
            raise self._err("join() needs on = column (or on = [a, b])", call, f"usage: {usage}")
        with self._at(pos[0].value):
            other = self.symbols.lookup(pos[0].value.name)
            if isinstance(other, GroupedDataset):
                raise SweetSemanticError("cannot join a grouped dataset", hint="call summarize(...) first")
        on = kws["on"].value
        items = on.items if isinstance(on, A.ListLit) else [on]
        keys = []
        for it in items:
            if not isinstance(it, A.NameRef):
                raise self._err("join keys must be plain column names", it)
            keys.append(it.name)
        how = "inner"
        if "how" in kws:
            h = kws["how"].value
            if not isinstance(h, A.StrLit):
                raise self._err('how must be a string such as "left"', h)
            how = h.value
            if how not in JOIN_TYPES:
                raise self._err(f"unsupported join type '{how}'", h, "supported: " + ", ".join(JOIN_TYPES))
        with self._at(on):
            return ds.join(other, tuple(keys), how)

    def _summarize(self, grouped, call):
        schema = grouped.dataset.schema
        aggs = []
        for name, arg in self._named(call, "summarize(total = sum(price), orders = count())"):
            expr = self._lower(arg.value, schema)
            with self._at(arg.value):
                T.infer(expr, schema, group_keys=set(grouped.keys))
                if not E.contains_agg(expr):
                    raise SweetSemanticError(
                        f"'{name}' must use an aggregate function (sum, mean, median, min, max, count)")
            aggs.append((name, expr))
        with self._at(call):
            return grouped.summarize(tuple(aggs))

    # ------------------------------------------------------------ actions
    def _action(self, ds, call):
        kind, args = call.name, ()
        if kind == "show":
            nodes = self._positional(call, 0, 1, "show(n)")
            args = (self._int(nodes[0], "show(n)") if nodes else 20,)
        elif kind == "save":
            (node,) = self._positional(call, 1, 1, 'save("file.csv")')
            if not isinstance(node, A.StrLit):
                raise self._err("save() needs a file name string", node)
            p = PurePosixPath(node.value.replace("\\", "/"))
            if p.is_absolute() or ".." in p.parts or not p.name:
                raise self._err("output path must be relative and stay inside the output directory", node)
            if p.suffix.lower() not in sio.WRITE_FORMATS:
                raise self._err(f"cannot save as '{p.suffix or '(none)'}'", node,
                                "supported: " + ", ".join(sorted(sio.WRITE_FORMATS)))
            args = (str(p),)
        else:
            self._positional(call, 0, 0, f"{kind}()")
        return ActionStmt(kind, ds.plan, ds.schema, args, call.line, call.col, call.length)
