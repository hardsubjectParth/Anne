import polars as pl
import pytest

from sweet import cli, repl
from sweet.compiler import Session
from sweet.runtime.polars_backend import PolarsBackend
from sweet.semantic.types import from_polars

SETUP = 'data sales = read "sales.csv";\n'


def test_A_inspection(session, capsys):
    session.run(SETUP + "sales.show(); sales.schema(); sales.describe(); sales.columns(); sales.shape();")
    out = capsys.readouterr().out
    assert "alice" in out and "price  " in out and "INTEGER" in out and "STRING" in out
    assert "mean" in out and "[customer, region, quantity, price]" in out and "(8 rows, 4 columns)" in out


def test_B_chained_transformations(session):
    session.run(SETUP + """
        data result = sales.filter(price > 100).derive(total = price * quantity)
            .select(customer, total).sort(total, desc).limit(20);
    """)
    df = session.result("result")
    assert df.to_dicts() == [
        {"customer": "dave", "total": 7500}, {"customer": "alice", "total": 3000},
        {"customer": "gina", "total": 2002}, {"customer": "frank", "total": 1000},
        {"customer": "carol", "total": 600}, {"customer": "bob", "total": 300},
    ]


def test_C_group_and_summarize(session):
    session.run(SETUP + """
        data report = sales.group_by(region)
            .summarize(total = sum(price), average = mean(price), orders = count());
    """)
    rows = {r["region"]: r for r in session.result("report").to_dicts()}
    assert rows["north"]["total"] == 1670 and rows["north"]["orders"] == 3
    assert rows["north"]["average"] == pytest.approx(1670 / 3)
    assert rows["east"]["total"] == 3500 and rows["west"]["orders"] == 1
    assert session.result("report")["region"].to_list() == ["north", "south", "east", "west"]


def test_C_two_step_grouping_matches_chained(session):
    session.run(SETUP + """
        data g = sales.group_by(region);
        data a = g.summarize(t = sum(price));
        data b = sales.group_by(region).summarize(t = sum(price));
    """)
    assert session.result("a").equals(session.result("b"))


def test_D_joins(session):
    session.run("""
        data customers = read "customers.csv"; data orders = read "orders.csv";
        data left = orders.join(customers, on = customer_id, how = "left");
        data inner = orders.join(customers, on = customer_id);
        data full = orders.join(customers, on = customer_id, how = "full");
        data selfj = orders.join(orders, on = order_id);
    """)
    left = session.result("left")
    assert left.columns == ["order_id", "customer_id", "amount", "name", "city"]
    assert left.height == 4 and left.filter(pl.col("order_id") == 12)["name"].item() is None
    assert session.result("inner").height == 3
    full = session.result("full")
    assert full.height == 5 and sorted(full["customer_id"].to_list()) == [1, 1, 2, 3, 4]
    assert session.result("selfj").columns == ["order_id", "customer_id", "amount", "customer_id_right", "amount_right"]


def test_E_save_only_explicit_exports(session, data_dir):
    session.run(SETUP + 'data tmp = sales.limit(2); data result = sales.filter(price > 1000); result.save("expensive.csv");')
    files = sorted(p.name for p in (data_dir / "out").iterdir())
    assert files == ["expensive.csv"]
    assert pl.read_csv(data_dir / "out" / "expensive.csv").height == 3


@pytest.mark.parametrize("name", ["r.csv", "r.parquet", "r.ndjson", "r.json", "sub/r.csv"])
def test_save_formats_roundtrip(session, data_dir, name):
    session.run(SETUP + f'data r = sales.limit(3); r.save("{name}");')
    path = data_dir / "out" / name
    reader = {"csv": pl.read_csv, "parquet": pl.read_parquet, "ndjson": pl.read_ndjson, "json": pl.read_json}
    assert reader[path.suffix[1:]](path).height == 3


def test_runtime_path_escape_blocked(data_dir):
    from sweet.diagnostics.errors import SweetRuntimeError
    from sweet.ir.logical_plan import ActionStmt, LogicalProgram
    from sweet.ir.plan_nodes import Scan
    from sweet.runtime.executor import Executor

    stmt = ActionStmt("save", Scan(str(data_dir / "sales.csv")), (), ("../evil.csv",))
    with pytest.raises(SweetRuntimeError):
        Executor(data_dir / "out").execute(LogicalProgram((stmt,)))
    assert not (data_dir / "evil.csv").exists()


def test_F_reuse(session, capsys):
    session.run(SETUP + """
        data expensive = sales.filter(price > 1000);
        data affordable = sales.filter(price <= 1000);
        expensive.show(); affordable.show();
    """)
    out = capsys.readouterr().out
    assert "dave" in out and "erin" in out
    assert session.result("sales").height == 8
    assert session.result("expensive").height == 3 and session.result("affordable").height == 5


def test_declarations_are_lazy(data_dir, monkeypatch):
    def boom(self, plan):
        raise AssertionError("executed during declaration")

    monkeypatch.setattr(PolarsBackend, "lazy", boom)
    Session(data_dir, data_dir / "o").run(SETUP + "data a = sales.filter(price > 1).derive(x = price * 2).limit(1);")


def test_collect_materializes_once(session):
    session.run(SETUP + "data c = sales.filter(price > 1000).collect(); c.show(); c.limit(1).show();")
    assert len(session.executor.backend._collected) == 1


def test_schema_matches_executed_result(session):
    session.run("""
        data sales = read "sales.csv"; data customers = read "customers.csv"; data orders = read "orders.csv";
        data a = sales.derive(total = price * quantity, ratio = price / quantity, big = price > 100);
        data b = sales.group_by(region, customer).summarize(s = sum(price), m = mean(price), n = count(), lo = min(price));
        data c = orders.join(customers, on = customer_id, how = "full");
        data d = sales.select(price, region).sort(price, desc).tail(3);
        data e = sales.derive(price = price * 1.5);
    """)
    for name in "abcde":
        ds, df = session.dataset(name), session.result(name)
        assert list(ds.columns) == df.columns, name
        assert [t for _, t in ds.schema] == [from_polars(t) for t in df.dtypes], name


def test_head_tail_sort_multi_and_drop_missing(session, data_dir):
    (data_dir / "m.csv").write_text("a,b\n1,x\n2,\n,z\n")
    session.run(SETUP + """
        data h = sales.head(2); data t = sales.tail(2);
        data s = sales.sort(region, price, desc);
        data m = read "m.csv"; data m_all = m.drop_missing(); data m_b = m.drop_missing(b);
    """)
    assert session.result("h")["customer"].to_list() == ["alice", "bob"]
    assert session.result("t")["customer"].to_list() == ["gina", "henry"]
    assert session.result("s")["customer"].to_list()[:3] == ["dave", "frank", "alice"]
    assert session.result("m_all").height == 1 and session.result("m_b").height == 2


def test_expressions_strings_booleans_math(session):
    session.run(SETUP + """
        data r = sales.filter(region == "north" and not (price < 100 or quantity > 4))
            .derive(label = customer + "!", neg = -price, rem = price % 7);
    """)
    df = session.result("r")
    assert df["customer"].to_list() == ["alice"] and df["label"].to_list() == ["alice!"]
    assert df["neg"].to_list() == [-1500]


def test_reader_options_and_formats(session, data_dir):
    (data_dir / "semi.csv").write_text("a;b\n1;2\n")
    pl.DataFrame({"a": [1, 2], "b": ["x", "y"]}).write_parquet(data_dir / "t.parquet")
    pl.DataFrame({"a": [1, 2], "b": ["x", "y"]}).write_json(data_dir / "t.json")
    pl.DataFrame({"a": [1, 2], "b": ["x", "y"]}).write_ndjson(data_dir / "t.ndjson")
    session.run("""
        data semi = read "semi.csv" with (delimiter = ";");
        data nohdr = read "semi.csv" with (header = false, delimiter = ";");
        data text = read "sales.csv" with (infer_schema = false);
        data p = read "t.parquet"; data j = read "t.json"; data n = read "t.ndjson";
    """)
    assert session.result("semi").columns == ["a", "b"]
    nohdr = session.result("nohdr")
    assert nohdr.height == 2 and len(nohdr.columns) == 2 and "a" not in nohdr.columns
    assert {t for _, t in session.dataset("text").schema} == {"STRING"}
    for name in "pjn":
        assert session.result(name).to_dicts() == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]


def test_excel_reader(session, data_dir):
    pytest.importorskip("xlsxwriter")
    pl.DataFrame({"a": [1, 2], "b": ["x", "y"]}).write_excel(data_dir / "t.xlsx")
    session.run('data x = read "t.xlsx";')
    assert session.result("x").to_dicts() == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]


def test_cli_run_writes_to_output_dir(data_dir, capsys):
    prog = data_dir / "analysis.anne"
    prog.write_text('data sales = read "sales.csv";\ndata result = sales.filter(price > 1000);\n'
                    'result.save("expensive.csv");\n')
    assert cli.main([str(prog), "-o", str(data_dir / "results")]) == 0
    assert (data_dir / "results" / "expensive.csv").exists()
    assert "saved" in capsys.readouterr().out


def test_cli_reports_errors_with_exit_code(data_dir, capsys):
    prog = data_dir / "bad.anne"
    prog.write_text('data sales = read "sales.csv";\nsales.filter(prcie > 1).show();\n')
    assert cli.main([str(prog)]) == 1
    err = capsys.readouterr().err
    assert "unknown column 'prcie'" in err and "bad.anne:2" in err and "did you mean 'price'" in err
    assert cli.main([str(data_dir / "nope.anne")]) == 2


def test_cli_check_does_not_execute(data_dir, capsys):
    prog = data_dir / "p.anne"
    prog.write_text('data sales = read "sales.csv";\nsales.show();\n')
    assert cli.main([str(prog), "--check"]) == 0
    assert capsys.readouterr().out == ""


def test_repl_uses_same_pipeline(data_dir, capsys):
    session = Session(base_dir=data_dir, output_dir=data_dir / "out")
    lines = iter([
        'data s = read "sales.csv";', "s.head(2)", "  .show();", "s.filter(nope > 1).show();",
        ":datasets", 'data s = s.limit(1);', ":quit",
    ])
    assert repl.run(session=session, input_fn=lambda prompt: next(lines)) == 0
    cap = capsys.readouterr()
    assert "alice" in cap.out and "s: [customer, region, quantity, price]" in cap.out
    assert "unknown column 'nope'" in cap.err and "already defined" in cap.err
