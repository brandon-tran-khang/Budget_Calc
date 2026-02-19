import pandas as pd


MONTH_NAMES = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
}


def _get_longest_consecutive_run(month_numbers):
    """Given sorted list of month numbers (1-12), return longest consecutive run."""
    if len(month_numbers) <= 1:
        return len(month_numbers)
    max_run = 1
    current_run = 1
    for i in range(1, len(month_numbers)):
        if month_numbers[i] == month_numbers[i - 1] + 1:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1
    return max_run


def detect_recurring_merchants(df, amount_tolerance=2.0, min_consecutive_months=2):
    """
    Detect merchants with consistent monthly charges.

    Criteria: same merchant in 2+ consecutive months, amount std <= tolerance,
    avg transactions per month <= 2 (filters out frequent shopping).

    Returns DataFrame with columns: Clean_Description, Budget_Category,
    Monthly_Amount, Months_Active, Consecutive_Months, Active_Range,
    Annual_Projected, Amount_Std.
    """
    result_cols = [
        'Clean_Description', 'Budget_Category', 'Monthly_Amount',
        'Months_Active', 'Consecutive_Months', 'Active_Range',
        'Annual_Projected', 'Amount_Std'
    ]
    if df.empty:
        return pd.DataFrame(columns=result_cols)

    df = df.copy()
    df['month_num'] = df['Transaction Date'].dt.month

    # Aggregate to monthly totals per merchant
    monthly = df.groupby(['Clean_Description', 'month_num']).agg(
        monthly_total=('Net_Amount', 'sum'),
        tx_count=('Net_Amount', 'count')
    ).reset_index()

    results = []
    for merchant, group in monthly.groupby('Clean_Description'):
        months_list = sorted(group['month_num'].tolist())
        months_active = len(months_list)

        if months_active < min_consecutive_months:
            continue

        consecutive = _get_longest_consecutive_run(months_list)
        if consecutive < min_consecutive_months:
            continue

        std_amount = group['monthly_total'].std()
        if pd.isna(std_amount):
            std_amount = 0.0
        if std_amount > amount_tolerance:
            continue

        # Filter out frequent shopping (e.g. Costco groceries 3x/month)
        if group['tx_count'].mean() > 2.0:
            continue

        median_amount = group['monthly_total'].median()
        top_category = df.loc[df['Clean_Description'] == merchant, 'Budget_Category'].mode()
        category = top_category.iloc[0] if not top_category.empty else 'Personal'
        active_range = ', '.join(MONTH_NAMES[m] for m in months_list)

        results.append({
            'Clean_Description': merchant,
            'Budget_Category': category,
            'Monthly_Amount': round(median_amount, 2),
            'Months_Active': months_active,
            'Consecutive_Months': consecutive,
            'Active_Range': active_range,
            'Annual_Projected': round(median_amount * 12, 2),
            'Amount_Std': round(std_amount, 2),
        })

    return pd.DataFrame(results, columns=result_cols) if results else pd.DataFrame(columns=result_cols)


def classify_transactions(df, recurring_merchants_df):
    """Add is_recurring (bool) and spending_type (Fixed/Variable) columns."""
    df = df.copy()
    if recurring_merchants_df.empty:
        df['is_recurring'] = False
        df['spending_type'] = 'Variable'
        return df

    recurring_names = set(recurring_merchants_df['Clean_Description'].tolist())
    df['is_recurring'] = df['Clean_Description'].isin(recurring_names)
    df['spending_type'] = df['is_recurring'].map({True: 'Fixed', False: 'Variable'})
    return df


def detect_subscription_changes(df, amount_tolerance=2.0):
    """
    Detect new subscriptions, cancellations, and price changes by comparing
    the earlier half vs recent half of available months.

    Returns list of dicts: {type, merchant, detail, old_amount, new_amount}.
    """
    if df.empty:
        return []

    df = df.copy()
    df['month_num'] = df['Transaction Date'].dt.month
    available_months = sorted(df['month_num'].unique())

    if len(available_months) < 3:
        return []

    midpoint = len(available_months) // 2
    earlier_months = set(available_months[:midpoint])
    recent_months = set(available_months[midpoint:])

    earlier_recurring = detect_recurring_merchants(
        df[df['month_num'].isin(earlier_months)], amount_tolerance
    )
    recent_recurring = detect_recurring_merchants(
        df[df['month_num'].isin(recent_months)], amount_tolerance
    )

    earlier_names = set(earlier_recurring['Clean_Description']) if not earlier_recurring.empty else set()
    recent_names = set(recent_recurring['Clean_Description']) if not recent_recurring.empty else set()

    alerts = []

    # New subscriptions
    for merchant in recent_names - earlier_names:
        row = recent_recurring[recent_recurring['Clean_Description'] == merchant].iloc[0]
        alerts.append({
            'type': 'new',
            'merchant': merchant,
            'detail': f"New recurring charge: ${row['Monthly_Amount']:.2f}/mo",
            'old_amount': None,
            'new_amount': row['Monthly_Amount']
        })

    # Cancelled subscriptions
    for merchant in earlier_names - recent_names:
        row = earlier_recurring[earlier_recurring['Clean_Description'] == merchant].iloc[0]
        alerts.append({
            'type': 'cancelled',
            'merchant': merchant,
            'detail': f"No longer appears (was ${row['Monthly_Amount']:.2f}/mo)",
            'old_amount': row['Monthly_Amount'],
            'new_amount': None
        })

    # Price changes
    for merchant in earlier_names & recent_names:
        old_row = earlier_recurring[earlier_recurring['Clean_Description'] == merchant].iloc[0]
        new_row = recent_recurring[recent_recurring['Clean_Description'] == merchant].iloc[0]
        diff = new_row['Monthly_Amount'] - old_row['Monthly_Amount']
        if abs(diff) > amount_tolerance:
            change_type = 'price_increase' if diff > 0 else 'price_decrease'
            alerts.append({
                'type': change_type,
                'merchant': merchant,
                'detail': f"${old_row['Monthly_Amount']:.2f} -> ${new_row['Monthly_Amount']:.2f}/mo ({'+' if diff > 0 else ''}{diff:.2f})",
                'old_amount': old_row['Monthly_Amount'],
                'new_amount': new_row['Monthly_Amount']
            })

    return alerts
