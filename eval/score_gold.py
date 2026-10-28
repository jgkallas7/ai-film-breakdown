"""Score a gold-set test run against Coach's calls, and measure reader agreement.

    python3 -P score_gold.py <run_dir> [--label "baseline"]

Per reader: front family (EVEN / ODD / TITE / BEAR), the exact line (offense left to right), 3 technique side, nose.
Pairs: how often two readers agree on family + line, and how accurate the agreed snaps are. That number decides how many
snaps could be auto-accepted without Coach. Appends one row to gold/score_log.csv and writes <run_dir>/misses.csv.
"""
import argparse, json, sys
from datetime import date
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gold_lib import summary  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('--label', default='')
a = ap.parse_args()
run = Path(a.run)
M = json.load(open(run / 'manifest.json'))
G = pd.read_csv(HERE / 'gold_fronts.csv').set_index(['game_id', 'clip'])

rows = []
for j in M['jobs']:
    p = Path(j['out'])
    if not p.exists():
        continue
    for line in p.read_text().splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if 'clip' not in o or int(o['clip']) not in j['clips']:
            continue
        s = summary(o.get('line') or [], o.get('front'))
        g = G.loc[(j['game_id'], int(o['clip']))]
        rows.append(dict(game_id=j['game_id'], clip=int(o['clip']), reader=j['reader'], conf=o.get('conf'),
                         r_family=s['family'], r_seq=s['seq'], r_core=s['core'], r_three=s['three'], r_nose=s['nose'],
                         g_family=g.gold_family, g_seq=g.gold_seq, g_core=g.gold_core, g_three=g.gold_three, g_nose=g.gold_nose, g_group=g.gold_group))
R = pd.DataFrame(rows).drop_duplicates(['game_id', 'clip', 'reader'], keep='last')
if R.empty:
    sys.exit('no reads yet')
R['ok_family'] = R.r_family == R.g_family
R['ok_seq'] = R.r_seq == R.g_seq
R['ok_core'] = R.r_core == R.g_core
R['ok_three'] = R.r_three == R.g_three
R['ok_nose'] = R.r_nose == R.g_nose
R['ok_all'] = R.ok_family & R.ok_seq


def pct(s):
    return f'{s.mean():.0%} ({int(s.sum())}/{len(s)})'


print(f'{len(R)} reads on {R.groupby(["game_id", "clip"]).ngroups} snaps\n')
print('PER READ        family', pct(R.ok_family), '| exact line', pct(R.ok_seq), '| core (inside + count)', pct(R.ok_core), '| 3 tech side', pct(R.ok_three), '| nose', pct(R.ok_nose))
for c, g in R.groupby(R.conf.fillna('?')):
    print(f'  conf {c}: exact line {pct(g.ok_seq)}')
print('\nBy Coach front group (exact line):')
print(R.groupby('g_group')[['ok_family', 'ok_core', 'ok_seq']].mean().round(2).to_string())

# agreement between readers on the same snap
P = R.pivot_table(index=['game_id', 'clip'], columns='reader', values=['r_family', 'r_seq', 'r_core', 'ok_all', 'ok_core'], aggfunc='first')
agree = acc_agree = None
if P.columns.get_level_values(1).nunique() >= 2:
    rs = sorted(P.columns.get_level_values(1).unique())[:2]
    both = P.dropna(subset=[('r_seq', rs[0]), ('r_seq', rs[1])])
    same = (both[('r_seq', rs[0])] == both[('r_seq', rs[1])]) & (both[('r_family', rs[0])] == both[('r_family', rs[1])])
    agree = same.mean()
    acc_agree = both[same][('ok_all', rs[0])].astype(bool).mean() if same.any() else float('nan')
    acc_dis = both[~same][[('ok_all', rs[0]), ('ok_all', rs[1])]].astype(bool).any(axis=1).mean() if (~same).any() else float('nan')
    print(f'\nAGREEMENT  readers {rs[0]}+{rs[1]} agree on {agree:.0%} of {len(both)} snaps ({int(same.sum())})')
    print(f'  when they agree, they are right {acc_agree:.0%}  -> these could be auto-accepted')
    print(f'  when they disagree ({int((~same).sum())} snaps), at least one is right {acc_dis:.0%}  -> these go to Coach')
    samec = (both[('r_core', rs[0])] == both[('r_core', rs[1])]) & (both[('r_family', rs[0])] == both[('r_family', rs[1])])
    accc = both[samec][('ok_core', rs[0])].astype(bool).mean() if samec.any() else float('nan')
    print(f'  CORE: agree on {samec.mean():.0%} ({int(samec.sum())}); right when they agree {accc:.0%}')

R[~R.ok_all].sort_values(['game_id', 'clip', 'reader']).to_csv(run / 'misses.csv', index=False)
log = HERE / 'score_log.csv'
row = pd.DataFrame([{'date': date.today().isoformat(), 'label': a.label, 'run': run.name, 'seed': M['seed'], 'brief': M['brief_sha'],
                     'reads': len(R), 'family': round(R.ok_family.mean(), 3), 'exact_line': round(R.ok_seq.mean(), 3), 'core': round(R.ok_core.mean(), 3),
                     'three_side': round(R.ok_three.mean(), 3), 'nose': round(R.ok_nose.mean(), 3),
                     'agree': None if agree is None else round(agree, 3), 'acc_when_agree': None if acc_agree is None else round(acc_agree, 3)}])
row.to_csv(log, mode='a', header=not log.exists(), index=False)
print('\nmisses ->', run / 'misses.csv', '| log ->', log)
