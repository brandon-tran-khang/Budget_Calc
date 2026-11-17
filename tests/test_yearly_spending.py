"""Tests for Yearly_Spending.py — merchant cleaning, classification, category mapping."""

import pandas as pd
import pytest
import Yearly_Spending as ys
from Yearly_Spending import (
    clean_merchant_name,
    classify_checking_transaction,
    classify_income_source,
    map_category,
    load_and_combine_csv_files,
    process_credit_cards,
    export_yearly_and_combined,
    _is_output_file,
)


class TestCleanMerchantName:
    def test_keyword_matching(self):
        assert clean_merchant_name('AMZN MKTP US*123ABC') == 'Amazon'
        assert clean_merchant_name('UBER *TRIP XYZ') == 'Uber'
        assert clean_merchant_name('STARBUCKS #12345') == 'Starbucks'
        assert clean_merchant_name('TRADER JOE\'S #456') == 'Trader Joes'

    def test_processor_prefix_removal(self):
        """SQ*, TST*, PY*, SP*, TOAST* prefixes should be stripped."""
        result = clean_merchant_name('SQ *LOCAL COFFEE SHOP')
        assert 'Sq' not in result
        assert result == 'Local Coffee Shop'

    def test_store_number_removal(self):
        result = clean_merchant_name('RANDOM STORE #9876')
        assert '#' not in result

    def test_title_case(self):
        result = clean_merchant_name('some random place')
        assert result == 'Some Random Place'

    def test_costco_variations(self):
        assert clean_merchant_name('COSTCO WHSE #1234') == 'Costco'
        assert clean_merchant_name('COSTCO GAS') == 'Costco'  # COSTCO keyword matches first

    def test_case_insensitivity(self):
        assert clean_merchant_name('spotify usa') == 'Spotify'
        assert clean_merchant_name('Netflix.com') == 'Netflix'


class TestClassifyCheckingTransaction:
    def test_income_keywords(self):
        assert classify_checking_transaction('DIRECT DEP COMPANY PAYROLL', 3000) == 'income'
        assert classify_checking_transaction('ACH CREDIT REFUND', 100) == 'income'

    def test_transfer_keywords(self):
        assert classify_checking_transaction('ONLINE TRANSFER TO SAVINGS', -500) == 'transfer'
        assert classify_checking_transaction('PAYMENT TO CHASE CARD', -1500) == 'transfer'
        # Card payments from checking would double-count the card's purchases
        assert classify_checking_transaction('CITI CARD ONLINE PAYMENT 4317 WEB ID: 1', -2788) == 'transfer'
        assert classify_checking_transaction('ZELLE SENT TO FRIEND', -50) == 'expense'
        assert classify_checking_transaction('ZELLE PAYMENT FROM X', 50) == 'income'
        assert classify_income_source('ZELLE PAYMENT FROM X') == 'P2P Transfer'

    def test_expense_by_amount(self):
        """Negative amount without transfer/income keywords = expense."""
        assert classify_checking_transaction('DEBIT CARD PURCHASE WALMART', -50) == 'expense'

    def test_income_by_positive_amount(self):
        """Positive amount without specific keywords = income."""
        assert classify_checking_transaction('MISCELLANEOUS DEPOSIT', 200) == 'income'

    def test_transfer_priority_over_income(self):
        """Transfer keywords should take priority even with income-like description."""
        assert classify_checking_transaction('TRANSFER DEPOSIT SAVINGS', 500) == 'transfer'


class TestClassifyIncomeSource:
    def test_payroll(self):
        assert classify_income_source('DIRECT DEP COMPANY PAYROLL') == 'Payroll'
        assert classify_income_source('PAYROLL DEPOSIT') == 'Payroll'

    def test_ach_credit(self):
        assert classify_income_source('ACH CREDIT REFUND') == 'ACH Credit'

    def test_deposit(self):
        assert classify_income_source('ATM DEPOSIT') == 'Deposit'

    def test_fallback(self):
        assert classify_income_source('UNKNOWN SOURCE') == 'Other Income'


class TestMapCategory:
    def test_exact_match(self):
        row = pd.Series({'Clean_Description': 'Costco', 'Category': 'Groceries'})
        category_map = {('Costco', 'Groceries'): 'Groceries'}
        assert map_category(row, category_map) == 'Groceries'

    def test_bank_fallback(self):
        row = pd.Series({'Clean_Description': 'Unknown Restaurant', 'Category': 'Food & Drink'})
        assert map_category(row, {}) == 'Restaurants'

    def test_bills_utilities_electric(self):
        row = pd.Series({'Clean_Description': 'Srp', 'Category': 'Bills & Utilities'})
        assert map_category(row, {}) == 'Home Electricity'

    def test_bills_utilities_water(self):
        row = pd.Series({'Clean_Description': 'City Of Chandler', 'Category': 'Bills & Utilities'})
        assert map_category(row, {}) == 'Home Water/Trash'

    def test_bills_utilities_internet(self):
        row = pd.Series({'Clean_Description': 'Cox', 'Category': 'Bills & Utilities'})
        assert map_category(row, {}) == 'Internet'

    def test_generic_gas_keyword(self):
        row = pd.Series({'Clean_Description': 'Some Gas Station', 'Category': 'Unknown'})
        assert map_category(row, {}) == 'Gas'

    def test_investment_keyword(self):
        row = pd.Series({'Clean_Description': 'Schwab Brokerage Moneylink Ppd Id: 1', 'Category': 'Uncategorized'})
        assert map_category(row, {}) == 'Investments'

    def test_default_personal(self):
        row = pd.Series({'Clean_Description': 'Mystery Store', 'Category': 'Unknown'})
        assert map_category(row, {}) == 'Personal'


class TestIsOutputFile:
    def test_year_prefixed(self):
        assert _is_output_file('2024_All_Transactions.csv') is True
        assert _is_output_file('2023_Weekly_Summary.csv') is True

    def test_all_prefixed(self):
        assert _is_output_file('all_transactions.csv') is True
        assert _is_output_file('all_income.csv') is True

    def test_raw_file(self):
        assert _is_output_file('Chase1234.csv') is False
        assert _is_output_file('Statement_Jan.csv') is False


CHASE = ("Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n"
         "01/05/2024,01/06/2024,STARBUCKS #1,Food & Drink,Sale,-5.00,\n"
         "01/07/2024,01/08/2024,STARBUCKS #1,Food & Drink,Sale,-5.00,\n"
         "01/09/2024,01/09/2024,Thanks,,Payment,100.00,\n"
         "01/10/2024,01/10/2024,TARGET,Shopping,Return,12.00,\n")
CITI_HDR = "Status,Date,Description,Debit,Credit,Member Name\n"
CITI_ROWS = ("Cleared,02/01/2024,SHELL OIL,30.00,,A\n"
             "Cleared,02/02/2024,\"ONLINE PAYMENT, THANK YOU\",,-1769.44,A\n")


def _write_data(d):
    (d / "chase.csv").write_text(CHASE)
    (d / "citi_new.csv").write_text("\ufeff" + CITI_HDR + CITI_ROWS, encoding="utf-8")
    (d / "citi_old.csv").write_text("Time period: x\n" + CITI_HDR + CITI_ROWS.replace("-1769", "1769"))
    (d / "zelle_assignments.csv").write_text("a,b\n1,2\n")
    (d / "junk.csv").write_text("foo,bar\n1,2\n")


def test_load_skips_non_exports_and_normalizes(tmp_path, monkeypatch):
    _write_data(tmp_path)
    monkeypatch.setattr(ys, "REIMBURSEMENTS_FILE", tmp_path / "zelle_assignments.csv")
    df = load_and_combine_csv_files(tmp_path)
    assert sorted(df['Source'].unique()) == ['Chase', 'Citi']
    assert len(df) == 4 + 2 + 2
    citi = df[df['Source'] == 'Citi']
    assert sorted(citi['Amount_Norm'].round(2)) == [-1769.44] * 2 + [30.0] * 2
    assert df[df['Description'] == 'TARGET']['Amount_Norm'].iloc[0] == -12.0


def test_citi_dollar_amounts_parse(tmp_path, monkeypatch):
    monkeypatch.setattr(ys, "REIMBURSEMENTS_FILE", tmp_path / "zelle_assignments.csv")
    (tmp_path / "citi.csv").write_text(
        CITI_HDR + 'Cleared,02/01/2024,SHELL OIL,$ 12.34,,A\nCleared,02/02/2024,REFUND, ,"$ 1,000.00",A\n')
    df = load_and_combine_csv_files(tmp_path)
    assert sorted(df['Amount_Norm'].round(2)) == [-1000.0, 12.34]


def test_unreadable_amount_skips_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ys, "REIMBURSEMENTS_FILE", tmp_path / "zelle_assignments.csv")
    (tmp_path / "bad.csv").write_text(CITI_HDR + "Cleared,02/01/2024,SHELL OIL,abc,,A\n")
    assert load_and_combine_csv_files(tmp_path).empty
    assert "ERROR bad.csv: 1 unreadable amounts, file skipped" in capsys.readouterr().out


def test_process_credit_cards_payments_and_refunds(tmp_path, monkeypatch):
    _write_data(tmp_path)
    monkeypatch.setattr(ys, "REIMBURSEMENTS_FILE", tmp_path / "zelle_assignments.csv")
    spend, pay = process_credit_cards(load_and_combine_csv_files(tmp_path), {})
    assert sorted(pay['Description']) == ['ONLINE PAYMENT, THANK YOU'] * 2 + ['Thanks']
    assert (spend['Net_Amount'] < 0).sum() == 1  # the Return stays as a negative
    assert spend['Net_Amount'].sum() == pytest.approx(5 + 5 - 12 + 30 + 30)
    assert (spend[spend['Source'] == 'Citi']['Category'] == 'Uncategorized').all()


def test_export_keeps_identical_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(ys, "DATA_DIR", tmp_path)
    df = pd.DataFrame({'Transaction Date': pd.to_datetime(['2024-01-05'] * 2), 'Net_Amount': [5.0, 5.0]})
    export_yearly_and_combined(df, [2024], ['Transaction Date', 'Net_Amount'], '_X.csv', 'all_x.csv')
    assert len(pd.read_csv(tmp_path / 'all_x.csv')) == 2


def test_main_end_to_end(tmp_path, monkeypatch):
    chk = tmp_path / "Checking"
    chk.mkdir()
    _write_data(tmp_path)
    (chk / "c.csv").write_text(
        "Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #\n"
        "DEBIT,01/03/2024,WALMART,-20.00,DEBIT_CARD,100,,\n"
        "CREDIT,01/04/2024,ZELLE PAYMENT FROM X,50.00,ACH_CREDIT,150,,\n"
        "DSLIP,01/05/2024,ONLINE TRANSFER TO SAV,-5.00,ACCT_XFER,145,,\n")
    for name, val in [("DATA_DIR", tmp_path), ("CHECKING_DIR", chk),
                      ("MAPPINGS_FILE", tmp_path.parent / f"{tmp_path.name}_map.csv"),
                      ("REIMBURSEMENTS_FILE", tmp_path / "zelle_assignments.csv")]:
        monkeypatch.setattr(ys, name, val)
    inbox = tmp_path / "Inbox"
    inbox.mkdir()
    (inbox / "chase2.csv").write_text(
        "Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n"
        "03/05/2024,03/06/2024,NEWSHOP,Shopping,Sale,-7.00,\n")
    ys.main()
    assert not (inbox / "chase2.csv").exists() and (tmp_path / "chase2.csv").exists()
    assert (tmp_path / "all_sources.csv").exists()
    assert '_file' not in pd.read_csv(tmp_path / "all_credit_card_payments.csv").columns
    assert (pd.read_csv(tmp_path / "all_transactions.csv")['Clean_Description'] == 'Newshop').any()
    names = {p.name for p in tmp_path.glob("*.csv")}
    assert {"2024_All_Transactions.csv", "2024_Weekly_Summary.csv", "2024_Quarterly_Summary.csv",
            "2024_Credit_Card_Payments.csv", "2024_All_Income.csv", "2024_All_Checking_Spending.csv",
            "all_transactions.csv", "all_credit_card_payments.csv", "all_income.csv",
            "all_checking_spending.csv"} <= names
    assert pd.read_csv(tmp_path / "all_income.csv")['Income_Source'].tolist() == ['P2P Transfer']


# --- history retention across successive Inbox drops (synthetic data, through main()) ---

CHASE_HDR = "Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n"


def _chase(rows):
    return CHASE_HDR + "".join(f"{d},{d},{n},Shopping,Sale,-{a},\n" for d, n, a in rows)


def _citi(rows):
    return CITI_HDR + "".join(f"Cleared,{d},{n},{a},,A\n" for d, n, a in rows)


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    for name, val in [("DATA_DIR", tmp_path), ("CHECKING_DIR", tmp_path / "Checking"),
                      ("MAPPINGS_FILE", tmp_path.parent / f"{tmp_path.name}_map.csv"),
                      ("REIMBURSEMENTS_FILE", tmp_path / "zelle_assignments.csv")]:
        monkeypatch.setattr(ys, name, val)

    def drop(name, text):
        (tmp_path / "Inbox").mkdir(exist_ok=True)
        (tmp_path / "Inbox" / name).write_text(text)
        ys.main()
        return pd.read_csv(tmp_path / "all_transactions.csv")
    return tmp_path, drop


OLD = [("01/05/2024", "JANSHOP", "10.00"), ("02/05/2024", "FEBSHOP", "20.00"),
       ("03/05/2024", "MARSHOP", "30.00"), ("03/20/2024", "MARTWO", "31.00")]
NEW = [("03/05/2024", "MARSHOP", "30.00"), ("03/20/2024", "MARTWO", "31.00"),
       ("04/10/2024", "COFFEE", "5.00"), ("04/10/2024", "COFFEE", "5.00"),
       ("05/02/2024", "MAYSHOP", "50.00")]


@pytest.mark.parametrize("fmt, name", [(_chase, "Chase1111_old.csv"), (_citi, "citi_old.csv")])
def test_newer_drop_keeps_history_without_double_count(pipeline, fmt, name):
    data, drop = pipeline
    first = drop(name, fmt(OLD))
    assert len(first) == 4
    second = drop(name.replace("old", "new"), fmt(NEW))
    counts = second['Clean_Description'].value_counts().to_dict()
    assert counts == {'Janshop': 1, 'Febshop': 1, 'Marshop': 1, 'Martwo': 1, 'Coffee': 2, 'Mayshop': 1}
    assert second['Net_Amount'].sum() == pytest.approx(10 + 20 + 30 + 31 + 10 + 50)
    assert (data / name).exists() and (data / name.replace("old", "new")).exists()


def test_reissued_card_counts_once_and_keeps_both_histories(pipeline):
    data, drop = pipeline
    overlap = [(f"02/{d:02d}/2024", f"OVER{d}", f"{d}.50") for d in range(1, 13)]
    drop("Chase1111_old.csv", _chase([("01/10/2024", "JANA", "7.00"), ("01/11/2024", "JANB", "8.00")] + overlap))
    out = drop("Chase2222_new.csv", _chase(overlap + [("03/10/2024", "MARA", "9.00"), ("04/10/2024", "APRA", "11.00")]))
    assert len(out) == 2 + 12 + 2
    assert out['Clean_Description'].str.startswith('Over').sum() == 12
    assert {'Jana', 'Janb', 'Mara', 'Apra'} <= set(out['Clean_Description'])
    assert (data / "Chase1111_old.csv").exists() and (data / "Chase2222_new.csv").exists()


def test_unused_inputs_flags_only_unread_bank_csvs(tmp_path, monkeypatch):
    monkeypatch.setattr(ys, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ys, "CHECKING_DIR", tmp_path / "Checking")
    monkeypatch.setattr(ys, "REIMBURSEMENTS_FILE", tmp_path / "zelle_assignments.csv")
    (tmp_path / "Checking").mkdir()
    for name in ("read.csv", "refused.CSV", "2024_All_Transactions.csv", "all_sources.csv", "zelle_assignments.csv"):
        (tmp_path / name).write_text("x\n")
    (tmp_path / "Checking" / "ck_refused.csv").write_text("x\n")
    assert ys.unused_inputs(pd.DataFrame({"File": ["read.csv"]})) == ["ck_refused.csv", "refused.CSV"]
