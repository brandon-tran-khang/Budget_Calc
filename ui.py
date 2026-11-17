"""Presentation helpers for the "Cash Envelopes" UI (see docs/UI_SPEC.md). All render functions return None."""

import datetime
import html

import streamlit as st

from config import CATEGORY_COLORS, CATEGORY_FALLBACK_COLOR

# Tokens derive from the inherited text color, so they follow Streamlit's light/dark switch client-side
# (st.context.theme.type is only known server-side at script run and goes stale when the user toggles).
_TOKENS = """:root, .stApp {
  --bc-ink: currentColor;
  --bc-muted: color-mix(in srgb, currentColor 66%, transparent);
  --bc-line: color-mix(in srgb, currentColor 14%, transparent);
  --bc-track: color-mix(in srgb, currentColor 8%, transparent);
  --bc-surface: color-mix(in srgb, currentColor 3%, transparent);
  --bc-primary: color-mix(in srgb, #3E9A74 75%, currentColor);
  --bc-returned: color-mix(in srgb, #3E9A74 75%, currentColor);
  --bc-alert: color-mix(in srgb, #D0453B 80%, currentColor);
}
"""


_CSS = """
html, body, .stApp { font-variant-numeric: tabular-nums; }
.block-container { padding-top: 4.5rem; animation: bc-fade 180ms ease-out; }
@keyframes bc-fade { from { opacity: 0; transform: translateY(4px); } }
::selection { background: color-mix(in srgb, var(--bc-primary) 25%, transparent); }
:focus-visible { outline: 2px solid var(--bc-primary) !important; outline-offset: 2px; }
button, a, [data-baseweb="tab"] { transition: background-color 150ms, color 150ms, border-color 150ms; }

/* metrics: quiet, no card */
div[data-testid="stMetric"] { background: transparent; border: 0; padding: 0; }
div[data-testid="stMetricLabel"] { color: var(--bc-muted); font-size: 13px; font-weight: 600; }
div[data-testid="stMetricValue"] { font-size: 26px; font-weight: 600; letter-spacing: -.01em; }

/* sidebar rail nav */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a { border-radius: 6px; padding: 2px 10px; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,.08); }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
  background: #F4F6F2; color: #1F4D3A; font-weight: 600; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] * { color: #1F4D3A !important; }
section[data-testid="stSidebar"] [data-testid="stNavSectionHeader"],
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] header {
  font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; opacity: .7; }
/* data-coverage warnings: full-strength rail text (muted caption was 4.06:1 on the light rail) */
section[data-testid="stSidebar"] .st-key-data-warn [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] .st-key-data-warn [data-testid="stCaptionContainer"] * { color: inherit !important; opacity: 1 !important; }
.bc-flabel { font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
  opacity: .7; margin: 4px 0 0 2px; }
[data-testid="stSidebarHeader"]::before { content: "Budget Calc"; font-weight: 800; font-size: 18px;
  letter-spacing: -.01em; padding-left: 22px; align-self: center;
  background: linear-gradient(#D9A21B, #D9A21B) left center / 14px 10px no-repeat; }

/* hero */
.bc-hero { display: flex; align-items: flex-end; flex-wrap: wrap; gap: 8px 40px; margin-bottom: 8px; }
.bc-big { font-size: clamp(56px, 8vw, 96px); font-weight: 800; line-height: 1; letter-spacing: -.03em;
  color: var(--bc-ink); }
.bc-big small { font-size: 15px; font-weight: 600; letter-spacing: 0; margin-left: 12px; color: var(--bc-muted); }
.bc-brk { padding-bottom: 10px; color: var(--bc-muted); line-height: 1.7; font-size: 14px; }
.bc-brk b { color: var(--bc-ink); font-weight: 600; }
.bc-spark { margin-left: auto; padding-bottom: 10px; text-align: right; color: var(--bc-muted); font-size: 13px; }
.bc-spark svg { display: block; margin-left: auto; }

/* section header */
.bc-sec { margin: 8px 0 12px; }
.bc-sec h3 { font-size: 18px; font-weight: 600; margin: 0; padding: 0; color: var(--bc-ink); }
.bc-sec p { margin: 2px 0 0; font-size: 13px; color: var(--bc-muted); }
.bc-ctx { font-size: 13px; color: var(--bc-muted); margin-top: -8px; margin-bottom: 16px; }

/* envelopes */
.bc-env { display: grid; grid-template-columns: minmax(130px, 190px) 1fr 96px; align-items: center;
  gap: 4px 16px; padding: 12px 0; border-top: 1px solid var(--bc-line); }
.bc-nm { display: flex; align-items: center; gap: 12px; font-weight: 600; font-size: 14px; color: var(--bc-ink); min-width: 0; }
.bc-nm span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bc-chip { position: relative; width: 26px; height: 18px; border-radius: 2px; background: var(--c); flex: none; }
.bc-chip:before { content: ""; position: absolute; left: 0; top: 0; border: 13px solid transparent;
  border-top: 9px solid rgba(0,0,0,.18); border-bottom: 0; }
.bc-track { position: relative; height: 14px; background: var(--bc-track); border-radius: 3px; overflow: hidden; display: flex; }
.bc-net { background: var(--c); height: 100%; transform-origin: left; animation: bc-draw 420ms cubic-bezier(.16,1,.3,1) both;
  animation-delay: calc(var(--i) * 30ms); }
.bc-ret { height: 100%; opacity: .7; transform-origin: left;
  background: repeating-linear-gradient(135deg, var(--c) 0 2px, transparent 2px 6px);
  animation: bc-draw 420ms cubic-bezier(.16,1,.3,1) both; animation-delay: calc(var(--i) * 30ms); }
.bc-mark { position: absolute; top: 0; bottom: 0; width: 2px; background: var(--bc-ink); }
@keyframes bc-draw { from { transform: scaleX(0); } }
.bc-amt { text-align: right; font-weight: 600; font-size: 14px; color: var(--bc-ink); }
.bc-rl { grid-column: 2; font-size: 12px; color: var(--bc-returned); }
.bc-empty { color: var(--bc-muted); font-size: 14px; padding: 12px 0; }

/* receipts */
.bc-panel { background: var(--bc-surface); border: 1px solid var(--bc-line); border-radius: 8px; padding: 14px 18px; }
.bc-panel h4 { font-size: 15px; font-weight: 600; margin: 0 0 6px; color: var(--bc-ink); }
.bc-it { padding: 10px 0; border-top: 1px solid var(--bc-line); }
.bc-it:first-of-type { border-top: 0; }
.bc-it b { font-weight: 600; font-size: 14px; color: var(--bc-ink); }
.bc-it span { display: block; color: var(--bc-muted); font-size: 13px; }

.bc-envs { container-type: inline-size; }
/* Stack the bar under name/amount whenever the list's own column is narrow (phone or a side panel). */
@container (max-width: 440px) {
  .bc-env { grid-template-columns: 1fr auto; }
  .bc-track { grid-column: 1 / -1; order: 3; }
  .bc-rl { grid-column: 1 / -1; order: 4; }
}
@media (max-width: 640px) { .bc-big small { display: block; margin: 8px 0 0; } }
.bc-sec [data-testid="stHeaderActionElements"] { display: none; }
@media (prefers-reduced-motion: reduce) {
  *, *:before, *:after { animation: none !important; transition: none !important; }
}
"""


def inject_css():
    st.markdown(f"<style>{_TOKENS}{_CSS}</style>", unsafe_allow_html=True)
    for text in st.session_state.pop("_toasts", []):
        st.toast(text, icon=":material/receipt_long:")


def _money(x):
    return ("−" if x < 0 else "") + f"${abs(x):,.2f}"


def _spark(trend):
    if not trend or len(trend) < 2:
        return ""
    w, h, pad = 140, 36, 3
    lo, hi = min(trend), max(trend)
    span = (hi - lo) or 1
    pts = [(pad + i * (w - 2 * pad) / (len(trend) - 1), h - pad - (v - lo) / span * (h - 2 * pad))
           for i, v in enumerate(trend)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    x, y = pts[-1]
    return (f'<div class="bc-spark">Last {len(trend)} months'
            f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Trend, last {len(trend)} months">'
            f'<polyline fill="none" stroke="var(--bc-primary)" stroke-width="2" points="{poly}"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="var(--bc-primary)"/></svg></div>')


def hero(amount, label, period, breakdown, trend=None):
    brk = " · ".join(f"{html.escape(n)} <b>{_money(v)}</b>" for n, v in breakdown)
    st.markdown(
        f'<section class="bc-hero"><div><div class="bc-big">{_money(amount)}'
        f'<small>{html.escape(label)} · {html.escape(period)}</small></div></div>'
        f'<div class="bc-brk">{brk}</div>{_spark(trend)}</section>',
        unsafe_allow_html=True)


def envelope_rows(df):
    """Per Budget_Category: spent (positive Net_Amount), returned (refunds/offsets, positive), net. Sorted by net desc."""
    if df is None or df.empty:
        return []
    amt = df["Net_Amount"]
    g = df.assign(_s=amt.clip(lower=0), _r=-amt.clip(upper=0)).groupby("Budget_Category").agg(
        spent=("_s", "sum"), returned=("_r", "sum"), net=("Net_Amount", "sum")).reset_index()
    g = g.rename(columns={"Budget_Category": "category"}).sort_values("net", ascending=False)
    return g.to_dict("records")


def envelopes(rows, limit=None):
    rows = rows[:limit] if limit else rows
    if not rows:
        st.markdown('<div class="bc-empty">No spending in this period.</div>', unsafe_allow_html=True)
        return
    top = max((r["spent"] for r in rows), default=0) or 1
    out = []
    for i, r in enumerate(rows):
        cat = str(r["category"])
        color = CATEGORY_COLORS.get(cat, CATEGORY_FALLBACK_COLOR)
        net_w = max(r["net"], 0) / top * 100
        ret_w = min(r["returned"] / top * 100, 100 - net_w)
        mark = ""
        if r.get("budget"):
            mark = f'<i class="bc-mark" style="left:{min(r["budget"] / top * 100, 100):.1f}%"></i>'
        rl = f'<div class="bc-rl">returned {_money(r["returned"])}</div>' if r["returned"] > 0 else ""
        out.append(
            f'<div class="bc-env" style="--c:{color};--i:{min(i, 8)}">'
            f'<div class="bc-nm"><i class="bc-chip"></i><span>{html.escape(cat)}</span></div>'
            f'<div class="bc-track"><div class="bc-net" style="width:{net_w:.2f}%"></div>'
            f'<div class="bc-ret" style="width:{max(ret_w, 0):.2f}%"></div>{mark}</div>'
            f'<div class="bc-amt">{_money(r["net"])}</div>{rl}</div>')
    st.markdown(f'<div class="bc-envs">{"".join(out)}</div>', unsafe_allow_html=True)


def receipt(text, detail=""):
    log = st.session_state.setdefault("receipts", [])
    log.insert(0, {"text": text, "detail": detail, "at": datetime.datetime.now().strftime("%b %d %H:%M")})
    del log[20:]
    # Queued, not toasted now: every save calls st.rerun() next, which drops a direct st.toast.
    st.session_state.setdefault("_toasts", []).append(text)


def receipts_panel(n=5):
    items = st.session_state.get("receipts", [])[:n]
    if items:
        body = "".join(
            f'<div class="bc-it"><b>{html.escape(r["text"])}</b>'
            f'<span>{html.escape(r["at"] + (" · " + r["detail"] if r["detail"] else ""))}</span></div>' for r in items)
    else:
        body = ('<div class="bc-empty">Category edits, notes and reimbursement assignments '
                'you make show up here.</div>')
    st.markdown(f'<div class="bc-panel"><h4>Changes this session</h4>{body}</div>', unsafe_allow_html=True)


def section(title, caption=None):
    cap = f"<p>{html.escape(caption)}</p>" if caption else ""
    st.markdown(f'<div class="bc-sec"><h3>{html.escape(title)}</h3>{cap}</div>', unsafe_allow_html=True)


def context_line(selected_year, selected_month, selected_category, include_investments):
    parts = [str(selected_year),
             "All months" if selected_month == "All" else selected_month,
             "All categories" if selected_category == "All" else selected_category,
             "investments included" if include_investments else "investments excluded"]
    st.markdown(f'<div class="bc-ctx">{html.escape(" · ".join(parts))}</div>', unsafe_allow_html=True)
