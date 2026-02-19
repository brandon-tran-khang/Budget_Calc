import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import datetime
import calendar
from recurring import detect_recurring_merchants, classify_transactions, detect_subscription_changes

# --- Page Configuration (Must be first) ---
st.set_page_config(
    page_title="Finance Dashboard",
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

# --- Category Mapping Configuration ---
BUDGET_CATEGORIES = [
    "Home Electricity", "Home Water/Trash", "Home Furniture", "Internet",
    "Phone Bill", "HOA Bill", "Home Maintenance", "Car Registration",
    "Discord Subscription", "Spotify Subscription", "Amazon Prime Subscription",
    "Gym Membership", "Chase Sapphire Preferred Fee", "Costco Membership",
    "Groceries", "Gas", "Restaurants", "Health / Doctors", "Car Maintenance",
    "Pest control", "Landscaping", "Games", "Vacation", "Personal"
]

MAPPINGS_FILE = Path(__file__).resolve().parent / "category_mappings.csv"

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
    mapping_dict = {}
    for _, row in mappings_df.iterrows():
        key = (row['Clean_Description'], row['Bank_Category'])
        mapping_dict[key] = row['Budget_Category']
    return mapping_dict

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
    for idx, row in df.iterrows():
        key = (row['Clean_Description'], row['Category'])
        if key in mappings_dict:
            df.at[idx, 'Budget_Category'] = mappings_dict[key]
    return df

# --- Data Loading ---
@st.cache_data
def load_data():
    directory = Path(__file__).resolve().parent / "Data"

    df_trans = pd.DataFrame()
    df_payments = pd.DataFrame()

    try:
        trans_path = directory / "all_transactions.csv"
        if trans_path.exists():
            df_trans = pd.read_csv(trans_path)
            df_trans['Transaction Date'] = pd.to_datetime(df_trans['Transaction Date'])
            if 'Year' not in df_trans.columns:
                df_trans['Year'] = df_trans['Transaction Date'].dt.year

        payments_path = directory / "all_credit_card_payments.csv"
        if payments_path.exists():
            df_payments = pd.read_csv(payments_path)
            df_payments['Transaction Date'] = pd.to_datetime(df_payments['Transaction Date'])
            if 'Year' not in df_payments.columns:
                df_payments['Year'] = df_payments['Transaction Date'].dt.year

    except FileNotFoundError:
        st.error("Data files not found. Please run 'Yearly_Spending.py' first.")
        return pd.DataFrame(), pd.DataFrame()

    return df_trans, df_payments

df_trans, df_payments = load_data()

# Apply mapping overlay from external CSV (instant feedback without re-running Yearly_Spending.py)
mappings_dict = load_mappings()
if not df_trans.empty and mappings_dict:
    df_trans = apply_mapping_overlay(df_trans, mappings_dict)

if df_trans.empty:
    st.warning("No spending transactions found. Check your CSV generation script.")
    st.stop()

# --- Sidebar Filters ---
with st.sidebar:
    st.header("Filters")

    # Year Filter
    available_years = sorted(df_trans['Year'].unique().tolist(), reverse=True)
    current_year = datetime.date.today().year
    default_year_index = available_years.index(current_year) if current_year in available_years else 0
    selected_year = st.selectbox("Select Year", available_years, index=default_year_index)

    # Filter by year first to scope month/category options
    df_year = df_trans[df_trans['Year'] == selected_year].copy()

    # Recurring expense detection for selected year
    _recurring_dict, subscription_alerts = get_recurring_analysis(df_year.to_dict('list'))
    recurring_merchants = pd.DataFrame(_recurring_dict)
    df_year = classify_transactions(df_year, recurring_merchants)

    # Month Filter (scoped to selected year)
    months = ['All'] + sorted(df_year['Month'].unique().tolist(), key=lambda m: datetime.datetime.strptime(m, "%B").month)
    selected_month = st.selectbox("Select Month", months)

    # Category Filter (scoped to selected year)
    categories = ['All'] + sorted(df_year['Budget_Category'].unique().tolist())
    selected_category = st.selectbox("Select Budget Category", categories)

    st.markdown("---")
    st.caption(f"Last Updated: {datetime.date.today()}")

# Apply Filters (starting from year-filtered data)
df_filtered = df_year.copy()
if selected_month != 'All':
    df_filtered = df_filtered[df_filtered['Month'] == selected_month]
if selected_category != 'All':
    df_filtered = df_filtered[df_filtered['Budget_Category'] == selected_category]

# --- Main Dashboard ---

st.title(f"💸 {selected_year} Spending Command Center")
st.markdown("Taking control of personal finances, one data point at a time.")
st.markdown("<br>", unsafe_allow_html=True)

# 1. Top Level Metrics
col1, col2, col3, col4 = st.columns(4)

total_spend = df_filtered['Net_Amount'].sum()
tx_count = len(df_filtered)
avg_tx = df_filtered['Net_Amount'].mean() if tx_count > 0 else 0

# Calculate Payment Total for display (Separated)
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
tab_overview, tab_vendor, tab_transactions, tab_forecast, tab_yoy, tab_recurring, tab_manage = st.tabs(
    ["📊 Overview", "🛍️ Vendor Analysis", "📋 Transactions", "🔮 Forecasting", "📈 Year Comparison", "🔄 Recurring", "⚙️ Manage Categories"])

# TAB 1: OVERVIEW
with tab_overview:
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
            fv_data = pd.DataFrame({
                'Type': ['Fixed', 'Variable'],
                'Amount': [fixed_total, variable_total]
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

# TAB 2: VENDOR ANALYSIS (No changes needed, uses merchant name)
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
                help="Net spending amount"
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
    actual_cum_resampled = actual_cum.resample('M').last()

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

# TAB 7: MANAGE CATEGORIES
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