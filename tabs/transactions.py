"""Transactions tab — search, tag metrics, editable table, save logic."""

import streamlit as st
import pandas as pd
from config import BUDGET_CATEGORIES
from ui import receipt
from transaction_notes import (
    load_notes, save_notes, compute_tag_totals, get_available_tags, count_changed_notes,
)


def render(df_filtered, df_trans, notes_df, selected_year, selected_month, selected_category,
           generate_filtered_transactions_csv, save_category_mappings):
    st.caption(f"Showing {len(df_filtered):,} of {len(df_trans[df_trans['Year'] == selected_year]):,} transactions")

    # --- A. Global Search ---
    search_query = st.text_input("Search transactions (all years)", placeholder="Search merchant, category, note, or tag...",
                                 icon=":material/search:")
    if search_query:
        q = search_query.lower()
        search_results = df_trans[
            df_trans['Clean_Description'].str.lower().str.contains(q, na=False)
            | df_trans['Budget_Category'].str.lower().str.contains(q, na=False)
            | df_trans['Note'].str.lower().str.contains(q, na=False)
            | df_trans['Tags'].str.lower().str.contains(q, na=False)
        ].copy()
        search_results = search_results.sort_values('Transaction Date', ascending=False)
        result_years = search_results['Year'].nunique()
        result_total = search_results['Net_Amount'].sum()
        with st.expander(f"Search results: {len(search_results)} transactions across {result_years} year(s) — ${result_total:,.2f} total", expanded=True):
            st.dataframe(
                search_results[['Year', 'Transaction Date', 'Clean_Description', 'Budget_Category', 'Net_Amount', 'Note', 'Tags']]
                .sort_values('Transaction Date', ascending=False),
                column_config={
                    "Year": st.column_config.NumberColumn("Year", format="%d"),
                    "Transaction Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                    "Clean_Description": st.column_config.TextColumn("Merchant"),
                    "Budget_Category": st.column_config.TextColumn("Category"),
                    "Net_Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "Note": st.column_config.TextColumn("Note"),
                    "Tags": st.column_config.TextColumn("Tags"),
                },
                width='stretch',
                height=400,
                hide_index=True
            )

    # --- B. Tag Summary Metrics ---
    tag_totals = compute_tag_totals(df_filtered)
    if tag_totals:
        visible_tags = list(tag_totals.items())[:4]
        tag_cols = st.columns(len(visible_tags))
        for col, (tag_name, tag_amount) in zip(tag_cols, visible_tags):
            with col:
                st.metric(tag_name, f"${tag_amount:,.2f}")

    # --- B2. Filtered Transactions Download ---
    month_part = selected_month[:3] if selected_month != 'All' else 'All'
    cat_part = selected_category.replace(' ', '_').replace('/', '-') if selected_category != 'All' else 'All'
    tx_filename = f"Transactions_{selected_year}_{month_part}_{cat_part}.csv"
    tx_csv = generate_filtered_transactions_csv(df_filtered)
    with st.container(horizontal=True, vertical_alignment="center"):
        st.download_button(
            f"Export CSV ({len(df_filtered)} rows)",
            data=tx_csv,
            file_name=tx_filename,
            mime="text/csv",
            icon=":material/download:",
        )
        save_clicked = st.button("Save changes", type="primary", icon=":material/save:")

    # --- C. Editable Transaction Table ---
    editor_df = df_filtered[['_tx_key', 'Transaction Date', 'Clean_Description', 'Category', 'Budget_Category', 'Net_Amount', 'Note', 'Tags']].copy()
    editor_df = editor_df.sort_values('Transaction Date', ascending=False).reset_index(drop=True)
    original_categories = editor_df[['_tx_key', 'Budget_Category']].copy()

    edited_df = st.data_editor(
        editor_df,
        column_config={
            "Transaction Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD", disabled=True),
            "Clean_Description": st.column_config.TextColumn("Merchant", disabled=True),
            "Budget_Category": st.column_config.SelectboxColumn(
                "Budget Category",
                options=sorted(BUDGET_CATEGORIES),
                required=True
            ),
            "Net_Amount": st.column_config.NumberColumn("Amount", format="$%.2f", disabled=True,
                                                         help="Negative indicates a refund or reimbursement"),
            "Note": st.column_config.TextColumn("Note", max_chars=200),
            "Tags": st.column_config.TextColumn("Tags", max_chars=100),
        },
        column_order=["Transaction Date", "Clean_Description", "Budget_Category", "Net_Amount", "Note", "Tags"],
        width='stretch',
        height=600,
        hide_index=True,
        num_rows="fixed",
        key="transaction_editor"
    )

    # --- D. Save Button ---
    if save_clicked:
        changes_made = False

        # 1. Category changes
        merged_cats = original_categories.merge(
            edited_df[['_tx_key', 'Budget_Category']],
            on='_tx_key', suffixes=('_old', '_new')
        )
        changed = merged_cats[merged_cats['Budget_Category_old'] != merged_cats['Budget_Category_new']]
        if not changed.empty:
            changed_with_info = changed.merge(
                editor_df[['_tx_key', 'Clean_Description', 'Category']].drop_duplicates(subset=['_tx_key']),
                on='_tx_key', how='left'
            )
            new_mapping_rows = []
            for _, row in changed_with_info.iterrows():
                new_mapping_rows.append({
                    'Clean_Description': row['Clean_Description'],
                    'Bank_Category': row['Category'],
                    'Budget_Category': row['Budget_Category_new']
                })
            save_category_mappings(pd.DataFrame(new_mapping_rows))
            changes_made = True
            first = new_mapping_rows[0]
            receipt(f"Recategorized {first['Clean_Description']} → {first['Budget_Category']}"
                    if len(new_mapping_rows) == 1 else f"Recategorized {len(new_mapping_rows)} transactions")

        # 2. Notes/Tags
        n_notes = count_changed_notes(editor_df, edited_df)
        if n_notes:
            full_notes = load_notes()
            editor_keys = set(edited_df['_tx_key'].tolist())
            other_notes = full_notes[~full_notes['_tx_key'].isin(editor_keys)]
            editor_notes = edited_df[['_tx_key', 'Note', 'Tags']].copy()
            save_notes(pd.concat([other_notes, editor_notes], ignore_index=True))
            changes_made = True
            receipt(f"Saved notes for {n_notes} transaction{'s' if n_notes != 1 else ''}")

        if not changes_made:
            st.toast("No changes to save")  # no rerun follows, so a direct toast survives
        else:
            st.cache_data.clear()
            st.rerun()

    # Available tags reference
    with st.expander("Available Tags"):
        st.caption("Enter these (comma-separated) in the Tags column:")
        all_tags = get_available_tags(notes_df)
        st.write(", ".join(all_tags))
