"""Shared test fixtures for Budget_Calc tests."""

import pandas as pd
import pytest


@pytest.fixture
def sample_transactions():
    """Basic credit card transactions DataFrame."""
    return pd.DataFrame({
        'Transaction Date': pd.to_datetime([
            '2024-01-15', '2024-01-15', '2024-02-10', '2024-03-05',
            '2024-03-05', '2024-04-20'
        ]),
        'Clean_Description': [
            'Starbucks', 'Starbucks', 'Costco', 'Starbucks',
            'Amazon', 'Costco'
        ],
        'Category': [
            'Food & Drink', 'Food & Drink', 'Groceries', 'Food & Drink',
            'Shopping', 'Groceries'
        ],
        'Budget_Category': [
            'Restaurants', 'Restaurants', 'Groceries', 'Restaurants',
            'Personal', 'Groceries'
        ],
        'Net_Amount': [5.25, 5.25, 150.00, 6.50, 29.99, 200.00],
        'Source': ['Chase'] * 6,
        'account_type': ['credit'] * 6,
    })


@pytest.fixture
def sample_checking():
    """Basic checking account transactions DataFrame."""
    return pd.DataFrame({
        'Transaction Date': pd.to_datetime([
            '2024-01-01', '2024-01-15', '2024-02-01', '2024-02-15',
        ]),
        'Description': [
            'DIRECT DEP COMPANY PAYROLL',
            'DEBIT CARD PURCHASE WALMART',
            'ONLINE TRANSFER TO SAVINGS',
            'ACH CREDIT REFUND',
        ],
        'Amount': [3000.00, -50.00, -500.00, 100.00],
        'Amount_Norm': [-3000.00, 50.00, 500.00, -100.00],
        'Category': ['Deposits', 'Shopping', 'Transfer', 'Deposits'],
        'Source': ['Chase Checking'] * 4,
        'account_type': ['checking'] * 4,
    })


@pytest.fixture
def recurring_transactions():
    """Transactions designed to trigger recurring detection (3 consecutive months)."""
    rows = []
    for month in [1, 2, 3, 4]:
        rows.append({
            'Transaction Date': pd.Timestamp(f'2024-{month:02d}-15'),
            'Clean_Description': 'Netflix',
            'Budget_Category': 'Personal',
            'Net_Amount': 15.99,
        })
        rows.append({
            'Transaction Date': pd.Timestamp(f'2024-{month:02d}-01'),
            'Clean_Description': 'Spotify',
            'Budget_Category': 'Spotify Subscription',
            'Net_Amount': 10.99,
        })
    # Add a non-recurring merchant
    rows.append({
        'Transaction Date': pd.Timestamp('2024-01-20'),
        'Clean_Description': 'Random Store',
        'Budget_Category': 'Personal',
        'Net_Amount': 45.00,
    })
    return pd.DataFrame(rows)
