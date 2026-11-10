#!/usr/bin/env python3
"""Shell and coverage calls two blind readers agree on, as film-room suggestions for Coach to confirm.

Coach 11/09: pre-fill agreed coverage calls for him to confirm. Nothing here is a tag: the film room shows
each one as a suggestion and saves it only when he taps it. Nothing from this file goes into the Hudl import
or a report.

Per clip (only clips that exactly two readers read):
  rs   agreed pre-snap shell: '2' / '1' / '0' / '3'
  rc   one-tap coverage suggestion, ONLY the two calls the readers have earned:
         '4' = both wrote Cover 4 and both had a 2-high shell
         '0' = both wrote Cover 0 and both had nobody deep
  rcq  any other coverage both wrote (e.g. 'Cover 3'): shown as a question with no button

Why only 4 and 0 (OPQ defense in the OPA game, Coach's blind chart, gold/score_opa.py): when both readers wrote
Cover 4 or Cover 0 they matched Coach 24 of 24 (October) and 11 of 11 (11/09, same snaps as October's chunk c).
When both wrote anything else they were 0 of 2 and 0 of 1 (clips 101, 130). Every reader's coverage call
followed his own shell call, so an agreed call is "two readers saw the same shell", not a read of the rotation.
OPQ played Cover 4 on about 4 of 5 charted snaps; on a team that rotates, expect the 4 / 0 number to drop.
Re-score it against Coach's calls each opponent before trusting it.

usage: python3 -I agreed_calls.py reads/x_a.jsonl reads/x_b.jsonl [more.jsonl ...] [--out agreed.json]
  The film-room builder merges the JSON into each snap:  sn.update(agreed.get(str(clip), {}))
"""
import collections
import json
import re
import sys


def shell_of(d):
    v = d.get('shell_pre') or (d.get('def') or {}).get('shell') or d.get('shell')
    v = str(v or '').lower()
    m = re.match(r'\s*([0-3])\b', v)
    return m.group(1) if m else None


def cov_of(d):
    """A clear call only. 'other: 1-high (Cover 3 or Cover 1)' and 'unclear (possible Cover 4)' are not calls."""
    v = d.get('coverage') or (d.get('def') or {}).get('coverage')
    m = re.fullmatch(r'\s*cover\s*([0-9])\s*', str(v or '').lower())
    return m.group(1) if m else None


def main(argv):
    out, paths = None, []
    it = iter(argv)
    for a in it:
        if a == '--out':
            out = next(it)
        else:
            paths.append(a)
    if len(paths) < 2:
        raise SystemExit(__doc__)
    by = collections.defaultdict(list)
    for p in paths:
        for ln in open(p, encoding='utf-8-sig'):
            ln = ln.strip()
            if not ln:
                continue
            d = json.loads(ln)
            if d.get('snap') is False or d.get('clip') is None:
                continue
            by[int(d['clip'])].append(d)
    res, n = {}, collections.Counter()
    for clip in sorted(by):
        rd = by[clip]
        if len(rd) != 2:
            n['not two readers'] += 1
            continue
        s1, s2 = shell_of(rd[0]), shell_of(rd[1])
        c1, c2 = cov_of(rd[0]), cov_of(rd[1])
        row = {}
        if s1 and s1 == s2:
            row['rs'] = s1
        if c1 and c1 == c2:
            if s1 == s2 and (c1, s1) in (('4', '2'), ('0', '0')):
                row['rc'] = c1
            else:
                row['rcq'] = 'Cover ' + c1
        if row:
            res[str(clip)] = row
        n['shell agreed' if 'rs' in row else 'shell split / none'] += 1
        n['coverage one-tap (4 / 0)' if 'rc' in row else 'coverage question' if 'rcq' in row else 'coverage: no agreed call'] += 1
    for clip, row in res.items():
        print(f"{clip:>4}  shell {row.get('rs', '-'):>2}  one-tap {row.get('rc', '-'):>2}  question {row.get('rcq', '-')}")
    print()
    for k, v in sorted(n.items()):
        print(f'{v:>4}  {k}')
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=1)
        print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1:])
