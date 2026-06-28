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
    "Pest control", "Landscaping", "Games", "Vacation", "Personal"
]

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
TRANSFER_KEYWORDS = [
    'TRANSFER', 'PAYMENT TO CHASE CARD', 'ONLINE TRANSFER',
    'SAVE AS YOU GO', 'ZELLE'
]
INCOME_SOURCE_MAP = {
    'DIRECT DEP': 'Payroll', 'PAYROLL': 'Payroll',
    'ACH CREDIT': 'ACH Credit', 'DEPOSIT': 'Deposit',
}

# --- Payment Detection ---
PAYMENT_TERMS = ['PAYMENT THANK YOU', 'MOBILE PAYMENT', 'CREDIT CARD PYMT', 'AUTOPAY']

# --- Transaction Notes ---
DEFAULT_TAGS = [
    "Tax Deductible", "Reimbursable", "Gift", "Business", "Impulse Buy", "Split Cost"
]
