# UI Spec: "Cash Envelopes" overhaul

Direction contract: `.impeccable/surfaces/frontend-py.md`. Product truth: `PRODUCT.md`. Money semantics: `docs/PROJECT_CONTEXT.md`.

Every budget category is an envelope. Spending leaves it, refunds and reimbursements slip back in, and **out of pocket** is what is really gone.

## Non-negotiables
- **Keep every feature and every money rule.** Do not change any computation in `frontend.py` data prep, `reimbursements.py`, `recurring.py`, `transaction_notes.py` or the pipeline. Do not change the existing tab render signatures.
- **Both themes must work.** Never hard-code text colors that break dark mode. Use Streamlit theme config or the CSS variables in `ui.py`.
- **Use standard controls:** Streamlit widgets, with no fake controls drawn in HTML. HTML is only for read-only display: the hero, envelopes, receipts and section headers.
- **No emoji as icons.** Use Material icons (`:material/name:`) in `st.Page`, buttons and headers.
- **Private data.** Never print or screenshot `Data/` rows into anything outside the machine.

## Tokens
| Token | Light | Dark |
|---|---|---|
| rail (sidebar bg) | `#1F4D3A` | `#0F2A20` |
| rail text | `#E4EFE8` | `#D5E6DC` |
| rail muted | `#9DBFAE` | `#86A897` |
| ground (bg) | `#F4F6F2` | `#101714` |
| surface (secondaryBackground / panels) | `#FFFFFF` | `#18221D` |
| ink (text) | `#17201B` | `#E6EDE8` |
| muted text | `#56636A` (≥4.5:1 on ground) | `#9AAAA2` |
| line (borders) | `#DDE3DB` | `#2A3830` |
| primary (actions, selection) | `#1F6B4F` | `#5BAE8C` |
| returned (refund/reimbursed) | `#2E7D5B` | `#6CC49C` |
| alert | `#B3261E` | `#F2867E` |

Type:
- Public Sans, self-hosted from `static/fonts/` (400/600/800) and wired in through `[theme] fontFaces`, with `enableStaticServing = true`.
- Tabular figures for all numbers (`font-variant-numeric: tabular-nums`).
- Scale: 13 / 14 / 15 / 18 / 24 / 32, plus the hero at 88–96px weight 800 with tracking −0.03em.
- Use exactly one hero figure per page.

Radius: 6px on controls and 8px on panels. Don't nest cards.

## Category colors (`config.CATEGORY_COLORS`)
Colors come from envelope-stock families. Every category gets its own shade, and a fallback is `#7A8580`.
- Food: Groceries `#D9A21B`, Restaurants `#E0674F`.
- Transport: Gas `#4F8FC0`, Car Maintenance `#3D6E99`, Car Registration `#7FB0D6`.
- Home & utilities, green family:
  - Home Electricity `#5BAE8C`
  - Home Water/Trash `#3F8F6E`
  - Internet `#2F7A62`
  - Phone Bill `#7CC2A3`
  - HOA Bill `#4C9A7E`
  - Home Maintenance `#6E9F5A`
  - Home Furniture `#93B36B`
  - Pest control `#A3C08A`
  - Landscaping `#5E8C3F`
- Subscriptions and fees, slate family:
  - Discord Subscription `#6C7A86`
  - Spotify Subscription `#55636E`
  - Amazon Prime Subscription `#8593A0`
  - Gym Membership `#9AA6B0`
  - Chase Sapphire Preferred Fee `#46525C`
  - Costco Membership `#B0BAC2`
- Health / Doctors `#D46A8C`; Games `#8C7BC4`; Vacation `#B49BE0`; Personal `#A88B6A`; Investments `#2C5F6E`.

Charts:
- Every Plotly chart colored by category uses `color_discrete_map=CATEGORY_COLORS`.
- `.streamlit/config.toml` sets `chartCategoricalColors` to an 8-color envelope list for non-category series.
- Hue is never the only signal: chips and legends always carry the name.

## Architecture (room to grow)
- **`ui.py`** is the new, single home of presentation helpers. Tabs import from it, and nothing else holds raw CSS. API (all functions return `None` and render directly):
  - `inject_css()` is called once in `frontend.py`. It holds the global CSS: tabular nums, the rail nav styling, focus rings in primary, `::selection` in primary at 25%, metric styling, the envelope/receipt/hero classes, motion and `@media (prefers-reduced-motion: reduce)`. It also shows any toasts queued in `st.session_state["_toasts"]`.
  - `hero(amount: float, label: str, period: str, breakdown: list[tuple[str, float]], trend: list[float] | None = None)` renders the monumental figure with the period inline (no eyebrow above it), the breakdown line (e.g. `[("Gross", 5640.12), ("Refunds", -212.40), ("Reimbursed", -615.35)]`) and an optional inline SVG trend line of the last N months.
  - `envelopes(rows: list[dict], limit: int | None = None)` renders the envelope list. Each dict has `category`, `spent` (gross positive), `returned` (positive number for money back) and `net`. The bar width is net / max(gross) and the hatched slip width is returned / max(gross). Use CATEGORY_COLORS. Leave a `budget` key optional for future limits; if present, draw a 2px marker at budget / max.
  - `receipt(text: str, detail: str = "")` appends to `st.session_state["receipts"]` (newest first, cap 20) and queues the text in `st.session_state["_toasts"]`. It does not call `st.toast` directly, because every save calls `st.rerun()` next, and that drops a direct toast. `inject_css()` shows the queued toasts after the rerun with `st.toast(text, icon=":material/receipt_long:")`.
  - `receipts_panel(n: int = 5)` renders "Changes this session" with an empty state that teaches ("Category edits, notes and reimbursement assignments you make show up here.").
  - `section(title: str, caption: str | None = None)` renders the section header (h3 + muted caption). Use it instead of `st.subheader` + `st.markdown("---")` dividers.
  - `envelope_rows(df) -> list[dict]` is a pure helper. It groups by `Budget_Category`: spent = sum of positive `Net_Amount`, returned = −sum of negative `Net_Amount` (refunds plus `Source == 'Checking Assignment'` offsets), net = sum. Sort by net descending. **Unit-test it** in `tests/test_ui.py`.
- **`chart_helpers.py`:**
  - `apply_default_layout` sets the font family Public Sans, transparent paper/plot bg, `margin=dict(t=24,l=8,r=8,b=8)`, `hovermode="x unified"` for time series (an opt-in kwarg), a light gridline and no chart title (titles come from `ui.section`). Keep `theme="streamlit"` (the default in `st.plotly_chart`) so light/dark adapt.
  - `make_pie_chart` keeps working but defaults to `color_discrete_map=CATEGORY_COLORS` when `names == 'Budget_Category'`.
- **Navigation (`frontend.py`):**
  - Replace `st.tabs` with `st.navigation({...}, position="sidebar")`. Use sections "Review", "Money flow" and "Clean up", with pages made by `st.Page(callable, title=..., icon=":material/...:", url_path=...)`. Each callable invokes the existing `tabs.<x>.render(...)` with the already-computed frames.
  - Data prep and filters stay above `pg.run()`, so every page shares them. Filters render in the sidebar **below** the nav under a "Filters" label: Year, Month, Category, Tags, Include investments.
  - Use `initial_sidebar_state="expanded"`.
  - The page header comes from the page title plus `ui.hero(...)` on Overview only. Other pages show a compact context line ("2026 · March · All categories · investments included") so filters are always visible.
  - The four old top metrics fold into the hero breakdown and the Overview content. Card Payments Made stays visible as a secondary `st.metric` with its help text.
  - Launch import: when `Data/Inbox` holds recognized exports, `frontend.py` runs the pipeline under a spinner ("Importing N new file(s)..."), then shows `st.toast` ("Imported N file(s). Data through ..."); pipeline ERROR/WARNING lines and a named list of unrecognized inbox files render as plain `st.warning` at the top of the page.
  - The sidebar caption "Data through <Mon D, YYYY>" shows the newest transaction date in any export (from `all_sources.csv`), not today. One `:material/warning:` caption per `ingest.coverage_warnings` line follows it (per-account gaps, stale accounts). The warnings render in full-strength rail text (the muted caption failed AA, 4.06:1, on the light rail) inside `st.container(key="data-warn")`.
- **Motion:** use CSS only.
  - Envelope bars draw in once with `transform: scaleX(0→1)`, `transform-origin:left`, 420ms `cubic-bezier(.16,1,.3,1)`, staggered by 30ms per row (max 8).
  - Page main content fades in over 180ms with opacity plus translateY(4px).
  - Nav items, buttons and pills use 150ms background/color transitions.
  - Everything goes to `animation: none; transition: none` under prefers-reduced-motion. Content stays visible by default (animations start from a visible-safe state, so if CSS fails the content still shows).

## Page treatment
- **Overview:**
  1. Hero (out of pocket for the filtered period).
  2. Envelopes (8 columns), next to Changes this session plus Card payments metric and Fixed vs Variable split (4 columns).
  3. Spending trend (area line in primary).
  4. Fixed vs Variable monthly stacked bars.
  5. Report downloads grouped in one row of `st.download_button`s with Material icons.
- **Transactions:**
  - Search and filters go in one horizontal row.
  - The table uses `st.column_config` (currency format, a category select column, tags), and rows are ranked by weight.
  - Saving edits calls `ui.receipt(...)`.
  - CSV export goes in a toolbar row above the table.
- **Reimbursements:** assign/remove call `ui.receipt`. Show the totals as a compact metric row. History can be removed with confirmation (use `st.popover` or a two-step button, never a modal-first flow).
- **Categories (Manage):** saving calls `ui.receipt`. Show the count of unmapped/"Personal" merchants as the to-do.
- **Recurring:** subscription alerts are shown as `st.badge`/colored text; fixed vs variable uses category colors.
- **Cash Flow / Forecast / Year Comparison / Vendors:** use `ui.section` headers and CATEGORY_COLORS. Remove stray `st.markdown("---")`/`<br>`. Charts go through `apply_default_layout`.

## Future hooks (don't build now)
- Per-category budget limits (`envelopes` row `budget`).
- Command palette / search across pages.
- Saved filter presets.
- A per-page `url_path` for deep links (already enabled by st.Page).
