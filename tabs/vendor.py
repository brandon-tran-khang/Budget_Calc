"""Vendor Analysis tab — top merchants by spend and frequency."""

import streamlit as st
import plotly.graph_objects as go
from chart_helpers import apply_default_layout


def render(df_filtered):
    st.subheader("Where does the money actually go?")
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        merchant_group = df_filtered.groupby('Clean_Description')['Net_Amount'].sum().sort_values(ascending=True).tail(10)
        fig_bar = go.Figure(go.Bar(
            x=merchant_group.values,
            y=merchant_group.index,
            orientation='h',
            marker_color='#6366f1'
        ))
        apply_default_layout(fig_bar, height=500, title="Top 10 Merchants by Spend")
        st.plotly_chart(fig_bar, use_container_width=True)
    with col_v2:
        st.info("This view helps you identify 'Subscription Creep' or frequent small purchases that add up.")
        st.write("**Top 5 Most Frequent Places**")
        freq_merchants = df_filtered['Clean_Description'].value_counts().head(5)
        st.table(freq_merchants)
