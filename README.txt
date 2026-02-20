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
- Maps transactions to 24 custom budget categories (Groceries, Gas, Restaurants, etc.)
- Filters out credit card payments to avoid double-counting
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

Requirements
-------------
- Python 3
- pandas
- streamlit
- plotly

Setup
------
1. Install dependencies:
       pip install pandas streamlit plotly

2. Export transaction CSVs from your bank accounts:
   - Credit card CSVs (Chase/Citi) go in the Data/ folder
   - Checking account CSVs (Chase) go in the Data/Checking/ folder
   CSVs from any year will be processed automatically.

3. Run the data processing script:
       python Yearly_Spending.py

4. Launch the dashboard:
       streamlit run frontend.py

Budget Categories
------------------
The system uses 24 predefined categories:
  Home Electricity, Home Water/Trash, Home Furniture, Internet, Phone Bill,
  HOA Bill, Home Maintenance, Car Registration, Discord Subscription,
  Spotify Subscription, Amazon Prime Subscription, Gym Membership,
  Chase Sapphire Preferred Fee, Costco Membership, Groceries, Gas,
  Restaurants, Health/Doctors, Car Maintenance, Pest Control, Landscaping,
  Games, Vacation, Personal

Transactions are mapped via category_mappings.csv (auto-created on first run).
Unmapped transactions default to "Personal" but can be assigned via the
"Manage Categories" tab in the dashboard. The dashboard writes changes back
to the CSV file, so no source code editing is needed to update mappings.

Project Structure
------------------
  Budget_Calc/
  ├── frontend.py              Streamlit dashboard
  ├── Yearly_Spending.py       Data processing pipeline
  ├── recurring.py             Recurring expense detection logic
  ├── category_mappings.csv    Merchant-to-category mappings (auto-created)
  ├── Data/                    Bank CSVs and processed output (git-ignored)
  │   └── Checking/            Chase checking account CSVs (git-ignored)
  ├── improvements/            Improvement proposals
  ├── CLAUDE.md                Project context for Claude Code
  └── README.txt               This file
