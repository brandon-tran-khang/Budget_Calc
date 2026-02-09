import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import datetime

# --- Page Configuration (Must be first) ---
st.set_page_config(
    page_title="2026 Finance Dashboard", 
    page_icon="💳", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- Modern "Fintech" UI Styling ---
st.markdown("""
    <style>
    /* Global Clean Font */
    html, body, [class*="css"] {
        font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Metrics Cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    
    /* Change metric label text to black */
    div[data-testid="stMetric"] label {
        color: #000000 !important;
        font-weight: 600;
    }
    
    /* Change metric value text to black */
    div[data-testid="stMetric"] div {
        color: #000000 !important;
    }
    
    /* Remove default top padding */
    .block-container {
        padding-top: 2rem;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1E293B;
        font-weight: 700;
    }
    
    /* Tabs */
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

# --- Data Loading ---
@st.cache_data
def load_data():
    # Update path to your specific directory
    directory = Path("/Users/brandontran/Desktop/Code/Budget_Calc/Data")
    
    df_trans = pd.DataFrame()
    df_payments = pd.DataFrame()
    
    try:
        # Load the detailed SPENDING log
        df_trans = pd.read_csv(directory / "2026_All_Transactions.csv")
        df_trans['Transaction Date'] = pd.to_datetime(df_trans['Transaction Date'])
        
        # Try Loading Payments (if it exists)
        payments_path = directory / "2026_Credit_Card_Payments.csv"
        if payments_path.exists():
            df_payments = pd.read_csv(payments_path)
            df_payments['Transaction Date'] = pd.to_datetime(df_payments['Transaction Date'])
            
    except FileNotFoundError:
        st.error("Data files not found. Please run 'Yearly_Spending.py' first.")
        return pd.DataFrame(), pd.DataFrame()
        
    return df_trans, df_payments

df_trans, df_payments = load_data()

if df_trans.empty:
    st.warning("No spending transactions found. Check your CSV generation script.")
    st.stop()

# --- Sidebar Filters ---
with st.sidebar:
    st.header("Filters")
    
    # Month Filter
    months = ['All'] + sorted(df_trans['Month'].unique().tolist(), key=lambda m: datetime.datetime.strptime(m, "%B").month)
    selected_month = st.selectbox("Select Month", months)
    
    # UPDATED: Category Filter to use Budget_Category
    categories = ['All'] + sorted(df_trans['Budget_Category'].unique().tolist())
    selected_category = st.selectbox("Select Budget Category", categories)

    st.markdown("---")
    st.caption(f"Last Updated: {datetime.date.today()}")

# Apply Filters
df_filtered = df_trans.copy()
if selected_month != 'All':
    df_filtered = df_filtered[df_filtered['Month'] == selected_month]
# UPDATED: Filter logic for Budget_Category
if selected_category != 'All':
    df_filtered = df_filtered[df_filtered['Budget_Category'] == selected_category]

# --- Main Dashboard ---

st.title("💸 2026 Spending Command Center")
st.markdown("Taking control of personal finances, one data point at a time.")
st.markdown("<br>", unsafe_allow_html=True)

# 1. Top Level Metrics
col1, col2, col3, col4 = st.columns(4)

total_spend = df_filtered['Net_Amount'].sum()
tx_count = len(df_filtered)
avg_tx = df_filtered['Net_Amount'].mean() if tx_count > 0 else 0

# Calculate Payment Total for display (Separated)
total_payments_made = 0
if not df_payments.empty:
    # Use the filtered month if selected, otherwise total
    pay_view = df_payments.copy()
    if selected_month != 'All':
        pay_view = pay_view[pay_view['Month'] == selected_month]
    # In raw CSV payments are positive
    total_payments_made = pay_view['Amount'].sum()

with col1:
    st.metric("Total Spending", f"${total_spend:,.2f}")
with col2:
    st.metric("Transactions", f"{tx_count}")
with col3:
    # UPDATED: Top Category now uses Budget_Category
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
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🛍️ Vendor Analysis", "📋 Transactions", "🔮 Forecasting"])

# TAB 1: OVERVIEW
with tab1:
    col_chart1, col_chart2 = st.columns([2, 1])
    
    with col_chart1:
        st.subheader("Spending Trend Over Time")
        time_group = df_filtered.groupby('Transaction Date')['Net_Amount'].sum().reset_index()
        time_group['Net_Amount'] = abs(time_group['Net_Amount'])
        
        fig_trend = px.line(time_group, x='Transaction Date', y='Net_Amount', 
                            markers=True, line_shape='spline')
        fig_trend.update_traces(line_color='#3B82F6', line_width=3)
        fig_trend.update_layout(height=350, xaxis_title="", yaxis_title="Amount ($)", template="plotly_white")
        st.plotly_chart(fig_trend, use_container_width=True)
        
    with col_chart2:
        st.subheader("Category Split")
        # UPDATED: Pi chart now uses Budget_Category
        cat_group = df_filtered.groupby('Budget_Category')['Net_Amount'].sum().reset_index()
        cat_group['Net_Amount'] = cat_group['Net_Amount'].clip(lower=0) 
        
        fig_pie = px.pie(cat_group, values='Net_Amount', names='Budget_Category', hole=0.6,
                              color_discrete_sequence=px.colors.qualitative.Prism)
        
        fig_pie.update_layout(height=350, showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

# TAB 2: VENDOR ANALYSIS (No changes needed, uses merchant name)
with tab2:
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
with tab3:
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
                help="Net spending amount"
            ),
        },
        use_container_width=True,
        height=600,
        hide_index=True
    )

# TAB 4: FORECASTING (No changes needed, uses dates and total Net_Amount)
with tab4:
    st.subheader("End of Year Projection")
    current_date = datetime.date.today()
    start_date = datetime.date(2026, 1, 1)
    days_passed = (current_date - start_date).days
    if days_passed < 1: days_passed = 1
    
    total_spend_ytd = df_trans['Net_Amount'].sum()
    daily_avg = total_spend_ytd / days_passed
    projected_total = daily_avg * 365
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.metric("Current Daily Burn Rate", f"${daily_avg:,.2f} / day")
    with col_f2:
        st.metric("Projected 2026 Total", f"${projected_total:,.2f}", 
                  help="Assumes you keep spending at exactly this rate for the rest of the year.")
        
    dates = pd.date_range(start='2026-01-01', end='2026-12-31', freq='M')
    projection_values = [daily_avg * d.day_of_year for d in dates]
    
    fig_proj = go.Figure()
    fig_proj.add_trace(go.Scatter(x=dates, y=projection_values, mode='lines', name='Projection', line=dict(dash='dot', color='gray')))
    
    actual_cum = df_trans.sort_values('Transaction Date').set_index('Transaction Date')['Net_Amount'].cumsum()
    actual_cum_resampled = actual_cum.resample('M').last()
    
    fig_proj.add_trace(go.Scatter(x=actual_cum_resampled.index, y=actual_cum_resampled.values, 
                                  mode='lines+markers', name='Actual Spending', line=dict(color='#3B82F6', width=4)))
    
    fig_proj.update_layout(title="Actual Cumulative Spend vs. Projected Path", template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig_proj, use_container_width=True)