from __future__ import annotations

import os
import sys
from pathlib import Path

import polars as pl

from ..diagnostics.errors import SweetRuntimeError
from ..ir.logical_plan import ActionStmt, LogicalProgram, format_plan
from . import io
from .polars_backend import PolarsBackend

_TABLE = dict(tbl_cols=-1, tbl_hide_dataframe_shape=True, tbl_hide_column_data_types=True)


class Executor:
    def __init__(self, output_dir="sweet_output", out=None, backend=None):
        self.output_dir = Path(output_dir)
        self.out = out  # None -> resolve sys.stdout at print time
        self.backend = backend or PolarsBackend()

    def execute(self, program: LogicalProgram) -> None:
        for stmt in program.statements:
            try:
                getattr(self, "_" + stmt.kind)(stmt)
            except (pl.exceptions.PolarsError, OSError) as e:
                raise SweetRuntimeError(str(e), line=stmt.line, col=stmt.col, length=stmt.length) from None

    def _p(self, text=""):
        print(text, file=self.out if self.out is not None else sys.stdout)

    def _show(self, st: ActionStmt):
        n = st.args[0]
        df = self.backend.lazy(st.plan).limit(n + 1).collect()
        with pl.Config(tbl_rows=max(n, 1), **_TABLE):
            self._p(df.head(n))
        self._p(f"({min(len(df), n)} rows shown{', more rows not shown' if len(df) > n else ''})")

    def _schema(self, st):
        width = max([len(n) for n, _ in st.schema] + [6])
        self._p(f"{'column'.ljust(width)}  type")
        for name, ty in st.schema:
            self._p(f"{name.ljust(width)}  {ty}")

    def _columns(self, st):
        self._p("[" + ", ".join(n for n, _ in st.schema) + "]")

    def _shape(self, st):
        rows = self.backend.lazy(st.plan).select(pl.len()).collect().item()
        self._p(f"({rows} rows, {len(st.schema)} columns)")

    def _describe(self, st):
        with pl.Config(tbl_rows=50, **_TABLE):
            self._p(self.backend.collect(st.plan).describe())

    def _explain(self, st):
        self._p(format_plan(st.plan))

    def _save(self, st):
        rel = st.args[0]
        base = self.output_dir.resolve()
        target = (base / rel).resolve()
        if target != base and base not in target.parents:
            raise SweetRuntimeError("output path escapes the output directory",
                                    line=st.line, col=st.col, length=st.length)
        fmt = io.WRITE_FORMATS[target.suffix.lower()]
        df = self.backend.collect(st.plan)
        target.parent.mkdir(parents=True, exist_ok=True)
        io.write(df, target, fmt)
        try:
            shown = os.path.relpath(target)
        except ValueError:
            shown = str(target)
        self._p(f"saved {shown} ({df.height} rows)")
