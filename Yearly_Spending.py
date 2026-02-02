import pandas as pd
import re
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path("/Users/brandontran/Desktop/Code/Budget_Calc")
DATA_DIR = BASE_DIR / "Data"

# Category Mapping for consistency (Chase + Citi)
CATEGORY_MAPPING = {
    'Merchandise': 'Shopping',
    'Vehicle Services': 'Automotive',
}

def clean_merchant_name(description):
    """
    Advanced cleaning for bank descriptions.
    Handles prefixes (SQ *, TST*), store numbers (#123), trailing locations,
    and trailing punctuation.
    """
    desc = str(description).upper()
    
    # 1. High-Priority Manual Overrides
    mappings = {
        'AMZN': 'Amazon', 'AMAZON': 'Amazon', 'UBER': 'Uber', 'LYFT': 'Lyft',
        'STARBUCKS': 'Starbucks', 'TRADER JOE': 'Trader Joes', 'WHOLEFDS': 'Whole Foods',
        'APPLE': 'Apple', 'NETFLIX': 'Netflix', 'SPOTIFY': 'Spotify',
        'TARGET': 'Target', 'COSTCO': 'Costco', 'SHELL': 'Shell',
        'CHEVRON': 'Chevron', 'IN-N-OUT': 'In-N-Out',
        'AMF': 'Amf Bowling',
        'QT ': 'Quick Trip',
        'CRAFTI TEA': 'Crafti Tea'
    }
    for key, value in mappings.items():
        if key in desc:
            return value

    # 2. Strip Payment Processor Prefixes (SQ *, TST*, PY *, etc.)
    desc = re.sub(r'^(SQ\s*\*|TST\s*\*|PY\s*\*|SP\s*\*|TOAST\s*\*)\s*', '', desc)
    
    # 3. Remove trailing location/store info (e.g., " - SCOTTSDA" or " #0736")
    desc = desc.split(' - ')[0]
    desc = desc.split(' #')[0]
    
    # 4. Standard Formatting (Remove extra spaces and Title Case)
    desc = " ".join(desc.split()).title()
    
    # 5. REMOVE TRAILING PERIODS
    # This strips any '.' characters from the very end of the name
    desc = desc.rstrip('.,;')
    
    return desc

def load_and_combine_csv_files(directory):
    """Load Chase and Citi CSV files, standardize them, and combine."""
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Data directory not found: {dir_path}")
        return pd.DataFrame()
    
    files_found = (list(dir_path.glob("Chase*.csv")) + 
                   list(dir_path.glob("Chase*.CSV")) + 
                   list(dir_path.glob("Year to date.CSV")))
    
    all_transactions = []
    for file in files_found:
        try:
            if "Year to date" in file.name:
                df = pd.read_csv(file, skiprows=1)
                df = df.rename(columns={'Date': 'Transaction Date'})
                debit = pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
                credit = pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
                df['Amount'] = credit - debit
                print(f"Loaded Citi: {file.name}")
            else:
                df = pd.read_csv(file)
                print(f"Loaded Chase: {file.name}")
            all_transactions.append(df)
        except Exception as e:
            print(f"Error loading {file.name}: {e}")
            
    return pd.concat(all_transactions, ignore_index=True) if all_transactions else pd.DataFrame()

def process_transactions(df, year=2026):
    """Process and clean combined transactions."""
    if df.empty: return pd.DataFrame(), pd.DataFrame()

    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], format='mixed')
    
    df = df[df['Transaction Date'].dt.year == year].copy()
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    df['Net_Amount'] = df['Amount'] * -1

    df['Week'] = df['Transaction Date'].dt.isocalendar().week
    df['Month'] = df['Transaction Date'].dt.strftime('%B')
    df['Quarter'] = df['Transaction Date'].dt.quarter
    
    # Categorization and Merchant Cleaning
    df['Category'] = df['Category'].fillna('Uncategorized').replace(CATEGORY_MAPPING)
    df['Clean_Description'] = df['Description'].apply(clean_merchant_name)

    # Separate Payments
    is_payment = df['Description'].str.contains('PAYMENT THANK YOU', case=False, na=False)
    df_payments = df[is_payment].copy()
    df_spending = df[~is_payment].copy()

    return df_spending.sort_values('Transaction Date', ascending=False), \
           df_payments.sort_values('Transaction Date', ascending=False)

def main():
    # --- 1. Cleanup Old Files ---
    files_to_remove = [
        "2026_All_Transactions.csv",
        "2026_Credit_Card_Payments.csv",
        "2026_Weekly_Summary.csv",
        "2026_Quarterly_Summary.csv"
    ]

    print("Cleaning up old export files...")
    for filename in files_to_remove:
        file_path = DATA_DIR / filename
        if file_path.exists():
            file_path.unlink()
            print(f"✓ Removed: {filename}")
    print("-" * 30)

    # --- 2. Processing ---
    raw_df = load_and_combine_csv_files(DATA_DIR)
    df_spending, df_payments = process_transactions(raw_df, year=2026)
    
    if df_spending.empty:
        print("No transactions found.")
        return

    # Export cleaned data
    df_spending.to_csv(DATA_DIR / "2026_All_Transactions.csv", index=False)
    if not df_payments.empty:
        df_payments.to_csv(DATA_DIR / "2026_Credit_Card_Payments.csv", index=False)
    
    # Summaries
    df_spending.groupby(['Week', 'Category'])['Net_Amount'].sum().unstack(fill_value=0).to_csv(DATA_DIR / "2026_Weekly_Summary.csv")
    df_spending.groupby(['Quarter', 'Category'])['Net_Amount'].sum().unstack(fill_value=0).to_csv(DATA_DIR / "2026_Quarterly_Summary.csv")

    print(f"✓ Success! Cleaned and processed {len(df_spending)} transactions.")

if __name__ == "__main__":
    main()