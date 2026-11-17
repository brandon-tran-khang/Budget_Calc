Budget_Calc - Personal Finance Tracker
=======================================

A personal finance tracking tool that consolidates credit card transactions
from multiple banks (Chase and Citi) and checking account transactions,
automatically categorizes spending into custom budget categories, tracks
income and cash flow, and provides an interactive web dashboard for
analyzing spending habits.

What It Does
-------------
- Imports raw CSV transaction exports from Chase and Citi credit cards
- Imports Chase checking account CSVs for income and debit spending tracking
- Normalizes different bank formats into a unified dataset
- Cleans up merchant descriptions (removes payment processor codes, normalizes names)
- Maps transactions to 25 custom budget categories (Groceries, Gas, Restaurants, etc.)
- Filters out credit card payments to avoid double-counting
- Treats refunds as negative spending, so they reduce the category total
- Classifies checking transactions as income, expense, or transfer
- Generates weekly and quarterly spending summaries
- Supports multiple years of data with automatic year detection
- Displays an interactive Streamlit dashboard with:
    * Year selector to switch between years
    * Total spending metrics and transaction counts
    * Spending trend charts over time
    * Category breakdown pie chart
    * Top 10 merchants by spend
    * Most frequently visited merchants
    * Full searchable transaction log
    * Year-end spending projection (current year) or year-in-review (past years)
    * Year-over-year comparison charts and tables
    * Recurring expense detection and subscription tracking
    * Fixed vs. variable spending breakdown
    * Subscription change alerts (new, cancelled, price changes)
    * Income & cash flow analysis (income vs expenses, savings rate)
    * Income breakdown by source (payroll, deposits, ACH credits)
    * Debit vs credit card spending comparison
    * Reimbursements tab: assign incoming Zelle/Venmo/Cash App payments to a
      budget category to offset spending in that category

Requirements
-------------
- Python 3
- pandas
- streamlit
- plotly
- pytest (for running the test suite)

Setup
------
1. Install dependencies:
       pip install -r requirements.txt

2. Refresh routine (first load and every update):
   a. Download one CSV per account: Chase "all transactions" with the
      longest date range, Citi any range.
   b. Drop the files into Data/Inbox/ (or any folder, and pass its path).
      Files are recognized by their header, not their name, and moved into
      Data/ (cards) or Data/Checking/ (checking).
   c. Open the dashboard (below): it imports anything in Data/Inbox/ on
      launch and shows a toast plus any WARNING lines. To process another
      folder, or without the dashboard, run:
          python Yearly_Spending.py [path-to-folder]
   Never delete old exports: Chase only exports about 24 months, so the old
   files hold the only copy of earlier history. Old exports are never removed,
   so Chase and Citi history is kept and extended by each drop. When exports
   overlap, the newest export wins for the dates it covers. Cards 5967 and
   3189 are the same card (auto-merged).

4. Launch the dashboard:
       streamlit run frontend.py

5. Run tests (optional):
       python -m pytest

Budget Categories
------------------
The system uses 25 predefined categories:
  Home Electricity, Home Water/Trash, Home Furniture, Internet, Phone Bill,
  HOA Bill, Home Maintenance, Car Registration, Discord Subscription,
  Spotify Subscription, Amazon Prime Subscription, Gym Membership,
  Chase Sapphire Preferred Fee, Costco Membership, Groceries, Gas,
  Restaurants, Health / Doctors, Car Maintenance, Pest control, Landscaping,
  Games, Vacation, Personal, Investments (Schwab/Wealthfront transfers; sidebar toggle hides them)

Transactions are mapped via category_mappings.csv (auto-created on first run).
Unmapped transactions default to "Personal" but can be assigned via the
"Manage Categories" tab in the dashboard. The dashboard writes changes back
to the CSV file, so no source code editing is needed to update mappings.

Project Structure
------------------
  Budget_Calc/
  ├── frontend.py              Streamlit dashboard (entry point)
  ├── tabs/                    One module per dashboard tab
  ├── Yearly_Spending.py       Data processing pipeline
  ├── ingest.py                Inbox intake, overlap handling, coverage warnings
  ├── config.py                Budget categories, month names, keyword and mapping settings
  ├── recurring.py             Recurring expense detection logic
  ├── transaction_notes.py     Per-transaction notes, tags, and category edits
  ├── chart_helpers.py         Shared Plotly chart helpers
  ├── category_mappings.csv    Merchant-to-category mappings (auto-created)
  ├── Data/                    Bank CSVs and processed output (git-ignored)
  │   └── Checking/            Chase checking account CSVs (git-ignored)
  ├── tests/                   pytest test suite
  ├── docs/
  │   └── PROJECT_CONTEXT.md   Detailed project context and design notes
  ├── improvements/            Improvement proposals
  ├── CLAUDE.md                Project context for Claude Code
  └── README.txt               This file
