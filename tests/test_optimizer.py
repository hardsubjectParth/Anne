from sweet.ir import plan_nodes as P
from sweet.ir.expressions import Bin, Col, Lit, Neg
from sweet.optimizer.constant_folding import fold_expr
from sweet.optimizer.optimizer import optimize


def test_folds_arithmetic_and_comparison():
    assert fold_expr(Bin("*", Lit(100), Lit(10))) == Lit(1000)
    assert fold_expr(Bin("<", Lit(1), Lit(2))) == Lit(True)
    assert fold_expr(Neg(Lit(5))) == Lit(-5)
    assert fold_expr(Bin("+", Lit("a"), Lit("b"))) == Lit("ab")


def test_does_not_fold_unsafe_cases():
    assert fold_expr(Bin("/", Lit(1), Lit(0))) == Bin("/", Lit(1), Lit(0))
    assert fold_expr(Bin("%", Lit(7), Lit(3))) == Bin("%", Lit(7), Lit(3))
    big = Bin("*", Lit(2 ** 40), Lit(2 ** 40))
    assert fold_expr(big) == big


def test_boolean_simplification():
    x = Bin(">", Col("a"), Lit(1))
    assert fold_expr(Bin("and", Lit(True), x)) == x
    assert fold_expr(Bin("and", x, Lit(False))) == Lit(False)
    assert fold_expr(Bin("or", x, Lit(True))) == Lit(True)
    assert fold_expr(Bin("or", Lit(False), x)) == x


def test_filter_fusion_and_true_filter_removal():
    scan = P.Scan("f.csv")
    a, b = Bin(">", Col("a"), Lit(1)), Bin("<", Col("b"), Lit(9))
    plan = P.Filter(P.Filter(P.Filter(scan, a), Lit(True)), b)
    out = optimize(plan)
    assert out == P.Filter(scan, Bin("and", a, b))


def test_explain_output(session, capsys):
    session.run('data s = read "sales.csv"; s.filter(price > 100 * 10).filter(quantity > 1).explain();')
    out = capsys.readouterr().out
    assert out.count("Filter") == 1 and "(price > 1000)" in out and "100 * 10" not in out


def test_optimized_and_unoptimized_agree(session):
    session.run('data s = read "sales.csv"; data r = s.filter(price > 100 * 10).filter(quantity >= 3 and true);')
    from sweet.runtime.polars_backend import PolarsBackend

    raw = PolarsBackend().collect(session.dataset("r").plan)
    assert session.result("r").equals(raw) and raw.height == 1 and raw["customer"].to_list() == ["dave"]
