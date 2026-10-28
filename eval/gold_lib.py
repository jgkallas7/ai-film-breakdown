"""Shared helpers for the gold-set test: parse a line of techniques, put it in the offense's left-to-right order,
and compare a reader's front with Coach's.

A "line" is a list like ["5 L hand #45", "3 L hand #88", "2i R hand #52", "5 R hand"] (offense's L / R / M).
"""
import ast
import re

ORDER = {'0': 0, '1': .6, '2i': .75, '2': 1.2, '3': 1.65, '4i': 1.95, '4': 2.4, '5': 2.85, '7': 3.15, '6': 3.6, '9': 4.05}


def parse(t):
    s = re.sub(r'^\s*wide\s+', '', str(t), flags=re.I)
    s = re.sub(r'^\s*0/1\b', '0', s)
    s = re.sub(r'^\s*(\d)i?/(\d)', r'\2', s)                 # "4/5", "7/9" -> the outside one
    m = re.match(r'\s*(\d i|\di|\d)\s+([LRM])\b\s*(hand|stand|crouch)?', s.replace('2 i', '2i'))
    if m:
        return m.group(1).replace(' ', ''), m.group(2), 'stand' if m.group(3) == 'stand' else 'hand'
    m = re.match(r'\s*0\b\s*(hand|stand)?', s)
    return ('0', 'M', m.group(1) or 'hand') if m else None


def as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip().startswith('['):
        return ast.literal_eval(v)
    return []


def canon(line, family=None):
    """Offense left-to-right tech sequence, e.g. '5-3-2i-5'. An ODD/TITE front with a 4th standing 0/6/7/9 drops him
    (he's a walked-up LB / OLB, not on the line) - Coach's rule used in the report."""
    P = [p for p in (parse(t) for t in as_list(line)) if p and p[0] in ORDER]
    if family in ('ODD', 'TITE') and len(P) == 4:
        P = [p for p in P if not (p[2] == 'stand' and p[0] in ('0', '6', '7', '9'))] or P
    if family in ('ODD', None) and len(P) == 3:            # Coach 10/19: 3 on the line, a 2i / 2 nose = the shade nose 1
        P = [('1', sd, st) if t in ('2i', '2') else (t, sd, st) for t, sd, st in P]
    pts = sorted((ORDER[t] * (0 if sd == 'M' else (-1 if sd == 'L' else 1)), t) for t, sd, _ in P)
    return '-'.join(t for _, t in pts), P


def core(seq):
    """Inside techniques + line count; the end men (5 / 6 / 7 / 9) all read 'E', 4 and 4i both '4'. A 'core' match
    is the call a coach cares about (where the 3 and the nose are, how many on the line), without the 5-vs-7 edge split."""
    out = []
    for t in seq.split('-') if seq else []:
        out.append('E' if t in ('5', '6', '7', '9') else '4' if t in ('4', '4i') else t)
    return '-'.join(out)


def family(front, seq):
    f = str(front or '').upper()
    if f.startswith('BEAR') or f.startswith('GOAL'):
        return 'BEAR'
    if f.startswith('TITE') or seq == '4i-0-4i':
        return 'TITE'
    if f.startswith('EVEN'):
        return 'EVEN'
    if f.startswith('ODD'):
        return 'ODD'
    n = len(seq.split('-')) if seq else 0
    return {4: 'EVEN', 3: 'ODD', 5: 'ODD'}.get(n)


def three(P):
    s = [sd for t, sd, _ in P if t == '3']
    return 'both' if len(s) >= 2 else (s[0] if s else 'none')


def nose(P):
    inside = sorted(P, key=lambda p: ORDER[p[0]])
    return inside[0][0] if inside else None


def summary(line, front):
    fam0 = family(front, None)
    seq, P = canon(line, fam0)
    fam = family(front, seq)
    return {'family': fam, 'seq': seq, 'core': core(seq), 'n_line': len(P), 'three': three(P), 'nose': nose(P)}
