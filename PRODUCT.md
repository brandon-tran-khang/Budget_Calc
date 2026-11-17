# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
One person (the owner) reviewing their own finances on a laptop or desktop in sit-down sessions. Their jobs, all equally important:
- **Monthly check-in:** where this month's money went compared with budget and last month, and anything unusual.
- **Year review:** year-over-year comparison, savings rate, category trends.
- **Data cleanup:** recategorize merchants, add notes and tags to transactions, assign reimbursements.
- **Subscription tracking:** recurring charges, fixed vs. variable spend, and changes over time.

## Product Purpose
Consolidates the owner's Chase and Citi credit-card exports and Chase checking exports into one honest picture of spending, income and cash flow. Success means net spending reflects what the owner actually paid out of pocket.

## Positioning
A private, local tool built around one person's own money rules, not a generic budgeting SaaS:
- Refunds and reimbursements (from work, friends and family) net against spending.
- Card payments are never double counted.
- Investments can be toggled in or out.
Data never leaves the machine.

## Operating Context
- `python Yearly_Spending.py` processes the raw CSVs in `Data/`.
- `streamlit run frontend.py --server.address 127.0.0.1` serves the dashboard on localhost only.
- Streamlit app: the sidebar holds the year/month filters and the Include Investments toggle; there are 9 tabs: Overview, Vendors, Transactions, Forecasting, Year Comparison, Recurring, Cash Flow, Reimbursements, Manage.

## Capabilities and Constraints
- Stack is fixed: Python + Streamlit + Plotly. Styling is limited to Streamlit theming (`.streamlit/config.toml`), injected CSS and Plotly templates. There is no custom JS framework.
- All existing functions must keep working:
  - transaction search, notes/tags, inline category edits and CSV export
  - report downloads and the HTML share export
  - reimbursement assign/remove
  - category mapping edits
- The money semantics are the owner's decisions; see `docs/PROJECT_CONTEXT.md`.
- Only the 24 budget categories defined in `config.py` exist.

## Evidence on Hand
Real data lives only in `Data/`, which is private. Never send it to an external service. Any screenshot is for local review only.

## Product Principles
1. Show the true out-of-pocket number first; explain it second.
2. Every edit (category, note, reimbursement) is visible right away and can be undone.
3. Get from a summary number to the transactions behind it in one or two moves.
4. Stay readable and calm during long review sessions; never perform.

## Accessibility & Inclusion
The app must work in both light and dark Streamlit themes. Chart colors must not depend on hue alone to separate categories.
