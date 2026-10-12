from __future__ import annotations

import difflib


class SweetError(Exception):
    kind = "error"

    def __init__(self, message, *, line=None, col=None, length=1, hint=None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.length = length
        self.hint = hint

    def at(self, node):
        """Attach a source location if this error does not have one yet."""
        if self.line is None and node is not None and getattr(node, "line", 0):
            self.line, self.col, self.length = node.line, node.col, max(1, node.length)
        return self

    def render(self, source=None, filename="<input>"):
        out = [f"{self.kind}: {self.message}"]
        if self.line is not None:
            out.append(f"  --> {filename}:{self.line}:{self.col}")
            if source is not None:
                lines = source.splitlines()
                if 1 <= self.line <= len(lines):
                    gutter = str(self.line)
                    pad = " " * len(gutter)
                    out.append(f" {pad} |")
                    out.append(f" {gutter} | {lines[self.line - 1]}")
                    out.append(f" {pad} | {' ' * max(0, (self.col or 1) - 1)}{'^' * max(1, self.length)}")
        if self.hint:
            out.append(f"help: {self.hint}")
        return "\n".join(out)


class SweetSyntaxError(SweetError):
    kind = "syntax error"


class SweetSemanticError(SweetError):
    kind = "error"


class SweetRuntimeError(SweetError):
    kind = "runtime error"


def suggest(name, candidates):
    """Return a 'did you mean' hint, or None."""
    match = difflib.get_close_matches(name, list(candidates), n=1, cutoff=0.6)
    return f"did you mean '{match[0]}'?" if match else None
