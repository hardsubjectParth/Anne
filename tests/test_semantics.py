import pytest

from sweet.diagnostics.errors import SweetError, SweetSemanticError


def fails(session, code, *needles):
    with pytest.raises(SweetError) as e:
        session.run('data sales = read "sales.csv"; data customers = read "customers.csv"; '
                    'data orders = read "orders.csv";\n' + code)
    text = (e.value.message + " " + (e.value.hint or "")).lower()
    for n in needles:
        assert n.lower() in text, text
    assert e.value.line is not None
    return e.value


def test_unknown_column_suggests(session):
    err = fails(session, "data r = sales.filter(prcie > 1);", "unknown column 'prcie'", "price")
    assert err.line == 2


def test_unknown_method_suggests(session):
    fails(session, "data r = sales.filtr(price > 1);", "unknown method", "filter")


def test_duplicate_binding(session):
    fails(session, "data a = sales.limit(1); data a = sales.limit(2);", "already defined")


def test_undefined_dataset(session):
    fails(session, "data a = salez.limit(1);", "undefined dataset", "sales")


def test_failed_program_defines_nothing(session):
    with pytest.raises(SweetError):
        session.run('data a = read "sales.csv"; data b = a.filter(nope > 1);')
    with pytest.raises(SweetSemanticError):
        session.dataset("a")


def test_summarize_requires_group_by(session):
    fails(session, "data r = sales.summarize(t = sum(price));", "must follow group_by")


def test_grouped_dataset_cannot_show_or_filter(session):
    fails(session, "data g = sales.group_by(region); g.show();", "grouped dataset")
    fails(session, "data g = sales.group_by(region).filter(price > 1);", "grouped dataset")


def test_bare_column_in_summarize(session):
    fails(session, "data r = sales.group_by(region).summarize(x = price);", "aggregate")
    fails(session, "data r = sales.group_by(region).summarize(x = price + 1);", "group key")


def test_aggregate_outside_summarize(session):
    fails(session, "data r = sales.filter(sum(price) > 1);", "only allowed inside summarize")


def test_type_errors(session):
    fails(session, 'data r = sales.derive(x = price + "a");', "cannot apply")
    fails(session, "data r = sales.filter(price);", "boolean")
    fails(session, "data r = sales.filter(region > 5);", "cannot compare")
    fails(session, "data r = sales.group_by(region).summarize(x = sum(customer));", "numeric")


def test_sort_direction_rules(session):
    fails(session, "data r = sales.sort(desc);", "directly follow")
    fails(session, "data r = sales.sort(price, desc, asc);", "directly follow")


def test_join_errors(session):
    fails(session, 'data r = orders.join(customers, on = nope);', "join key 'nope'")
    fails(session, 'data r = orders.join(customers, on = customer_id, how = "cross");', "unsupported join type")
    fails(session, "data r = orders.join(sales, on = customer_id);", "not found in the right")
    fails(session, "data r = orders.join(customers);", "needs on")


def test_statement_without_effect(session):
    fails(session, "sales.filter(price > 1);", "no effect")


def test_action_cannot_be_assigned_or_chained(session):
    fails(session, "data r = sales.show();", "cannot be assigned")
    fails(session, "sales.show().limit(1);", "last call")


def test_save_path_rules(session):
    fails(session, 'sales.save("../x.csv");', "inside the output directory")
    fails(session, 'sales.save("/tmp/x.csv");', "inside the output directory")
    fails(session, 'sales.save("x.xlsx");', "cannot save")


def test_read_errors(session):
    with pytest.raises(SweetError) as e:
        session.run('data x = read "missing.csv";')
    assert "file not found" in e.value.message
    with pytest.raises(SweetError) as e:
        session.run('data x = read "sales.csv" with (bogus = true);')
    assert "not supported" in e.value.message


def test_unknown_function_and_list(session):
    fails(session, "data r = sales.group_by(region).summarize(x = summ(price));", "unknown function", "sum")
    fails(session, "data r = sales.filter([1, 2]);", "lists")


def test_error_rendering_points_at_the_problem(session):
    src = 'data sales = read "sales.csv";\ndata r = sales.filter(prcie > 1);'
    with pytest.raises(SweetError) as e:
        session.run(src)
    text = e.value.render(src, "x.anne")
    assert "x.anne:2:" in text and "^^^^^" in text and "did you mean 'price'?" in text
