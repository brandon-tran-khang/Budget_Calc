"""Forecasting tab — year-end projections and cumulative spend."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
import calendar
from chart_helpers import apply_default_layout


def render(df_year, df_income_year, df_checking_year, selected_year,
           generate_annual_summary_csv):
    is_current_year = (selected_year == datetime.date.today().year)
    days_in_year = 366 if calendar.isleap(selected_year) else 365

    if is_current_year:
        st.subheader("End of Year Projection")
        current_date = datetime.date.today()
        start_date = datetime.date(selected_year, 1, 1)
        days_passed = (current_date - start_date).days
        if days_passed < 1:
            days_passed = 1

        total_spend_ytd = df_year['Net_Amount'].sum()
        daily_avg = total_spend_ytd / days_passed
        projected_total = daily_avg * days_in_year
    else:
        st.subheader(f"{selected_year} Year in Review")
        total_spend_ytd = df_year['Net_Amount'].sum()
        days_with_data = (df_year['Transaction Date'].max() - df_year['Transaction Date'].min()).days
        if days_with_data < 1:
            days_with_data = 1
        daily_avg = total_spend_ytd / days_with_data
        projected_total = total_spend_ytd

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        label = "Current Daily Burn Rate" if is_current_year else "Average Daily Spend"
        st.metric(label, f"${daily_avg:,.2f} / day")
    with col_f2:
        label = f"Projected {selected_year} Total" if is_current_year else f"{selected_year} Total Spend"
        help_text = ("Assumes you keep spending at exactly this rate for the rest of the year."
                     if is_current_year else "Final total for this completed year.")
        st.metric(label, f"${projected_total:,.2f}", help=help_text)

    year_start = f'{selected_year}-01-01'
    year_end = f'{selected_year}-12-31'
    dates = pd.date_range(start=year_start, end=year_end, freq='M')

    fig_proj = go.Figure()

    if is_current_year:
        projection_values = [daily_avg * d.day_of_year for d in dates]
        fig_proj.add_trace(go.Scatter(
            x=dates, y=projection_values, mode='lines',
            name='Projection', line=dict(dash='dot', color='gray')))

    actual_cum = df_year.sort_values('Transaction Date').set_index('Transaction Date')['Net_Amount'].cumsum()
    actual_cum_resampled = actual_cum.resample('M').last()

    fig_proj.add_trace(go.Scatter(
        x=actual_cum_resampled.index, y=actual_cum_resampled.values,
        mode='lines+markers', name='Actual Spending',
        line=dict(color='#3B82F6', width=4)))

    title = "Actual Cumulative Spend vs. Projected Path" if is_current_year else f"Cumulative Spend for {selected_year}"
    apply_default_layout(fig_proj, title=title, hovermode="x unified")
    st.plotly_chart(fig_proj, use_container_width=True)

    # --- Annual Report Download ---
    st.markdown("---")
    annual_csv = generate_annual_summary_csv(
        df_year.to_dict('list'),
        df_income_year.to_dict('list') if not df_income_year.empty else {},
        df_checking_year.to_dict('list') if not df_checking_year.empty else {},
        selected_year
    )
    ytd_label = " (YTD)" if is_current_year else ""
    st.download_button(
        f"Download {selected_year} Annual Report{ytd_label}",
        data=annual_csv,
        file_name=f"{selected_year}_Annual_Summary.csv",
        mime="text/csv"
    )
