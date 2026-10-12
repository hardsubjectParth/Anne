from __future__ import annotations

from pathlib import Path

from lark import Lark
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, UnexpectedToken

from ..diagnostics.errors import SweetSyntaxError
from .ast_builder import build_program

_FRIENDLY = {
    "SEMICOLON": "';'", "LPAR": "'('", "RPAR": "')'", "COMMA": "','", "DOT": "'.'",
    "EQUAL": "'='", "$END": "end of input", "NAME": "a name", "STRING": "a string",
    "INT": "a number", "FLOAT": "a number", "LSQB": "'['", "RSQB": "']'",
}

_PARSER = Lark(
    (Path(__file__).with_name("grammar.lark")).read_text(encoding="utf-8"),
    parser="lalr",
    maybe_placeholders=False,
)


def parse(source: str):
    """Parse Anne source into AST nodes (raises SweetSyntaxError)."""
    try:
        tree = _PARSER.parse(source)
    except UnexpectedCharacters as e:
        raise SweetSyntaxError(f"unexpected character {e.char!r}", line=e.line, col=e.column) from None
    except UnexpectedToken as e:
        tok = e.token
        expected = sorted({_FRIENDLY.get(x, x.lower()) for x in e.expected})
        hint = "expected " + ", ".join(expected[:6]) + (" ..." if len(expected) > 6 else "")
        at_end = tok.type == "$END"
        lines = source.rstrip().splitlines() or [""]
        line = lines.__len__() if at_end else (tok.line or 1)
        col = (len(lines[-1]) + 1) if at_end else (tok.column or 1)
        msg = "unexpected end of input (missing ';'?)" if at_end else f"unexpected {str(tok)!r}"
        raise SweetSyntaxError(msg, line=line, col=col, length=1 if at_end else max(1, len(str(tok))), hint=hint) from None
    except UnexpectedEOF:
        raise SweetSyntaxError("unexpected end of input", line=1, col=1) from None
    except UnexpectedInput as e:
        raise SweetSyntaxError("invalid syntax", line=getattr(e, "line", None), col=getattr(e, "column", None)) from None
    return build_program(tree)
