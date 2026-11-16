# Improvements backlog

Small follow-ups found in review on 2026-11-16. Open items go at the top; done items stay below as a record.

## Open
None.

## Done (2026-11-16)
1. **Toast queue key used outside ui.py.** Removed the outside use, so no `ui.toast` helper was needed. The "No changes to save" branch calls `st.toast` directly because no rerun follows it. Only `ui.py` touches `_toasts` now.
2. **Saving with no changes rewrote notes.** `tabs/transactions.py` now loads and saves notes only when `n_notes > 0`. It clears the cache and reruns only when a category or a note changed.
3. **No test for the changed-notes count.** Extracted `count_changed_notes(before, after)` into `transaction_notes.py`. Tests are in `tests/test_transaction_notes.py`: one edited row counts 1, and None, NaN and '' count as equal (0).
