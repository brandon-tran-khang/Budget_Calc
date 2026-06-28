"""Tests for recurring.py — detection, classification, subscription changes."""

import pandas as pd
import pytest
from recurring import (
    _get_longest_consecutive_run,
    detect_recurring_merchants,
    classify_transactions,
    detect_subscription_changes,
)


class TestConsecutiveRun:
    def test_full_sequence(self):
        assert _get_longest_consecutive_run([1, 2, 3, 4, 5]) == 5

    def test_gap_in_middle(self):
        assert _get_longest_consecutive_run([1, 2, 4, 5, 6]) == 3

    def test_single_month(self):
        assert _get_longest_consecutive_run([7]) == 1

    def test_empty(self):
        assert _get_longest_consecutive_run([]) == 0

    def test_no_consecutive(self):
        assert _get_longest_consecutive_run([1, 3, 5, 7]) == 1


class TestDetectRecurringMerchants:
    def test_detects_recurring(self, recurring_transactions):
        result = detect_recurring_merchants(recurring_transactions)
        merchants = result['Clean_Description'].tolist()
        assert 'Netflix' in merchants
        assert 'Spotify' in merchants

    def test_filters_non_recurring(self, recurring_transactions):
        result = detect_recurring_merchants(recurring_transactions)
        merchants = result['Clean_Description'].tolist()
        assert 'Random Store' not in merchants

    def test_empty_dataframe(self):
        empty = pd.DataFrame(columns=['Transaction Date', 'Clean_Description', 'Budget_Category', 'Net_Amount'])
        result = detect_recurring_merchants(empty)
        assert result.empty

    def test_single_month_not_recurring(self):
        df = pd.DataFrame({
            'Transaction Date': pd.to_datetime(['2024-01-15']),
            'Clean_Description': ['Netflix'],
            'Budget_Category': ['Personal'],
            'Net_Amount': [15.99],
        })
        result = detect_recurring_merchants(df)
        assert result.empty

    def test_high_variance_filtered_out(self):
        """Merchant with wildly different amounts each month should not be recurring."""
        df = pd.DataFrame({
            'Transaction Date': pd.to_datetime(['2024-01-15', '2024-02-15', '2024-03-15']),
            'Clean_Description': ['Store'] * 3,
            'Budget_Category': ['Personal'] * 3,
            'Net_Amount': [10.00, 50.00, 100.00],
        })
        result = detect_recurring_merchants(df, amount_tolerance=2.0)
        assert result.empty

    def test_max_monthly_frequency_param(self):
        """Merchants with high frequency should be filtered by max_monthly_frequency."""
        rows = []
        for month in [1, 2, 3]:
            for _ in range(5):  # 5 visits per month
                rows.append({
                    'Transaction Date': pd.Timestamp(f'2024-{month:02d}-15'),
                    'Clean_Description': 'Frequent Shop',
                    'Budget_Category': 'Personal',
                    'Net_Amount': 10.00,
                })
        df = pd.DataFrame(rows)
        # Default max_monthly_frequency=2.0 should filter this out
        result = detect_recurring_merchants(df)
        assert result.empty
        # But a higher threshold should include it
        result = detect_recurring_merchants(df, max_monthly_frequency=10.0)
        assert not result.empty


class TestClassifyTransactions:
    def test_classifies_recurring(self, recurring_transactions):
        recurring_df = detect_recurring_merchants(recurring_transactions)
        classified = classify_transactions(recurring_transactions, recurring_df)
        netflix_rows = classified[classified['Clean_Description'] == 'Netflix']
        assert all(netflix_rows['is_recurring'])
        assert all(netflix_rows['spending_type'] == 'Fixed')

    def test_classifies_variable(self, recurring_transactions):
        recurring_df = detect_recurring_merchants(recurring_transactions)
        classified = classify_transactions(recurring_transactions, recurring_df)
        random_rows = classified[classified['Clean_Description'] == 'Random Store']
        assert all(~random_rows['is_recurring'])
        assert all(random_rows['spending_type'] == 'Variable')

    def test_empty_recurring(self, recurring_transactions):
        empty_recurring = pd.DataFrame(columns=['Clean_Description'])
        classified = classify_transactions(recurring_transactions, empty_recurring)
        assert all(~classified['is_recurring'])


class TestSubscriptionChanges:
    def test_detects_new_subscription(self):
        """A merchant appearing only in later months should be flagged as new."""
        rows = []
        # Netflix in all 6 months
        for m in range(1, 7):
            rows.append({
                'Transaction Date': pd.Timestamp(f'2024-{m:02d}-15'),
                'Clean_Description': 'Netflix',
                'Budget_Category': 'Personal',
                'Net_Amount': 15.99,
            })
        # New sub only in months 4-6
        for m in range(4, 7):
            rows.append({
                'Transaction Date': pd.Timestamp(f'2024-{m:02d}-01'),
                'Clean_Description': 'New Service',
                'Budget_Category': 'Personal',
                'Net_Amount': 9.99,
            })
        df = pd.DataFrame(rows)
        alerts = detect_subscription_changes(df)
        new_alerts = [a for a in alerts if a['type'] == 'new']
        assert any(a['merchant'] == 'New Service' for a in new_alerts)

    def test_empty_data(self):
        empty = pd.DataFrame(columns=['Transaction Date', 'Clean_Description', 'Budget_Category', 'Net_Amount'])
        assert detect_subscription_changes(empty) == []

    def test_too_few_months(self):
        """With min_consecutive_months=2, need at least 4 unique months for change detection."""
        df = pd.DataFrame({
            'Transaction Date': pd.to_datetime(['2024-01-15', '2024-02-15']),
            'Clean_Description': ['Netflix', 'Netflix'],
            'Budget_Category': ['Personal', 'Personal'],
            'Net_Amount': [15.99, 15.99],
        })
        assert detect_subscription_changes(df) == []
