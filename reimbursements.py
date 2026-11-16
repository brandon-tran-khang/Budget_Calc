"""Reimbursement assignments: match incoming Zelle/Venmo/Cash App income to spending categories.

Pure pandas (no streamlit). An assignment consumes exactly one income row, so it is
removed from income and injected into spending as a negative offset.
"""

import pandas as pd

from config import P2P_KEYWORDS, REIMBURSEMENTS_FILE

COLUMNS = ["Transaction Date", "Clean_Description", "Net_Amount", "Budget_Category"]
_KEY = ["_d", "Clean_Description", "_amt"]


def load_assignments():
    if not REIMBURSEMENTS_FILE.exists():
        return pd.DataFrame(columns=COLUMNS)
    try:
        df = pd.read_csv(REIMBURSEMENTS_FILE)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=COLUMNS)
    df = df[COLUMNS].copy()
    df["Transaction Date"] = pd.to_datetime(df["Transaction Date"])
    return df


def save_assignments(df):
    """Write the whole assignments file atomically (also used to undo assignments)."""
    out = df[COLUMNS].copy()
    out["Transaction Date"] = pd.to_datetime(out["Transaction Date"]).dt.strftime("%Y-%m-%d")
    tmp = REIMBURSEMENTS_FILE.with_suffix(".csv.tmp")
    out.to_csv(tmp, index=False)
    tmp.replace(REIMBURSEMENTS_FILE)


def find_candidates(income_df):
    """Incoming P2P payments (income data only; Net_Amount > 0)."""
    if income_df.empty:
        return income_df.copy()
    is_p2p = income_df["Clean_Description"].str.contains("|".join(P2P_KEYWORDS), case=False, na=False)
    return income_df[is_p2p & (income_df["Net_Amount"] > 0)].copy()


def _keys(df):
    """Per-row (date, description, amount, occurrence) tuples; occurrence makes duplicates distinct."""
    k = pd.DataFrame({
        "_d": pd.to_datetime(df["Transaction Date"]).dt.strftime("%Y-%m-%d").to_numpy(),
        "Clean_Description": df["Clean_Description"].to_numpy(),
        "_amt": df["Net_Amount"].astype(float).round(2).to_numpy(),
    })
    k["_occ"] = k.groupby(_KEY).cumcount()
    return list(zip(k["_d"], k["Clean_Description"], k["_amt"], k["_occ"]))


def _matched(df, assigned_df):
    """Boolean numpy mask: rows of df consumed by an assignment (one-for-one)."""
    if df.empty or assigned_df.empty:
        return pd.Series(False, index=range(len(df))).to_numpy()
    assigned = set(_keys(assigned_df))
    return pd.Series([k in assigned for k in _keys(df)]).to_numpy()


def unassigned_candidates(income_df, assigned_df):
    cands = find_candidates(income_df)
    return cands[~_matched(cands, assigned_df)]


def remove_assigned_from_income(income_df, assigned_df):
    """Drop income rows consumed by assignments so reimbursements are not also income."""
    return income_df[~_matched(income_df, assigned_df)].copy()


def assignments_as_offsets(assigned_df):
    """Negative-amount spending rows that net assignments against their category."""
    d = pd.to_datetime(assigned_df["Transaction Date"])
    return pd.DataFrame({
        "Transaction Date": d,
        "Clean_Description": "Reimbursement: " + assigned_df["Clean_Description"].str.title(),
        "Category": "Transfer",
        "Budget_Category": assigned_df["Budget_Category"],
        "Net_Amount": -assigned_df["Net_Amount"].abs(),
        "Source": "Checking Assignment",
        "account_type": "credit",
        "Month": d.dt.strftime("%B"),
        "Quarter": d.dt.quarter,
        "Week": d.dt.strftime("%W").astype(int),
        "Year": d.dt.year,
    })
