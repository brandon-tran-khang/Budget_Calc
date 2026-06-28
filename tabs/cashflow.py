"""Income & Cash Flow tab — income vs expenses, source breakdown, debit vs credit."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config import MONTH_NAMES
from chart_helpers import apply_default_layout, make_pie_chart


def render(df_year, df_income_year, df_checking_year):
    st.subheader("Income & Cash Flow")

    if df_income_year.empty:
        st.info("No income data found for this year. To enable this tab:\n"
                "1. Export your Chase checking account CSV\n"
                "2. Place it in `Data/Checking/`\n"
                "3. Re-run `python Yearly_Spending.py`")
        return

    # --- Metric Cards ---
    total_income = df_income_year['Net_Amount'].sum()
    total_cc_expenses = df_year['Net_Amount'].sum()
    total_checking_expenses = df_checking_year['Net_Amount'].sum() if not df_checking_year.empty else 0
    total_all_expenses = total_cc_expenses + total_checking_expenses
    net_savings = total_income - total_all_expenses
    savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0

    col_cf1, col_cf2, col_cf3, col_cf4 = st.columns(4)
    with col_cf1:
        st.metric("Total Income", f"${total_income:,.2f}")
    with col_cf2:
        st.metric("Total Expenses", f"${total_all_expenses:,.2f}",
                   help="Credit card + checking/debit spending combined")
    with col_cf3:
        delta_color = "normal" if net_savings >= 0 else "inverse"
        st.metric("Net Savings", f"${net_savings:,.2f}",
                   delta=f"{savings_rate:.1f}% savings rate",
                   delta_color=delta_color)
    with col_cf4:
        st.metric("Checking Expenses", f"${total_checking_expenses:,.2f}",
                   help="Debit card / ACH expenses from checking account")

    st.markdown("---")

    # --- Monthly Income vs Expenses Chart ---
    st.subheader("Monthly Income vs Expenses")

    df_income_year = df_income_year.copy()
    df_income_year['month_num'] = df_income_year['Transaction Date'].dt.month
    monthly_income = df_income_year.groupby('month_num')['Net_Amount'].sum().reset_index()
    monthly_income.columns = ['month_num', 'Income']

    df_year_copy = df_year.copy()
    df_year_copy['month_num'] = df_year_copy['Transaction Date'].dt.month
    monthly_cc = df_year_copy.groupby('month_num')['Net_Amount'].sum().reset_index()
    monthly_cc.columns = ['month_num', 'CC_Expenses']

    monthly_ck_exp = pd.DataFrame({'month_num': range(1, 13), 'Checking_Expenses': 0})
    if not df_checking_year.empty:
        df_ck_copy = df_checking_year.copy()
        df_ck_copy['month_num'] = df_ck_copy['Transaction Date'].dt.month
        monthly_ck_exp = df_ck_copy.groupby('month_num')['Net_Amount'].sum().reset_index()
        monthly_ck_exp.columns = ['month_num', 'Checking_Expenses']

    monthly_cf = monthly_income.merge(monthly_cc, on='month_num', how='outer') \
                               .merge(monthly_ck_exp, on='month_num', how='outer') \
                               .fillna(0)
    monthly_cf['Total_Expenses'] = monthly_cf['CC_Expenses'] + monthly_cf['Checking_Expenses']
    monthly_cf['Net_Savings'] = monthly_cf['Income'] - monthly_cf['Total_Expenses']
    monthly_cf['Month'] = monthly_cf['month_num'].map(MONTH_NAMES)
    monthly_cf = monthly_cf.sort_values('month_num')

    fig_cf = go.Figure()
    fig_cf.add_trace(go.Bar(
        x=monthly_cf['Month'], y=monthly_cf['Income'],
        name='Income', marker_color='#22C55E'
    ))
    fig_cf.add_trace(go.Bar(
        x=monthly_cf['Month'], y=monthly_cf['Total_Expenses'],
        name='Expenses', marker_color='#EF4444'
    ))
    fig_cf.add_trace(go.Scatter(
        x=monthly_cf['Month'], y=monthly_cf['Net_Savings'],
        name='Net Savings', mode='lines+markers',
        line=dict(color='#3B82F6', width=3, dash='dot')
    ))
    apply_default_layout(fig_cf, height=400, barmode='group',
                         yaxis_title="Amount ($)", legend_title_text="")
    st.plotly_chart(fig_cf, use_container_width=True)

    # --- Two-column layout: Income Source + Checking Category ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Income Breakdown by Source")
        if 'Income_Source' in df_income_year.columns:
            source_group = df_income_year.groupby('Income_Source')['Net_Amount'].sum().reset_index()
            fig_income_pie = make_pie_chart(
                source_group, 'Net_Amount', 'Income_Source',
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            st.plotly_chart(fig_income_pie, use_container_width=True)
        else:
            st.info("Income source classification not available.")

    with col_right:
        st.subheader("Checking Spending by Category")
        if not df_checking_year.empty and 'Budget_Category' in df_checking_year.columns:
            ck_cat_group = df_checking_year.groupby('Budget_Category')['Net_Amount'].sum().reset_index()
            fig_ck_pie = make_pie_chart(ck_cat_group, 'Net_Amount', 'Budget_Category')
            st.plotly_chart(fig_ck_pie, use_container_width=True)
        else:
            st.info("No checking expenses to display.")

    # --- Debit vs Credit Spending ---
    st.markdown("---")
    st.subheader("Debit vs Credit Card Spending")

    df_year_copy['source_type'] = 'Credit Card'
    debit_monthly = pd.DataFrame({'month_num': range(1, 13), 'Amount': 0, 'source_type': 'Checking/Debit'})
    if not df_checking_year.empty:
        df_ck_m = df_checking_year.copy()
        df_ck_m['month_num'] = df_ck_m['Transaction Date'].dt.month
        debit_monthly = df_ck_m.groupby('month_num')['Net_Amount'].sum().reset_index()
        debit_monthly.columns = ['month_num', 'Amount']
        debit_monthly['source_type'] = 'Checking/Debit'

    credit_monthly = df_year_copy.groupby('month_num')['Net_Amount'].sum().reset_index()
    credit_monthly.columns = ['month_num', 'Amount']
    credit_monthly['source_type'] = 'Credit Card'

    combined_sources = pd.concat([credit_monthly, debit_monthly], ignore_index=True)
    combined_sources['Month'] = combined_sources['month_num'].map(MONTH_NAMES)
    combined_sources = combined_sources.sort_values('month_num')

    fig_sources = px.bar(
        combined_sources, x='Month', y='Amount', color='source_type',
        barmode='stack',
        labels={'Amount': 'Amount ($)', 'source_type': 'Account'},
        color_discrete_map={'Credit Card': '#8B5CF6', 'Checking/Debit': '#F59E0B'}
    )
    apply_default_layout(fig_sources, legend_title_text="")
    st.plotly_chart(fig_sources, use_container_width=True)

    # --- Income Transactions Table ---
    st.markdown("---")
    st.subheader("Income Transactions")

    income_display_cols = ['Transaction Date', 'Clean_Description', 'Net_Amount']
    if 'Income_Source' in df_income_year.columns:
        income_display_cols.insert(2, 'Income_Source')

    st.dataframe(
        df_income_year[income_display_cols].sort_values('Transaction Date', ascending=False),
        column_config={
            "Transaction Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "Clean_Description": st.column_config.TextColumn("Description"),
            "Income_Source": st.column_config.TextColumn("Source"),
            "Net_Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
        },
        use_container_width=True,
        height=400,
        hide_index=True
    )
