"""Drop-folder intake and overlap handling for bank exports. No streamlit; pandas + stdlib only."""
import filecmp
import re
import shutil
from collections import Counter
from itertools import count
from pathlib import Path

import pandas as pd

SOURCE_COLS = ['Account', 'Source', 'File', 'First', 'Last', 'Rows_In_File', 'Rows_Used']


def classify_file(path):
    """Return 'card', 'checking' or None, from the header line (never the filename)."""
    try:
        with open(path, encoding='utf-8-sig', errors='replace') as f:
            head = f.readline()
            if 'Time period' in head:
                head = f.readline()
    except OSError:
        return None
    if head.startswith('Details,Posting Date'):
        return 'checking'
    if all(w in head for w in ('Debit', 'Credit', 'Date')) or all(
            w in head for w in ('Transaction Date', 'Description', 'Amount')):
        return 'card'
    return None


def pending_files(inbox):
    """Return (recognized, unrecognized) CSVs sitting directly in inbox; read-only."""
    inbox = Path(inbox)
    csvs = sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() == '.csv') if inbox.is_dir() else []
    kinds = [(p, classify_file(p)) for p in csvs]
    return [p for p, k in kinds if k], [p for p, k in kinds if not k]


def intake(inbox, data_dir, checking_dir):
    """Move recognized CSVs from inbox into data_dir/checking_dir; return the printed lines."""
    inbox, data_dir, checking_dir = Path(inbox), Path(data_dir), Path(checking_dir)
    if inbox.resolve() in (data_dir.resolve(), checking_dir.resolve()):
        return []
    inbox.mkdir(parents=True, exist_ok=True)
    lines = []
    for p in sorted(inbox.iterdir()):
        if not p.is_file() or p.suffix.lower() != '.csv':
            continue
        kind = classify_file(p)
        if kind is None:
            lines.append(f'WARNING {p.name}: unrecognized format, left in {inbox}')
            continue
        dest = checking_dir if kind == 'checking' else data_dir
        for n in count(1):
            t = dest / (p.name if n == 1 else f'{p.stem}_{n}{p.suffix}')
            if not t.exists():
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), t)
                lines.append(f'moved {p.name} -> {t}')
                break
            if filecmp.cmp(p, t, shallow=False):
                p.unlink()
                lines.append(f'already imported: {p.name}')
                break
    for line in lines:
        print(line)
    return lines


def _account(file, source):
    m = re.search(r'Chase(\d{4})', file)
    return 'Citi' if source == 'Citi' else m.group(1) if m else Path(file).stem


def drop_superseded(df):
    """Newest export wins inside its own date span; older files keep only dates outside it.

    shortcut: a pending row whose date moves across the newer file's start boundary is
    counted twice; fine for full exports (boundary is years back), revisit for short partial ones.
    """
    if df.empty:
        return df, pd.DataFrame(columns=SOURCE_COLS)
    d = df.reset_index(drop=True)
    d = d.assign(_d=pd.to_datetime(d['Transaction Date'], format='mixed').dt.normalize())
    d['_acct'] = [_account(f, s) for f, s in zip(d['_file'], d['Source'])]
    d['_k'] = list(zip(d['_d'], d['Description'], d['Amount_Norm'].round(2)))

    # Account merge: a reissued card whose rows overlap the newer card's span almost 1:1.
    for src in d['Source'].unique():
        m = d['Source'] == src
        for old in d[m].groupby('_acct')['_d'].max().sort_values().index:
            acc = d[m].groupby('_acct')['_d'].agg(['min', 'max']).sort_values('max')
            if old not in acc.index:
                continue
            for new, r in acc[acc['max'] > acc.loc[old, 'max']].iterrows():
                o = d[m & (d['_acct'] == old) & d['_d'].between(r['min'], r['max'])]
                if len(o) < 10:
                    continue
                pool, hit = Counter(d.loc[m & (d['_acct'] == new), '_k']), 0
                for k in o['_k']:
                    if pool[k] > 0:
                        pool[k] -= 1
                        hit += 1
                if hit >= 0.9 * len(o):
                    print(f'merged account {old} into {new} ({hit}/{len(o)} overlapping rows match)')
                    d.loc[m & (d['_acct'] == old), '_acct'] = new
                    break

    keep, rows = pd.Series(True, index=d.index), []
    for acct, g in d.groupby('_acct'):
        files = g.groupby('_file').agg(lo=('_d', 'min'), hi=('_d', 'max'), n=('_d', 'size'),
                                       src=('Source', 'first')).reset_index()
        files = files.sort_values(['hi', 'n', '_file'], ascending=False)
        spans = []
        for f, lo, hi, n, src in files[['_file', 'lo', 'hi', 'n', 'src']].itertuples(index=False, name=None):
            idx = g.index[g['_file'] == f]
            for s_lo, s_hi in spans:
                keep[idx[d.loc[idx, '_d'].between(s_lo, s_hi).to_numpy()]] = False
            spans.append((lo, hi))
            rows.append((acct, src, f, lo, hi, n, int(keep[idx].sum())))
    sources = pd.DataFrame(rows, columns=SOURCE_COLS).sort_values(['Account', 'First'], ignore_index=True)
    return d[keep].drop(columns=['_file', '_d', '_acct', '_k']), sources


def coverage_warnings(sources, gap_days=7, stale_days=30):
    """Per-account gaps between files and accounts whose data stops well before the newest export."""
    if sources.empty:
        return []
    s = sources.assign(First=pd.to_datetime(sources['First']), Last=pd.to_datetime(sources['Last']))
    through, out = s['Last'].max(), []
    for acct, g in s.groupby('Account'):
        run = None
        for first, last in g.sort_values('First')[['First', 'Last']].itertuples(index=False, name=None):
            if run is not None and (first - (run + pd.Timedelta(days=1))).days > gap_days:
                a, b = run + pd.Timedelta(days=1), first - pd.Timedelta(days=1)
                out.append(f'{acct}: no data {a:%Y-%m-%d}..{b:%Y-%m-%d} ({(b - a).days + 1} days)')
            run = last if run is None else max(run, last)
        if (through - run).days > stale_days:
            out.append(f'{acct}: last transaction {run:%Y-%m-%d}, {(through - run).days} days behind')
    return out
