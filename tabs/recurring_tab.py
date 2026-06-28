"""Recurring Expenses tab — subscription detection and fixed cost tracking."""

import streamlit as st
import plotly.express as px
from config import MONTH_NAMES
from chart_helpers import apply_default_layout, make_pie_chart


def render(df_year, recurring_merchants, subscription_alerts):
    st.subheader("Recurring Expenses & Subscriptions")
    st.caption("Auto-detected charges that appear monthly with consistent amounts.")

    if recurring_merchants.empty:
        st.info("No recurring expenses detected. This feature needs at least 2 consecutive months "
                "of data from the same merchant with consistent amounts.")
        return

    # Summary Metrics
    total_monthly_fixed = recurring_merchants['Monthly_Amount'].sum()
    total_annual_fixed = recurring_merchants['Annual_Projected'].sum()
    total_year_spend = df_year['Net_Amount'].sum()
    recurring_actual = df_year[df_year['is_recurring']]['Net_Amount'].sum()
    recurring_pct = (recurring_actual / total_year_spend * 100) if total_year_spend > 0 else 0

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.metric("Monthly Fixed Costs", f"${total_monthly_fixed:,.2f}")
    with col_r2:
        st.metric("Annual Fixed Costs", f"${total_annual_fixed:,.2f}")
    with col_r3:
        st.metric("% of Spending (Recurring)", f"{recurring_pct:.1f}%")

    st.markdown("---")

    # Subscription Change Alerts
    if subscription_alerts:
        st.markdown("#### Subscription Changes Detected")
        for alert in subscription_alerts:
            if alert['type'] == 'new':
                st.success(f"**{alert['merchant']}** — {alert['detail']}")
            elif alert['type'] == 'cancelled':
                st.warning(f"**{alert['merchant']}** — {alert['detail']}")
            elif alert['type'] == 'price_increase':
                st.error(f"**{alert['merchant']}** — {alert['detail']}")
            elif alert['type'] == 'price_decrease':
                st.info(f"**{alert['merchant']}** — {alert['detail']}")
        st.markdown("---")

    # Main Content: Table + Chart
    col_rt1, col_rt2 = st.columns([2, 1])

    with col_rt1:
        st.markdown("#### All Recurring Charges")
        display_df = recurring_merchants[[
            'Clean_Description', 'Monthly_Amount', 'Budget_Category',
            'Months_Active', 'Active_Range', 'Annual_Projected'
        ]].sort_values('Annual_Projected', ascending=False)

        st.dataframe(
            display_df,
            column_config={
                "Clean_Description": st.column_config.TextColumn("Merchant"),
                "Monthly_Amount": st.column_config.NumberColumn("Monthly", format="$%.2f"),
                "Budget_Category": st.column_config.TextColumn("Category"),
                "Months_Active": st.column_config.NumberColumn("Months"),
                "Active_Range": st.column_config.TextColumn("Active Months"),
                "Annual_Projected": st.column_config.NumberColumn("Annual Cost", format="$%.2f"),
            },
            use_container_width=True,
            hide_index=True,
            height=400
        )

    with col_rt2:
        st.markdown("#### Recurring by Category")
        cat_recurring = recurring_merchants.groupby('Budget_Category')['Monthly_Amount'].sum().reset_index()
        fig_rec_pie = make_pie_chart(
            cat_recurring, 'Monthly_Amount', 'Budget_Category',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_rec_pie, use_container_width=True)

    # Monthly Recurring Spend Trend
    st.markdown("#### Monthly Recurring Spend")
    recurring_tx = df_year[df_year['is_recurring']].copy()
    if not recurring_tx.empty:
        recurring_tx['month_num'] = recurring_tx['Transaction Date'].dt.month
        monthly_recurring = recurring_tx.groupby('month_num')['Net_Amount'].sum().reset_index()
        monthly_recurring['Month_Name'] = monthly_recurring['month_num'].map(MONTH_NAMES)

        fig_rec_trend = px.bar(
            monthly_recurring, x='Month_Name', y='Net_Amount',
            labels={'Net_Amount': 'Recurring Spend ($)', 'Month_Name': 'Month'},
            color_discrete_sequence=['#6366f1']
        )
        apply_default_layout(fig_rec_trend, height=300)
        st.plotly_chart(fig_rec_trend, use_container_width=True)
