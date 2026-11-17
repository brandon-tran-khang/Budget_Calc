"""Headless dashboard check: opening the app auto-imports Data/Inbox (synthetic data only)."""
import pytest
from streamlit.testing.v1 import AppTest

import config
import Yearly_Spending as ys

CHASE = ("Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n"
         "03/05/2024,03/06/2024,NEWSHOP,Shopping,Sale,-7.00,\n"
         "03/09/2024,03/10/2024,OTHERSHOP,Shopping,Sale,-9.00,\n")


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    import streamlit as st
    st.cache_data.clear()  # process-wide cache; keep scenarios independent
    for mod in (config, ys):
        monkeypatch.setattr(mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ys, "CHECKING_DIR", tmp_path / "Checking")
    for mod in (config, ys):
        monkeypatch.setattr(mod, "MAPPINGS_FILE", tmp_path / "map.csv")
        monkeypatch.setattr(mod, "REIMBURSEMENTS_FILE", tmp_path / "zelle_assignments.csv")
    (tmp_path / "Inbox").mkdir()
    yield tmp_path
    st.cache_data.clear()


def test_launch_imports_inbox(sandbox):
    (sandbox / "Inbox" / "Chase1111_x.csv").write_text(CHASE)
    (sandbox / "Inbox" / "junk.csv").write_text("a,b\n1,2\n")
    at = AppTest.from_file("frontend.py", default_timeout=60).run()
    assert not at.exception
    assert (sandbox / "Chase1111_x.csv").exists() and not (sandbox / "Inbox" / "Chase1111_x.csv").exists()
    assert (sandbox / "all_transactions.csv").exists()
    assert any("junk.csv" in w.value for w in at.warning)  # unrecognized file named, not imported
    assert (sandbox / "Inbox" / "junk.csv").exists()


def test_refused_file_stays_flagged_after_reload(sandbox):
    (sandbox / "Inbox" / "Chase1111_x.csv").write_text(CHASE)
    (sandbox / "Inbox" / "badciti.csv").write_text(
        "Status,Date,Description,Debit,Credit,Member Name\nCleared,03/10/2024,SHOP,abc,,X\n")
    first = AppTest.from_file("frontend.py", default_timeout=60).run()
    assert any(w.value.startswith("ERROR badciti.csv") for w in first.warning)
    assert not any("WARNING" in w.value for w in first.warning)  # gaps/unrecognized are shown elsewhere
    again = AppTest.from_file("frontend.py", default_timeout=60).run()  # new session, empty inbox
    assert any("Not read" in w.value and "badciti.csv" in w.value for w in again.warning)
