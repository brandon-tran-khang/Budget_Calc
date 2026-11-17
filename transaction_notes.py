import pandas as pd

import config


def generate_tx_key(date, merchant, amount):
    """Build a unique-ish key from date, merchant, and amount.

    Format: ``2024-01-15::Starbucks::5.25`` (amount always 2 decimals).
    """
    date_str = pd.Timestamp(date).strftime("%Y-%m-%d") if not isinstance(date, str) else date
    return f"{date_str}::{merchant}::{float(amount):.2f}"


def add_tx_keys(df):
    """Add a ``_tx_key`` column to a transactions DataFrame.

    Keys include an occurrence index to handle duplicate transactions
    (e.g., two $5.25 Starbucks charges on the same day) — keys become
    ``2024-01-15::Starbucks::5.25::0``, ``...::1``, etc. Duplicates are
    numbered after a stable sort on Source/account_type/Category, so the
    keys don't depend on input row order.
    """
    df = df.copy()
    base_key = df.apply(
        lambda r: generate_tx_key(r["Transaction Date"], r["Clean_Description"], r["Net_Amount"]),
        axis=1,
    )
    tie = [c for c in ("Source", "account_type", "Category") if c in df.columns]
    pos = pd.DataFrame({"k": base_key.to_numpy()}).join(df[tie].reset_index(drop=True))
    occurrence = pos.sort_values(["k"] + tie, kind="stable").groupby("k").cumcount().sort_index()
    df["_tx_key"] = base_key + "::" + occurrence.astype(str).to_numpy()
    return df


def _normalize_amount(key):
    """Rewrite the amount segment of a 4-part key to 2 decimals; leave non-numeric ones alone."""
    parts = key.rsplit("::", 2)
    if len(parts) < 3:
        return key
    try:
        parts[1] = f"{float(parts[1]):.2f}"
    except ValueError:
        return key
    return "::".join(parts)


def load_notes():
    """Read ``transaction_notes.csv`` and return a DataFrame with ``[_tx_key, Note, Tags]``.

    Migrates old 3-part keys (``date::merchant::amount``) to 4-part format
    (``date::merchant::amount::0``) and rewrites old repr amounts (``12.5``)
    to 2 decimals (``12.50``) for backward compatibility. Does not write the file.
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
        df["_tx_key"] = df["_tx_key"].map(_normalize_amount)
        return df[["_tx_key", "Note", "Tags"]]
    except pd.errors.EmptyDataError:
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


def count_changed_notes(before, after):
    """Count rows whose Note or Tags differ; None, NaN and '' count as equal."""
    cols = ["Note", "Tags"]
    b = before[cols].fillna("").astype(str)
    a = after[cols].fillna("").astype(str)
    return int((b != a).any(axis=1).sum())


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
