import pandas as pd
import os
from pathlib import Path
import re


# --- Configuration ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "Data"

# 1. Your Strict Budget Categories
BUDGET_CATEGORIES = [
    "Home Electricity", "Home Water/Trash", "Home Furniture", "Internet",
    "Phone Bill", "HOA Bill", "Home Maintenance", "Car Registration",
    "Discord Subscription", "Spotify Subscription", "Amazon Prime Subscription",
    "Gym Membership", "Chase Sapphire Preferred Fee", "Costco Membership",
    "Groceries", "Gas", "Restaurants", "Health / Doctors", "Car Maintenance",
    "Pest control", "Landscaping", "Games", "Vacation", "Personal"
]

MAPPINGS_FILE = BASE_DIR / "category_mappings.csv"

# Bank category fallback — maps bank's original category to a reasonable budget default
BANK_CATEGORY_FALLBACK = {
    'Food & Drink': 'Restaurants',
    'Vehicle Services': 'Gas',
    'Health & Wellness': 'Health / Doctors',
    'Groceries': 'Groceries',
    'Home': 'Home Furniture',
    'Travel': 'Vacation',
    'Automotive': 'Car Maintenance',
}

# --- Checking Account Configuration ---
CHECKING_DIR = DATA_DIR / "Checking"

INCOME_KEYWORDS = ['DIRECT DEP', 'PAYROLL', 'ACH CREDIT', 'DEPOSIT']
TRANSFER_KEYWORDS = [
    'TRANSFER', 'PAYMENT TO CHASE CARD', 'ONLINE TRANSFER',
    'SAVE AS YOU GO'
]
INCOME_SOURCE_MAP = {
    'DIRECT DEP': 'Payroll', 'PAYROLL': 'Payroll',
    'ACH CREDIT': 'ACH Credit', 'DEPOSIT': 'Deposit',
}

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
    ('Amazon', 'Shopping'): 'Personal',
    ('Amazon', 'Bills & Utilities'): 'Personal',
    ("Andy'S", 'Food & Drink'): 'Restaurants',
    ('Apple', 'Shopping'): 'Personal',
    ('Arco', 'Vehicle Services'): 'Personal',
    ('Arirang Banchan', 'Groceries'): 'Groceries',
    ('Big O Tires 4247', 'Automotive'): 'Personal',
    ('Broken Rice', 'Food & Drink'): 'Restaurants',
    ('Caffenio', 'Food & Drink'): 'Restaurants',
    ('Costco', 'Merchandise'): 'Groceries',
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
    ('Qt', 'Vehicle Services'): 'Gas',
    ('Snowy Village', 'Food & Drink'): 'Restaurants',
    ('Sp Flakes', 'Shopping'): 'Personal',
    ('Sp Revival Rugs', 'Home'): 'Personal',
    ('Spotify', 'Bills & Utilities'): 'Spotify Subscription',
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

    mapping_dict = {}
    for _, row in mappings_df.iterrows():
        key = (row['Clean_Description'], row['Bank_Category'])
        mapping_dict[key] = row['Budget_Category']
    return mapping_dict

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

        try:
            with open(file, 'r') as f:
                first_line = f.readline()

            if "Time period" in first_line:
                df = pd.read_csv(file, skiprows=1)
                df['Source'] = 'Citi'
                df['Amount_Norm'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0) - \
                                   pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
                df = df.rename(columns={'Date': 'Transaction Date'})
            else:
                df = pd.read_csv(file)
                # Safeguard: Skip it if it's actually a checking file accidentally placed here
                if 'Details' in df.columns or 'Posting Date' in df.columns:
                    continue
                df['Source'] = 'Chase'
                df['Amount_Norm'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0) * -1

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
            with open(file, 'r') as f:
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

def main():
    print("--- Starting Budget Processing ---")

    raw_df = load_and_combine_csv_files(DATA_DIR)
    checking_df = load_checking_csv_files(CHECKING_DIR)

    if raw_df.empty and checking_df.empty:
        print("No data found.")
        return

    all_yearly_spending = []
    all_yearly_payments = []

    # --- Process credit card data ---
    if not raw_df.empty:
        df = raw_df.copy()
        df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], format='mixed')
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['Net_Amount'] = df['Amount_Norm']
        df['account_type'] = 'credit'

        df['Week'] = df['Transaction Date'].dt.isocalendar().week
        df['Month'] = df['Transaction Date'].dt.strftime('%B')
        df['Quarter'] = df['Transaction Date'].dt.quarter

        df['Clean_Description'] = df['Description'].apply(clean_merchant_name)
        df['Category'] = df['Category'].fillna('Uncategorized')

        payment_terms = ['PAYMENT THANK YOU', 'MOBILE PAYMENT', 'CREDIT CARD PYMT', 'AUTOPAY']
        is_payment = df['Description'].str.contains('|'.join(payment_terms), case=False, na=False)

        df_spending = df[~is_payment].copy()
        df_payments = df[is_payment].copy()
        df_spending = df_spending[df_spending['Net_Amount'] > 0].copy()

        category_map = load_category_mappings()
        df_spending['Budget_Category'] = df_spending.apply(
            lambda row: map_category(row, category_map), axis=1
        )

        cc_years = sorted(df_spending['Transaction Date'].dt.year.unique())

        print("Cleaning up old export files...")
        for year in cc_years:
            for suffix in ['_All_Transactions.csv', '_Credit_Card_Payments.csv',
                           '_Weekly_Summary.csv', '_Quarterly_Summary.csv']:
                file_path = DATA_DIR / f"{year}{suffix}"
                if file_path.exists():
                    file_path.unlink()
                    print(f"  Removed: {year}{suffix}")

        output_cols = ['Transaction Date', 'Clean_Description', 'Category', 'Budget_Category',
                       'Net_Amount', 'Source', 'account_type', 'Month', 'Quarter', 'Week']

        for year in cc_years:
            year_spending = df_spending[df_spending['Transaction Date'].dt.year == year].copy()
            year_payments = df_payments[df_payments['Transaction Date'].dt.year == year].copy()

            if not year_spending.empty:
                year_spending[output_cols].to_csv(DATA_DIR / f"{year}_All_Transactions.csv", index=False)
                all_yearly_spending.append(year_spending[output_cols])

                year_spending.groupby(['Week', 'Category'])['Net_Amount'].sum().unstack(fill_value=0).to_csv(
                    DATA_DIR / f"{year}_Weekly_Summary.csv")
                year_spending.groupby(['Quarter', 'Category'])['Net_Amount'].sum().unstack(fill_value=0).to_csv(
                    DATA_DIR / f"{year}_Quarterly_Summary.csv")

                print(f"  {year}: {len(year_spending)} transactions, ${year_spending['Net_Amount'].sum():,.2f}")

            if not year_payments.empty:
                year_payments.to_csv(DATA_DIR / f"{year}_Credit_Card_Payments.csv", index=False)
                all_yearly_payments.append(year_payments)

        if all_yearly_spending:
            combined_spending = pd.concat(all_yearly_spending, ignore_index=True).drop_duplicates()
            combined_spending.to_csv(DATA_DIR / "all_transactions.csv", index=False)
            print(f"\nCombined: {len(combined_spending)} total credit card transactions across {len(cc_years)} year(s)")

        if all_yearly_payments:
            combined_payments = pd.concat(all_yearly_payments, ignore_index=True).drop_duplicates()
            combined_payments.to_csv(DATA_DIR / "all_credit_card_payments.csv", index=False)

        all_spending = pd.concat(all_yearly_spending, ignore_index=True) if all_yearly_spending else pd.DataFrame()
        if not all_spending.empty:
            unmapped = all_spending[all_spending['Budget_Category'] == 'Personal']
            unmapped_merchants = unmapped[['Clean_Description', 'Category']].drop_duplicates()
            if not unmapped_merchants.empty:
                print(f"\n{len(unmapped_merchants)} merchant(s) defaulted to 'Personal'.")
                print("Use the 'Manage Categories' tab in the dashboard to review and assign them.")

# --- Process checking data ---
    all_yearly_income = []
    all_yearly_checking_spending = []

    if not checking_df.empty:
        ck = checking_df.copy()
        ck['Transaction Date'] = pd.to_datetime(ck['Transaction Date'], format='mixed')
            
        ck['Transaction Date'] = pd.to_datetime(ck['Transaction Date'], format='mixed')
        ck['Raw_Amount'] = pd.to_numeric(ck['Amount'], errors='coerce').fillna(0)
        ck['Net_Amount'] = ck['Amount_Norm']

        ck['Week'] = ck['Transaction Date'].dt.isocalendar().week
        ck['Month'] = ck['Transaction Date'].dt.strftime('%B')
        ck['Quarter'] = ck['Transaction Date'].dt.quarter

        ck['Clean_Description'] = ck['Description'].apply(clean_merchant_name)
        
        # FIX: Chase Checking doesn't usually have a 'Category' column, make sure it is safe
        if 'Category' not in ck.columns:
            ck['Category'] = 'Uncategorized'
        else:
            ck['Category'] = ck['Category'].fillna('Uncategorized')

        ck['tx_type'] = ck.apply(
            lambda row: classify_checking_transaction(row['Description'], row['Raw_Amount']), axis=1
        )

        ck_income = ck[ck['tx_type'] == 'income'].copy()
        ck_expense = ck[ck['tx_type'] == 'expense'].copy()

        # --- Income processing ---
        if not ck_income.empty:
            ck_income['Net_Amount'] = ck_income['Raw_Amount'].abs()
            ck_income = ck_income[ck_income['Net_Amount'] > 0].copy()
            ck_income['Income_Source'] = ck_income['Description'].apply(classify_income_source)

            income_cols = ['Transaction Date', 'Clean_Description', 'Category', 'Income_Source',
                           'Net_Amount', 'Source', 'account_type', 'Month', 'Quarter', 'Week']

            income_years = sorted(ck_income['Transaction Date'].dt.year.unique())
            for year in income_years:
                fp = DATA_DIR / f"{year}_All_Income.csv"
                if fp.exists():
                    fp.unlink()

            for year in income_years:
                year_income = ck_income[ck_income['Transaction Date'].dt.year == year].copy()
                if not year_income.empty:
                    year_income[income_cols].to_csv(DATA_DIR / f"{year}_All_Income.csv", index=False)
                    all_yearly_income.append(year_income[income_cols])
                    print(f"  {year} Income: {len(year_income)} deposits, ${year_income['Net_Amount'].sum():,.2f}")

            if all_yearly_income:
                combined_income = pd.concat(all_yearly_income, ignore_index=True).drop_duplicates()
                combined_income.to_csv(DATA_DIR / "all_income.csv", index=False)
                print(f"\nCombined: {len(combined_income)} total income transactions")

        # --- Checking expense processing ---
        if not ck_expense.empty:
            ck_expense['Net_Amount'] = ck_expense['Net_Amount'].abs()
            ck_expense = ck_expense[ck_expense['Net_Amount'] > 0].copy()

            category_map = load_category_mappings()

            ck_expense['Budget_Category'] = ck_expense.apply(
                lambda row: map_category(row, category_map), axis=1
            )

            expense_cols = ['Transaction Date', 'Clean_Description', 'Category', 'Budget_Category',
                            'Net_Amount', 'Source', 'account_type', 'Month', 'Quarter', 'Week']

            expense_years = sorted(ck_expense['Transaction Date'].dt.year.unique())
            for year in expense_years:
                fp = DATA_DIR / f"{year}_All_Checking_Spending.csv"
                if fp.exists():
                    fp.unlink()

            for year in expense_years:
                year_expense = ck_expense[ck_expense['Transaction Date'].dt.year == year].copy()
                if not year_expense.empty:
                    year_expense[expense_cols].to_csv(DATA_DIR / f"{year}_All_Checking_Spending.csv", index=False)
                    all_yearly_checking_spending.append(year_expense[expense_cols])
                    print(f"  {year} Checking Expenses: {len(year_expense)} transactions, ${year_expense['Net_Amount'].sum():,.2f}")

            if all_yearly_checking_spending:
                combined_checking = pd.concat(all_yearly_checking_spending, ignore_index=True).drop_duplicates()
                combined_checking.to_csv(DATA_DIR / "all_checking_spending.csv", index=False)
                print(f"\nCombined: {len(combined_checking)} total checking expense transactions")

    print("\n" + "-" * 30)
    print("--- Budget Processing Complete ---")

if __name__ == "__main__":
    main()