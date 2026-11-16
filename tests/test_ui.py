import pandas as pd
from ui import envelope_rows


def _df(rows):
    return pd.DataFrame(rows, columns=["Budget_Category", "Net_Amount", "Source"])


def test_refund_row():
    r = {x["category"]: x for x in envelope_rows(_df([("Gas", 100, "Card"), ("Gas", -30, "Card")]))}["Gas"]
    assert (r["spent"], r["returned"], r["net"]) == (100, 30, 70)


def test_checking_assignment_offset_counts_as_returned():
    rows = envelope_rows(_df([("Restaurants", 80, "Card"), ("Restaurants", -42, "Checking Assignment"),
                              ("Gas", 10, "Card")]))
    assert [x["category"] for x in rows] == ["Restaurants", "Gas"]  # sorted by net desc
    rest = rows[0]
    assert (rest["spent"], rest["returned"], rest["net"]) == (80, 42, 38)


def test_spending_only_and_empty():
    rows = envelope_rows(_df([("Groceries", 50, "Card"), ("Groceries", 25, "Card")]))
    assert rows == [{"category": "Groceries", "spent": 75, "returned": 0, "net": 75}]
    assert envelope_rows(_df([])) == []
