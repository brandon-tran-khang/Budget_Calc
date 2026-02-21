"""Year-over-Year Comparison tab — multi-year spending analysis."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from chart_helpers import apply_default_layout


def render(df_trans):
    available_years_list = sorted(df_trans['Year'].unique().tolist())

    if len(available_years_list) < 2:
        st.info("Year-over-year comparison requires at least 2 years of data. "
                "Keep adding transaction CSVs from different years to unlock this view.")
        return

    st.subheader("Year-over-Year Spending Comparison")

    compare_years = st.multiselect(
        "Select years to compare",
        available_years_list,
        default=available_years_list[-2:]
    )

    if len(compare_years) < 2:
        st.warning("Please select at least 2 years to compare.")
        return

    df_compare = df_trans[df_trans['Year'].isin(compare_years)].copy()
    df_compare['Month_Num'] = df_compare['Transaction Date'].dt.month
    df_compare['Month_Name'] = df_compare['Transaction Date'].dt.strftime('%b')
    compare_years_str = [str(y) for y in sorted(compare_years)]
    df_compare['Year'] = df_compare['Year'].astype(str)

    # Chart 1: Monthly Spending Overlay
    st.markdown("#### Monthly Spending by Year")
    monthly = df_compare.groupby(['Year', 'Month_Num', 'Month_Name'])['Net_Amount'].sum().reset_index()
    monthly = monthly.sort_values('Month_Num')

    fig_monthly = px.line(
        monthly, x='Month_Name', y='Net_Amount', color='Year',
        markers=True, labels={'Net_Amount': 'Total Spend ($)', 'Month_Name': 'Month'},
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    apply_default_layout(fig_monthly, hovermode="x unified")
    st.plotly_chart(fig_monthly, use_container_width=True)

    # Chart 2: Category Comparison
    st.markdown("#### Spending by Category per Year")
    cat_compare = df_compare.groupby(['Year', 'Budget_Category'])['Net_Amount'].sum().reset_index()

    fig_cat = px.bar(
        cat_compare, x='Budget_Category', y='Net_Amount', color='Year',
        barmode='group', labels={'Net_Amount': 'Total ($)', 'Budget_Category': 'Category'},
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    apply_default_layout(fig_cat, xaxis_tickangle=-45)
    st.plotly_chart(fig_cat, use_container_width=True)

    # Chart 3: Cumulative Spending Curves
    st.markdown("#### Cumulative Spending Through the Year")
    fig_cum = go.Figure()
    for year_str in compare_years_str:
        yr_data = df_compare[df_compare['Year'] == year_str].sort_values('Transaction Date').copy()
        yr_data['DayOfYear'] = yr_data['Transaction Date'].dt.dayofyear
        yr_data['Cumulative'] = yr_data['Net_Amount'].cumsum()
        fig_cum.add_trace(go.Scatter(
            x=yr_data['DayOfYear'], y=yr_data['Cumulative'],
            mode='lines', name=year_str, line=dict(width=3)
        ))
    apply_default_layout(fig_cum, xaxis_title="Day of Year", yaxis_title="Cumulative Spend ($)",
                         hovermode="x unified")
    st.plotly_chart(fig_cum, use_container_width=True)

    # Table: YoY Change by Category
    st.markdown("#### Year-over-Year Change by Category")
    if len(compare_years_str) == 2:
        yr_old, yr_new = compare_years_str
        old_cats = df_compare[df_compare['Year'] == yr_old].groupby('Budget_Category')['Net_Amount'].sum()
        new_cats = df_compare[df_compare['Year'] == yr_new].groupby('Budget_Category')['Net_Amount'].sum()

        change_df = pd.DataFrame({
            f'{yr_old} Total': old_cats,
            f'{yr_new} Total': new_cats
        }).fillna(0)
        change_df['Change ($)'] = change_df[f'{yr_new} Total'] - change_df[f'{yr_old} Total']
        change_df['Change (%)'] = (
            (change_df['Change ($)'] / change_df[f'{yr_old} Total'].replace(0, float('nan'))) * 100
        ).round(1)
        change_df = change_df.sort_values('Change ($)', ascending=False)

        st.dataframe(
            change_df.style.format({
                f'{yr_old} Total': '${:,.2f}',
                f'{yr_new} Total': '${:,.2f}',
                'Change ($)': '${:+,.2f}',
                'Change (%)': '{:+.1f}%'
            }),
            use_container_width=True
        )
    else:
        pivot = df_compare.groupby(['Budget_Category', 'Year'])['Net_Amount'].sum().unstack(fill_value=0)
        st.dataframe(
            pivot.style.format('${:,.2f}'),
            use_container_width=True
        )
