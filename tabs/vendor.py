"""Vendor Analysis tab — top merchants by spend and frequency."""

import streamlit as st
import plotly.graph_objects as go
from chart_helpers import apply_default_layout
from ui import section


def render(df_filtered):
    st.caption("Spot subscription creep and frequent small purchases that add up.")
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        section("Top 10 Merchants by Spend")
        merchant_group = df_filtered.groupby('Clean_Description')['Net_Amount'].sum().sort_values(ascending=True).tail(10)
        fig_bar = go.Figure(go.Bar(
            x=merchant_group.values,
            y=merchant_group.index,
            orientation='h',
            marker_color='#1F6B4F'
        ))
        apply_default_layout(fig_bar, height=500)
        st.plotly_chart(fig_bar, width='stretch')
    with col_v2:
        st.write("**Top 5 Most Frequent Places** (purchases only, refunds excluded)")
        freq_merchants = df_filtered[df_filtered['Net_Amount'] > 0]['Clean_Description'].value_counts().head(5)
        st.table(freq_merchants.rename_axis("Merchant").reset_index(name="Purchases").set_index("Merchant"))
