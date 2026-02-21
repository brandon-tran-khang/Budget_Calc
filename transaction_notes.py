import pandas as pd

import config


def generate_tx_key(date, merchant, amount):
    """Build a unique-ish key from date, merchant, and amount.

    Format: ``2024-01-15::Starbucks::5.25``
    """
    date_str = pd.Timestamp(date).strftime("%Y-%m-%d") if not isinstance(date, str) else date
    return f"{date_str}::{merchant}::{amount}"


def add_tx_keys(df):
    """Add a ``_tx_key`` column to a transactions DataFrame.

    Keys include an occurrence index to handle duplicate transactions
    (e.g., two $5.25 Starbucks charges on the same day) — keys become
    ``2024-01-15::Starbucks::5.25::0``, ``...::1``, etc.
    """
    df = df.copy()
    base_key = df.apply(
        lambda r: generate_tx_key(r["Transaction Date"], r["Clean_Description"], r["Net_Amount"]),
        axis=1,
    )
    occurrence = base_key.groupby(base_key).cumcount()
    df["_tx_key"] = base_key + "::" + occurrence.astype(str)
    return df


def load_notes():
    """Read ``transaction_notes.csv`` and return a DataFrame with ``[_tx_key, Note, Tags]``.

    Migrates old 3-part keys (``date::merchant::amount``) to 4-part format
    (``date::merchant::amount::0``) for backward compatibility.
    """
    if not config.NOTES_FILE.exists():
        return pd.DataFrame(columns=["_tx_key", "Note", "Tags"])
    try:
        df = pd.read_csv(config.NOTES_FILE, dtype=str).fillna("")
        for col in ("_tx_key", "Note", "Tags"):
            if col not in df.columns:
                df[col] = ""
        # Migrate old 3-part keys → 4-part by appending ::0
        mask = df["_tx_key"].str.count("::") == 2
        df.loc[mask, "_tx_key"] = df.loc[mask, "_tx_key"] + "::0"
        return df[["_tx_key", "Note", "Tags"]]
    except (pd.errors.EmptyDataError, Exception):
        return pd.DataFrame(columns=["_tx_key", "Note", "Tags"])


def save_notes(notes_df):
    """Persist notes/tags to CSV. Only keeps rows that have actual content.

    Uses atomic write (temp file + rename) to prevent corruption on crash.
    """
    df = notes_df.copy()
    df["Note"] = df["Note"].fillna("").astype(str).str.strip()
    df["Tags"] = df["Tags"].fillna("").astype(str).str.strip()

    # Drop rows with no content
    df = df[~((df["Note"] == "") & (df["Tags"] == ""))]

    # Deduplicate — keep last entry per key
    df = df.drop_duplicates(subset=["_tx_key"], keep="last")

    # Atomic write: write to temp file, then rename
    tmp_file = config.NOTES_FILE.with_suffix(".csv.tmp")
    df[["_tx_key", "Note", "Tags"]].to_csv(tmp_file, index=False)
    tmp_file.replace(config.NOTES_FILE)


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
    combined = set(config.DEFAULT_TAGS) | custom_tags
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
    if "Tags" not in df.columns or "Net_Amount" not in df.columns:
        return {}

    tagged = df[df["Tags"].fillna("").str.strip().ne("")][["Tags", "Net_Amount"]].copy()
    if tagged.empty:
        return {}

    # Vectorized: split tags, explode to one row per tag, then groupby sum
    tagged["Tags"] = tagged["Tags"].str.split(",")
    exploded = tagged.explode("Tags")
    exploded["Tags"] = exploded["Tags"].str.strip()
    exploded = exploded[exploded["Tags"].ne("")]
    return exploded.groupby("Tags")["Net_Amount"].sum().to_dict()
