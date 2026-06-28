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

    # Apply Workflow Assigned Zelle Offsets directly to the transactions
    assignments_path = directory / "zelle_assignments.csv"
    if assignments_path.exists() and not df_trans.empty:
        try:
            df_assigned = pd.read_csv(assignments_path)
            if not df_assigned.empty:
                df_assigned['Transaction Date'] = pd.to_datetime(df_assigned['Transaction Date'])
                
                df_assigned_formatted = pd.DataFrame({
                    'Transaction Date': df_assigned['Transaction Date'],
                    'Clean_Description': 'Reimbursement: ' + df_assigned['Clean_Description'].str.title(),
                    'Category': 'Transfer',
                    'Budget_Category': df_assigned['Budget_Category'],
                    # Force the amount to be negative so it always subtracts from total spending
                    'Net_Amount': -abs(df_assigned['Net_Amount']),  
                    'Source': 'Checking Assignment',
                    'account_type': 'credit',
                    'Month': df_assigned['Transaction Date'].dt.strftime('%B'),
                    'Quarter': df_assigned['Transaction Date'].dt.quarter,
                    'Week': df_assigned['Transaction Date'].dt.isocalendar().week,
                    'Year': df_assigned['Transaction Date'].dt.year
                })
                # Append offsets to main transactions
                df_trans = pd.concat([df_trans, df_assigned_formatted], ignore_index=True)
        except pd.errors.EmptyDataError:
            pass

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

# --- Tabs for different views ---
tab_overview, tab_vendor, tab_transactions, tab_forecast, tab_yoy, tab_recurring, tab_cashflow, tab_manage, tab_reimburse = st.tabs(
    ["📊 Overview", "🛍️ Vendor Analysis", "📋 Transactions", "🔮 Forecasting",
     "📈 Year Comparison", "🔄 Recurring", "💰 Income & Cash Flow", "⚙️ Manage Categories", "🤝 Reimbursements"])

# TAB 1: OVERVIEW
with tab_overview:
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.subheader("Spending Trend Over Time")
        time_group = df_filtered.groupby('Transaction Date')['Net_Amount'].sum().reset_index()
        # Fix abs() issue so reimbursements reflect properly as a net drop
        # time_group['Net_Amount'] = abs(time_group['Net_Amount']) <- REMOVED to allow negative net days

        fig_trend = px.line(time_group, x='Transaction Date', y='Net_Amount',
                            markers=True, line_shape='spline')
        fig_trend.update_traces(line_color='#3B82F6', line_width=3)
        fig_trend.update_layout(height=350, xaxis_title="", yaxis_title="Amount ($)", template="plotly_white")
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_chart2:
        st.subheader("Category Split")
        # UPDATED: Pi chart now uses Budget_Category
        cat_group = df_filtered.groupby('Budget_Category')['Net_Amount'].sum().reset_index()
        # The clip(lower=0) natively handles cases where reimbursements > spending in a category
        cat_group['Net_Amount'] = cat_group['Net_Amount'].clip(lower=0)

        fig_pie = px.pie(cat_group, values='Net_Amount', names='Budget_Category', hole=0.6,
                              color_discrete_sequence=px.colors.qualitative.Prism)

        fig_pie.update_layout(height=350, showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
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
            # Prevent graphing negative values in pie chart if variable total drops below 0 due to heavy offset
            graph_fixed = max(0, fixed_total)
            graph_var = max(0, variable_total)
            
            fv_data = pd.DataFrame({
                'Type': ['Fixed', 'Variable'],
                'Amount': [graph_fixed, graph_var]
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
        month_names_map = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        }
        month_fv['Month'] = month_fv['month_num'].map(month_names_map)
        month_fv = month_fv.sort_values('month_num')

        fig_stacked = px.bar(
            month_fv, x='Month', y='Net_Amount', color='spending_type',
            barmode='stack',
            labels={'Net_Amount': 'Amount ($)', 'spending_type': 'Type'},
            color_discrete_map={'Fixed': '#EF4444', 'Variable': '#3B82F6'}
        )
        fig_stacked.update_layout(
            title="Monthly Spending: Fixed vs. Variable",
            template="plotly_white", height=350,
            legend_title_text=""
        )
        st.plotly_chart(fig_stacked, use_container_width=True)

# TAB 2: VENDOR ANALYSIS
with tab_vendor:
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
        fig_bar.update_layout(title="Top 10 Merchants by Spend", height=500, template="plotly_white")
        st.plotly_chart(fig_bar, use_container_width=True)
    with col_v2:
        st.info("💡 **Insight:** This view helps you identify 'Subscription Creep' or frequent small purchases that add up.")
        st.write("**Top 5 Most Frequent Places**")
        freq_merchants = df_filtered['Clean_Description'].value_counts().head(5)
        st.table(freq_merchants)

# TAB 3: TRANSACTION DATA
with tab_transactions:
    st.subheader("Detailed Transaction Log")

    # UPDATED: Table now displays Budget_Category instead of bank Category
    st.dataframe(
        df_filtered[['Transaction Date', 'Clean_Description', 'Budget_Category', 'Net_Amount']]
        .sort_values('Transaction Date', ascending=False),
        column_config={
            "Transaction Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "Clean_Description": st.column_config.TextColumn("Merchant"),
            "Budget_Category": st.column_config.TextColumn("Budget Category"),
            "Net_Amount": st.column_config.NumberColumn(
                "Amount",
                format="$%.2f",
                help="Net spending amount (Negative indicates a reimbursement)"
            ),
        },
        use_container_width=True,
        height=600,
        hide_index=True
    )

# TAB 4: FORECASTING
with tab_forecast:
    is_current_year = (selected_year == datetime.date.today().year)
    days_in_year = 366 if calendar.isleap(selected_year) else 365

    if is_current_year:
        st.subheader("End of Year Projection")
        current_date = datetime.date.today()
        start_date = datetime.date(selected_year, 1, 1)
        days_passed = (current_date - start_date).days
        if days_passed < 1:
            days_passed = 1

        total_spend_ytd = df_year['Net_Amount'].sum()
        daily_avg = total_spend_ytd / days_passed
        projected_total = daily_avg * days_in_year
    else:
        st.subheader(f"{selected_year} Year in Review")
        total_spend_ytd = df_year['Net_Amount'].sum()
        days_with_data = (df_year['Transaction Date'].max() - df_year['Transaction Date'].min()).days
        if days_with_data < 1:
            days_with_data = 1
        daily_avg = total_spend_ytd / days_with_data
        projected_total = total_spend_ytd

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        label = "Current Daily Burn Rate" if is_current_year else "Average Daily Spend"
        st.metric(label, f"${daily_avg:,.2f} / day")
    with col_f2:
        label = f"Projected {selected_year} Total" if is_current_year else f"{selected_year} Total Spend"
        help_text = ("Assumes you keep spending at exactly this rate for the rest of the year."
                     if is_current_year else "Final total for this completed year.")
        st.metric(label, f"${projected_total:,.2f}", help=help_text)

    year_start = f'{selected_year}-01-01'
    year_end = f'{selected_year}-12-31'
    dates = pd.date_range(start=year_start, end=year_end, freq='M')

    fig_proj = go.Figure()

    if is_current_year:
        projection_values = [daily_avg * d.day_of_year for d in dates]
        fig_proj.add_trace(go.Scatter(
            x=dates, y=projection_values, mode='lines',
            name='Projection', line=dict(dash='dot', color='gray')))

    actual_cum = df_year.sort_values('Transaction Date').set_index('Transaction Date')['Net_Amount'].cumsum()
    actual_cum_resampled = actual_cum.resample('ME').last()

    fig_proj.add_trace(go.Scatter(
        x=actual_cum_resampled.index, y=actual_cum_resampled.values,
        mode='lines+markers', name='Actual Spending',
        line=dict(color='#3B82F6', width=4)))

    title = "Actual Cumulative Spend vs. Projected Path" if is_current_year else f"Cumulative Spend for {selected_year}"
    fig_proj.update_layout(title=title, template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig_proj, use_container_width=True)

# TAB 5: YEAR-OVER-YEAR COMPARISON
with tab_yoy:
    available_years_list = sorted(df_trans['Year'].unique().tolist())

    if len(available_years_list) < 2:
        st.info("Year-over-year comparison requires at least 2 years of data. "
                "Keep adding transaction CSVs from different years to unlock this view.")
    else:
        st.subheader("Year-over-Year Spending Comparison")

        compare_years = st.multiselect(
            "Select years to compare",
            available_years_list,
            default=available_years_list[-2:]
        )

        if len(compare_years) < 2:
            st.warning("Please select at least 2 years to compare.")
        else:
            df_compare = df_trans[df_trans['Year'].isin(compare_years)].copy()
            df_compare['Month_Num'] = df_compare['Transaction Date'].dt.month
            df_compare['Month_Name'] = df_compare['Transaction Date'].dt.strftime('%b')
            # Convert Year to string for chart legends
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
            fig_monthly.update_layout(template="plotly_white", hovermode="x unified")
            st.plotly_chart(fig_monthly, use_container_width=True)

            # Chart 2: Category Comparison (Grouped Bar)
            st.markdown("#### Spending by Category per Year")
            cat_compare = df_compare.groupby(['Year', 'Budget_Category'])['Net_Amount'].sum().reset_index()

            fig_cat = px.bar(
                cat_compare, x='Budget_Category', y='Net_Amount', color='Year',
                barmode='group', labels={'Net_Amount': 'Total ($)', 'Budget_Category': 'Category'},
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_cat.update_layout(template="plotly_white", xaxis_tickangle=-45)
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
            fig_cum.update_layout(
                template="plotly_white",
                xaxis_title="Day of Year", yaxis_title="Cumulative Spend ($)",
                hovermode="x unified"
            )
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

# TAB 6: RECURRING EXPENSES
with tab_recurring:
    st.subheader("Recurring Expenses & Subscriptions")
    st.caption("Auto-detected charges that appear monthly with consistent amounts.")

    if recurring_merchants.empty:
        st.info("No recurring expenses detected. This feature needs at least 2 consecutive months "
                "of data from the same merchant with consistent amounts.")
    else:
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
            fig_rec_pie = px.pie(
                cat_recurring, values='Monthly_Amount', names='Budget_Category',
                hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_rec_pie.update_layout(
                height=350, showlegend=True,
                margin=dict(t=0, b=0, l=0, r=0)
            )
            st.plotly_chart(fig_rec_pie, use_container_width=True)

        # Monthly Recurring Spend Trend
        st.markdown("#### Monthly Recurring Spend")
        recurring_tx = df_year[df_year['is_recurring']].copy()
        if not recurring_tx.empty:
            month_names_map = {
                1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
            }
            recurring_tx['month_num'] = recurring_tx['Transaction Date'].dt.month
            monthly_recurring = recurring_tx.groupby('month_num')['Net_Amount'].sum().reset_index()
            monthly_recurring['Month_Name'] = monthly_recurring['month_num'].map(month_names_map)

            fig_rec_trend = px.bar(
                monthly_recurring, x='Month_Name', y='Net_Amount',
                labels={'Net_Amount': 'Recurring Spend ($)', 'Month_Name': 'Month'},
                color_discrete_sequence=['#6366f1']
            )
            fig_rec_trend.update_layout(template="plotly_white", height=300)
            st.plotly_chart(fig_rec_trend, use_container_width=True)

# TAB 7: INCOME & CASH FLOW
with tab_cashflow:
    st.subheader("Income & Cash Flow")

    if df_income_year.empty:
        st.info("No income data found for this year. To enable this tab:\n"
                "1. Export your Chase checking account CSV\n"
                "2. Place it in `Data/Checking/`\n"
                "3. Re-run `python Yearly_Spending.py`")
    else:
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

        month_names_map = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        }

        # Monthly income
        df_income_year['month_num'] = df_income_year['Transaction Date'].dt.month
        monthly_income = df_income_year.groupby('month_num')['Net_Amount'].sum().reset_index()
        monthly_income.columns = ['month_num', 'Income']

        # Monthly expenses (credit + checking)
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

        # Merge all monthly data
        monthly_cf = monthly_income.merge(monthly_cc, on='month_num', how='outer') \
                                   .merge(monthly_ck_exp, on='month_num', how='outer') \
                                   .fillna(0)
        monthly_cf['Total_Expenses'] = monthly_cf['CC_Expenses'] + monthly_cf['Checking_Expenses']
        monthly_cf['Net_Savings'] = monthly_cf['Income'] - monthly_cf['Total_Expenses']
        monthly_cf['Month'] = monthly_cf['month_num'].map(month_names_map)
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
        fig_cf.update_layout(
            barmode='group', template="plotly_white", height=400,
            yaxis_title="Amount ($)", legend_title_text=""
        )
        st.plotly_chart(fig_cf, use_container_width=True)

        # --- Two-column layout: Income Source + Checking Category ---
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Income Breakdown by Source")
            if 'Income_Source' in df_income_year.columns:
                source_group = df_income_year.groupby('Income_Source')['Net_Amount'].sum().reset_index()
                fig_income_pie = px.pie(
                    source_group, values='Net_Amount', names='Income_Source', hole=0.6,
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                fig_income_pie.update_layout(height=350, margin=dict(t=10, b=0, l=0, r=0))
                st.plotly_chart(fig_income_pie, use_container_width=True)
            else:
                st.info("Income source classification not available.")

        with col_right:
            st.subheader("Checking Spending by Category")
            if not df_checking_year.empty and 'Budget_Category' in df_checking_year.columns:
                ck_cat_group = df_checking_year.groupby('Budget_Category')['Net_Amount'].sum().reset_index()
                fig_ck_pie = px.pie(
                    ck_cat_group, values='Net_Amount', names='Budget_Category', hole=0.6,
                    color_discrete_sequence=px.colors.qualitative.Prism
                )
                fig_ck_pie.update_layout(height=350, margin=dict(t=10, b=0, l=0, r=0))
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
        combined_sources['Month'] = combined_sources['month_num'].map(month_names_map)
        combined_sources = combined_sources.sort_values('month_num')

        fig_sources = px.bar(
            combined_sources, x='Month', y='Amount', color='source_type',
            barmode='stack',
            labels={'Amount': 'Amount ($)', 'source_type': 'Account'},
            color_discrete_map={'Credit Card': '#8B5CF6', 'Checking/Debit': '#F59E0B'}
        )
        fig_sources.update_layout(template="plotly_white", height=350, legend_title_text="")
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

# TAB 8: MANAGE CATEGORIES
with tab_manage:
    st.subheader("Category Mapping Manager")
    st.caption("Review and assign budget categories to merchants. "
               "Merchants not in the mappings file are flagged as unreviewed.")

    # Identify unreviewed merchants across ALL data (not just filtered)
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

    # Get current Budget_Category (from fallback logic in processed data)
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
            new_rows = []
            for _, row in edited_df.iterrows():
                new_rows.append({
                    'Clean_Description': row['Clean_Description'],
                    'Bank_Category': row['Category'],
                    'Budget_Category': row['Budget_Category']
                })
            new_mappings_df = pd.DataFrame(new_rows)

            if MAPPINGS_FILE.exists():
                existing_df = pd.read_csv(MAPPINGS_FILE)
                combined_df = pd.concat([existing_df, new_mappings_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(
                    subset=['Clean_Description', 'Bank_Category'], keep='last'
                )
            else:
                combined_df = new_mappings_df

            combined_df.to_csv(MAPPINGS_FILE, index=False)
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

# TAB 9: LOG REIMBURSEMENTS (NEW)
# TAB 9: LOG REIMBURSEMENTS (NEW WORKFLOW)
with tab_reimburse:
    st.subheader("Assign Incoming Transfers to Expenses")
    st.caption("Review incoming Zelle/Venmo transfers from your checking account and assign them to offset specific budget categories. This automatically reduces your top-line spending for those categories.")

    # 1. Gather all potential incoming transfers (Checking deposits + Income)
    candidates = pd.DataFrame()
    if not df_income_year.empty:
        candidates = pd.concat([candidates, df_income_year], ignore_index=True)
    if not df_checking_year.empty:
        candidates = pd.concat([candidates, df_checking_year], ignore_index=True)

    if not candidates.empty:
        # Filter for Zelle/Venmo that are DEPOSITS (Amount > 0)
        mask = candidates['Clean_Description'].str.contains('ZELLE|VENMO|CASH APP', case=False, na=False)
        positive_cashflow = candidates['Net_Amount'] > 0
        zelle_tx = candidates[mask & positive_cashflow].copy()

        # 2. Deduplicate and filter out already assigned transactions
        zelle_tx = zelle_tx.drop_duplicates(subset=['Transaction Date', 'Clean_Description', 'Net_Amount'])
        
        assignments_file = Path(__file__).resolve().parent / "Data" / "zelle_assignments.csv"
        
        if not zelle_tx.empty:
            if assignments_file.exists():
                assigned_df = pd.read_csv(assignments_file)
                if not assigned_df.empty:
                    # Create exact string dates for safe merging
                    zelle_tx['merge_date'] = pd.to_datetime(zelle_tx['Transaction Date']).dt.strftime('%Y-%m-%d')
                    assigned_df['merge_date'] = pd.to_datetime(assigned_df['Transaction Date']).dt.strftime('%Y-%m-%d')

                    merged = zelle_tx.merge(
                        assigned_df[['merge_date', 'Clean_Description', 'Net_Amount']], 
                        on=['merge_date', 'Clean_Description', 'Net_Amount'], 
                        how='left', indicator=True
                    )
                    unassigned = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge', 'merge_date'])
                else:
                    unassigned = zelle_tx
            else:
                unassigned = zelle_tx
        else:
            unassigned = pd.DataFrame()

        # 3. UI for Bulk Assignment
        if unassigned.empty:
            st.success("🎉 All incoming Zelle/Venmo transactions for this year have been mapped!")
        else:
            st.markdown("#### Unassigned Incoming Transfers")
            unassigned['Offset_Category'] = "Select Category..."
            
            # Format date for data editor
            unassigned['Transaction Date'] = pd.to_datetime(unassigned['Transaction Date']).dt.date
            
            display_cols = ['Transaction Date', 'Clean_Description', 'Net_Amount', 'Offset_Category']

            edited_df = st.data_editor(
                unassigned[display_cols].reset_index(drop=True),
                column_config={
                    "Transaction Date": st.column_config.DateColumn("Date", disabled=True),
                    "Clean_Description": st.column_config.TextColumn("Description", disabled=True),
                    "Net_Amount": st.column_config.NumberColumn("Amount", format="$%.2f", disabled=True),
                    "Offset_Category": st.column_config.SelectboxColumn(
                        "Assign to Category",
                        options=["Select Category..."] + sorted(BUDGET_CATEGORIES)
                    )
                },
                hide_index=True,
                use_container_width=True
            )

            if st.button("Save Assignments", type="primary"):
                # Grab only the rows where the user actually made a selection
                to_assign = edited_df[edited_df['Offset_Category'] != "Select Category..."].copy()
                
                if not to_assign.empty:
                    to_assign = to_assign.rename(columns={'Offset_Category': 'Budget_Category'})
                    
                    if assignments_file.exists():
                        to_assign.to_csv(assignments_file, mode='a', header=False, index=False)
                    else:
                        to_assign.to_csv(assignments_file, index=False)
                        
                    st.toast(f"Successfully assigned {len(to_assign)} transactions!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Please select a category for at least one transaction before saving.")
    else:
        st.info("No checking or income data found for this year. Make sure your checking CSVs are loaded.")
        
    # 4. View Assignment History
    st.markdown("---")
    st.markdown("#### Assignment History")
    assignments_file = Path(__file__).resolve().parent / "Data" / "zelle_assignments.csv"
    if assignments_file.exists():
        history_df = pd.read_csv(assignments_file)
        if not history_df.empty:
            st.dataframe(
                history_df.sort_values('Transaction Date', ascending=False),
                column_config={
                    "Transaction Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                    "Net_Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "Budget_Category": st.column_config.TextColumn("Offset Category"),
                    "Clean_Description": st.column_config.TextColumn("Description")
                },
                use_container_width=True,
                hide_index=True,
                height=300
            )
        else:
             st.info("No reimbursements logged yet.")
    else:
        st.info("No reimbursements logged yet.")

