"""Shared configuration — single source of truth for constants used across modules."""

from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "Data"
CHECKING_DIR = DATA_DIR / "Checking"
MAPPINGS_FILE = BASE_DIR / "category_mappings.csv"
NOTES_FILE = BASE_DIR / "transaction_notes.csv"

# --- Budget Categories ---
BUDGET_CATEGORIES = [
    "Home Electricity", "Home Water/Trash", "Home Furniture", "Internet",
    "Phone Bill", "HOA Bill", "Home Maintenance", "Car Registration",
    "Discord Subscription", "Spotify Subscription", "Amazon Prime Subscription",
    "Gym Membership", "Chase Sapphire Preferred Fee", "Costco Membership",
    "Groceries", "Gas", "Restaurants", "Health / Doctors", "Car Maintenance",
    "Pest control", "Landscaping", "Games", "Vacation", "Personal", "Investments"
]

# Brokerage/robo-advisor deposits from checking -> 'Investments' (still counted as spending;
# the sidebar "Include Investments" toggle hides them).
INVESTMENT_KEYWORDS = ['SCHWAB BROKERAGE', 'WEALTHFRONT']

# --- Month Names ---
MONTH_NAMES = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
}

# --- Bank Category Fallback ---
BANK_CATEGORY_FALLBACK = {
    'Food & Drink': 'Restaurants',
    'Vehicle Services': 'Gas',
    'Health & Wellness': 'Health / Doctors',
    'Groceries': 'Groceries',
    'Home': 'Home Furniture',
    'Travel': 'Vacation',
    'Automotive': 'Car Maintenance',
}

# --- Checking Account Classification ---
INCOME_KEYWORDS = ['DIRECT DEP', 'PAYROLL', 'ACH CREDIT', 'DEPOSIT']
# Zelle/Venmo/Cash App are NOT transfers: incoming lands in income so the Reimbursements tab
# can offset it against spending; outgoing is an expense (paying someone).
TRANSFER_KEYWORDS = [
    'TRANSFER', 'PAYMENT TO CHASE CARD', 'CITI CARD ONLINE PAYMENT', 'ONLINE TRANSFER',
    'SAVE AS YOU GO'
]
P2P_KEYWORDS = ['ZELLE', 'VENMO', 'CASH APP']
# Checked in order; P2P first so "ZELLE ... DEPOSIT" isn't labelled a plain Deposit.
INCOME_SOURCE_MAP = {
    'ZELLE': 'P2P Transfer', 'VENMO': 'P2P Transfer', 'CASH APP': 'P2P Transfer',
    'DIRECT DEP': 'Payroll', 'PAYROLL': 'Payroll',
    'ACH CREDIT': 'ACH Credit', 'DEPOSIT': 'Deposit',
}

# --- Payment Detection ---
# 'PAYMENT, THANK YOU' is Citi's wording ("ONLINE PAYMENT, THANK YOU").
PAYMENT_TERMS = ['PAYMENT THANK YOU', 'PAYMENT, THANK YOU', 'MOBILE PAYMENT', 'CREDIT CARD PYMT', 'AUTOPAY']

# User-state files that live in DATA_DIR but are not bank exports.
REIMBURSEMENTS_FILE = DATA_DIR / "zelle_assignments.csv"

# --- Transaction Notes ---
DEFAULT_TAGS = [
    "Tax Deductible", "Reimbursable", "Gift", "Business", "Impulse Buy", "Split Cost"
]
