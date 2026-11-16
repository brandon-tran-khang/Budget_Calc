import pandas as pd
from pathlib import Path
import re

from config import (
    DATA_DIR, CHECKING_DIR, MAPPINGS_FILE, BANK_CATEGORY_FALLBACK,
    INCOME_KEYWORDS, TRANSFER_KEYWORDS, INCOME_SOURCE_MAP, PAYMENT_TERMS, REIMBURSEMENTS_FILE,
    INVESTMENT_KEYWORDS,
)

# Legacy mapping dictionary — used ONLY to seed category_mappings.csv on first run.
_SEED_CATEGORY_MAP = {
    ('Costco', 'Groceries'): 'Groceries',
    ('Costco', 'Merchandise'): 'Groceries',
    ('Costco', 'Shopping'): 'Groceries',
    ('Costco Gas', 'Gas'): 'Gas',
    ('Costco Gas', 'Vehicle Services'): 'Gas',
    ('Qt', 'Vehicle Services'): 'Gas',
    ('Qt', 'Gas'): 'Gas',
    ('Shell', 'Gas'): 'Gas',
    ('Chevron', 'Gas'): 'Gas',
    ('Amazon', 'Shopping'): 'Personal', 
    ('Amazon Prime', 'Bills & Utilities'): 'Amazon Prime Subscription',
    ('Spotify', 'Bills & Utilities'): 'Spotify Subscription',
    ('Discord', 'Bills & Utilities'): 'Discord Subscription',
    ('Eos Fitness', 'Health & Wellness'): 'Gym Membership',
    ('Cox', 'Bills & Utilities'): 'Internet',
    ('Verizon', 'Bills & Utilities'): 'Phone Bill',
    ('Srp', 'Bills & Utilities'): 'Home Electricity',
    ('City Of Chandler', 'Bills & Utilities'): 'Home Water/Trash',
    ('354 Amf 8003425263', 'Food & Drink'): 'Personal',
    ('Amazon', 'Bills & Utilities'): 'Personal',
    ("Andy'S", 'Food & Drink'): 'Restaurants',
    ('Apple', 'Shopping'): 'Personal',
    ('Arco', 'Vehicle Services'): 'Personal',
    ('Arirang Banchan', 'Groceries'): 'Groceries',
    ('Big O Tires 4247', 'Automotive'): 'Personal',
    ('Broken Rice', 'Food & Drink'): 'Restaurants',
    ('Caffenio', 'Food & Drink'): 'Restaurants',
    ('Costco', 'Vehicle Services'): 'Personal',
    ('Crafti Tea &Amp; Mocktail', 'Food & Drink'): 'Restaurants',
    ('Dayungs Tea Chandler', 'Food & Drink'): 'Restaurants',
    ('Dong Feng Seafood City', 'Groceries'): 'Restaurants',
    ('Fitness Your Way', 'Health & Wellness'): 'Personal',
    ('Go Green Valet', 'Travel'): 'Personal',
    ('Green Corner Restaura', 'Food & Drink'): 'Restaurants',
    ('H Mart Mesa Llc', 'Groceries'): 'Personal',
    ('Hechalou', 'Food & Drink'): 'Restaurants',
    ('Hiro Sushi', 'Food & Drink'): 'Restaurants',
    ('Hodori Restaurant.', 'Food & Drink'): 'Restaurants',
    ('Ikea Tempe', 'Home'): 'Personal',
    ('In-N-Out', 'Food & Drink'): 'Restaurants',
    ('Laymoon Cafe', 'Food & Drink'): 'Restaurants',
    ('Meet Fresh', 'Food & Drink'): 'Restaurants',
    ('Micro Center', 'Shopping'): 'Personal',
    ('Phoenyx International', 'Food & Drink'): 'Restaurants',
    ('Pizzeria Bianco', 'Food & Drink'): 'Restaurants',
    ('Snowy Village', 'Food & Drink'): 'Restaurants',
    ('Sp Flakes', 'Shopping'): 'Personal',
    ('Sp Revival Rugs', 'Home'): 'Personal',
    ('T-Swirl Crepe Arizona', 'Food & Drink'): 'Restaurants',
    ('Taqueria Mi Casita', 'Food & Drink'): 'Restaurants',
    ('Tasty Pot', 'Food & Drink'): 'Restaurants',
    ('Tous Les Jours Mesa', 'Food & Drink'): 'Groceries',
    ('Trader Joes', 'Groceries'): 'Groceries'
}

def load_category_mappings():
    if not MAPPINGS_FILE.exists():
        rows = [
            {'Clean_Description': desc, 'Bank_Category': bank_cat, 'Budget_Category': budget_cat}
            for (desc, bank_cat), budget_cat in _SEED_CATEGORY_MAP.items()
        ]
        seed_df = pd.DataFrame(rows).drop_duplicates(
            subset=['Clean_Description', 'Bank_Category'], keep='last'
        )
        seed_df.to_csv(MAPPINGS_FILE, index=False)
        print(f"Created {MAPPINGS_FILE.name} with {len(seed_df)} mappings from defaults.")

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

# --- Helper Functions ---

def _is_output_file(filename):
    return bool(re.match(r'^\d{4}_', filename)) or filename.startswith('all_')

def clean_merchant_name(description):
    desc = str(description).upper()
    keyword_map = {
        'AMZN': 'Amazon', 'AMAZON': 'Amazon', 'UBER': 'Uber', 'LYFT': 'Lyft',
        'STARBUCKS': 'Starbucks', 'TRADER JOE': 'Trader Joes', 'WHOLEFDS': 'Whole Foods',
        'APPLE': 'Apple', 'NETFLIX': 'Netflix', 'SPOTIFY': 'Spotify',
        'TARGET': 'Target', 'COSTCO': 'Costco', 'SHELL': 'Shell',
        'CHEVRON': 'Chevron', 'IN-N-OUT': 'In-N-Out', 'QT ': 'Qt',
        'ARCO': 'Arco', 'EOS FITNESS': 'Eos Fitness', 'DISCORD': 'Discord',
        'COX': 'Cox', 'VERIZON': 'Verizon', 'SRP': 'Srp'
    }

    for key, value in keyword_map.items():
        if key in desc:
            return value

    desc = re.sub(r'^(SQ\s*\*|TST\s*\*|PY\s*\*|SP\s*\*|TOAST\s*\*)\s*', '', desc)
    desc = desc.split(' - ')[0]
    desc = desc.split(' #')[0]
    desc = " ".join(desc.split()).title()
    return desc

def load_and_combine_csv_files(directory):
    """
    Loads ONLY top-level Chase and Citi credit card files, standardizing columns.
    Ignores subdirectories like Checking/.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Data directory not found: {dir_path}")
        return pd.DataFrame()

    # FIX: Use iterdir() and check is_file() to ensure we don't look into subdirectories
    files_found = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.upper() == '.CSV']

    all_transactions = []
    for file in files_found:
        if _is_output_file(file.name):
            continue

        if file.name == REIMBURSEMENTS_FILE.name:
            continue

        try:
            with open(file, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline()

            df = pd.read_csv(file, skiprows=1 if "Time period" in first_line else 0,
                             encoding='utf-8-sig')
            if {'Debit', 'Credit'} <= set(df.columns):
                df['Source'] = 'Citi'
                # Credit sign varies between Citi exports, so force it to reduce spending.
                df['Amount_Norm'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0) - \
                                   pd.to_numeric(df['Credit'], errors='coerce').fillna(0).abs()
                df = df.rename(columns={'Date': 'Transaction Date'})
            elif 'Details' in df.columns or 'Posting Date' in df.columns:
                continue  # checking file accidentally placed here
            elif {'Transaction Date', 'Description', 'Amount'} <= set(df.columns):
                df['Source'] = 'Chase'
                df['Amount_Norm'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0) * -1
            else:
                print(f"Skipping unrecognized file: {file.name}")
                continue

            all_transactions.append(df)
            print(f"Loaded: {file.name}")

        except Exception as e:
            print(f"Error loading {file.name}: {e}")

    return pd.concat(all_transactions, ignore_index=True) if all_transactions else pd.DataFrame()


def load_checking_csv_files(directory):
    """
    Loads Chase checking account CSVs from Data/Checking/.
    Strictly maps columns positionally to handle Chase's blank trailing headers.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"No checking directory found at {dir_path} — skipping checking data.")
        return pd.DataFrame()

    files_found = [f for f in dir_path.iterdir() if f.is_file() and f.suffix.upper() == '.CSV']

    all_transactions = []
    for file in files_found:
        if _is_output_file(file.name):
            continue

        try:
            # Read the first line to confirm it's actually the checking file
            with open(file, 'r', encoding='utf-8-sig') as f:
                header_line = f.readline().upper()
            
            # If it's a credit card file accidentally placed here, skip it
            if "MEMO" in header_line or "CARD ENDING" in header_line:
                print(f"Skipping credit card file found in checking directory: {file.name}")
                continue

            # Force parse using Chase Checking's explicit 7-column layout
            # This completely bypasses shifted/unnamed header logic errors
            df = pd.read_csv(
                file, 
                skiprows=1, # Skip the problematic original bank header row
                names=['Details', 'Transaction Date', 'Description', 'Amount', 'Type', 'Balance', 'Check_Slip'],
                usecols=[0, 1, 2, 3, 4, 5, 6] # Lock strictly to the first 7 data positions
            )
            
            if df.empty:
                continue

            df['Source'] = 'Chase Checking'
            df['account_type'] = 'checking'
            
            # Handle Amount normalization safely
            df['Amount_Norm'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0) * -1
            
            all_transactions.append(df)
            print(f"Loaded checking: {file.name}")
            
        except Exception as e:
            print(f"Error loading checking {file.name}: {e}")

    return pd.concat(all_transactions, ignore_index=True) if all_transactions else pd.DataFrame()

def classify_checking_transaction(description, amount):
    desc_upper = str(description).upper()
    for kw in TRANSFER_KEYWORDS:
        if kw in desc_upper:
            return 'transfer'
    for kw in INCOME_KEYWORDS:
        if kw in desc_upper:
            return 'income'
    if amount > 0:
        return 'income'
    else:
        return 'expense'

def classify_income_source(description):
    desc_upper = str(description).upper()
    for keyword, source in INCOME_SOURCE_MAP.items():
        if keyword in desc_upper:
            return source
    return 'Other Income'

def map_category(row, category_map):
    key = (row['Clean_Description'], row['Category'])

    if key in category_map:
        return category_map[key]

    bank_cat = row['Category']
    desc_lower = row['Clean_Description'].lower()
    if any(kw.lower() in desc_lower for kw in INVESTMENT_KEYWORDS):
        return 'Investments'
    if bank_cat in BANK_CATEGORY_FALLBACK:
        return BANK_CATEGORY_FALLBACK[bank_cat]

    if bank_cat == 'Bills & Utilities' or bank_cat == 'Uncategorized':
        if any(kw in desc_lower for kw in ['electric', 'srp', 'power']):
            return 'Home Electricity'
        if any(kw in desc_lower for kw in ['water', 'trash', 'sewer', 'city of', 'hoapayments', 'paylease']):
            return 'Home Water/Trash' if 'city of' in desc_lower else 'HOA Bill'
        if any(kw in desc_lower for kw in ['internet', 'cox', 'wifi']):
            return 'Internet'
        if any(kw in desc_lower for kw in ['phone', 'verizon', 'mobile', 't-mobile']):
            return 'Phone Bill'

    if 'gas' in desc_lower or 'fuel' in desc_lower:
        return 'Gas'
    if 'food' in desc_lower or 'restaurant' in desc_lower:
        return 'Restaurants'

    return 'Personal'

def process_credit_cards(raw_df, category_map):
    """Process credit card transactions: clean, categorize, split spending/payments.

    Returns (spending_list, payments_list) — each a list of per-year DataFrames.
    """
    df = raw_df.copy()
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], format='mixed')
    df['Net_Amount'] = df['Amount_Norm']
    df['account_type'] = 'credit'

    df['Week'] = df['Transaction Date'].dt.isocalendar().week
    df['Month'] = df['Transaction Date'].dt.strftime('%B')
    df['Quarter'] = df['Transaction Date'].dt.quarter

    df['Clean_Description'] = df['Description'].apply(clean_merchant_name)
    if 'Category' not in df.columns:  # Citi exports have none
        df['Category'] = None
    df['Category'] = df['Category'].fillna('Uncategorized')

    # Filter out payments (Chase marks them Type == 'Payment'; Citi only by description)
    is_payment = df['Description'].str.contains(
        '|'.join(re.escape(t) for t in PAYMENT_TERMS), case=False, na=False)
    if 'Type' in df.columns:
        is_payment |= df['Type'].eq('Payment')
    df_spending = df[~is_payment].copy()
    df_payments = df[is_payment].copy()

    # Keep refunds (negative Net_Amount) so they reduce spending; drop only zero rows
    df_spending = df_spending[df_spending['Net_Amount'] != 0].copy()

    # Apply category mapping
    df_spending['Budget_Category'] = df_spending.apply(
        lambda row: map_category(row, category_map), axis=1
    )

    return df_spending, df_payments


def process_checking(checking_df, category_map):
    """Process checking transactions: classify as income/expense/transfer.

    Returns (income_df, expense_df). Transfers are excluded.
    """
    ck = checking_df.copy()
    ck['Transaction Date'] = pd.to_datetime(ck['Transaction Date'], format='mixed')
    ck['Raw_Amount'] = pd.to_numeric(ck['Amount'], errors='coerce').fillna(0)
    ck['Net_Amount'] = ck['Amount_Norm']

    ck['Week'] = ck['Transaction Date'].dt.isocalendar().week
    ck['Month'] = ck['Transaction Date'].dt.strftime('%B')
    ck['Quarter'] = ck['Transaction Date'].dt.quarter

    ck['Clean_Description'] = ck['Description'].apply(clean_merchant_name)
    ck['Category'] = ck['Category'].fillna('Uncategorized') if 'Category' in ck.columns else 'Uncategorized'

    # Classify each transaction
    ck['tx_type'] = ck.apply(
        lambda row: classify_checking_transaction(row['Description'], row['Raw_Amount']), axis=1
    )

    ck_income = ck[ck['tx_type'] == 'income'].copy()
    ck_expense = ck[ck['tx_type'] == 'expense'].copy()

    # Income: ensure positive amounts
    if not ck_income.empty:
        ck_income['Net_Amount'] = ck_income['Raw_Amount'].abs()
        ck_income = ck_income[ck_income['Net_Amount'] > 0].copy()
        ck_income['Income_Source'] = ck_income['Description'].apply(classify_income_source)

    # Expenses: ensure positive amounts + categorize
    if not ck_expense.empty:
        ck_expense['Net_Amount'] = ck_expense['Net_Amount'].abs()
        ck_expense = ck_expense[ck_expense['Net_Amount'] > 0].copy()
        ck_expense['Budget_Category'] = ck_expense.apply(
            lambda row: map_category(row, category_map), axis=1
        )

    return ck_income, ck_expense


def export_yearly_and_combined(data_list, years, output_cols, per_year_suffix, combined_filename,
                               extra_per_year_exports=None):
    """Export per-year CSVs and a combined multi-year CSV.

    Args:
        data_list: Full DataFrame to split by year.
        years: Sorted list of years.
        output_cols: Columns to include in output.
        per_year_suffix: e.g. '_All_Transactions.csv'.
        combined_filename: e.g. 'all_transactions.csv'.
        extra_per_year_exports: Optional callable(year_df, year) for extra per-year files.
    """
    all_yearly = []

    # Clean up old files
    for year in years:
        file_path = DATA_DIR / f"{year}{per_year_suffix}"
        if file_path.exists():
            file_path.unlink()

    for year in years:
        year_data = data_list[data_list['Transaction Date'].dt.year == year].copy()
        if not year_data.empty:
            year_data[output_cols].to_csv(DATA_DIR / f"{year}{per_year_suffix}", index=False)
            all_yearly.append(year_data[output_cols])

            if extra_per_year_exports:
                extra_per_year_exports(year_data, year)

            print(f"  {year}: {len(year_data)} transactions, ${year_data['Net_Amount'].sum():,.2f}")

    if all_yearly:
        combined = pd.concat(all_yearly, ignore_index=True)
        combined.to_csv(DATA_DIR / combined_filename, index=False)
        print(f"\nCombined: {len(combined)} total transactions in {combined_filename}")

    return all_yearly


def main():
    print("--- Starting Budget Processing ---")

    raw_df = load_and_combine_csv_files(DATA_DIR)
    checking_df = load_checking_csv_files(CHECKING_DIR)

    if raw_df.empty and checking_df.empty:
        print("No data found.")
        return

    category_map = load_category_mappings()
    spend_cols = ['Transaction Date', 'Clean_Description', 'Category', 'Budget_Category',
                  'Net_Amount', 'Source', 'account_type', 'Month', 'Quarter', 'Week']
    income_cols = ['Transaction Date', 'Clean_Description', 'Category', 'Income_Source',
                   'Net_Amount', 'Source', 'account_type', 'Month', 'Quarter', 'Week']

    def years_of(df):
        return sorted(df['Transaction Date'].dt.year.unique())

    def summaries(year_data, year):
        for col, name in [('Week', 'Weekly'), ('Quarter', 'Quarterly')]:
            year_data.groupby([col, 'Category'])['Net_Amount'].sum().unstack(fill_value=0).to_csv(
                DATA_DIR / f"{year}_{name}_Summary.csv")

    if not raw_df.empty:
        df_spending, df_payments = process_credit_cards(raw_df, category_map)
        if not df_spending.empty:
            export_yearly_and_combined(df_spending, years_of(df_spending), spend_cols,
                                       '_All_Transactions.csv', 'all_transactions.csv',
                                       extra_per_year_exports=summaries)
            unmapped = df_spending[df_spending['Budget_Category'] == 'Personal']
            n = len(unmapped[['Clean_Description', 'Category']].drop_duplicates())
            if n:
                print(f"\n{n} merchant(s) defaulted to 'Personal'.")
                print("Use the 'Manage Categories' tab in the dashboard to review and assign them.")
        if not df_payments.empty:
            export_yearly_and_combined(df_payments, years_of(df_payments), list(df_payments.columns),
                                       '_Credit_Card_Payments.csv', 'all_credit_card_payments.csv')

    if not checking_df.empty:
        ck_income, ck_expense = process_checking(checking_df, category_map)
        if not ck_income.empty:
            export_yearly_and_combined(ck_income, years_of(ck_income), income_cols,
                                       '_All_Income.csv', 'all_income.csv')
        if not ck_expense.empty:
            export_yearly_and_combined(ck_expense, years_of(ck_expense), spend_cols,
                                       '_All_Checking_Spending.csv', 'all_checking_spending.csv')

    print("\n" + "-" * 30)
    print("--- Budget Processing Complete ---")


if __name__ == "__main__":
    main()
