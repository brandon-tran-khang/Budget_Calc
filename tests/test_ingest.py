"""Synthetic-data tests for ingest.py (no real bank data)."""
import pandas as pd

from ingest import classify_file, coverage_warnings, drop_superseded, intake, pending_files

CARD = 'Card,Transaction Date,Post Date,Description,Category,Type,Amount,Memo\n'
CHECKING = 'Details,Posting Date,Description,Amount,Type,Balance,Check or Slip #\n'
CITI = 'Status,Date,Description,Debit,Credit\n'


def mk(file, rows, source='Chase'):
    return pd.DataFrame({'_file': file, 'Source': source,
                         'Transaction Date': [r[0] for r in rows],
                         'Description': [r[1] for r in rows],
                         'Amount_Norm': [float(r[2]) for r in rows]})


def run(*frames):
    out, src = drop_superseded(pd.concat(frames, ignore_index=True))
    return out, src.set_index('File')


def test_reexport_not_double_counted():
    old = mk('Chase1111_old.csv', [('2024-01-05', 'A', 1), ('2024-01-20', 'B', 2),
                                   ('2024-02-10', 'C', 3), ('2024-03-20', 'D', 4)])
    new = mk('Chase1111_new.csv', [('2024-02-01', 'E', 5), ('2024-02-10', 'C', 3),
                                   ('2024-03-20', 'D', 4), ('2024-04-10', 'F', 6)])
    out, src = run(old, new)
    assert sorted(out['Description']) == list('ABCDEF')
    assert src.loc['Chase1111_old.csv', 'Rows_Used'] == 2
    assert src.loc['Chase1111_new.csv', 'Rows_Used'] == 4
    assert '_file' not in out.columns


def test_identical_purchases_survive():
    old = mk('Chase1111_old.csv', [('2024-01-05', 'COFFEE', 3)] * 2 + [('2024-01-06', 'Z', 1)])
    new = mk('Chase1111_new.csv', [('2024-02-01', 'LUNCH', 9)] * 2 + [('2024-03-01', 'Y', 1)])
    out, _ = run(old, new)
    assert (out['Description'] == 'COFFEE').sum() == 2
    assert (out['Description'] == 'LUNCH').sum() == 2


def test_pending_to_posted_not_duplicated():
    old = mk('Chase1111_old.csv', [('2024-03-01', 'A', 1), ('2024-03-30', 'PENDING X', 10)])
    new = mk('Chase1111_new.csv', [('2024-03-01', 'A', 1), ('2024-04-01', 'X', 10),
                                   ('2024-04-10', 'B', 2)])
    out, _ = run(old, new)
    assert 'PENDING X' not in set(out['Description'])
    assert (out['Description'] == 'X').sum() == 1


def _overlap_frames(n_match):
    old = [('2024-01-10', f'JAN{i}', 1) for i in range(2)]
    old += [('2024-02-%02d' % (i + 1), f'S{i}' if i < n_match else f'OLD{i}', i + 1) for i in range(12)]
    new = [('2024-02-%02d' % (i + 1), f'S{i}', i + 1) for i in range(12)] + [('2024-03-01', 'LAST', 1)]
    return mk('Chase2222_old.csv', old), mk('Chase3333_new.csv', new)


def test_account_merge(capsys):
    out, src = run(*_overlap_frames(12))
    assert set(src['Account']) == {'3333'}
    assert len(out) == 2 + 13  # old Jan rows kept, overlap not doubled
    assert 'merged account 2222 into 3333 (12/12' in capsys.readouterr().out


def test_no_merge_when_few_rows_match():
    old, new = _overlap_frames(2)
    out, src = run(old, new)
    assert set(src['Account']) == {'2222', '3333'}
    assert len(out) == len(old) + len(new)
    # too few rows in the overlap (<10) also blocks a merge
    out, src = run(old.head(4), new)
    assert set(src['Account']) == {'2222', '3333'} and len(out) == 4 + len(new)


def test_citi_never_merged_with_chase():
    rows = [('2024-02-%02d' % (i + 1), f'S{i}', i + 1) for i in range(12)]
    out, src = run(mk('Chase1111_a.csv', rows), mk('Citi_ytd.CSV', rows, source='Citi'))
    assert len(out) == 24
    assert set(src['Account']) == {'1111', 'Citi'}


def test_classify_file(tmp_path):
    def f(name, text):
        p = tmp_path / name
        p.write_bytes(text if isinstance(text, bytes) else text.encode())
        return p
    assert classify_file(f('a.csv', CARD + '1,2,3\n')) == 'card'
    assert classify_file(f('b.csv', '﻿' + CITI)) == 'card'
    assert classify_file(f('c.csv', 'Time period: Jan\n' + CITI)) == 'card'
    assert classify_file(f('d.csv', CHECKING)) == 'checking'
    assert classify_file(f('e.csv', 'Description,Assigned\nx,y\n')) is None
    assert classify_file(f('g.csv', b'\x00\xff\xfe\x80\x81')) is None
    assert classify_file(tmp_path / 'missing.csv') is None


def test_intake(tmp_path):
    inbox, data, ck = tmp_path / 'Inbox', tmp_path / 'Data', tmp_path / 'Data' / 'Checking'
    inbox.mkdir()
    (inbox / 'x.csv').write_text(CARD + 'row1\n')
    (inbox / 'Y.CSV').write_text(CITI + 'row\n')
    (inbox / 'z.csv').write_text(CHECKING + 'row\n')
    (inbox / 'junk.csv').write_text('a,b\n1,2\n')
    lines = intake(inbox, data, ck)
    assert (data / 'x.csv').exists() and (data / 'Y.CSV').exists() and (ck / 'z.csv').exists()
    assert (inbox / 'junk.csv').exists() and not (inbox / 'x.csv').exists()
    assert sum(l.startswith('WARNING') and 'junk.csv' in l for l in lines) == 1
    # second run: nothing moves, listing unchanged
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob('*'))
    assert not [l for l in intake(inbox, data, ck) if l.startswith('moved')]
    assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob('*')) == before
    # byte-identical re-drop is removed; different content gets _2
    (inbox / 'x.csv').write_text(CARD + 'row1\n')
    assert intake(inbox, data, ck) == ['WARNING junk.csv: unrecognized format, left in ' + str(inbox),
                                       'already imported: x.csv']
    assert not (inbox / 'x.csv').exists()
    (inbox / 'x.csv').write_text(CARD + 'different\n')
    intake(inbox, data, ck)
    assert (data / 'x_2.csv').read_text().endswith('different\n')


def test_intake_skips_data_dir(tmp_path):
    (tmp_path / 'x.csv').write_text(CARD)
    assert intake(tmp_path, tmp_path, tmp_path / 'Checking') == []


def _src(*rows):
    return pd.DataFrame(rows, columns=['Account', 'Source', 'File', 'First', 'Last',
                                       'Rows_In_File', 'Rows_Used'])


def test_coverage_warnings():
    gap = _src(('Citi', 'Citi', 'a', '2026-01-01', '2026-06-28', 5, 5),
               ('Citi', 'Citi', 'b', '2026-10-24', '2026-11-09', 5, 5))
    assert coverage_warnings(gap) == ['Citi: no data 2026-06-29..2026-10-23 (117 days)']
    stale = _src(('1111', 'Chase', 'a', '2026-01-01', '2026-03-01', 5, 5),
                 ('2222', 'Chase', 'b', '2026-01-01', '2026-11-01', 5, 5))
    assert coverage_warnings(stale) == ['1111: last transaction 2026-03-01, 245 days behind']
    ok = _src(('1111', 'Chase', 'a', '2026-01-01', '2026-06-01', 5, 5),
              ('1111', 'Chase', 'b', '2026-05-01', '2026-11-01', 5, 5),
              ('1111', 'Chase', 'c', '2026-11-02', '2026-11-05', 5, 5))
    assert coverage_warnings(ok) == []
    assert coverage_warnings(_src()) == []


def test_pending_files(tmp_path):
    inbox = tmp_path / 'Inbox'
    assert pending_files(inbox) == ([], [])  # missing inbox
    inbox.mkdir()
    assert pending_files(inbox) == ([], [])  # empty inbox
    (inbox / 'a.csv').write_text(CARD)
    (inbox / 'B.CSV').write_text(CHECKING)
    (inbox / 'junk.csv').write_text('a,b\n')
    (inbox / 'notes.txt').write_text(CARD)
    (inbox / 'sub').mkdir()
    assert pending_files(inbox) == ([inbox / 'B.CSV', inbox / 'a.csv'], [inbox / 'junk.csv'])
