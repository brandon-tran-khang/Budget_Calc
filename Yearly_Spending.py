import pandas as pd
import os
from pathlib import Path
import re


# --- Configuration ---
BASE_DIR = Path("/Users/brandontran/Desktop/Code/Budget_Calc")
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

# Legacy mapping dictionary — used ONLY to seed category_mappings.csv on first run.
# To update mappings, edit category_mappings.csv directly or use the Streamlit UI.
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
    ('Amazon', 'Shopping'): 'Personal', # Default Amazon to personal, override specific subs below if needed
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
    """
    Load category mappings from external CSV file.
    If the file doesn't exist, seed it from the legacy _SEED_CATEGORY_MAP.
    Returns a dict of (Clean_Description, Bank_Category) -> Budget_Category.
    """
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

def clean_merchant_name(description):
    """
    Cleans up bank transaction descriptions to make them readable.
    """
    desc = str(description).upper()
    
    # Keyword overrides to normalize names
    keyword_map = {
        'AMZN': 'Amazon', 'AMAZON': 'Amazon', 'UBER': 'Uber', 'LYFT': 'Lyft',
        'STARBUCKS': 'Starbucks', 'TRADER JOE': 'Trader Joes', 'WHOLEFDS': 'Whole Foods',
        'APPLE': 'Apple', 'NETFLIX': 'Netflix', 'SPOTIFY': 'Spotify',
        'TARGET': 'Target', 'COSTCO': 'Costco', 'SHELL': 'Shell',
        'CHEVRON': 'Chevron', 'IN-N-OUT': 'In-N-Out', 'QT ': 'Qt', 
        'ARCO': 'Arco', 'EOS FITNESS': 'Eos Fitness', 'DISCORD': 'Discord',
        'COX': 'Cox', 'VERIZON': 'Verizon', 'SRP': 'Srp'
    }
    
    # 1. Check for keyword matches first
    for key, value in keyword_map.items():
        if key in desc:
            return value

    # 2. General cleanup if no keyword matched
    desc = re.sub(r'^(SQ\s*\*|TST\s*\*|PY\s*\*|SP\s*\*|TOAST\s*\*)\s*', '', desc) # Remove processors
    desc = desc.split(' - ')[0]  # Remove trailing dashes
    desc = desc.split(' #')[0]   # Remove store numbers
    desc = " ".join(desc.split()).title() # Fix capitalization and spaces
    return desc

def load_and_combine_csv_files(directory):
    """
    Loads Chase and Citi files, standardizing columns.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Data directory not found: {dir_path}")
        return pd.DataFrame()
    
    files_found = list(dir_path.glob("*.CSV")) + list(dir_path.glob("*.csv"))
    
    all_transactions = []
    for file in files_found:
        # Skip output files to avoid infinite loops
        if "2026_" in file.name:
            continue
            
        try:
            # Check for Citi format (often starts with "Time period...")
            with open(file, 'r') as f:
                first_line = f.readline()
            
            if "Time period" in first_line:
                # Citi Logic
                df = pd.read_csv(file, skiprows=1)
                df['Source'] = 'Citi'
                # Normalize Citi: Net = Debit - Credit
                df['Amount_Norm'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0) - \
                                   pd.to_numeric(df['Credit'], errors='coerce').fillna(0)
                df = df.rename(columns={'Date': 'Transaction Date'})
            else:
                # Chase Logic
                df = pd.read_csv(file)
                df['Source'] = 'Chase'
                # Normalize Chase: Net = Amount * -1 (Chase shows spending as negative)
                df['Amount_Norm'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0) * -1
            
            all_transactions.append(df)
            print(f"Loaded: {file.name}")
            
        except Exception as e:
            print(f"Error loading {file.name}: {e}")
    
    return pd.concat(all_transactions, ignore_index=True) if all_transactions else pd.DataFrame()

def map_category(row, category_map):
    """
    Applies category mapping with improved fallback logic.
    Priority:
    1. Exact match in category_map (loaded from CSV)
    2. Bank category fallback
    3. Special handling for Bills & Utilities
    4. Keyword matching in description
    5. Default to 'Personal'
    """
    key = (row['Clean_Description'], row['Category'])

    # 1. Exact match from external mapping file
    if key in category_map:
        return category_map[key]

    # 2. Bank category fallback
    bank_cat = row['Category']
    desc_lower = row['Clean_Description'].lower()
    if bank_cat in BANK_CATEGORY_FALLBACK:
        return BANK_CATEGORY_FALLBACK[bank_cat]

    # 3. Special handling for Bills & Utilities
    if bank_cat == 'Bills & Utilities':
        if any(kw in desc_lower for kw in ['electric', 'srp', 'power']):
            return 'Home Electricity'
        if any(kw in desc_lower for kw in ['water', 'trash', 'sewer', 'city of']):
            return 'Home Water/Trash'
        if any(kw in desc_lower for kw in ['internet', 'cox', 'wifi']):
            return 'Internet'
        if any(kw in desc_lower for kw in ['phone', 'verizon', 'mobile', 't-mobile']):
            return 'Phone Bill'

    # 4. Generic keyword fallback
    if 'gas' in desc_lower or 'fuel' in desc_lower:
        return 'Gas'
    if 'food' in desc_lower or 'restaurant' in desc_lower:
        return 'Restaurants'

    # 5. Default
    return 'Personal'

def main():
    print("--- Starting Budget Processing ---")

    # --- Cleanup Old Files ---
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
    
    # 1. Load Data
    raw_df = load_and_combine_csv_files(DATA_DIR)
    if raw_df.empty:
        print("No data found.")
        return

    # 2. Pre-process
    df = raw_df.copy()
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], format='mixed')
    df = df[df['Transaction Date'].dt.year == 2026].copy()
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    df['Net_Amount'] = df['Amount'] * -1

    df['Week'] = df['Transaction Date'].dt.isocalendar().week
    df['Month'] = df['Transaction Date'].dt.strftime('%B')
    df['Quarter'] = df['Transaction Date'].dt.quarter
    
    df['Clean_Description'] = df['Description'].apply(clean_merchant_name)
    df['Category'] = df['Category'].fillna('Uncategorized')
    df['Net_Amount'] = df['Amount_Norm']

    # 3. Apply Category Mapping
    # Filter out payments first so we don't map them
    payment_terms = ['PAYMENT THANK YOU', 'MOBILE PAYMENT', 'CREDIT CARD PYMT', 'AUTOPAY']
    is_payment = df['Description'].str.contains('|'.join(payment_terms), case=False, na=False)
    
    df_spending = df[~is_payment].copy()
    df_payments = df[is_payment].copy()
    
    # Keep only positive spending (money leaving account)
    df_spending = df_spending[df_spending['Net_Amount'] > 0].copy()
    
    # Load category mappings from external CSV (seeds on first run)
    category_map = load_category_mappings()

    # Apply the map
    df_spending['Budget_Category'] = df_spending.apply(
        lambda row: map_category(row, category_map), axis=1
    )

    # 4. Export
    output_cols = ['Transaction Date', 'Clean_Description', 'Category', 'Budget_Category', 'Net_Amount', 'Source', 'Month', 'Quarter', 'Week']
    df_spending[output_cols].to_csv(DATA_DIR / "2026_All_Transactions.csv", index=False)
    
    if not df_payments.empty:
        df_payments.to_csv(DATA_DIR / "2026_Credit_Card_Payments.csv", index=False)
        df_spending.groupby(['Week', 'Category'])['Net_Amount'].sum().unstack(fill_value=0).to_csv(DATA_DIR / "2026_Weekly_Summary.csv")
        df_spending.groupby(['Quarter', 'Category'])['Net_Amount'].sum().unstack(fill_value=0).to_csv(DATA_DIR / "2026_Quarterly_Summary.csv")

    print(f"✓ Success! Cleaned and processed {len(df_spending)} transactions.")


    print("-" * 30)
    print(f"✓ Processed {len(df_spending)} transactions.")
    print(f"✓ Total Spending: ${df_spending['Net_Amount'].sum():,.2f}")
    print("-" * 30)
    
    # Count unmapped merchants for user awareness
    unmapped = df_spending[df_spending['Budget_Category'] == 'Personal']
    unmapped_merchants = unmapped[['Clean_Description', 'Category']].drop_duplicates()
    if not unmapped_merchants.empty:
        print(f"\n{len(unmapped_merchants)} merchant(s) defaulted to 'Personal'.")
        print("Use the 'Manage Categories' tab in the dashboard to review and assign them.")

if __name__ == "__main__":
    main()