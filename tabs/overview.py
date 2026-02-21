"""Overview tab — spending trends, category split, fixed vs variable breakdown."""

import streamlit as st
import pandas as pd
import plotly.express as px
from config import MONTH_NAMES
from chart_helpers import apply_default_layout, make_pie_chart


def render(df_filtered, df_year, df_trans, df_income_year, selected_year, selected_month,
           generate_monthly_summary_csv, generate_html_summary):
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.subheader("Spending Trend Over Time")
        time_group = df_filtered.groupby('Transaction Date')['Net_Amount'].sum().reset_index()
        time_group['Net_Amount'] = abs(time_group['Net_Amount'])

        fig_trend = px.line(time_group, x='Transaction Date', y='Net_Amount',
                            markers=True, line_shape='spline')
        fig_trend.update_traces(line_color='#3B82F6', line_width=3)
        apply_default_layout(fig_trend, xaxis_title="", yaxis_title="Amount ($)")
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_chart2:
        st.subheader("Category Split")
        cat_group = df_filtered.groupby('Budget_Category')['Net_Amount'].sum().reset_index()
        cat_group['Net_Amount'] = cat_group['Net_Amount'].clip(lower=0)

        fig_pie = make_pie_chart(cat_group, 'Net_Amount', 'Budget_Category', showlegend=False,
                                 margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    # Fixed vs. Variable Spending Breakdown
    if 'spending_type' in df_filtered.columns:
        st.markdown("---")
        st.subheader("Fixed vs. Variable Spending")

        fixed_total = df_filtered[df_filtered['spending_type'] == 'Fixed']['Net_Amount'].sum()
        variable_total = df_filtered[df_filtered['spending_type'] == 'Variable']['Net_Amount'].sum()
        total_fv = fixed_total + variable_total
        fixed_pct = (fixed_total / total_fv * 100) if total_fv > 0 else 0
        variable_pct = (variable_total / total_fv * 100) if total_fv > 0 else 0

        col_fv1, col_fv2, col_fv3 = st.columns([1, 1, 1])
        with col_fv1:
            st.metric("Fixed / Recurring", f"${fixed_total:,.2f}", f"{fixed_pct:.1f}% of total")
        with col_fv2:
            st.metric("Variable / Discretionary", f"${variable_total:,.2f}", f"{variable_pct:.1f}% of total")
        with col_fv3:
            fv_data = pd.DataFrame({
                'Type': ['Fixed', 'Variable'],
                'Amount': [fixed_total, variable_total]
            })
            fig_fv = px.pie(fv_data, values='Amount', names='Type', hole=0.65,
                            color='Type',
                            color_discrete_map={'Fixed': '#EF4444', 'Variable': '#3B82F6'})
            fig_fv.update_layout(height=200, showlegend=True,
                                 margin=dict(t=0, b=0, l=10, r=10))
            st.plotly_chart(fig_fv, use_container_width=True)

        # Stacked bar: Fixed vs Variable per month
        df_fv = df_filtered.copy()
        df_fv['month_num'] = df_fv['Transaction Date'].dt.month
        month_fv = df_fv.groupby(['month_num', 'spending_type'])['Net_Amount'].sum().reset_index()
        month_fv['Month'] = month_fv['month_num'].map(MONTH_NAMES)
        month_fv = month_fv.sort_values('month_num')

        fig_stacked = px.bar(
            month_fv, x='Month', y='Net_Amount', color='spending_type',
            barmode='stack',
            labels={'Net_Amount': 'Amount ($)', 'spending_type': 'Type'},
            color_discrete_map={'Fixed': '#EF4444', 'Variable': '#3B82F6'}
        )
        apply_default_layout(fig_stacked, title="Monthly Spending: Fixed vs. Variable",
                             legend_title_text="")
        st.plotly_chart(fig_stacked, use_container_width=True)

    # --- Monthly Report Download ---
    st.markdown("---")
    if selected_month == 'All':
        st.download_button(
            "Download Monthly Report",
            data="",
            file_name="select_a_month.csv",
            mime="text/csv",
            disabled=True,
            help="Select a specific month in the sidebar to download a monthly report."
        )
    else:
        month_abbr = selected_month[:3]
        monthly_csv = generate_monthly_summary_csv(
            df_year.to_dict('list'), df_trans.to_dict('list'),
            selected_year, selected_month
        )
        st.download_button(
            f"Download Monthly Report — {selected_month} {selected_year}",
            data=monthly_csv,
            file_name=f"{selected_year}_{month_abbr}_Summary.csv",
            mime="text/csv"
        )

    # --- Shareable HTML Summary ---
    html_summary = generate_html_summary(df_filtered, df_income_year, selected_year, selected_month)
    with st.expander("Share This Summary"):
        st.markdown(html_summary, unsafe_allow_html=True)
        st.caption("Copy the table above and paste into email or Slack. The formatting will be preserved.")
