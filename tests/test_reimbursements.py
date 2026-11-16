import pandas as pd
import pytest

import reimbursements as r


def _income(rows):
    return pd.DataFrame(rows, columns=["Transaction Date", "Clean_Description", "Net_Amount"]).assign(
        **{"Transaction Date": lambda d: pd.to_datetime(d["Transaction Date"])})


def _assigned(rows):
    return pd.DataFrame(rows, columns=r.COLUMNS)


@pytest.fixture
def income():
    return _income([
        ("2025-01-05", "ZELLE FROM BOB", 20.0),
        ("2025-01-05", "ZELLE FROM BOB", 20.0),
        ("2025-01-06", "PAYROLL ACME", 2000.0),
        ("2025-01-07", "venmo cashout", -15.0),
    ])


def test_candidates_exclude_non_p2p_and_negative(income):
    c = r.find_candidates(income)
    assert list(c["Clean_Description"]) == ["ZELLE FROM BOB"] * 2


def test_one_assignment_consumes_one_row(income):
    a = _assigned([("2025-01-05", "ZELLE FROM BOB", 20.0, "Groceries")])
    assert len(r.unassigned_candidates(income, a)) == 1
    assert len(r.remove_assigned_from_income(income, a)) == len(income) - 1


def test_remove_assigned_only_matched(income):
    a = _assigned([("2025-01-05", "ZELLE FROM BOB", 20.0, "Groceries")] * 2)
    left = r.remove_assigned_from_income(income, a)
    assert list(left["Clean_Description"]) == ["PAYROLL ACME", "venmo cashout"]


def test_offsets_negative():
    a = _assigned([("2025-02-03", "zelle from bob", 20.0, "Groceries")])
    o = r.assignments_as_offsets(a)
    assert o["Net_Amount"].iloc[0] == -20.0
    assert o["Clean_Description"].iloc[0] == "Reimbursement: Zelle From Bob"
    assert o["Month"].iloc[0] == "February" and o["Year"].iloc[0] == 2025


def test_save_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "REIMBURSEMENTS_FILE", tmp_path / "z.csv")
    assert r.load_assignments().empty
    a = _assigned([("2025-02-03", "ZELLE X", 12.5, "Gas")])
    r.save_assignments(a)
    back = r.load_assignments()
    assert back["Net_Amount"].iloc[0] == 12.5 and back["Budget_Category"].iloc[0] == "Gas"
    r.save_assignments(back.iloc[0:0])
    assert r.load_assignments().empty
