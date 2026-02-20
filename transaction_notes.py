import pandas as pd
from pathlib import Path


NOTES_FILE = Path(__file__).resolve().parent / "transaction_notes.csv"

DEFAULT_TAGS = [
    "Tax Deductible", "Reimbursable", "Gift", "Business", "Impulse Buy", "Split Cost"
]


def generate_tx_key(date, merchant, amount):
    """Build a unique-ish key from date, merchant, and amount.

    Format: ``2024-01-15::Starbucks::5.25``
    """
    date_str = pd.Timestamp(date).strftime("%Y-%m-%d") if not isinstance(date, str) else date
    return f"{date_str}::{merchant}::{amount}"


def add_tx_keys(df):
    """Add a ``_tx_key`` column to a transactions DataFrame."""
    df = df.copy()
    df["_tx_key"] = df.apply(
        lambda r: generate_tx_key(r["Transaction Date"], r["Clean_Description"], r["Net_Amount"]),
        axis=1,
    )
    return df


def load_notes():
    """Read ``transaction_notes.csv`` and return a DataFrame with ``[_tx_key, Note, Tags]``."""
    if not NOTES_FILE.exists():
        return pd.DataFrame(columns=["_tx_key", "Note", "Tags"])
    try:
        df = pd.read_csv(NOTES_FILE, dtype=str).fillna("")
        for col in ("_tx_key", "Note", "Tags"):
            if col not in df.columns:
                df[col] = ""
        return df[["_tx_key", "Note", "Tags"]]
    except (pd.errors.EmptyDataError, Exception):
        return pd.DataFrame(columns=["_tx_key", "Note", "Tags"])


def save_notes(notes_df):
    """Persist notes/tags to CSV. Only keeps rows that have actual content."""
    df = notes_df.copy()
    df["Note"] = df["Note"].fillna("").astype(str).str.strip()
    df["Tags"] = df["Tags"].fillna("").astype(str).str.strip()

    # Drop rows with no content
    df = df[~((df["Note"] == "") & (df["Tags"] == ""))]

    # Deduplicate — keep last entry per key
    df = df.drop_duplicates(subset=["_tx_key"], keep="last")

    df[["_tx_key", "Note", "Tags"]].to_csv(NOTES_FILE, index=False)


def merge_notes(df, notes_df):
    """Left-join notes/tags onto a keyed transactions DataFrame."""
    if notes_df.empty:
        df = df.copy()
        if "Note" not in df.columns:
            df["Note"] = ""
        if "Tags" not in df.columns:
            df["Tags"] = ""
        return df

    # Avoid column collisions on repeated merges
    for col in ("Note", "Tags"):
        if col in df.columns:
            df = df.drop(columns=[col])

    merged = df.merge(notes_df[["_tx_key", "Note", "Tags"]], on="_tx_key", how="left")
    merged["Note"] = merged["Note"].fillna("")
    merged["Tags"] = merged["Tags"].fillna("")
    return merged


def get_all_tags(notes_df):
    """Extract all unique tags that appear in the data."""
    if notes_df.empty or "Tags" not in notes_df.columns:
        return set()
    all_tags = set()
    for tag_str in notes_df["Tags"].dropna():
        for tag in str(tag_str).split(","):
            tag = tag.strip()
            if tag:
                all_tags.add(tag)
    return all_tags


def get_available_tags(notes_df):
    """Return combined default tags + any custom tags from data, sorted."""
    custom_tags = get_all_tags(notes_df)
    combined = set(DEFAULT_TAGS) | custom_tags
    return sorted(combined)


def filter_by_tags(df, selected_tags):
    """Filter DataFrame to rows that have ANY of the selected tags."""
    if not selected_tags or "Tags" not in df.columns:
        return df

    selected = set(selected_tags)

    def has_tag(tag_str):
        if not isinstance(tag_str, str) or not tag_str.strip():
            return False
        row_tags = {t.strip() for t in tag_str.split(",")}
        return bool(row_tags & selected)

    return df[df["Tags"].apply(has_tag)].copy()


def compute_tag_totals(df):
    """Return ``{tag_name: total_amount}`` for all tags in the DataFrame."""
    totals = {}
    if "Tags" not in df.columns or "Net_Amount" not in df.columns:
        return totals

    for _, row in df.iterrows():
        tag_str = row.get("Tags", "")
        if not isinstance(tag_str, str) or not tag_str.strip():
            continue
        for tag in tag_str.split(","):
            tag = tag.strip()
            if tag:
                totals[tag] = totals.get(tag, 0) + row["Net_Amount"]

    return totals
