"""Reimbursements tab — assign incoming Zelle/Venmo/Cash App payments to spending categories."""

import pandas as pd
import streamlit as st
from config import BUDGET_CATEGORIES
from reimbursements import COLUMNS, save_assignments, unassigned_candidates

PLACEHOLDER = "Select Category..."


def render(df_income_year, assigned_df, selected_year):
    st.subheader("Assign Incoming Transfers to Expenses")
    st.caption("Assign incoming Zelle/Venmo/Cash App payments to a budget category. The amount reduces "
               "that category's spending and is no longer counted as income.")

    if df_income_year.empty:
        st.info("No income data found for this year. Make sure your checking CSVs are loaded.")
    else:
        unassigned = unassigned_candidates(df_income_year, assigned_df)
        if unassigned.empty:
            st.success("All incoming Zelle/Venmo transactions for this year have been assigned.")
        else:
            st.markdown("#### Unassigned Incoming Transfers")
            view = unassigned[['Transaction Date', 'Clean_Description', 'Net_Amount']].copy()
            view['Transaction Date'] = pd.to_datetime(view['Transaction Date']).dt.date
            view['Offset_Category'] = PLACEHOLDER
            edited_df = st.data_editor(
                view.reset_index(drop=True),
                column_config={
                    "Transaction Date": st.column_config.DateColumn("Date", disabled=True),
                    "Clean_Description": st.column_config.TextColumn("Description", disabled=True),
                    "Net_Amount": st.column_config.NumberColumn("Amount", format="$%.2f", disabled=True),
                    "Offset_Category": st.column_config.SelectboxColumn(
                        "Assign to Category", options=[PLACEHOLDER] + sorted(BUDGET_CATEGORIES)),
                },
                hide_index=True,
                width='stretch',
                num_rows="fixed",
                key=f"reimbursement_editor_{selected_year}",
            )
            if st.button("Save Assignments", type="primary"):
                chosen = edited_df[edited_df['Offset_Category'] != PLACEHOLDER].rename(
                    columns={'Offset_Category': 'Budget_Category'})
                if chosen.empty:
                    st.warning("Select a category for at least one transaction before saving.")
                else:
                    save_assignments(pd.concat([assigned_df, chosen[COLUMNS]], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

    st.markdown("---")
    st.markdown("#### Assignment History")
    if assigned_df.empty:
        st.info("No reimbursements logged yet.")
        return
    history = assigned_df.sort_values('Transaction Date', ascending=False).copy()
    history['Transaction Date'] = history['Transaction Date'].dt.date
    history.insert(0, 'Remove', False)
    edited_hist = st.data_editor(
        history,
        column_config={
            "Remove": st.column_config.CheckboxColumn("Remove"),
            "Transaction Date": st.column_config.DateColumn("Date", disabled=True),
            "Clean_Description": st.column_config.TextColumn("Description", disabled=True),
            "Net_Amount": st.column_config.NumberColumn("Amount", format="$%.2f", disabled=True),
            "Budget_Category": st.column_config.TextColumn("Offset Category", disabled=True),
        },
        hide_index=True,
        width='stretch',
        num_rows="fixed",
        key="reimbursement_history_editor",
    )
    if st.button("Remove selected"):
        keep = edited_hist[~edited_hist['Remove']]
        if len(keep) == len(edited_hist):
            st.warning("Tick the rows to remove first.")
        else:
            save_assignments(keep.drop(columns='Remove'))
            st.cache_data.clear()
            st.rerun()
