"""Pipeline: parse -> AST -> semantic analysis (Dataset objects) -> logical IR -> optimizer -> executor."""
from __future__ import annotations

from dataclasses import replace

from .frontend.parser import parse
from .ir.logical_plan import LogicalProgram
from .optimizer.optimizer import optimize
from .runtime.executor import Executor
from .semantic.analyzer import Analyzer


class Compiler:
    def __init__(self, base_dir="."):
        self.analyzer = Analyzer(base_dir)

    def compile(self, source: str) -> LogicalProgram:
        program = self.analyzer.analyze(parse(source))
        return LogicalProgram(tuple(replace(s, plan=optimize(s.plan)) for s in program.statements))


class Session:
    """One compiler + one executor. The CLI and the REPL both run through this class."""

    def __init__(self, base_dir=".", output_dir="sweet_output", out=None):
        self.compiler = Compiler(base_dir)
        self.executor = Executor(output_dir, out)

    def run(self, source: str, execute: bool = True) -> LogicalProgram:
        program = self.compiler.compile(source)  # whole program is checked before anything runs
        if execute:
            self.executor.execute(program)
        return program

    def dataset(self, name):
        return self.compiler.analyzer.symbols.lookup(name)

    def result(self, name):
        """Testing/embedding hook: materialize a bound dataset as a Polars DataFrame."""
        ds = self.dataset(name)
        return self.executor.backend.collect(optimize(ds.plan))
