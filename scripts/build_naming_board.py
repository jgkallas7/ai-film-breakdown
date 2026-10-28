"""Group snaps by measured front alignment -> data for the naming board page (Coach names each group).

    python3 build_naming_board.py <scout_folder> <workdir> --reads "reads/front_*.jsonl" --title "OPA Front Board" \
        --import <import.xlsx> --outdir <scratch>/board

Each reader line has `techs` like ["5 L stand","3 L hand","1 R hand","5 R hand"] (offense's L/R) and off_form_seen
("DICE LT"). Techs are rewritten strength-relative (S = strength side, W = weak), so mirrored looks group together;
DOUBLE (no Y) and unknown strength fall back to the RB-away side, else screen L/R.
Writes <outdir>/board.json + <outdir>/img/cNNN_set.jpg / cNNN_strip.jpg (960 px) for publishing beside the page.
"""
import argparse, glob, json, re
from collections import defaultdict
from pathlib import Path
import pandas as pd
from PIL import Image

ORDER = {"0": 0, "1": 1, "2i": 2, "2": 3, "3": 4, "4i": 5, "4": 6, "5": 7, "7/9": 8, "7": 8, "9": 9, "wide": 10}


def parse(t):
    p = t.replace("-", " ").split()
    tech = p[0]
    side = next((x for x in p[1:] if x in ("L", "R")), "")
    stance = "hand" if "hand" in t else "stand" if "stand" in t else "?"
    return tech, side, stance


def strength(form):
    m = re.search(r"\b(LT|RT)\b", str(form or "").upper())
    return m.group(1)[0] if m else None


def key_of(techs, form):
    s = strength(form)
    out = []
    for t in techs:
        if t == "partial":
            continue
        tech, side, stance = parse(t)
        rel = "" if tech == "0" else ("S" if side == s else "W") if s else side
        out.append((rel, tech, stance))
    # weak side first, outside-in; then 0; then strong side inside-out
    w = sorted([x for x in out if x[0] in ("W", "L")], key=lambda x: -ORDER.get(x[1], 5))
    z = [x for x in out if x[0] == ""]
    st = sorted([x for x in out if x[0] in ("S", "R")], key=lambda x: ORDER.get(x[1], 5))
    seq = w + z + st
    return " · ".join(f"{r}{t}{'' if st_ == 'hand' else '(up)'}" for r, t, st_ in seq), seq, bool(s)


def coarse(seq, has_s):
    """Group on what defines the front, not noise: count on the line, 0 nose, which side the shade (1/2i)
    and the guard tech (2/3/4i) are on (Over vs Under), which side the standup end is on, and a wide 9.
    Readers' techs are only good to about one gap, and hand/stand flips in fog, so exact strings over-split."""
    n = len(seq)
    if not n:
        return "unreadable", "Unreadable"
    side = lambda xs: "/".join(sorted({r for r, _, _ in xs})) or "-"
    shade = [x for x in seq if x[1] in ("1", "2i")]
    guard = [x for x in seq if x[1] in ("2", "3", "4i")]
    ups = [x for x in seq if x[2] == "stand"]
    nine = any(x[1] in ("7/9", "7", "9", "wide") for x in seq)
    nose0 = any(x[1] == "0" for x in seq)
    S, W = ("strength", "weak") if has_s else ("R", "L")
    nm = lambda r: {"S": S, "W": W, "L": "L", "R": "R"}.get(r, r)
    parts = [f"{n} on the line"]
    if nose0:
        parts.append("0 nose")
    if shade:
        parts.append("shade to " + " & ".join(nm(r) for r in side(shade).split("/")))
    if guard:
        parts.append("3-tech to " + " & ".join(nm(r) for r in side(guard).split("/")))

    # standup side and the wide 9 flip between readers' clips on the same look, so they stay in the label/table
    # but don't split groups. The group is the count + nose + shade/3-tech orientation (Over vs Under).
    key = (n, nose0, side(shade), side(guard), has_s)
    return str(key), ", ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder"); ap.add_argument("work")
    ap.add_argument("--reads", default="reads/front_*.jsonl"); ap.add_argument("--title", default="Front Board")
    ap.add_argument("--import", dest="imp"); ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    folder, work, out = Path(a.folder), Path(a.work), Path(a.outdir)
    (out / "img").mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for f in sorted(glob.glob(str(folder / a.reads))) for l in open(f) if l.strip()]
    imp = pd.read_excel(folder / a.imp).set_index("PLAY #") if a.imp else None
    groups = defaultdict(list)
    for r in rows:
        techs = r.get("techs") or []
        exact, seq, has_s = key_of(techs, r.get("off_form_seen"))
        k, label = coarse(seq, has_s)
        groups[k].append((r, seq, has_s, label, exact))
    G = []
    for i, (k, items) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1])), 1):
        snaps = []
        for r, seq, has_s, label, exact in items:
            c = int(r["clip"])
            for kind in ("set", "strip"):
                src = work / "cv" / f"c{c:03d}_{kind}.jpg"
                if src.exists():
                    im = Image.open(src); im.thumbnail((960, 960)); im.save(out / "img" / f"c{c:03d}_{kind}.jpg", quality=78)
            dd = None
            if imp is not None and c in imp.index:
                x = imp.loc[c]
                if pd.notna(x.get("DN")):
                    dd = f"{int(x['DN'])}&{int(x['DIST'])}"
                gain = x.get("GN/LS")
                res = f"{x.get('PLAY TYPE', '')} {'' if pd.isna(gain) else int(gain)}".strip()
            else:
                res = ""
            snaps.append({"clip": c, "exact": exact, "form": r.get("off_form_seen"), "dd": dd, "res": res, "front": r.get("front"),
                          "edge": r.get("edge_play"), "lbs": r.get("lbs"), "box": r.get("box"),
                          "pressure": r.get("pressure"), "conf": r.get("conf"), "note": r.get("note")})
        seq = items[0][1]
        n_line = len(seq)
        G.append({"id": f"g{i:02d}", "key": items[0][3], "n": len(items), "on_line": n_line,
                  "rule_front": ("EVEN" if n_line % 2 == 0 else "ODD") if n_line else None,
                  "nose0": any(t == "0" for _, t, _ in seq),
                  "diagram": [{"side": s_, "tech": t, "stance": st} for s_, t, st in seq],
                  "strength_known": items[0][2], "snaps": sorted(snaps, key=lambda s: s["clip"])})
    (out / "board.json").write_text(json.dumps({"title": a.title, "groups": G}, indent=1))
    print(f"{len(rows)} snaps -> {len(G)} groups")
    for g in G:
        print(f"  {g['id']} n={g['n']:>2} {g['rule_front'] or '-':<5} {g['key']}")


if __name__ == "__main__":
    main()
