import pytest

from sweet.diagnostics.errors import SweetSyntaxError
from sweet.frontend import ast_nodes as A
from sweet.frontend.parser import parse


def test_parses_declaration_and_chain():
    prog = parse('data s = read "a.csv"; data t = s.filter(price > 1).limit(3);')
    assert isinstance(prog.statements[0].value, A.ReadExpr)
    chain = prog.statements[1].value
    assert [c.name for c in chain.calls] == ["filter", "limit"]


def test_ast_has_no_lark_objects():
    import lark

    prog = parse('data t = s.derive(x = a * (b + 1)).show();'.replace(".show()", ""))

    def walk(n):
        assert not isinstance(n, lark.Tree | lark.Token)
        if isinstance(n, A.Node):
            for v in vars(n).values():
                walk(v)
        elif isinstance(n, tuple):
            for v in n:
                walk(v)

    walk(prog)


def test_kwarg_vs_positional_and_comments():
    prog = parse("# hi\ns.derive(a = b == 1);  # trailing\n")
    arg = prog.statements[0].chain.calls[0].args[0]
    assert arg.name == "a" and arg.value.op == "=="


def test_precedence():
    e = parse("s.filter(1 + 2 * 3 > 6 and not false);").statements[0].chain.calls[0].args[0].value
    assert e.op == "and" and e.left.op == ">" and e.left.left.right.op == "*"


def test_read_options():
    prog = parse('data s = read "a.csv" with (header = true, delimiter = ";");')
    assert [a.name for a in prog.statements[0].value.options] == ["header", "delimiter"]


def test_syntax_error_has_location():
    with pytest.raises(SweetSyntaxError) as e:
        parse("data s = read \"a.csv\";\ns.show()\n")
    assert e.value.line == 2 and "';'" in e.value.message


def test_bad_character():
    with pytest.raises(SweetSyntaxError) as e:
        parse("data s = $;")
    assert e.value.line == 1 and e.value.col == 10
