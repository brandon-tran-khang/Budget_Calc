"""Tests for transaction_notes.py — key generation, save/load, merge, tag totals."""

import pandas as pd
import pytest
from transaction_notes import (
    generate_tx_key, add_tx_keys, load_notes, save_notes,
    merge_notes, get_all_tags, filter_by_tags, compute_tag_totals,
)
import config


class TestKeyGeneration:
    def test_basic_key_format(self):
        key = generate_tx_key('2024-01-15', 'Starbucks', 5.25)
        assert key == '2024-01-15::Starbucks::5.25'

    def test_timestamp_input(self):
        key = generate_tx_key(pd.Timestamp('2024-03-20'), 'Amazon', 29.99)
        assert key == '2024-03-20::Amazon::29.99'


class TestAddTxKeys:
    def test_unique_keys_for_duplicates(self, sample_transactions):
        """Phase 1a fix: duplicate transactions should get unique keys."""
        df = add_tx_keys(sample_transactions)
        assert df['_tx_key'].is_unique, "Transaction keys must be unique even for duplicate transactions"

    def test_duplicate_transactions_get_indexed_keys(self, sample_transactions):
        """Two $5.25 Starbucks on 2024-01-15 should get ::0 and ::1 suffixes."""
        df = add_tx_keys(sample_transactions)
        starbucks_keys = df[
            (df['Clean_Description'] == 'Starbucks') &
            (df['Transaction Date'] == pd.Timestamp('2024-01-15'))
        ]['_tx_key'].tolist()
        assert len(starbucks_keys) == 2
        assert starbucks_keys[0].endswith('::0')
        assert starbucks_keys[1].endswith('::1')

    def test_single_transactions_get_zero_index(self, sample_transactions):
        """Non-duplicate transactions should get ::0 suffix."""
        df = add_tx_keys(sample_transactions)
        amazon_keys = df[df['Clean_Description'] == 'Amazon']['_tx_key'].tolist()
        assert len(amazon_keys) == 1
        assert amazon_keys[0].endswith('::0')


class TestSaveLoadRoundTrip:
    def test_save_and_load(self, tmp_path, monkeypatch):
        """Notes should survive a save → load round-trip."""
        notes_file = tmp_path / "test_notes.csv"
        monkeypatch.setattr(config, "NOTES_FILE", notes_file)

        notes = pd.DataFrame({
            '_tx_key': ['2024-01-15::Starbucks::5.25::0', '2024-02-10::Costco::150.00::0'],
            'Note': ['Morning coffee', ''],
            'Tags': ['Business', 'Groceries'],
        })
        save_notes(notes)
        loaded = load_notes()

        assert len(loaded) == 2  # Both have content (tags count)
        starbucks = loaded[loaded['_tx_key'] == '2024-01-15::Starbucks::5.25::0']
        assert starbucks.iloc[0]['Note'] == 'Morning coffee'
        assert starbucks.iloc[0]['Tags'] == 'Business'

    def test_empty_notes_dropped(self, tmp_path, monkeypatch):
        """Rows with no note and no tags should be dropped on save."""
        notes_file = tmp_path / "test_notes.csv"
        monkeypatch.setattr(config, "NOTES_FILE", notes_file)

        notes = pd.DataFrame({
            '_tx_key': ['key1::0', 'key2::0'],
            'Note': ['has content', ''],
            'Tags': ['', ''],
        })
        save_notes(notes)
        loaded = load_notes()
        assert len(loaded) == 1
        assert loaded.iloc[0]['_tx_key'] == 'key1::0'

    def test_old_3part_keys_migrated(self, tmp_path, monkeypatch):
        """Old 3-part keys should be migrated to 4-part on load."""
        notes_file = tmp_path / "test_notes.csv"
        monkeypatch.setattr(config, "NOTES_FILE", notes_file)

        # Write old-format keys directly
        pd.DataFrame({
            '_tx_key': ['2024-01-15::Starbucks::5.25'],
            'Note': ['Old note'],
            'Tags': [''],
        }).to_csv(notes_file, index=False)

        loaded = load_notes()
        assert loaded.iloc[0]['_tx_key'] == '2024-01-15::Starbucks::5.25::0'


class TestMergeNotes:
    def test_merge_adds_note_columns(self, sample_transactions):
        df = add_tx_keys(sample_transactions)
        notes = pd.DataFrame(columns=['_tx_key', 'Note', 'Tags'])
        merged = merge_notes(df, notes)
        assert 'Note' in merged.columns
        assert 'Tags' in merged.columns

    def test_merge_matches_notes(self, sample_transactions):
        df = add_tx_keys(sample_transactions)
        first_key = df['_tx_key'].iloc[0]
        notes = pd.DataFrame({
            '_tx_key': [first_key],
            'Note': ['Test note'],
            'Tags': ['Business'],
        })
        merged = merge_notes(df, notes)
        matched = merged[merged['_tx_key'] == first_key]
        assert matched.iloc[0]['Note'] == 'Test note'


class TestComputeTagTotals:
    def test_basic_tag_totals(self):
        df = pd.DataFrame({
            'Tags': ['Business, Tax Deductible', 'Business', '', 'Gift'],
            'Net_Amount': [100.0, 50.0, 25.0, 30.0],
        })
        totals = compute_tag_totals(df)
        assert totals['Business'] == 150.0
        assert totals['Tax Deductible'] == 100.0
        assert totals['Gift'] == 30.0

    def test_empty_tags_ignored(self):
        df = pd.DataFrame({
            'Tags': ['', None, '  '],
            'Net_Amount': [10.0, 20.0, 30.0],
        })
        assert compute_tag_totals(df) == {}

    def test_missing_columns(self):
        df = pd.DataFrame({'other': [1, 2]})
        assert compute_tag_totals(df) == {}


class TestFilterByTags:
    def test_filters_matching_tags(self):
        df = pd.DataFrame({
            'Tags': ['Business', 'Gift', 'Business, Gift', ''],
            'Net_Amount': [1, 2, 3, 4],
        })
        result = filter_by_tags(df, ['Business'])
        assert len(result) == 2
        assert set(result.index) == {0, 2}

    def test_no_tags_returns_full_df(self):
        df = pd.DataFrame({'Tags': ['A'], 'Net_Amount': [1]})
        result = filter_by_tags(df, [])
        assert len(result) == 1
