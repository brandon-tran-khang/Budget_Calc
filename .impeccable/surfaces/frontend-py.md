---
version: 1
slug: "frontend-py"
primary_target: "frontend.py"
related_targets: ["tabs/overview.py"]
---

# Budget Calc dashboard (Streamlit app: frontend.py + tabs/)

Mode: Operate. Single owner, laptop, sit-down sessions. Jobs:
- monthly check-in
- year review
- data cleanup (categories, notes, reimbursements)
- subscription tracking

Constraints: Streamlit + Plotly only. Keep every existing function. Works in light and dark themes.

## Direction contract

THESIS: Every budget category is an envelope. Spending leaves it; refunds and reimbursements slip back in; out-of-pocket is what is really gone. This refuses the category default of white KPI cards, a donut and an indigo accent.

OWN-WORLD:
- Bank-envelope green rail (#1F4D3A) carrying grouped navigation and filters.
- Cool paper ground (#F4F6F2), not cream; ink #17201B; dark mode uses a deep green-black ground.
- One envelope-stock color per category family, used identically in charts, tables and chips.
- Public Sans (self-hosted) with tabular figures throughout.
- Envelope-flap chips; returned money drawn as a hatched slip.

STORY: Open the app and see the true out-of-pocket figure for the period first. Then see which envelopes it left from and how much came back. Then jump to the transactions or cleanup task behind any number. Every edit stamps a visible receipt.

FIRST VIEWPORT:
- Left green rail: app name, then Review (Overview, Vendors, Year Comparison, Forecast), Money flow (Cash Flow, Recurring), Clean up (Transactions, Reimbursements, Categories), then filters.
- Main, on a 12-column grid: one monumental figure (~96px/800) for out of pocket, with the period inline; a gross · refunds · reimbursed breakdown; a 6-month trend.
- Below: the Envelopes list (8 columns) beside Recent receipts (4 columns).

Signature move: envelope rows, where the bar is spent share and a hatched slip is the money returned. Motion: the bars draw in once (ease-out, ~400ms), with a reduced-motion fallback; 150–250ms state transitions.

Raises:
- From the type specimen: hierarchy by scale alone.
- From the Factory sleeve: one color code per category everywhere.
- From the timetable: tables rank by weight, not size.
- From Crouwel: a strict 12-column grid.
- From the ticket wallet: edits stamp receipts.

FORM: Cash Envelopes, position 7 of 7 on the grounded list (envelope budgeting); seed:6bbcd8c0ed2f0e11.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved
Envelopes show share of spend, not remaining budget: there are no per-category budget limits yet. That is a future feature, and the envelope list leaves room for a limit marker.
