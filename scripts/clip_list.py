"""Short clip lists for Coach's [C] / [R->C] scout questions: the 8-12 snaps that best show each one.

    python3 -P clip_list.py <week_report.csv> <out.md> [--assist code=breakdown.xlsx ...] [--q 10,15,17,18] [--n 10]

Picks by facts only (play type, run direction vs the hash, down & distance, shell, formation) plus reader notes as a
hint of where something happened (a reader flagged a rotation, a walked-up backer, a safety fit). Readers never make the
call here: Coach watches the list and answers the question. Spread across formations and both directions so one look
doesn't fill the list. Clip numbers = Hudl PLAY #, so Coach can jump to them in Hudl.
"""
import argparse, re
from pathlib import Path
import pandas as pd

QUESTIONS = {
    3: 'Do they stem or move the DL before the snap? From what to what?',
    10: 'How do the LBs fit our runs (fast flow, scrape, spill or box)?',
    14: 'Rotation at the snap (sky, buzz, cloud): to the field, the trips, or the boundary?',
    15: 'Who forces the run, and how fast do the safeties fill?',
    17: 'How aggressive are the corners in press and on quick game? Eyes on the receiver or the QB?',
    18: 'Do they blitz or sim? When, from where, and what coverage is behind it?',
}
DB_QS = {14, 15, 17}                                 # need the secondary in the wide frame
NOTE_COLS = ['disguise', 'rotation', 'rushers', 'safety_fit', 'what_broke', 'lbs', 'read', 'mreact', 'motion', 'cov_ev']


def txt(r):
    return ' '.join(str(r.get(c, '')) for c in NOTE_COLS if isinstance(r.get(c), str)).lower()


def run_dir_vs_field(r):
    d, h = r.get('play_dir'), r.get('hash')
    if d not in ('L', 'R') or h not in ('L', 'R'):
        return 'middle'
    return 'boundary' if d == h else 'field'            # hash L = boundary on the offense's left


def score(q, r):
    t, run, pas = txt(r), r.get('rp') == 'Run', r.get('rp') == 'Pass'
    dn, dist, ytg = r.get('dn') or 0, r.get('dist') or 0, r.get('ytg') or 50
    gl = ytg <= 4
    s, why = 0, []
    if q == 10 and run and not gl:
        s += 3; why.append('run')
        if r.get('box', 0) >= 6: s += 1
        if re.search(r'scrap|fast flow|flowed|spill|squeez|filled|fit (?:the|inside|outside)|overran|cut back', t): s += 2; why.append('reader noted the LB fit')
    elif q == 15 and run and not gl:
        s += 2; why.append(f"run to the {run_dir_vs_field(r)}")
        if run_dir_vs_field(r) == 'field': s += 1
        if (r.get('gain') or 0) >= 5: s += 2; why.append('got to the second level')
        if re.search(r'alley|force|safety (?:fit|came|fill|tackl|down)|#12 (?:fit|came|tackl)', t): s += 2; why.append('reader saw a safety in the fit')
    elif q == 17 and pas:
        s += 2; why.append('pass')
        if (r.get('gain') or 0) <= 8: s += 1; why.append('short / quick')
        if re.search(r'press|bail|squat|corner|cb', t): s += 2; why.append('reader noted the corner')
    elif q == 14 and pas and str(r.get('shell', '')).startswith('2'):
        s += 2; why.append('pass vs 2-high')
        if re.search(r'rotat|sky|buzz|cloud|roll|spin|walked down|slid', t): s += 3; why.append('reader saw movement in the shell')
        if r.get('fam') in ('TRIPS', 'TREY', 'TRIO', 'TRIBE'): s += 1; why.append('3x1')
    elif q == 18:
        if pas and dn >= 3 and dist >= 6: s += 3; why.append('3rd & 6+ pass')
        elif pas: s += 1
        if r.get('pressure') is True or re.search(r'blitz|came|green|creep|mug|walked up|bluff|sim|pressure', t):
            s += 3; why.append('reader flagged a pressure look')
        if ytg <= 20: s += 1; why.append('red zone')
    elif q == 3:
        if re.search(r'stem|slant|stunt|twist|angle|shift|moved|walked|backed off|creep', t): s += 4; why.append('reader noted DL movement')
        if run: s += 1
    return s, '; '.join(why)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv'); ap.add_argument('out')
    ap.add_argument('--assist', nargs='*', default=[]); ap.add_argument('--q', default='10,15,17,18'); ap.add_argument('--n', type=int, default=10)
    ap.add_argument('--no-secondary', default='', help='games whose wide camera cuts off the DBs (e.g. opl): left out of DB questions')
    a = ap.parse_args()
    D = pd.read_csv(a.csv)
    D['play_dir'] = None
    for spec in a.assist:
        code, path = spec.split('=', 1)
        B = pd.read_excel(path)[['PLAY #', 'PLAY DIR']].rename(columns={'PLAY #': 'clip', 'PLAY DIR': 'pd'})
        m = D['code'] == code
        D.loc[m, 'play_dir'] = D.loc[m, 'clip'].map(dict(zip(B['clip'], B['pd'])))
    out = [f'# Clip lists ({Path(a.csv).resolve().parents[2].name})', '',
           'Picked by play type, direction, down & distance, shell and formation, with reader notes only as a hint of where '
           'to look. Watch each list and write the answer; nothing here is a call.', '']
    for q in [int(x) for x in a.q.split(',')]:
        rows = []
        for r in D.to_dict('records'):
            s, why = score(q, r)
            if s > 0:
                rows.append((s, r, why))
        if q in DB_QS:
            rows = [x for x in rows if x[1]['code'] not in a.no_secondary.split(',')]
        rows.sort(key=lambda x: -x[0])
        # ties: alternate games so one game can't fill the list
        order, k = [], {}
        for s, r, why in rows:
            k[r['code']] = k.get(r['code'], 0) + 1
            order.append((-s, k[r['code']], s, r, why))
        rows = [(s, r, why) for _, _, s, r, why in sorted(order, key=lambda x: (x[0], x[1]))]
        pick, seen = [], {}
        for s, r, why in rows:                          # at most 3 per formation family, so one look can't fill the list
            f = r.get('fam') or '?'
            if seen.get(f, 0) >= 3:
                continue
            seen[f] = seen.get(f, 0) + 1
            pick.append((r, why))
            if len(pick) >= a.n:
                break
        out += [f'## Q{q}. {QUESTIONS.get(q, "")}', '', '| Game | Clip | Down | Formation | Front | Play | Why this clip |', '|---|---|---|---|---|---|---|']
        for r, why in sorted(pick, key=lambda x: (x[0]['game'], x[0]['clip'])):
            dd = f"{int(r['dn'])} & {int(r['dist'])}" if pd.notna(r.get('dn')) and pd.notna(r.get('dist')) else ''
            out.append(f"| {r['game']} | {int(r['clip'])} | {dd} | {r.get('form') or ''} | {r.get('fname') or ''} | {r.get('rp') or ''} | {why} |")
        out += ['', 'Answer:', '', '']
    Path(a.out).write_text('\n'.join(out))
    print('wrote', a.out)


if __name__ == '__main__':
    main()
