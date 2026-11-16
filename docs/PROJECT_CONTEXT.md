# Budget_Calc — Project Context & Evaluation

_Evaluated 2026-11-16 at commit 7d68804 (HEAD of main). Source of truth for future sessions; update when findings are fixed._

## Status after the 2026-11-16 repair (uncommitted working tree)
Owner decisions: tabs/ router is canonical; refunds reduce spending; reimbursements (work/friends/family Zelle/Venmo/Cash App) reduce spending and are removed from income; brokerage transfers (Schwab/Wealthfront) are spending in a separate **Investments** category with a sidebar "Include Investments" toggle. Manager call: outgoing P2P = expense.

**Fixed:** findings 1–9, 11, 12 (Transactions search/notes/tags/category edit/CSV, report downloads, HTML share restored), 15 (load_notes raises on non-empty parse errors so a save can't wipe notes; income/checking loaders show st.error), 16 (note keys use 2-decimal amounts and order-independent duplicate numbering; load_notes migrates old keys), 18 (Week is Monday-based week of calendar year, %W, 0–53; never wraps), 13 (pipeline imports config), 14, 17; finding 10 handled (assigned reimbursements removed from income via `reimbursements.remove_assigned_from_income`); `freq='M'` and the deprecated `use_container_width` replaced. Pipeline and app run; 70 tests pass; pyflakes clean; all 9 tabs render for 2024–2026 (AppTest + browser).
**Also found and fixed during the repair:**
- The Citi export (`Data/Year to date.CSV`, header-first format, negative Credit values) was silently skipped, so 56 purchases were missing. Citi payments ("ONLINE PAYMENT, THANK YOU") are now detected.
- 31 checking-account payments to the Citi card ($16,970) were counted as spending (double count). They are now transfers.
- `zelle_assignments.csv` was being parsed as a bank file.

Effect on real data: card rows 1305→1395 (+7 restored duplicates, +27 refunds, +56 Citi); checking spending 179→148 rows.
**Still open:** stale per-year files aren't deleted for years that vanish; HTML entity in merchant names ("&Amp;"); no tag-totals UI when no notes exist yet. The Citi export covers only Jan–Jun 2026, so 2024–2025 Citi purchases are absent (owner should export full history). Two existing reimbursement assignments are outgoing "Zelle Payment To …" rows created by the old bug. They now net to zero; the owner can remove them in Assignment History.
New modules: `reimbursements.py` (pure matching/offset logic, one-for-one occurrence-index matching), `tabs/reimbursements.py` (assign + history with remove), `tests/test_reimbursements.py`.
The findings list below is the original 2026-11-16 evaluation, kept for history.

## UI overhaul ("Cash Envelopes"), 2026-11-16
Visual world chosen by the owner through impeccable. Contract: `.impeccable/surfaces/frontend-py.md`; spec: `docs/UI_SPEC.md`; tokens: `DESIGN.md`.
- `frontend.py` now uses `st.navigation` grouped pages (Review / Money flow / Clean up) in place of `st.tabs`. The filters sit in the sidebar under the nav, and data prep still runs before `pg.run()`. Tab `render()` signatures are unchanged; `overview.render` gains `card_payments=`.
- `ui.py` is the single home for presentation:
  - CSS tokens are derived from `currentColor`, so they follow Streamlit's light/dark toggle.
  - Components: `hero`, `envelopes`/`envelope_rows`, `receipt`/`receipts_panel`, `section`, `context_line`.
- `config.CATEGORY_COLORS` gives one color per budget category, used in every chart and envelope.
- `.streamlit/config.toml` holds the light/dark/sidebar themes and self-hosted Public Sans (`static/fonts`, OFL).
- Every edit (category, notes, reimbursement assign/remove, mappings) calls `ui.receipt`, which raises a toast and logs to "Changes this session". Reimbursement removal needs a popover confirm.
- Pie/donut charts were removed in favor of envelope rows and single-hue bars.
- Future hooks: per-category budget limits (`budget` key on envelope rows), command palette, saved filter presets.


## Purpose
Personal finance tracker for one user. It consolidates Chase/Citi credit-card CSV exports and Chase checking CSV exports,
categorizes spending into 24 custom budget categories, tracks income/cash flow, detects recurring subscriptions, and shows
it all in a Streamlit dashboard. Goal: understand spending habits, year-over-year trends, savings rate, and reimbursements
(Zelle/Venmo money received from others to offset shared costs).

## How it runs
1. Drop raw bank CSVs into `Data/` (credit cards) and `Data/Checking/` (checking). `Data/` is gitignored (private).
2. `python Yearly_Spending.py`: pipeline that writes processed CSVs back into `Data/`.
3. `streamlit run frontend.py`: dashboard that reads only the processed CSVs plus user-edited CSVs.
4. `pytest`: tests in `tests/` (pytest is not installed in system python; `uv run --with pandas --with pytest --with streamlit --with plotly python -m pytest`).

Python 3.14, pandas 2.3.3, streamlit 1.53.1, plotly 6.5.2.

## Modules
| File | Role |
|---|---|
| `Yearly_Spending.py` | Pipeline: load bank CSVs, normalize sign (spending positive), `clean_merchant_name`, `map_category`, split payments, classify checking rows as income/expense/transfer, then export per-year and combined CSVs. |
| `config.py` | Intended single source of truth for paths, categories, keywords, `PAYMENT_TERMS`, `DEFAULT_TAGS`. **Yearly_Spending.py does not import it** (it keeps its own diverged copies). |
| `recurring.py` | `detect_recurring_merchants` (same merchant, consecutive months, low std, ≤2 tx/month), `classify_transactions` (Fixed/Variable), `detect_subscription_changes` (earlier vs recent half). |
| `transaction_notes.py` | Notes/tags keyed by `date::merchant::amount::occurrence`; atomic save to `transaction_notes.csv`. |
| `chart_helpers.py` | Plotly styling helpers; used only by `tabs/`. |
| `frontend.py` | Streamlit app (1312 lines, monolithic). |
| `tabs/*.py` | Refactored per-tab `render()` modules (overview, vendor, transactions, forecasting, year_comparison, recurring_tab, cashflow, manage). **Imported but never called (dead).** |

## Data contracts
Pipeline outputs in `Data/`:
- `{YYYY}_All_Transactions.csv`, `all_transactions.csv`: credit-card spending. Columns: Transaction Date, Clean_Description, Category (bank's), Budget_Category, Net_Amount (+ = spend), Source, account_type, Month, Quarter, Week.
- `{YYYY}_Weekly_Summary.csv`, `{YYYY}_Quarterly_Summary.csv`: pivot tables by bank Category.
- `{YYYY}_Credit_Card_Payments.csv`, `all_credit_card_payments.csv`.
- `{YYYY}_All_Income.csv`, `all_income.csv`: checking income with Income_Source.
- `{YYYY}_All_Checking_Spending.csv`, `all_checking_spending.csv`.
User-edited state:
- `category_mappings.csv` (project root, untracked): (Clean_Description, Bank_Category) → Budget_Category. Seeded from `_SEED_CATEGORY_MAP` on first run; edited by the Manage tab.
- `transaction_notes.csv` (root, gitignored): _tx_key, Note, Tags.
- `Data/zelle_assignments.csv`: reimbursements assigned in the Reimbursements tab; `load_data()` injects them as negative-amount rows.

Category mapping precedence (`map_category`): exact (desc, bank_cat) mapping, then BANK_CATEGORY_FALLBACK, then Bills & Utilities/Uncategorized keyword rules, then gas/food keywords, then 'Personal' (also used as the "unreviewed" bucket).

## History that explains the current state
- Feb 2026: features added in sequence (multi-year, category mappings CSV, recurring, checking/income, notes/tags, monthly export).
- 793018f (2026-02-21): big refactor. Added config.py, tabs/ modules, chart_helpers, transaction_notes, tests; frontend.py became a thin router.
- 07a05fb (2026-06-27): "Add Reimbursements tab". Built on dbefff2 (before the refactor) on another branch, so it edited the **old monolithic** frontend.py and Yearly_Spending.py.
- 7d68804 (2026-06-27): merge of the two. Conflict resolution kept the monolith plus refactor imports, leaving **both files broken**. Both parents pass pyflakes; the merge does not.

## Verified findings (ranked)
### Critical: app and pipeline do not run
1. `frontend.py:365` uses undefined `directory` inside cached `load_data()`. NameError on every launch. Should be `DATA_DIR`.
2. `frontend.py` lacks `import plotly.express as px`, `import plotly.graph_objects as go`, `import calendar`. Every chart tab fails with NameError.
3. `Yearly_Spending.py:502-511` uses undefined `year_spending` (merge leftover). The pipeline crashes after writing credit-card files and **before** writing payments, income, and checking outputs. Evidence: in Data/, transactions/summaries are dated Jul 2, while income/checking/combined payments are still Jun 27 and per-year payment files are missing (deleted, never rewritten).
4. `Yearly_Spending.py:324` `process_credit_cards` references `PAYMENT_TERMS`, which is not defined in that module. `process_credit_cards`/`process_checking` exist but `main()` duplicates their logic inline instead of calling them.
5. Merge regression: `Yearly_Spending.TRANSFER_KEYWORDS` lost 'ZELLE' (config.py has it). Zelle sent counts as expense and Zelle received as income. Test `test_transfer_keywords` fails (56/57 pass).

### High: wrong numbers
6. `all_*.csv` combined files use `.drop_duplicates()`, which deletes legitimate identical transactions (same day, merchant, amount). Measured: 1312 per-year rows become 1305 combined, so **7 real transactions lost** from the dashboard.
7. Card refunds/credits (`Net_Amount <= 0`) are dropped entirely, so spending is overstated (27 such rows in the raw Chase exports).
8. `get_recurring_analysis(_df_dict)` (frontend.py:86): the only argument is underscore-prefixed, so Streamlit's cache ignores it. **Recurring/Fixed-vs-Variable results are stale when switching years** (first computed year is reused). The same pattern applies to `generate_*_summary_csv(_df_..._dict, ...)` (partially keyed by year/month only).
9. `detect_subscription_changes` splits by calendar month number only (`dt.month`), so multi-year input collapses Jan 2025 and Jan 2026. `Active_Range` shows month names without year.
10. Reimbursements: income deposits assigned as offsets are subtracted from spending but remain in income. Cashflow net savings double-counts them (logic-read; not measured).
11. Reimbursement assignment de-dupes by (date, merchant, amount), so two identical Zelle receipts can't both be assigned. No undo/delete UI.

### Medium: maintainability
12. Two parallel UIs: inline tab bodies in frontend.py vs tabs/*.render. The inline versions lost features that exist only in tabs/: Transactions search/notes/tags/inline category edit/CSV download, monthly/annual report downloads, HTML share. Reimbursements exists only inline.
13. Constants duplicated between Yearly_Spending.py and config.py (already diverged). Month dict re-created in frontend.py instead of `config.MONTH_NAMES`. Paths hard-coded instead of `DATA_DIR`.
14. `main()` deletes the same output files 2–3 times; duplicate dict keys in `_SEED_CATEGORY_MAP`.
15. Silent `except Exception: return pd.DataFrame()` in loaders and `load_notes` hides parse errors.
16. Notes key uses float amount repr plus occurrence index. Re-ordering or re-processing can re-attach notes to the wrong duplicate.
17. `__pycache__/*.pyc` files are committed to git (should be gitignored). README lists categories with slightly different names than code ("Health/Doctors" vs "Health / Doctors", "Pest Control" vs "Pest control").
18. ISO week numbers: late-December dates can land in week 1 of the year's weekly summary.

### UI/UX
Sidebar collapsed by default but holds all filters. Forced black metric text, so dark mode is unreadable. "Last Updated" shows today's date, not the data date. 9 emoji tabs overflow on narrow screens. Manage tab gives no save confirmation. Forecast for past years uses min-to-max date span, inconsistent with "year in review". `freq='M'` deprecated in tabs/forecasting.py.
- Minor follow-ups from the 2026-11-16 review: see `docs/IMPROVEMENTS.md`.

### Tests
57 tests (recurring, transaction_notes, pure Yearly_Spending helpers). Untested: all loaders, `process_*`, `export_yearly_and_combined`, `main`, `load_category_mappings`, chart_helpers, and the entire frontend/tabs layer. No test would have caught findings 1–4 (a pyflakes/ruff run would).

## Open decisions for the owner
- Which UI is canonical: restore the 793018f router with tabs/ (and port Reimbursements to `tabs/reimbursements.py`), or keep the monolith? Recommended: the tabs/ router.
- Should refunds offset category spending (net) or be shown separately?
- Should reimbursements reduce spending, income, or both (to avoid double counting)?
