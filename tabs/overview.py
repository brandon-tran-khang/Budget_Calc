"""Overview tab — spending trends, category split, fixed vs variable breakdown."""

import streamlit as st
import pandas as pd
import plotly.express as px
from config import MONTH_NAMES
from ui import hero, envelopes, envelope_rows, receipts_panel, section
from chart_helpers import apply_default_layout

FV_COLORS = {'Fixed': '#46525C', 'Variable': '#D9A21B'}


def _trend(df_trans, end):
    """Net spend for the 6 months ending at `end` (Timestamp)."""
    if df_trans is None or df_trans.empty or pd.isna(end):
        return None
    end_p = end.to_period('M')
    m = df_trans.groupby(df_trans['Transaction Date'].dt.to_period('M'))['Net_Amount'].sum()
    return m.reindex(pd.period_range(end=end_p, periods=6, freq='M'), fill_value=0).tolist()


def render(df_filtered, df_year, df_trans, df_income_year, selected_year, selected_month,
           generate_monthly_summary_csv, generate_html_summary, card_payments=0.0):
    period = str(selected_year) if selected_month == 'All' else f"{selected_month} {selected_year}"
    net = df_filtered['Net_Amount']
    neg = df_filtered[net < 0]
    is_assign = neg['Source'] == 'Checking Assignment' if 'Source' in neg.columns else pd.Series(False, index=neg.index)
    hero(net.sum(), "out of pocket", period, [
        ("Gross", net[net > 0].sum()),
        ("Refunds", neg.loc[~is_assign, 'Net_Amount'].sum()),
        ("Reimbursed", neg.loc[is_assign, 'Net_Amount'].sum()),
    ], trend=_trend(df_trans, df_filtered['Transaction Date'].max() if not df_filtered.empty else pd.NaT))

    col_env, col_side = st.columns([8, 4])
    with col_env:
        section("Envelopes", "Spent per category; hatched slip is money that came back.")
        envelopes(envelope_rows(df_filtered))
    with col_side:
        receipts_panel()
        st.space("medium")
        st.metric("Card payments", f"${card_payments:,.2f}", border=False,
                  help="Payments to credit card balance (excluded from spending)")
        st.metric("Transactions", f"{len(df_filtered):,}", border=False)
        if 'spending_type' in df_filtered.columns:
            fixed_total = df_filtered[df_filtered['spending_type'] == 'Fixed']['Net_Amount'].sum()
            variable_total = df_filtered[df_filtered['spending_type'] == 'Variable']['Net_Amount'].sum()
            total_fv = fixed_total + variable_total
            fixed_pct = (fixed_total / total_fv * 100) if total_fv > 0 else 0
            variable_pct = (variable_total / total_fv * 100) if total_fv > 0 else 0
            st.metric("Fixed / Recurring", f"${fixed_total:,.2f}", f"{fixed_pct:.1f}% of total",
                      delta_color="off", delta_arrow="off", border=False)
            st.metric("Variable / Discretionary", f"${variable_total:,.2f}", f"{variable_pct:.1f}% of total",
                      delta_color="off", delta_arrow="off", border=False)

    section("Spending trend")
    time_group = df_filtered.groupby('Transaction Date')['Net_Amount'].sum().reset_index()
    fig_trend = px.area(time_group, x='Transaction Date', y='Net_Amount', line_shape='spline')
    fig_trend.update_traces(line_color='#1F6B4F', line_width=2, fillcolor='rgba(31,107,79,0.15)')
    apply_default_layout(fig_trend, xaxis_title="", yaxis_title="Amount ($)")
    st.plotly_chart(fig_trend, width='stretch')

    if 'spending_type' in df_filtered.columns:
        section("Fixed vs. Variable", "Monthly spending split.")
        df_fv = df_filtered.copy()
        df_fv['month_num'] = df_fv['Transaction Date'].dt.month
        month_fv = df_fv.groupby(['month_num', 'spending_type'])['Net_Amount'].sum().reset_index()
        month_fv['Month'] = month_fv['month_num'].map(MONTH_NAMES)
        month_fv = month_fv.sort_values('month_num')

        fig_stacked = px.bar(
            month_fv, x='Month', y='Net_Amount', color='spending_type',
            barmode='stack',
            labels={'Net_Amount': 'Amount ($)', 'spending_type': 'Type'},
            color_discrete_map=FV_COLORS
        )
        apply_default_layout(fig_stacked, legend_title_text="")
        st.plotly_chart(fig_stacked, width='stretch')

    # --- Downloads ---
    section("Reports")
    dl1, dl2 = st.columns(2)
    with dl1:
        if selected_month == 'All':
            st.download_button(
                "Download Monthly Report", data="", file_name="select_a_month.csv",
                mime="text/csv", disabled=True, icon=":material/download:",
                help="Select a specific month in the sidebar to download a monthly report."
            )
        else:
            monthly_csv = generate_monthly_summary_csv(
                df_year.to_dict('list'), df_trans.to_dict('list'),
                selected_year, selected_month
            )
            st.download_button(
                f"Download Monthly Report — {selected_month} {selected_year}",
                data=monthly_csv,
                file_name=f"{selected_year}_{selected_month[:3]}_Summary.csv",
                mime="text/csv", icon=":material/download:"
            )

    # --- Shareable HTML Summary ---
    html_summary = generate_html_summary(df_filtered, df_income_year, selected_year, selected_month)
    with st.expander("Share This Summary", icon=":material/share:"):
        st.markdown(html_summary, unsafe_allow_html=True)
        st.caption("Copy the table above and paste into email or Slack. The formatting will be preserved.")
