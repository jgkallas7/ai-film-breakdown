"""Set up one gold-set test run: pick snaps, pull only their clips from the zips, make strips, write reader prompts.

    python3 -P make_gold_test.py <run_dir> [--n 24] [--per 12] [--readers 2] [--seed 1] [--game opj_stce,opj_scn]

- Picks n snaps spread across Coach's front groups (seeded, so the same seed = the same snaps; compare briefs on the
  same snaps).
- Every chunk of `per` snaps gets `readers` independent prompts (same snaps, separate readers), so the score shows both
  accuracy and how often two readers agree.
- Film goes to <run_dir>/<game_id>/ (keep run_dir in the session scratchpad, never a synced folder).
- Writes <run_dir>/manifest.json and <run_dir>/prompts/<job>.md. Launch one reader agent per prompt (effort xhigh),
  then run score_gold.py <run_dir>.
"""
import argparse, json, re, subprocess, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import imageio_ffmpeg
import pandas as pd
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
FILM = HERE.parents[3] / 'Hudl Data' / 'Game Film 2026'
FF = imageio_ffmpeg.get_ffmpeg_exe()
ap = argparse.ArgumentParser()
ap.add_argument('run'); ap.add_argument('--n', type=int, default=24); ap.add_argument('--per', type=int, default=12)
ap.add_argument('--readers', type=int, default=2); ap.add_argument('--seed', type=int, default=1); ap.add_argument('--game')
ap.add_argument('--snaps-from', help='manifest.json of an earlier run: reuse exactly its snaps (compare briefs fairly)')
a = ap.parse_args()
run = Path(a.run); run.mkdir(parents=True, exist_ok=True)

G = pd.read_csv(HERE / 'gold_fronts.csv')
if a.game:
    G = G[G.game_id.isin(a.game.split(','))]
G = G[G.set_t.notna()]
# Blind test: drop every snap the readers' rule files quote as an example ("OPK 7 and 111", "OPL 72").
RULES = [HERE.parent / 'front_brief.md', HERE / 'front_test_brief.md',
         HERE.parents[3] / 'library' / '00_standards' / 'defensive_front_definitions.md']
named = set()
for f in RULES:
    txt = f.read_text()
    for m in re.finditer(r'\b([A-Z]{2,5})\s+((?:\d{1,3}(?:\s*(?:,|and|/)\s*)?)+)', txt):
        for n in re.findall(r'\d{1,3}', m.group(2)):
            named.add((m.group(1).lower(), int(n)))
code = G.game_id.str.split('_').str[-1]
leak = [(c, k) in named for c, k in zip(code, G['clip'])]
print('left out (quoted in the rules):', sorted(f'{c} {k}' for (c, k), l in zip(zip(code, G['clip']), leak) if l))
G = G[[not l for l in leak]]
# spread across front groups: round-robin over groups in a seeded order
groups = [g.sample(frac=1, random_state=a.seed) for _, g in G.groupby('gold_group')]
pick, k = [], 0
while len(pick) < min(a.n, len(G)):
    g = groups[k % len(groups)]
    i = len([p for p in pick if p['gold_group'] == g.gold_group.iloc[0]])
    if i < len(g):
        pick.append(g.iloc[i].to_dict())
    k += 1
    if k > 10000:
        break
S = pd.DataFrame(pick).sort_values(['game_id', 'clip']).reset_index(drop=True)
if a.snaps_from:
    keep = {(x['game_id'], int(x['clip'])) for x in json.load(open(a.snaps_from))['snaps']}
    bad = keep & {(c, k) for c, k in named} if False else set()
    S = G[[(g, int(c)) in keep for g, c in zip(G.game_id, G['clip'])]].sort_values(['game_id', 'clip']).reset_index(drop=True)
    if len(S) != len(keep):
        raise SystemExit(f'{len(keep) - len(S)} reused snaps are now quoted in the rules (would leak); pick other examples')


def extract(args):
    gid, zipname, clip = args
    work = run / gid
    with zipfile.ZipFile(FILM / zipname) as zf:
        for n in zf.namelist():
            m = re.match(r'^(?:.*/)?(.+?) - Clip (\d+)\.mp4$', n)
            if m and int(m.group(2)) == clip:
                ang = m.group(1).lower().replace(' ', '')
                dst = work / ang / f'Clip {clip:03d}.mp4'
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(n) as src, open(dst, 'wb') as f:
                        while b := src.read(1 << 22):
                            f.write(b)
                strip(work, ang, clip)


def strip(work, ang, c):
    mp4 = work / ang / f'Clip {c:03d}.mp4'
    outd = work / 'strips' / ang
    outd.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([FF, '-v', 'error', '-i', str(mp4), '-vf', 'fps=2,scale=480:-1', f'{td}/f%03d.jpg'], check=True)
        tiles = []
        for i, f in enumerate(sorted(Path(td).glob('f*.jpg'))):
            im = Image.open(f).convert('RGB')
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 110, 22), fill=(0, 0, 0))
            d.text((4, 4), f'#{c} t={i * 0.5:.1f}s', fill=(255, 255, 0))
            tiles.append(im)
    if tiles:
        tw, th = tiles[0].size
        sheet = Image.new('RGB', (tw * 4, th * (-(-len(tiles) // 4))))
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % 4) * tw, (i // 4) * th))
        sheet.save(outd / f'c{c:03d}.jpg', quality=80)


with ThreadPoolExecutor(6) as ex:
    list(ex.map(extract, [(r.game_id, r.zip, int(r.clip)) for r in S.itertuples()]))

brief = (HERE / 'front_test_brief.md').read_text()
(run / 'tools').mkdir(exist_ok=True)                 # readers get the grab tool here, never the gold folder (answer key)
(run / 'tools' / 'grab_gold.py').write_text((HERE / 'grab_gold.py').read_text())
import shutil
shutil.copytree(HERE / 'examples', run / 'tools' / 'examples', dirs_exist_ok=True)
(run / 'prompts').mkdir(exist_ok=True)
(run / 'reads').mkdir(exist_ok=True)
jobs = []
for gid, gg in S.groupby('game_id'):
    rows = gg.to_dict('records')
    nch = -(-len(rows) // a.per)
    size = -(-len(rows) // nch)                      # even chunks (14 snaps at per 12 -> 7 + 7)
    chunks = [rows[i:i + size] for i in range(0, len(rows), size)]
    for ci, ch in enumerate(chunks):
        snaps = '; '.join(f"{int(r['clip'])}: {r['set_t']} / {r['set_t_wide']} / {r['cam_hint']}" for r in ch)
        for rd in range(a.readers):
            name = f'{gid}_{ci}_{"ABCDEFG"[rd]}'
            fill = {'{team}': ch[0]['team'], '{team_desc}': ch[0]['team_desc'], '{opp}': ch[0]['opp'], '{work}': str(run / gid),
                    '{gold}': str(run / 'tools'), '{examples}': str(run / 'tools' / 'examples'), '{snaps}': snaps, '{out}': str(run / 'reads' / f'{name}.jsonl')}
            p = brief
            for k2, v in fill.items():
                p = p.replace(k2, v)
            (run / 'prompts' / f'{name}.md').write_text(p)
            jobs.append({'name': name, 'game_id': gid, 'reader': 'ABCDEFG'[rd], 'clips': [int(r['clip']) for r in ch],
                         'prompt': str(run / 'prompts' / f'{name}.md'), 'out': str(run / 'reads' / f'{name}.jsonl')})
json.dump({'seed': a.seed, 'brief_sha': __import__('hashlib').sha1(brief.encode()).hexdigest()[:10], 'jobs': jobs,
           'snaps': S[['game_id', 'clip', 'gold_group']].to_dict('records')}, open(run / 'manifest.json', 'w'), indent=1)
print(len(S), 'snaps |', S.gold_group.value_counts().to_dict())
print(len(jobs), 'reader jobs ->', run / 'prompts')
