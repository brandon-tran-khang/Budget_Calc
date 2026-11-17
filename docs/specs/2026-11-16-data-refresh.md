# Spec: drop-folder data refresh ("update to current day")

_Written 2026-11-16 at 6f42d2d (branch fix/repair-june-merge). Baseline: 80 tests pass, pyflakes clean._
Owner request: "Drop new bank exports into a folder and the app updates to the current day. This must work for future refreshes."

Privacy: `Data/` and every bank CSV are private. Workers print only counts, date ranges, sums and headers, never rows, descriptions or merchants. They never modify the real `Data/` until step 5 below. A backup of `Data/` is at `../Budget_Calc_backups/Data_20261116_pre-refresh`.

## 1. Investigation findings (aggregates only)

New files in the repo root, classified by header:

| File | Format | Rows | Dates |
|---|---|---|---|
| `Chase5735_Activity_20261116.csv` | Chase card | 1149 | 2024-11-15..2026-11-13 |
| `Chase3189_Activity_20261116.csv` | Chase card | 294 | 2024-11-18..2026-11-06 |
| `Chase9088_Activity_20261116.csv` | Chase checking | 535 | 2024-11-18..2026-11-16 |
| `Since Oct 24, 2026.CSV` | Citi | 14 | 2026-10-24..2026-11-09 |

Chase exports reach back only about 24 months. The old files are therefore the **only** source for Jul–Nov 2024 and must be kept: they contribute 129 (5735), 159 (5967) and 124 (9088) rows that the new files lack.

**Overlap between the old and new exports**, matched as a (date, description, amount) multiset:
- 5735: all 873 old rows inside the new file's date range match new rows 1:1. The new file has 1 extra row inside that range (a 2026-02-26 transaction posted 02-27 that the old export lacked).
- 9088 checking: 430 of 434 match. The 4 that don't are 2026-07-01/02 rows whose descriptions changed between exports (date and amount still match: pending to posted). 0 rows would be lost if the newest file wins.
- **3189 is the reissued 5967 card**, not a new account. All 250 of the 5967 rows inside 3189's date range match 3189 rows exactly, and the per-quarter counts are identical from 2025Q1 to 2026Q2. 5967 alone holds Jul 2024 to 2024-11-17. Treating them as two accounts would double count about 250 rows.
- Within-file identical rows (real repeat purchases) do occur: 5–6 extra copies per card file. They must survive.

**Current code against the new files (scratch run with all files dropped into `Data/`, no code change):**
- Double counting: 2025 card spending goes from 637 rows/$29,493.79 to 1274/$58,987.58, income 2025 doubles, and so on.
- **A silent data-loss bug:** the new Citi export formats amounts as `$ 12.34` and ` -$ 123.45`, while the old one used `12.34`. `pd.to_numeric(..., errors='coerce').fillna(0)` turns every amount into 0. The 13 purchases are then dropped as zero rows, and the payment becomes $0. Nothing is printed.

**Citi gap:** `Year to date.CSV` ends 2026-06-28 and the new file starts 2026-10-24, so 2026-06-29..2026-10-23 (117 days) is missing. Checking still shows payments to Citi in Jul, Sep, Oct and Nov 2026, so the card was used and the spending is truly absent.

**Prototype of the chosen design**, run on a scratch copy with the real files. Per-year results, rows / sum:

| Output | Before (today) | After |
|---|---|---|
| all_transactions 2024 | 380 / 15,898.59 | 380 / 15,898.59 (identical) |
| all_transactions 2025 | 637 / 29,493.79 | 637 / 29,493.79 (identical) |
| all_transactions 2026 | 378 / 16,775.29 (to 06-30) | 703 / 31,336.54 (to 11-13) |
| Source split | Chase 1339, Citi 56 | Chase 1651, Citi 69 |
| credit_card_payments 2026 | 21 / -21,457.93 | 30 / -34,603.89 |
| all_income 2026 | 49 / 66,736.77 | 97 / 96,093.09 |
| all_checking_spending 2026 | 57 / 46,007.02 | 98 / 58,569.28 |
| rows with Budget_Category 'Personal' | 425 | 525 |

- Up to 2026-06-30, income, checking spending and payments are an identical multiset. Card spending differs only by the one 2026-02-26 row that was missing before (+1 row, +$13.51).
- `zelle_assignments.csv`: 14 assignments, 12 matched to income rows both before and after (the 2 unmatched are the known old outgoing-Zelle rows). Assignments are content-keyed, so they survive re-ingest.
- `transaction_notes.csv` does not exist yet, so no notes are at risk. `_tx_key` is content-based (date::merchant::amount::occ), so it stays stable as long as dedup gives the same rows. The table above shows it does for all history.
- `category_mappings.csv` needs no change. About 100 new rows default to 'Personal' for the owner to review on the Categories page.
- The years set is unchanged (2024–2026), so no stale per-year files are created.

## 2. Chosen design

There is one command and no new script: `python Yearly_Spending.py [INBOX]`. INBOX defaults to `Data/Inbox/`.

1. **Intake** (new `ingest.py`, `intake()`):
   - For every `*.csv`/`*.CSV` directly in INBOX, classify it by **header**, never by filename:
     - Chase card goes to `Data/`.
     - Citi goes to `Data/`.
     - Chase checking goes to `Data/Checking/`.
     - Anything else is unrecognized: it is left where it is and a `WARNING` line is printed. It is never moved or deleted.
   - Move recognized files into the folder above. If the name already exists there:
     - Byte-identical: delete the inbox copy and print "already imported".
     - Different: add `_2`, `_3`, … before the suffix.
   - Running again with an empty inbox does nothing.
   - If INBOX is `Data/` or `Data/Checking/` itself, intake is skipped.
2. **Loading** (existing loaders): unchanged, except:
   - Each row gets a `_file` column holding the file name.
   - Amounts are parsed with a tolerant helper that strips `$`, `,` and whitespace.
   - A recognized file that still has unreadable non-blank amounts is **refused**: `ERROR <file>: N unreadable amounts, file skipped`. It is never zero-filled.
3. **Overlap rule** (`ingest.drop_superseded`), applied separately to the card frame and the checking frame:
   - **Account** comes from `Chase(\d{4})` in the file name; Citi files use `Citi`; otherwise the file stem.
   - **Account merge:** for two files of different accounts but the same `Source`, take the older account (smaller max date). If at least 10 of its rows fall inside the newer file's [min, max] date span, and at least 90% of those rows match the newer file by (date, Description, Amount_Norm rounded to 2) multiset, relabel the older account to the newer one and print `merged account 5967 into 3189 (250/250 overlapping rows match)`. This handles card reissues without any config.
   - **Newest wins:** within an account, order files by (max date, row count, file name), newest first. The newest file contributes all its rows, identical rows included. Each older file contributes only rows whose date lies **outside** the [min, max] span of every newer file of that account.
   - Why: a re-export is authoritative for the dates it covers, so pending-to-posted description or date changes and late-posted rows inside the window resolve to the new version. Identical purchases within a file are never compared to each other.
   - Rejected alternatives:
     - `drop_duplicates` deletes real repeat purchases (finding 6).
     - A max-multiplicity union double counts description changes (the 4 checking rows) and collapses identical charges across different cards.
     - Filename date or mtime is unreliable after copying, and Citi names carry no date.
   - Superseded files are **not** archived or moved. Chase exports cap at about 24 months, so old files hold history that no new export can replace. A file that contributes 0 rows just shows `Rows_Used=0` in the report.
4. **Coverage report:**
   - `drop_superseded` also returns one row per file: `Account, Source, File, First, Last, Rows_In_File, Rows_Used`. `main()` concatenates the card and checking rows and writes `Data/all_sources.csv`. The `all_` prefix means the loaders already skip it, and `Data/*` is gitignored.
   - `main()` then prints:
     - `Data through YYYY-MM-DD`: the max `Last` across all files. This is what "current day" means: the newest transaction date in any export.
     - One line per account: dates, rows used, file count.
     - Each line from `coverage_warnings(sources)`, prefixed with `WARNING`.
   - `coverage_warnings`:
     - **Gap:** within an account, sort files by `First` and keep a running max of `Last`. If the next `First` is more than 7 days after the running max + 1 day, warn `"<Account>: no data <a>..<b> (<n> days)"`. For the real data this gives `Citi: no data 2026-06-29..2026-10-23 (117 days)`.
     - **Stale:** an account whose `Last` is more than 30 days before Data-through gets `"<Account>: last transaction <date>, <n> days behind"`. The real data has none: 5735 ends 11-13, 3189 11-06, Citi 11-09, 9088 11-16.
5. **Web element** (minimal; skipped: an in-app "Import" button, because the pipeline has side effects and the CLI command is enough):
   - In the `frontend.py` sidebar, replace `st.caption(f"Last updated: ...")` with:
     - `st.caption(f"Data through {d:%b %-d, %Y}")`, where `d` = max `Last` from `all_sources.csv`, falling back to `df_trans['Transaction Date'].max()` when the file is missing.
     - Then one `st.caption(f":material/warning: {w}")` per `coverage_warnings` line.
   - Captions use theme-muted text with no colors set.
   - Add a cached `load_sources()` beside the other loaders. It returns an empty DataFrame if the file is missing, and shows `st.error` and an empty frame on a parse error, like `load_income_data`.
6. **gitignore:** add `/*.csv` and `/*.CSV`. Root-level CSVs are private: bank drops, `category_mappings.csv`, notes.

## 3. Exact changes

### New `ingest.py` (pure pandas plus pathlib/shutil/filecmp; imports nothing from streamlit)
- `classify_file(path) -> 'card' | 'checking' | None`
  - Reads the first line with `utf-8-sig`. If it contains `Time period`, read the second line instead.
  - Returns `'checking'` when the header starts with `Details,Posting Date`.
  - Returns `'card'` when it contains `Debit` and `Credit` and `Date` (Citi), or `Transaction Date` and `Description` and `Amount` (Chase card).
  - Otherwise returns `None`. Never raises on an unreadable or binary file: it returns `None`.
- `intake(inbox, data_dir, checking_dir) -> list[str]`
  - Implements step 1 and returns the printed lines. Creates `inbox` if it is missing (so `Data/Inbox/` appears on first run).
- `drop_superseded(df) -> (df, sources)`
  - Implements step 3.
  - The input needs `_file`, `Source`, `Transaction Date`, `Description` and `Amount_Norm`. The output drops `_file` and any temporary columns, and keeps the input row order within the rows it keeps.
  - On an empty input it returns `(df, empty sources)`.
- `coverage_warnings(sources, gap_days=7, stale_days=30) -> list[str]`: step 4.

Target size is about 100 lines. The thresholds stay as default arguments and do not go in config.

### `Yearly_Spending.py`
- Add `_to_amount(s)`: `pd.to_numeric(s.astype(str).str.replace(r'[$,\s]', '', regex=True), errors='coerce')`. Use it for Citi `Debit`/`Credit`, Chase `Amount` and checking `Amount`.
  - Before using the result, count the "bad" values: raw non-blank (`notna` and `strip() != ''`) but parsed NaN. If there are any, print the ERROR and `continue`, skipping the file. Then `fillna(0)` as today.
- Both loaders add `df['_file'] = file.name`.
- `main(inbox=None)`:
  1. `inbox = Path(inbox) if inbox else DATA_DIR / 'Inbox'`, resolved at call time, because tests monkeypatch `DATA_DIR`.
  2. Run `intake(inbox, DATA_DIR, CHECKING_DIR)` first, before loading.
  3. After loading: `raw_df, card_src = drop_superseded(raw_df)` and the same for `checking_df`, each only if non-empty.
  4. At the end, write `DATA_DIR/'all_sources.csv'` and print the coverage report.
- `if __name__ == "__main__": main(sys.argv[1] if len(sys.argv) > 1 else None)`.
- `all_credit_card_payments.csv` must not gain a `_file` column.

### `frontend.py`
- Add `load_sources()`.
- Replace the line 435 caption as in step 5.
- Import `coverage_warnings` from `ingest`.

### Docs
- `README.txt` Setup step 2–3 and `docs/PROJECT_CONTEXT.md` "How it runs": describe the routine below.
- `docs/PROJECT_CONTEXT.md` Status: record the Citi `$` parsing fix, the dedup rule, 3189 = reissued 5967, and the Citi gap. Add `all_sources.csv` to the data contracts.
- `docs/UI_SPEC.md` line 83: "Data through" plus coverage warnings.

The routine:
1. Download a CSV per account: Chase "all transactions" (max range), Citi any range.
2. Put the files in `Data/Inbox/` (or anywhere, and pass that path).
3. Run `python Yearly_Spending.py [path]`, read the WARNING lines, then refresh the dashboard.

Never delete old exports: they hold history beyond Chase's 24-month window.

### Tests
- New `tests/test_ingest.py`, synthetic data only:
  1. **Re-export not double counted:**
     - Old Chase1111 file has 2024-01-05..2024-03-20.
     - New Chase1111 file has 2024-02-01..2024-04-10, with identical rows for the Feb–Mar dates.
     - Result: old Jan rows plus all new rows, with no Feb–Mar duplicates. The `Rows_Used` values are correct.
  2. **Identical purchases survive:** two identical same-day rows in the new file stay 2, and two identical rows in the old file outside the new span stay 2.
  3. **Pending/posted change does not duplicate:** the old file has `PENDING X`, 2024-03-30, 10.00. The new file (span covers 03-30) has `X`, 2024-04-01, 10.00. Exactly one row remains.
  4. **Account merge:**
     - Chase2222 old and Chase3333 new share at least 10 identical rows in the overlap: merged, no double count, and the old rows outside the span are kept.
     - Two accounts sharing only 2 identical rows: not merged, and all rows kept.
  5. **Citi:** one Citi file is never merged with a Chase file, even if rows match (different `Source`).
  6. **`classify_file`:** the Chase card, Chase checking, Citi, and Citi-with-`Time period` headers classify correctly. `zelle_assignments.csv`-style headers and junk return None.
  7. **`intake`:**
     - Files are moved to the right folder, and an unrecognized file stays in the inbox.
     - A second run returns no moves and leaves the folder listing unchanged.
     - A byte-identical re-drop removes the inbox copy.
     - A different file with the same name lands as `_2`.
     - `.CSV` and `.csv` are both handled.
  8. **`coverage_warnings`:** gap detected with the right dates and day count; stale detected; no warning for overlapping files.
- `tests/test_yearly_spending.py`:
  - Citi `$ 12.34` / ` -$ 1.00` amounts parse to 12.34 / -1.00.
  - A file with an unreadable amount (`abc`) is skipped and prints `ERROR`.
  - `test_main_end_to_end` still passes; extend it so that:
    - a file dropped in an inbox directory gets ingested and appears in the outputs,
    - `all_sources.csv` exists,
    - the payments output has no `_file` column.
  - Existing loader tests stay unchanged: dedup lives in `main`, not in the loaders.

## 4. Task breakdown (Sonnet workers)

| # | Worker | Owns | Depends on |
|---|---|---|---|
| A | ingest | `ingest.py`, `tests/test_ingest.py` | none; the interface is fixed in section 3 |
| B | pipeline | `Yearly_Spending.py`, `tests/test_yearly_spending.py` | A's interface (can start in parallel; run tests once A lands) |
| C | UI + docs | `frontend.py`, `README.txt`, `docs/PROJECT_CONTEXT.md`, `docs/UI_SPEC.md`, `.gitignore` | A (imports `coverage_warnings`) |
| D | manager (me) | scratch real-data run, impeccable/browser review, then the real run | A, B, C reviewed |

A and B run in parallel; C starts when A is done. Each worker runs the full tests and pyflakes before handing back, and runs `graphify update .` after code changes. No worker touches the real `Data/` or the root CSVs.

**Final real-data step** (D, after acceptance passes on scratch):
```
mkdir -p Data/Inbox && mv Chase3189_Activity_20261116.csv Chase5735_Activity_20261116.csv Chase9088_Activity_20261116.csv "Since Oct 24, 2026.CSV" Data/Inbox/ && python Yearly_Spending.py
```
Final state:
- `Data/` holds 3 old card/Citi exports + `Chase3189_Activity_20261116.csv` + `Chase5735_Activity_20261116.csv` + `Since Oct 24, 2026.CSV` + outputs + `all_sources.csv` + `zelle_assignments.csv` + an empty `Inbox/`.
- `Data/Checking/` holds both 9088 files.
- The repo root has no bank CSVs.

## 5. Acceptance checklist (I review against this)

1. `uv run --with pandas --with pytest --with streamlit --with plotly python -m pytest -q`: all pass. That is more than 80, including the new tests from section 3.
2. `uvx pyflakes *.py tabs/*.py tests/*.py`: no output.
3. **Scratch real-data run.** Copy the repo without `.git`/graphify-out to the scratchpad and move the 4 new files into its `Data/Inbox/`. Then run `python -I -c 'import sys; sys.path.insert(0,"."); import Yearly_Spending as y; y.main()'`. Expect:
   - stdout shows 4 files moved (3 to `Data/`, 1 to `Data/Checking/`), `merged account 5967 into 3189`, `Data through 2026-11-16`, and exactly one WARNING: the Citi gap 2026-06-29..2026-10-23 (117 days).
   - Per-year aggregates equal the "After" column in section 1 (2024 and 2025 card spending identical to before; Chase 1651 / Citi 69; 2026 703 rows / 31,336.54; income 2026 97 / 96,093.09; checking 2026 98 / 58,569.28; payments 2026 30 / -34,603.89).
   - Running it again prints no intake moves, and every `Data/*.csv` output is byte-identical (`shasum` before and after).
   - Drop a junk CSV into the inbox: it is reported and stays put. Drop a Citi file with an `abc` amount: it is refused with ERROR and the outputs are unchanged.
4. **Headless app.** Run a fresh `AppTest.from_file("frontend.py")` on the scratch copy. Expect:
   - no exception,
   - a sidebar caption starting `Data through Nov 16, 2026`,
   - a caption containing `Citi: no data 2026-06-29..2026-10-23`.
   With `all_sources.csv` deleted, the app still runs and shows `Data through` from the transactions.
5. **Browser and impeccable.** Run `streamlit run frontend.py --server.address 127.0.0.1` on the scratch copy and take light and dark screenshots of the sidebar. Run the impeccable finish review against `.impeccable/surfaces/frontend-py.md` and DESIGN.md. Pass means: muted caption type, no hard-coded colors, readable in dark mode, no layout shift in the filters.
6. `git status --porcelain` after the real run shows no root-level CSVs. The diff touches only the files in section 3 (plus `graphify-out/`).
7. The real run's stdout matches item 3's numbers. The dashboard's 2026 Overview shows data into November.

## 6. Risks
- **Account auto-merge false positive:** this needs at least 90% of at least 10 overlapping rows to be identical across two different cards, which is implausible. Every merge is printed, so it can be audited.
- **A pending row whose date moves across the newer file's start boundary** could be counted twice. That boundary is 2+ years back for full exports, so the risk is negligible. Not handled: shortcut comment in code.
- **A short partial export dropped later** (e.g. "Since Oct 24") replaces older rows only inside its own span, which is correct. But if a statement-period file has gaps inside its span (Citi "since last statement" omits pending rows), those pending rows vanish until the next export. Acceptable, and documented.
- **The Citi gap stays** until the owner exports Jun 29–Oct 23. Until then, 2026 Citi spending is understated, and the warning surfaces this.
- Moving files is the only intake side effect, and the backup exists.

## 7. Owner questions (none blocking; defaults chosen)
1. Please download a Citi export covering 2026-06-29..2026-10-23 (or full-year 2026) and drop it into `Data/Inbox/`. Default until then: the warning stays visible.
2. Is 3189 the replacement card for 5967? The data says yes (250/250 rows identical), so the default merges them. Answer only if 5967 is still a separate, active card.
