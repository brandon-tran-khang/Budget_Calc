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
    ys.main()
    names = {p.name for p in tmp_path.glob("*.csv")}
    assert {"2024_All_Transactions.csv", "2024_Weekly_Summary.csv", "2024_Quarterly_Summary.csv",
            "2024_Credit_Card_Payments.csv", "2024_All_Income.csv", "2024_All_Checking_Spending.csv",
            "all_transactions.csv", "all_credit_card_payments.csv", "all_income.csv",
            "all_checking_spending.csv"} <= names
    assert pd.read_csv(tmp_path / "all_income.csv")['Income_Source'].tolist() == ['P2P Transfer']
