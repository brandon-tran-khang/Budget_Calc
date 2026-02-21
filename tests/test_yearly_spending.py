"""Tests for Yearly_Spending.py — merchant cleaning, classification, category mapping."""

import pandas as pd
import pytest
from Yearly_Spending import (
    clean_merchant_name,
    classify_checking_transaction,
    classify_income_source,
    map_category,
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
        assert classify_checking_transaction('ZELLE SENT TO FRIEND', -50) == 'transfer'

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
