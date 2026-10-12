from __future__ import annotations

from ..diagnostics.errors import SweetSemanticError, suggest


class SymbolTable:
    """Dataset bindings. Immutable: a name can be defined once per scope."""

    def __init__(self):
        self._items = {}

    def define(self, name, value):
        if name in self._items:
            raise SweetSemanticError(
                f"dataset '{name}' is already defined in this scope",
                hint="dataset bindings are immutable; choose a new name",
            )
        self._items[name] = value

    def lookup(self, name):
        if name not in self._items:
            hint = suggest(name, self._items) or 'declare it first: data name = read "file.csv";'
            raise SweetSemanticError(f"undefined dataset '{name}'", hint=hint)
        return self._items[name]

    def names(self):
        return list(self._items)

    def snapshot(self):
        return dict(self._items)

    def restore(self, snap):
        self._items = dict(snap)
