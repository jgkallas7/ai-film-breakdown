"""Score a gold-set test run against Coach's calls, and measure reader agreement.

    python3 -P score_gold.py <run_dir> [--label "baseline"] [--model fable-5-2] [--rules <note or hash>] [--no-log]

Per reader: front family (EVEN / ODD / TITE / BEAR), the exact line (offense left to right), 3 technique side, nose.
FAIR LINE = the exact line with one allowance: an end man on a side with no Y may be written 5 or 9 (Coach 11/09: that
call is gray, and the OPJ key was tagged before his wide-end rule). Judge rule changes on the fair line.
Pairs: how often two readers agree on family + line, and how accurate the agreed snaps are. That number decides how many
snaps could be auto-accepted without Coach. Appends one row to gold/score_log.csv and writes <run_dir>/misses.csv.
Always pass --model (which model the readers ran on): the same brief scores differently on a different model, and a
row without it can't be compared later. --no-log scores without touching the log (partial runs, rescoring by hand).
"""
import argparse, json, sys
from datetime import date
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gold_lib import summary, fair_seq  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('--label', default='')
ap.add_argument('--model', default='', help='model the readers ran on, e.g. fable-5-2')
ap.add_argument('--rules', default='', help='which shared rule files the readers saw (hash or note); default = manifest rules_sha')
ap.add_argument('--no-log', action='store_true', help='print the score, do not append to score_log.csv')
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
        g = G.loc[(j['game_id'], int(o['clip']))]
        s = summary(o.get('line') or [], o.get('front'), g.form)
        rows.append(dict(game_id=j['game_id'], clip=int(o['clip']), reader=j['reader'], conf=o.get('conf'),
                         r_family=s['family'], r_linefam=s['line_family'], r_seq=s['seq'], r_core=s['core'], r_three=s['three'], r_nose=s['nose'], r_fair=s['fair'], g_fair=fair_seq(g.gold_line, g.gold_family, g.form),
                         g_family=g.gold_family, g_seq=g.gold_seq, g_core=g.gold_core, g_three=g.gold_three, g_nose=g.gold_nose, g_group=g.gold_group))
R = pd.DataFrame(rows).drop_duplicates(['game_id', 'clip', 'reader'], keep='last')
if R.empty:
    sys.exit('no reads yet')
R['ok_family'] = R.r_family == R.g_family
R['ok_seq'] = R.r_seq == R.g_seq
R['ok_linefam'] = R.r_linefam == R.g_family
R['ok_core'] = R.r_core == R.g_core
R['ok_three'] = R.r_three == R.g_three
R['ok_nose'] = R.r_nose == R.g_nose
R['ok_all'] = R.ok_family & R.ok_seq
R['ok_fair'] = R.r_fair == R.g_fair          # exact line, but an end with no Y on his side may be 5 or 9 (Coach 11/09)
R['ok_fair_all'] = R.ok_family & R.ok_fair


def pct(s):
    return f'{s.mean():.0%} ({int(s.sum())}/{len(s)})'


print(f'{len(R)} reads on {R.groupby(["game_id", "clip"]).ngroups} snaps\n')
print('PER READ        family', pct(R.ok_family), '| exact line', pct(R.ok_seq), '| core (inside + count)', pct(R.ok_core), '| 3 tech side', pct(R.ok_three), '| nose', pct(R.ok_nose))
print('  FAIR LINE (exact, but an end with no Y on his side may be 5 or 9; Coach 11/09):', pct(R.ok_fair))
print('  family named by code from the LINE (gold_lib.line_family):', pct(R.ok_linefam), '| by the reader (front word):', pct(R.ok_family))
for c, g in R.groupby(R.conf.fillna('?')):
    print(f'  conf {c}: exact line {pct(g.ok_seq)}')
print('\nBy Coach front group (exact line):')
print(R.groupby('g_group')[['ok_family', 'ok_core', 'ok_seq']].mean().round(2).to_string())

# agreement between readers on the same snap
P = R.pivot_table(index=['game_id', 'clip'], columns='reader', values=['r_family', 'r_seq', 'r_core', 'r_fair', 'ok_all', 'ok_core', 'ok_fair_all'], aggfunc='first')
agree = acc_agree = fam_agree = fam_acc = fair_agree = fair_acc = None
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
    samefr = (both[('r_fair', rs[0])] == both[('r_fair', rs[1])]) & (both[('r_family', rs[0])] == both[('r_family', rs[1])])
    fair_agree = samefr.mean()
    fair_acc = both[samefr][('ok_fair_all', rs[0])].astype(bool).mean() if samefr.any() else float('nan')
    print(f'  FAIR LINE: agree on {fair_agree:.0%} ({int(samefr.sum())}); right when they agree {fair_acc:.0%}')
    samef = both[('r_family', rs[0])] == both[('r_family', rs[1])]
    okf = R[R.reader == rs[0]].set_index(['game_id', 'clip']).ok_family.reindex(both.index).astype(bool)
    fam_agree = samef.mean()
    fam_acc = okf[samef].mean() if samef.any() else float('nan')
    print(f'  FAMILY: agree on {fam_agree:.0%} ({int(samef.sum())}); right when they agree {fam_acc:.0%} ({int(okf[samef].sum())}/{int(samef.sum())})')

R[~R.ok_fair_all].sort_values(['game_id', 'clip', 'reader']).to_csv(run / 'misses_fair.csv', index=False)
R[~R.ok_all].sort_values(['game_id', 'clip', 'reader']).to_csv(run / 'misses.csv', index=False)
if a.no_log:
    print('\nmisses ->', run / 'misses.csv', '| log not touched (--no-log)')
    sys.exit(0)
log = HERE / 'score_log.csv'
r3 = lambda v: None if v is None or v != v else round(v, 3)
row = pd.DataFrame([{'date': date.today().isoformat(), 'label': a.label, 'run': run.name, 'seed': M['seed'], 'brief': M['brief_sha'],
                     'reads': len(R), 'family': round(R.ok_family.mean(), 3), 'exact_line': round(R.ok_seq.mean(), 3), 'core': round(R.ok_core.mean(), 3),
                     'three_side': round(R.ok_three.mean(), 3), 'nose': round(R.ok_nose.mean(), 3),
                     'agree': r3(agree), 'acc_when_agree': r3(acc_agree),
                     'family_from_line': round(R.ok_linefam.mean(), 3), 'fam_agree': r3(fam_agree), 'fam_acc_when_agree': r3(fam_acc),
                     'model': a.model, 'rules': a.rules or M.get('rules_sha', ''),
                     'line_fair': round(R.ok_fair.mean(), 3), 'fair_agree': r3(fair_agree), 'fair_acc_when_agree': r3(fair_acc)}])
# older rows have fewer columns: rewrite the whole log so every row lines up under one header
old = pd.read_csv(log, dtype=str) if log.exists() else pd.DataFrame()
pd.concat([old, row.astype(object)], ignore_index=True).to_csv(log, index=False)
print('\nmisses ->', run / 'misses.csv', '| log ->', log)
