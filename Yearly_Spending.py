import pandas as pd
import os
from pathlib import Path

# --- Configuration ---
# Update this path to your actual directory
BASE_DIR = Path("/Users/brandontran/Desktop/Code")

def clean_merchant_name(description):
    """
    Cleans messy bank descriptions.
    Example: 'STARBUCKS STORE 00329 CA' -> 'Starbucks'
    """
    desc = str(description).upper()
    
    # Dictionary of common messy descriptors to clean up
    mappings = {
        'AMZN': 'Amazon',
        'AMAZON': 'Amazon',
        'UBER': 'Uber',
        'LYFT': 'Lyft',
        'STARBUCKS': 'Starbucks',
        'TRADER JOE': 'Trader Joes',
        'WHOLEFDS': 'Whole Foods',
        'APPLE': 'Apple',
        'NETFLIX': 'Netflix',
        'SPOTIFY': 'Spotify',
        'TARGET': 'Target',
        'COSTCO': 'Costco',
        'SHELL': 'Shell',
        'CHEVRON': 'Chevron',
        'IN-N-OUT': 'In-N-Out'
    }
    
    for key, value in mappings.items():
        if key in desc:
            return value
            
    # If no match, just title case the original and remove extra whitespace
    return " ".join(desc.split()).title()

def load_and_combine_csv_files(directory):
    """Load all Chase CSV files from directory and combine them"""
    dir_path = Path(directory)
    
    # Look for both .CSV and .csv to avoid case sensitivity issues
    files_found = list(dir_path.glob("Chase*.CSV")) + list(dir_path.glob("Chase*.csv"))
    
    if not files_found:
        print(f"No Chase CSV files found in {directory}")
        return pd.DataFrame()

    all_transactions = []
    for file in files_found:
        try:
            df = pd.read_csv(file)
            all_transactions.append(df)
            print(f"Loaded: {file.name}")
        except Exception as e:
            print(f"Error loading {file.name}: {e}")
    
    if not all_transactions:
        return pd.DataFrame()
        
    return pd.concat(all_transactions, ignore_index=True)

def process_transactions(df, year=2026):
    """
    Process transactions:
    1. Standardize Dates and Amounts.
    2. Split 'Payments' (Credit Card payoffs) from actual 'Spending'.
    3. Clean merchant descriptions.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # --- 1. Basic Cleaning ---
    if 'Transaction Date' not in df.columns:
        print("Error: 'Transaction Date' column missing. Check your CSV headers.")
        return pd.DataFrame(), pd.DataFrame()

    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    
    # Filter for Year
    df = df[df['Transaction Date'].dt.year == year].copy()

    # Standardize 'Amount' to numeric
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)

    # In Chase CSVs: Sale = -10.00. We want this to be +10.00 for "Spending".
    # Payments are usually positive numbers in raw CSV, so they become negative here.
    df['Net_Amount'] = df['Amount'] * -1

    # Extract time data
    df['Week'] = df['Transaction Date'].dt.isocalendar().week
    df['Month'] = df['Transaction Date'].dt.strftime('%B')
    df['Quarter'] = df['Transaction Date'].dt.quarter
    
    # Clean Category
    if 'Category' in df.columns:
        df['Category'] = df['Category'].fillna('Uncategorized')
    else:
        df['Category'] = 'Uncategorized'
        
    # Clean Description
    if 'Description' in df.columns:
        df['Clean_Description'] = df['Description'].apply(clean_merchant_name)
    else:
        df['Clean_Description'] = 'Unknown'
        df['Description'] = 'Unknown'

    # --- 2. Separate Payments from Spending ---
    # Logic: Identify payments by description text "Payment Thank You"
    # We use regex to catch "Payment Thank You - Mobile", "Web", etc.
    is_payment = df['Description'].str.contains('PAYMENT THANK YOU', case=False, na=False)
    
    df_payments = df[is_payment].copy()
    df_spending = df[~is_payment].copy()

    # OPTIONAL: Filter out positive values from spending if you only want pure outflows
    # (Sometimes returns appear as positive Net_Amount in this logic, which is fine to keep as it lowers spend)
    
    # Sort by date
    df_spending = df_spending.sort_values('Transaction Date', ascending=False)
    df_payments = df_payments.sort_values('Transaction Date', ascending=False)
    
    return df_spending, df_payments

def main():
    print(f"Processing data in: {BASE_DIR}")
    
    # 1. Load
    raw_df = load_and_combine_csv_files(BASE_DIR)
    
    # 2. Process
    df_spending, df_payments = process_transactions(raw_df, year=2026)
    
    if df_spending.empty:
        print("No transactions found for 2026.")
        return

    # Statistics
    total_spend = df_spending['Net_Amount'].sum()
    total_payments = df_payments['Amount'].sum() # Use raw amount for payments (which is usually positive in CSV)
    
    print("-" * 30)
    print(f"Total Transactions: {len(df_spending)}")
    print(f"Total Net Spending: ${total_spend:,.2f}")
    print(f"Total Payments (Removed): ${total_payments:,.2f} ({len(df_payments)} txns)")
    print("-" * 30)

    # 3. Export Files
    
    # A. Spending Log (Main File for Frontend)
    df_spending.to_csv(BASE_DIR / "2026_All_Transactions.csv", index=False)
    
    # B. Payment Log (Separate Tracking)
    if not df_payments.empty:
        # For the payments file, we might prefer the raw Amount (positive) to look natural
        df_payments.to_csv(BASE_DIR / "2026_Credit_Card_Payments.csv", index=False)
    
    # C. Weekly Summary (Based on SPENDING only)
    weekly = df_spending.groupby(['Week', 'Category'])['Net_Amount'].sum().unstack(fill_value=0)
    weekly['Total'] = weekly.sum(axis=1)
    weekly.to_csv(BASE_DIR / "2026_Weekly_Summary.csv")
    
    # D. Quarterly Summary (Based on SPENDING only)
    quarterly = df_spending.groupby(['Quarter', 'Category'])['Net_Amount'].sum().unstack(fill_value=0)
    quarterly['Total'] = quarterly.sum(axis=1)
    quarterly.to_csv(BASE_DIR / "2026_Quarterly_Summary.csv")

    print("✓ Success! Generated cleaned spending logs and payment trackers.")

if __name__ == "__main__":
    main()