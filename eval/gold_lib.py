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


END = ('5', '7', '6', '9')


def y_sides(form):
    """Sides (offense's 'L' / 'R') where a Y gives the end man something to line up on. LT / RT in our formation names
    is the Y side (Coach 10/18). No Y near the tackle: DOUBLE and TRIPS (spread), EMPTY / QUAD, an unnamed set, and a
    BULL / BEAR Y (he sits in a guard-tackle gap). TWINS names the receivers, so the Y is opposite. DOUBLE DICE has two."""
    f = str(form or '').upper()
    side = 'L' if re.search(r'\bLT\b', f) else 'R' if re.search(r'\bRT\b', f) else None
    if 'DOUBLE DICE' in f or 'DOUBLE TIGHT' in f:
        return {'L', 'R'}
    if re.search(r'\b(BULL|BEAR)\b', f) or re.match(r'\s*(DOUBLE|TRIPS|EMPTY|QUAD|2X2)\b', f) or side is None:
        return set()
    if f.lstrip().startswith('TWINS'):
        return {'R' if side == 'L' else 'L'}
    return {side}


def fair_seq(line, family=None, form=None):
    """The exact line, except that the end man on a side with NO Y reads 'E' whether he was written 5, 7, 6 or 9.
    Coach 11/09: with no tight end the 5-or-9 call on a wide end is gray (the gaps are not uniform; "a wide 5 with no
    tight end is a 9"), so two people who see the same man can write either. On a Y side the number still has to match
    (5 / 7 / 6 / 9 by width). Everyone inside the ends has to match exactly, and so does the count."""
    _, P = canon(line, family)
    ys = y_sides(form)
    pts = sorted((ORDER[t] * (0 if sd == 'M' else (-1 if sd == 'L' else 1)), t, sd) for t, sd, _ in P)
    out = [t for _, t, _ in pts]
    if pts and pts[0][2] == 'L' and 'L' not in ys and out[0] in END:
        out[0] = 'E'
    if len(pts) > 1 and pts[-1][2] == 'R' and 'R' not in ys and out[-1] in END:
        out[-1] = 'E'
    return '-'.join(out)


def summary(line, front, form=None):
    fam0 = family(front, None)
    seq, P = canon(line, fam0)
    fam = family(front, seq)
    return {'family': fam, 'seq': seq, 'core': core(seq), 'n_line': len(P), 'three': three(P), 'nose': nose(P),
            'line_family': line_family(P)[0], 'fair': fair_seq(line, fam0, form)}


GUARD = ('2i', '2', '3')


def line_family(P):
    """Front family from the line alone: Coach's COUNT rule plus the two names the alignment decides.
    P = parsed line [(tech, side, stance), ...]. Returns (family, check): check is True when the line can't settle it
    and Coach has to look (4 on the line with a 0 nose is EVEN by count, but a 0 with a walked-up backer is ODD:
    OPA 100, Coach 10/10).

    - BEAR = the center and both guards covered (0 or a 1, plus a 2i / 2 / 3 on each guard), whatever the count.
    - TITE = 3 on the line, a 0 or shaded 1, and a 4i or 4 on both tackles (the ENDS define it, Coach 10/16).
    - else the count: 4 or 6 = EVEN, 3 or 5 = ODD.
    Readers name techniques; this names the family, so the same line always gets the same family."""
    t = [p[0] for p in P]
    n = len(t)
    center = any(x in ('0', '1') for x in t)
    if center and all(any(x in GUARD and sd == s for x, sd, _ in P) for s in ('L', 'R')):
        return 'BEAR', False
    if n == 3 and center and sum(x in ('4i', '4') for x in t) == 2:
        return 'TITE', False
    if n in (4, 6):
        return 'EVEN', '0' in t
    if n in (3, 5):
        return 'ODD', False
    return None, True
