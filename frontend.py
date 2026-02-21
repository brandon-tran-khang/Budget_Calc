import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
from config import BUDGET_CATEGORIES, MONTH_NAMES, MAPPINGS_FILE, DATA_DIR, DEFAULT_TAGS
from recurring import detect_recurring_merchants, classify_transactions, detect_subscription_changes
from transaction_notes import (
    add_tx_keys, load_notes, save_notes, merge_notes,
    get_available_tags, filter_by_tags, compute_tag_totals,
)
from tabs import overview, vendor, transactions, forecasting, year_comparison, recurring_tab, cashflow, manage

# --- Page Configuration (Must be first) ---
st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="\U0001f4b3",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Modern "Fintech" UI Styling ---
st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetric"] label {
        color: #000000 !important;
        font-weight: 600;
    }
    div[data-testid="stMetric"] div {
        color: #000000 !important;
    }
    .block-container {
        padding-top: 2rem;
    }
    h1, h2, h3 {
        color: #1E293B;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 4px;
        color: #64748B;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #F1F5F9;
        color: #0F172A;
        border-bottom: 2px solid #3B82F6;
    }
    </style>
""", unsafe_allow_html=True)

# --- Helpers (kept here because they use @st.cache_data) ---

@st.cache_data
def load_mappings():
    """Load category mappings from external CSV. Returns a dict."""
    if not MAPPINGS_FILE.exists():
        return {}
    try:
        mappings_df = pd.read_csv(MAPPINGS_FILE)
        if mappings_df.empty:
            return {}
    except pd.errors.EmptyDataError:
        return {}
    return dict(zip(
        zip(mappings_df['Clean_Description'], mappings_df['Bank_Category']),
        mappings_df['Budget_Category']
    ))

@st.cache_data
def get_recurring_analysis(_df_dict):
    """Cached recurring detection to avoid recomputing on every rerender."""
    df = pd.DataFrame(_df_dict)
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    recurring_df = detect_recurring_merchants(df)
    alerts = detect_subscription_changes(df)
    return recurring_df.to_dict('list'), alerts

def apply_mapping_overlay(df, mappings_dict):
    """Re-apply category mappings from CSV to override Budget_Category values."""
    if not mappings_dict:
        return df
    df = df.copy()
    overlay = pd.DataFrame([
        {'Clean_Description': k[0], 'Category': k[1], '_mapped_cat': v}
        for k, v in mappings_dict.items()
    ])
    merged = df.merge(overlay, on=['Clean_Description', 'Category'], how='left')
    mask = merged['_mapped_cat'].notna()
    df.loc[mask.values, 'Budget_Category'] = merged.loc[mask, '_mapped_cat'].values
    return df

def save_category_mappings(new_mappings_df):
    """Merge new mappings into category_mappings.csv (upsert by merchant+bank_category)."""
    if MAPPINGS_FILE.exists():
        existing_df = pd.read_csv(MAPPINGS_FILE)
        combined_df = pd.concat([existing_df, new_mappings_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(
            subset=['Clean_Description', 'Bank_Category'], keep='last'
        )
    else:
        combined_df = new_mappings_df
    combined_df.to_csv(MAPPINGS_FILE, index=False)

# --- Report Generation (cached) ---

@st.cache_data
def generate_monthly_summary_csv(_df_year_dict, _df_trans_dict, selected_year, selected_month):
    """Generate a monthly spending summary CSV with comparisons to prior periods."""
    df_year = pd.DataFrame(_df_year_dict)
    df_year['Transaction Date'] = pd.to_datetime(df_year['Transaction Date'])
    df_trans = pd.DataFrame(_df_trans_dict)
    df_trans['Transaction Date'] = pd.to_datetime(df_trans['Transaction Date'])

    month_num = {v: k for k, v in MONTH_NAMES.items()}.get(selected_month[:3])
    if month_num is None:
        try:
            month_num = datetime.datetime.strptime(selected_month, "%B").month
        except ValueError:
            return ""

    month_data = df_year[df_year['Transaction Date'].dt.month == month_num]
    if month_data.empty:
        return pd.DataFrame(columns=['Category', 'Total_Spent', 'Transactions', 'Pct_of_Total',
                                      'vs_Prev_Month_$', 'vs_Prev_Month_%',
                                      'vs_Same_Month_Last_Year_$', 'vs_Same_Month_Last_Year_%']).to_csv(index=False)

    summary = month_data.groupby('Budget_Category').agg(
        Total_Spent=('Net_Amount', 'sum'),
        Transactions=('Net_Amount', 'count')
    ).reset_index()

    grand_total = summary['Total_Spent'].sum()
    summary['Pct_of_Total'] = (summary['Total_Spent'] / grand_total * 100).round(1) if grand_total > 0 else 0

    if month_num > 1:
        prev_data = df_year[df_year['Transaction Date'].dt.month == month_num - 1]
        prev_by_cat = prev_data.groupby('Budget_Category')['Net_Amount'].sum()
        summary['vs_Prev_Month_$'] = summary.apply(
            lambda r: r['Total_Spent'] - prev_by_cat.get(r['Budget_Category'], 0), axis=1).round(2)
        summary['vs_Prev_Month_%'] = summary.apply(
            lambda r: ((r['Total_Spent'] - prev_by_cat.get(r['Budget_Category'], 0))
                        / prev_by_cat.get(r['Budget_Category'], 1) * 100)
            if prev_by_cat.get(r['Budget_Category'], 0) != 0 else None, axis=1).round(1)
    else:
        summary['vs_Prev_Month_$'] = None
        summary['vs_Prev_Month_%'] = None

    prev_year_data = df_trans[(df_trans['Transaction Date'].dt.year == selected_year - 1) &
                              (df_trans['Transaction Date'].dt.month == month_num)]
    if not prev_year_data.empty:
        ly_by_cat = prev_year_data.groupby('Budget_Category')['Net_Amount'].sum()
        summary['vs_Same_Month_Last_Year_$'] = summary.apply(
            lambda r: r['Total_Spent'] - ly_by_cat.get(r['Budget_Category'], 0), axis=1).round(2)
        summary['vs_Same_Month_Last_Year_%'] = summary.apply(
            lambda r: ((r['Total_Spent'] - ly_by_cat.get(r['Budget_Category'], 0))
                        / ly_by_cat.get(r['Budget_Category'], 1) * 100)
            if ly_by_cat.get(r['Budget_Category'], 0) != 0 else None, axis=1).round(1)
    else:
        summary['vs_Same_Month_Last_Year_$'] = None
        summary['vs_Same_Month_Last_Year_%'] = None

    summary = summary.sort_values('Total_Spent', ascending=False)

    totals = pd.DataFrame([{
        'Budget_Category': 'TOTAL',
        'Total_Spent': grand_total,
        'Transactions': summary['Transactions'].sum(),
        'Pct_of_Total': 100.0,
        'vs_Prev_Month_$': summary['vs_Prev_Month_$'].sum() if summary['vs_Prev_Month_$'].notna().any() else None,
        'vs_Prev_Month_%': None,
        'vs_Same_Month_Last_Year_$': summary['vs_Same_Month_Last_Year_$'].sum() if summary['vs_Same_Month_Last_Year_$'].notna().any() else None,
        'vs_Same_Month_Last_Year_%': None,
    }])
    summary = pd.concat([summary, totals], ignore_index=True)
    summary = summary.rename(columns={'Budget_Category': 'Category'})
    return summary.to_csv(index=False)


@st.cache_data
def generate_annual_summary_csv(_df_year_dict, _df_income_year_dict, _df_checking_year_dict, selected_year):
    """Generate an annual summary CSV with monthly breakdown by category."""
    df_year = pd.DataFrame(_df_year_dict)
    df_year['Transaction Date'] = pd.to_datetime(df_year['Transaction Date'])
    df_year['month_num'] = df_year['Transaction Date'].dt.month

    pivot = df_year.pivot_table(
        index='Budget_Category', columns='month_num',
        values='Net_Amount', aggfunc='sum', fill_value=0
    )
    for m in range(1, 13):
        if m not in pivot.columns:
            pivot[m] = 0
    pivot = pivot[sorted(pivot.columns)]
    pivot.columns = [MONTH_NAMES[m] for m in pivot.columns]

    pivot['Annual_Total'] = pivot.sum(axis=1)

    is_current = (selected_year == datetime.date.today().year)
    elapsed_months = datetime.date.today().month if is_current else 12
    pivot['Monthly_Avg'] = (pivot['Annual_Total'] / elapsed_months).round(2)

    month_cols = [MONTH_NAMES[m] for m in range(1, 13)]
    pivot['Min_Month'] = pivot[month_cols].replace(0, float('nan')).min(axis=1)
    pivot['Max_Month'] = pivot[month_cols].max(axis=1)
    pivot = pivot.sort_values('Annual_Total', ascending=False)

    monthly_total = pivot[month_cols].sum()
    monthly_total['Annual_Total'] = monthly_total.sum()
    monthly_total['Monthly_Avg'] = (monthly_total['Annual_Total'] / elapsed_months).round(2) if elapsed_months > 0 else 0
    monthly_total['Min_Month'] = monthly_total[month_cols].replace(0, float('nan')).min()
    monthly_total['Max_Month'] = monthly_total[month_cols].max()
    monthly_total.name = 'MONTHLY TOTAL'
    pivot = pd.concat([pivot, monthly_total.to_frame().T])

    monthly_avg_row = monthly_total / elapsed_months if elapsed_months > 0 else monthly_total * 0
    monthly_avg_row.name = 'MONTHLY AVERAGE'
    pivot = pd.concat([pivot, monthly_avg_row.to_frame().T])

    df_income_year = pd.DataFrame(_df_income_year_dict)
    df_checking_year = pd.DataFrame(_df_checking_year_dict)

    if not df_income_year.empty and 'Net_Amount' in df_income_year.columns:
        df_income_year['Transaction Date'] = pd.to_datetime(df_income_year['Transaction Date'])
        df_income_year['month_num'] = df_income_year['Transaction Date'].dt.month
        income_monthly = df_income_year.groupby('month_num')['Net_Amount'].sum()

        income_row = pd.Series(0, index=pivot.columns, name='INCOME')
        for m_num, m_name in MONTH_NAMES.items():
            income_row[m_name] = income_monthly.get(m_num, 0)
        income_row['Annual_Total'] = income_row[month_cols].sum()
        income_row['Monthly_Avg'] = (income_row['Annual_Total'] / elapsed_months).round(2) if elapsed_months > 0 else 0
        income_row['Min_Month'] = None
        income_row['Max_Month'] = None

        total_exp_row = monthly_total.copy()
        if not df_checking_year.empty and 'Net_Amount' in df_checking_year.columns:
            df_checking_year['Transaction Date'] = pd.to_datetime(df_checking_year['Transaction Date'])
            df_checking_year['month_num'] = df_checking_year['Transaction Date'].dt.month
            ck_monthly = df_checking_year.groupby('month_num')['Net_Amount'].sum()
            for m_num, m_name in MONTH_NAMES.items():
                total_exp_row[m_name] = total_exp_row.get(m_name, 0) + ck_monthly.get(m_num, 0)
            total_exp_row['Annual_Total'] = total_exp_row[month_cols].sum()
            total_exp_row['Monthly_Avg'] = (total_exp_row['Annual_Total'] / elapsed_months).round(2) if elapsed_months > 0 else 0
        total_exp_row.name = 'TOTAL EXPENSES'
        total_exp_row['Min_Month'] = None
        total_exp_row['Max_Month'] = None

        net_row = pd.Series(0, index=pivot.columns, name='NET SAVINGS')
        for col in month_cols:
            net_row[col] = income_row[col] - total_exp_row[col]
        net_row['Annual_Total'] = income_row['Annual_Total'] - total_exp_row['Annual_Total']
        net_row['Monthly_Avg'] = (net_row['Annual_Total'] / elapsed_months).round(2) if elapsed_months > 0 else 0
        net_row['Min_Month'] = None
        net_row['Max_Month'] = None

        rate_row = pd.Series(0, index=pivot.columns, name='SAVINGS RATE')
        for col in month_cols:
            rate_row[col] = (net_row[col] / income_row[col] * 100).round(1) if income_row[col] > 0 else 0
        rate_row['Annual_Total'] = (net_row['Annual_Total'] / income_row['Annual_Total'] * 100).round(1) if income_row['Annual_Total'] > 0 else 0
        rate_row['Monthly_Avg'] = None
        rate_row['Min_Month'] = None
        rate_row['Max_Month'] = None

        blank_row = pd.Series('', index=pivot.columns, name='')
        pivot = pd.concat([pivot, blank_row.to_frame().T, income_row.to_frame().T,
                           total_exp_row.to_frame().T, net_row.to_frame().T, rate_row.to_frame().T])

    pivot.index.name = 'Category'
    return pivot.to_csv()


def generate_filtered_transactions_csv(df_filtered):
    """Generate a CSV of the currently filtered transactions."""
    if df_filtered.empty:
        return pd.DataFrame(columns=['Date', 'Merchant', 'Category', 'Amount', 'Note', 'Tags']).to_csv(index=False)
    cols = [c for c in ['Transaction Date', 'Clean_Description', 'Budget_Category', 'Net_Amount', 'Note', 'Tags']
            if c in df_filtered.columns]
    export = df_filtered[cols].copy()
    export = export.rename(columns={
        'Transaction Date': 'Date', 'Clean_Description': 'Merchant',
        'Budget_Category': 'Category', 'Net_Amount': 'Amount',
    })
    return export.sort_values('Date', ascending=False).to_csv(index=False)


def generate_html_summary(df_filtered, df_income_year, selected_year, selected_month):
    """Generate a copy-pasteable HTML summary of spending."""
    total_spend = df_filtered['Net_Amount'].sum() if not df_filtered.empty else 0
    tx_count = len(df_filtered)
    top_cats = []
    if not df_filtered.empty:
        cat_totals = df_filtered.groupby('Budget_Category')['Net_Amount'].sum().sort_values(ascending=False)
        for cat, amt in cat_totals.head(3).items():
            top_cats.append(f"{cat}: ${amt:,.2f}")
    biggest = ""
    if not df_filtered.empty:
        max_row = df_filtered.loc[df_filtered['Net_Amount'].idxmax()]
        biggest = f"{max_row.get('Clean_Description', 'N/A')} \u2014 ${max_row['Net_Amount']:,.2f}"
    savings_line = ""
    if not df_income_year.empty and 'Net_Amount' in df_income_year.columns:
        total_income = df_income_year['Net_Amount'].sum()
        if total_income > 0:
            net = total_income - total_spend
            rate = net / total_income * 100
            savings_line = f"""
            <tr><td style="padding:8px 12px;border:1px solid #ddd;font-weight:600;">Savings Rate</td>
                <td style="padding:8px 12px;border:1px solid #ddd;">{rate:.1f}% (${net:,.2f} saved)</td></tr>"""
    period = f"{selected_month} {selected_year}" if selected_month != 'All' else str(selected_year)
    top_cats_html = "<br>".join(top_cats) if top_cats else "N/A"
    return f"""<table style="border-collapse:collapse;font-family:Arial,sans-serif;max-width:500px;">
  <tr style="background:#1E293B;color:white;">
    <th colspan="2" style="padding:12px;text-align:left;font-size:16px;">Spending Summary \u2014 {period}</th>
  </tr>
  <tr><td style="padding:8px 12px;border:1px solid #ddd;font-weight:600;">Total Spent</td>
      <td style="padding:8px 12px;border:1px solid #ddd;">${total_spend:,.2f}</td></tr>
  <tr><td style="padding:8px 12px;border:1px solid #ddd;font-weight:600;">Transactions</td>
      <td style="padding:8px 12px;border:1px solid #ddd;">{tx_count}</td></tr>
  <tr><td style="padding:8px 12px;border:1px solid #ddd;font-weight:600;">Top Categories</td>
      <td style="padding:8px 12px;border:1px solid #ddd;">{top_cats_html}</td></tr>
  <tr><td style="padding:8px 12px;border:1px solid #ddd;font-weight:600;">Biggest Purchase</td>
      <td style="padding:8px 12px;border:1px solid #ddd;">{biggest}</td></tr>{savings_line}
</table>"""


# --- Data Loading ---

@st.cache_data
def load_data():
    df_trans = pd.DataFrame()
    df_payments = pd.DataFrame()
    try:
        trans_path = DATA_DIR / "all_transactions.csv"
        if trans_path.exists():
            df_trans = pd.read_csv(trans_path)
            df_trans['Transaction Date'] = pd.to_datetime(df_trans['Transaction Date'])
            if 'Year' not in df_trans.columns:
                df_trans['Year'] = df_trans['Transaction Date'].dt.year
        payments_path = DATA_DIR / "all_credit_card_payments.csv"
        if payments_path.exists():
            df_payments = pd.read_csv(payments_path)
            df_payments['Transaction Date'] = pd.to_datetime(df_payments['Transaction Date'])
            if 'Year' not in df_payments.columns:
                df_payments['Year'] = df_payments['Transaction Date'].dt.year
    except FileNotFoundError:
        st.error("Data files not found. Please run 'Yearly_Spending.py' first.")
        return pd.DataFrame(), pd.DataFrame()
    return df_trans, df_payments

@st.cache_data
def load_income_data():
    income_path = DATA_DIR / "all_income.csv"
    if not income_path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(income_path)
        df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
        if 'Year' not in df.columns:
            df['Year'] = df['Transaction Date'].dt.year
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_checking_spending():
    checking_path = DATA_DIR / "all_checking_spending.csv"
    if not checking_path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(checking_path)
        df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
        if 'Year' not in df.columns:
            df['Year'] = df['Transaction Date'].dt.year
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_transaction_notes():
    return load_notes()


# ========== MAIN APP ==========

df_trans, df_payments = load_data()
df_income = load_income_data()
df_checking = load_checking_spending()

# Apply mapping overlay
mappings_dict = load_mappings()
if not df_trans.empty and mappings_dict:
    df_trans = apply_mapping_overlay(df_trans, mappings_dict)

# Merge transaction notes/tags
notes_df = load_transaction_notes()
if not df_trans.empty:
    df_trans = add_tx_keys(df_trans)
    df_trans = merge_notes(df_trans, notes_df)

if df_trans.empty:
    st.warning("No spending transactions found. Check your CSV generation script.")
    st.stop()

# --- Sidebar Filters ---
with st.sidebar:
    st.header("Filters")

    available_years = sorted(df_trans['Year'].unique().tolist(), reverse=True)
    current_year = datetime.date.today().year
    default_year_index = available_years.index(current_year) if current_year in available_years else 0
    selected_year = st.selectbox("Select Year", available_years, index=default_year_index)

    df_year = df_trans[df_trans['Year'] == selected_year].copy()
    df_income_year = df_income[df_income['Year'] == selected_year].copy() if not df_income.empty else pd.DataFrame()
    df_checking_year = df_checking[df_checking['Year'] == selected_year].copy() if not df_checking.empty else pd.DataFrame()

    # Recurring detection
    df_for_recurring = df_year.copy()
    if not df_checking_year.empty:
        checking_for_recurring = df_checking_year.copy()
        if 'Budget_Category' not in checking_for_recurring.columns:
            checking_for_recurring['Budget_Category'] = 'Personal'
        common_cols = [c for c in df_for_recurring.columns if c in checking_for_recurring.columns]
        df_for_recurring = pd.concat([df_for_recurring[common_cols], checking_for_recurring[common_cols]], ignore_index=True)

    _recurring_dict, subscription_alerts = get_recurring_analysis(df_for_recurring.to_dict('list'))
    recurring_merchants = pd.DataFrame(_recurring_dict)
    df_year = classify_transactions(df_year, recurring_merchants)
    if not df_checking_year.empty:
        df_checking_year = classify_transactions(df_checking_year, recurring_merchants)

    months = ['All'] + sorted(df_year['Month'].unique().tolist(), key=lambda m: datetime.datetime.strptime(m, "%B").month)
    selected_month = st.selectbox("Select Month", months)
    categories = ['All'] + sorted(df_year['Budget_Category'].unique().tolist())
    selected_category = st.selectbox("Select Budget Category", categories)
    available_tags = get_available_tags(notes_df)
    selected_tags = st.multiselect("Filter by Tags", available_tags)

    st.markdown("---")
    st.caption(f"Last Updated: {datetime.date.today()}")

# Apply Filters
df_filtered = df_year.copy()
if selected_month != 'All':
    df_filtered = df_filtered[df_filtered['Month'] == selected_month]
if selected_category != 'All':
    df_filtered = df_filtered[df_filtered['Budget_Category'] == selected_category]
if selected_tags:
    df_filtered = filter_by_tags(df_filtered, selected_tags)

# --- Header + Top Metrics ---

st.title(f"\U0001f4b8 {selected_year} Spending Command Center")
st.markdown("Taking control of personal finances, one data point at a time.")
st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
total_spend = df_filtered['Net_Amount'].sum()
tx_count = len(df_filtered)

total_payments_made = 0
if not df_payments.empty and 'Year' in df_payments.columns:
    pay_view = df_payments[df_payments['Year'] == selected_year].copy()
    if selected_month != 'All':
        pay_view = pay_view[pay_view['Month'] == selected_month]
    total_payments_made = pay_view['Amount'].sum()

with col1:
    st.metric("Total Spending", f"${total_spend:,.2f}")
with col2:
    st.metric("Transactions", f"{tx_count}")
with col3:
    if not df_filtered.empty:
        top_cat = df_filtered.groupby('Budget_Category')['Net_Amount'].sum().idxmax()
        top_cat_amount = df_filtered.groupby('Budget_Category')['Net_Amount'].sum().max()
        st.metric("Top Category", top_cat, f"${top_cat_amount:,.0f}")
    else:
        st.metric("Top Category", "N/A", "$0")
with col4:
    st.metric("Card Payments Made", f"${total_payments_made:,.2f}",
              help="Payments to credit card balance (excluded from spending)")

st.markdown("---")

# --- Tab Routing ---
tab_ov, tab_ve, tab_tx, tab_fc, tab_yy, tab_rc, tab_cf, tab_mg = st.tabs(
    ["\U0001f4ca Overview", "\U0001f6cd\ufe0f Vendor Analysis", "\U0001f4cb Transactions", "\U0001f52e Forecasting",
     "\U0001f4c8 Year Comparison", "\U0001f504 Recurring", "\U0001f4b0 Income & Cash Flow", "\u2699\ufe0f Manage Categories"])

with tab_ov:
    overview.render(df_filtered, df_year, df_trans, df_income_year, selected_year, selected_month,
                    generate_monthly_summary_csv, generate_html_summary)

with tab_ve:
    vendor.render(df_filtered)

with tab_tx:
    transactions.render(df_filtered, df_trans, notes_df, selected_year, selected_month, selected_category,
                        generate_filtered_transactions_csv, save_category_mappings)

with tab_fc:
    forecasting.render(df_year, df_income_year, df_checking_year, selected_year,
                       generate_annual_summary_csv)

with tab_yy:
    year_comparison.render(df_trans)

with tab_rc:
    recurring_tab.render(df_year, recurring_merchants, subscription_alerts)

with tab_cf:
    cashflow.render(df_year, df_income_year, df_checking_year)

with tab_mg:
    manage.render(df_trans, mappings_dict, save_category_mappings)
