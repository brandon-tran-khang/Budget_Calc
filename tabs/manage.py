"""Manage Categories tab — review and assign budget categories to merchants."""

import streamlit as st
import pandas as pd
from config import BUDGET_CATEGORIES, MAPPINGS_FILE


def render(df_trans, mappings_dict, save_category_mappings):
    st.subheader("Category Mapping Manager")
    st.caption("Review and assign budget categories to merchants. "
               "Merchants not in the mappings file are flagged as unreviewed.")

    # Identify unreviewed merchants across ALL data
    all_combos = df_trans[['Clean_Description', 'Category']].drop_duplicates()
    reviewed_keys = set(mappings_dict.keys())

    unreviewed_mask = all_combos.apply(
        lambda r: (r['Clean_Description'], r['Category']) not in reviewed_keys, axis=1
    )
    unreviewed_combos = all_combos[unreviewed_mask].copy()

    # Enrich with transaction count and total spend
    merchant_stats = df_trans.groupby(['Clean_Description', 'Category']).agg(
        Transactions=('Net_Amount', 'count'),
        Total_Amount=('Net_Amount', 'sum')
    ).reset_index()

    unreviewed_df = unreviewed_combos.merge(
        merchant_stats, on=['Clean_Description', 'Category'], how='left'
    ).sort_values('Total_Amount', ascending=False)

    # Get current Budget_Category
    current_cats = df_trans[['Clean_Description', 'Category', 'Budget_Category']].drop_duplicates(
        subset=['Clean_Description', 'Category'], keep='first'
    )
    unreviewed_df = unreviewed_df.merge(
        current_cats, on=['Clean_Description', 'Category'], how='left'
    )
    unreviewed_df['Budget_Category'] = unreviewed_df['Budget_Category'].fillna('Personal')

    # Metrics
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Unreviewed Merchants", len(unreviewed_df))
    with col_m2:
        st.metric("Reviewed Mappings", len(reviewed_keys))
    with col_m3:
        st.metric("Total Unique Merchants", len(all_combos))

    st.markdown("---")

    if unreviewed_df.empty:
        st.success("All merchants have been reviewed and mapped!")
    else:
        st.markdown("#### Unreviewed Merchants")
        st.caption("Assign a budget category to each merchant, then click Save.")

        edited_df = st.data_editor(
            unreviewed_df.reset_index(drop=True),
            column_config={
                "Clean_Description": st.column_config.TextColumn("Merchant", disabled=True),
                "Category": st.column_config.TextColumn("Bank Category", disabled=True),
                "Transactions": st.column_config.NumberColumn("# Transactions", disabled=True),
                "Total_Amount": st.column_config.NumberColumn("Total Spend", format="$%.2f", disabled=True),
                "Budget_Category": st.column_config.SelectboxColumn(
                    "Budget Category",
                    options=sorted(BUDGET_CATEGORIES),
                    required=True
                ),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            key="mapping_editor"
        )

        if st.button("Save Mappings", type="primary"):
            new_mappings_df = edited_df[['Clean_Description', 'Category', 'Budget_Category']].rename(
                columns={'Category': 'Bank_Category'}
            )
            save_category_mappings(new_mappings_df)
            st.cache_data.clear()
            st.rerun()

    # Reference: show existing mappings
    st.markdown("---")
    st.markdown("#### Current Mapping Table")
    if MAPPINGS_FILE.exists():
        existing_mappings = pd.read_csv(MAPPINGS_FILE)
        st.dataframe(
            existing_mappings.sort_values('Clean_Description'),
            use_container_width=True,
            hide_index=True,
            height=400
        )
    else:
        st.info("No mappings file found. Run Yearly_Spending.py to create the initial mappings file.")
