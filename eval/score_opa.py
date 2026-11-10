#!/usr/bin/env python3
"""Second graded set: shell, blitz, coverage and the line, scored against a chart Coach made blind.

    python3 -P score_opa.py <chart.json> <reads_dir> [--prefix opa_] [--csv out.csv]

The answer key is Coach's own charting of 49 snaps (OPQ's defense against OPA, charted 11/01 without
seeing any reader output): 60_scout_gameplans/2026_wk12_opq/scout/data/filmroom2_chart_v261101c.json.
`gold_fronts.csv` only grades fronts; this is the only set that grades what readers say about the secondary.
Reader files: <reads_dir>/<prefix>{a1,a2,b1,b2,c1,c2}.jsonl (reader_brief.md format); the two readers of a chunk are
the pair for that chunk's snaps. Never show the chart, or this folder, to a reader. See README.md for the numbers.
"""
import json, re, sys, glob, os, collections, csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gold_lib import parse, ORDER  # noqa: E402  (same line parsing and left-to-right ordering as score_gold.py)

LADDER = ["0", "1", "2i", "2", "3", "4i", "4", "5", "7", "6", "9"]
IDX = {t: i for i, t in enumerate(LADDER)}


def tech(s):
    m = re.match(r"\s*(\d+i?)", str(s).lower())
    return m.group(1) if m else None


def coach_line(s):
    return [t.lower() for t in str(s).split("-")] if s else []


FLIPPED = []


def reader_line(row):
    """Techniques left to right from the offense. Each entry carries its own side ("5 R hand"), and the order comes
    from those sides, not from the order of the list: readers working off a behind-the-defense frame (mirrored) often
    write the list right-to-left with every side label correct. Entries without a side keep the order they were
    written in."""
    ents = [e for e in (row.get("line") or []) if tech(e)]
    listed = [tech(e) for e in ents]
    P = [parse(e) for e in ents]
    if not P or any(p is None or p[0] not in ORDER for p in P):
        return listed
    out = [t for _, _, t in sorted((ORDER[t] * (0 if sd == "M" else (-1 if sd == "L" else 1)), i, t)
                                   for i, (t, sd, _) in enumerate(P))]
    if out == listed[::-1] and out != listed and row.get("clip") not in FLIPPED:
        FLIPPED.append(row.get("clip"))
    return out


def shell_of(row):
    m = re.match(r"\s*(\d)", str(row.get("shell_pre") or ""))
    return m.group(1) if m else None


def cov_of(row):
    c = str(row.get("coverage") or "").lower()
    m = re.search(r"cover\s*(\d)", c)
    if m and "/" not in c and " or " not in c and "?" not in c:
        return m.group(1)
    return None  # run / other / hedged


def blitz_of(row):
    p = str(row.get("pressure") or "").lower()
    if p.startswith("blitz") or p.startswith("sim"):
        return True
    if p.startswith("none") or p.startswith("stunt"):
        return False
    r = row.get("rushers")
    return bool(isinstance(r, (int, float)) and r >= 5)


def coach_blitz(d):
    return d.get("rush") == "pressure" or bool(d.get("blitz"))


def interior(line):
    """DTs = everything but the two ends (first and last)."""
    return line[1:-1] if len(line) >= 3 else []


def three_side(line):
    """L / R / both / None from a left-to-right line."""
    n = len(line)
    idx = [i for i, t in enumerate(line) if t == "3"]
    if not idx:
        return None
    sides = {("L" if i < n / 2 else "R") for i in idx}
    return "both" if len(sides) == 2 else sides.pop()


def main():
    chart = json.load(open(sys.argv[1]))["docs"]
    rd = sys.argv[2]
    prefix = "opa_"
    if "--prefix" in sys.argv:
        prefix = sys.argv[sys.argv.index("--prefix") + 1]
    reads = collections.defaultdict(dict)  # clip -> reader -> row
    for f in sorted(glob.glob(os.path.join(rd, prefix + "*.jsonl"))):
        name = os.path.basename(f)[len(prefix):-6]
        if not re.fullmatch(r"[abc][12]", name):
            continue
        for l in open(f, encoding="utf-8"):
            l = l.strip()
            if not l:
                continue
            try:
                r = json.loads(l)
            except Exception:
                continue
            reads[int(r["clip"])][name] = r
    rows = []
    S = collections.Counter()
    for key, d in sorted(chart.items(), key=lambda kv: kv[1]["c"]):
        c = d["c"]
        rr = reads.get(c, {})
        names = sorted(rr)
        S["snaps"] += 1
        if not names:
            S["no_read"] += 1
            continue
        cl = coach_line(d.get("line"))
        # ---- shell
        cs = str(d.get("shell")) if d.get("shell") is not None else None
        rs = [shell_of(rr[n]) for n in names]
        if cs:
            S["shell_n"] += 1
            S["shell_reads"] += len(rs)
            S["shell_read_ok"] += sum(x == cs for x in rs)
            S["shell_any"] += any(x == cs for x in rs)
            S["shell_first"] += rs[0] == cs
            if len(set(rs)) == 1:
                S["shell_agree_n"] += 1
                S["shell_agree_ok"] += rs[0] == cs
        # ---- blitz y/n
        if d.get("rush") not in (None, ""):
            cb = coach_blitz(d)
            rb = [blitz_of(rr[n]) for n in names]
            S["blitz_n"] += 1
            S["blitz_reads"] += len(rb)
            S["blitz_read_ok"] += sum(x == cb for x in rb)
            S["blitz_any"] += any(x == cb for x in rb)
            S["blitz_first"] += rb[0] == cb
            if len(set(rb)) == 1:
                S["blitz_agree_n"] += 1
                S["blitz_agree_ok"] += rb[0] == cb
            if cb:
                S["blitz_true_n"] += 1
                S["blitz_true_caught_any"] += any(rb)
                S["blitz_true_caught_all"] += all(rb)
        # ---- coverage
        cc = str(d.get("cov")) if d.get("cov") is not None else None
        if cc and re.fullmatch(r"\d", cc):
            rc = [cov_of(rr[n]) for n in names]
            S["cov_n"] += 1
            S["cov_reads"] += len(rc)
            S["cov_read_called"] += sum(x is not None for x in rc)
            S["cov_read_ok"] += sum(x == cc for x in rc)
            if len(rc) >= 2 and rc[0] is not None and len(set(rc)) == 1:
                S["cov_agree_n"] += 1
                S["cov_agree_ok"] += rc[0] == cc
        # ---- line
        if cl:
            S["line_n"] += 1
            rl = [reader_line(rr[n]) for n in names]
            S["line_reads"] += len(rl)
            S["line_read_exact"] += sum(x == cl for x in rl)
            S["line_any_exact"] += any(x == cl for x in rl)
            S["line_first_exact"] += rl[0] == cl
            if len(rl) >= 2 and rl[0] == rl[1]:
                S["line_agree_n"] += 1
                S["line_agree_ok"] += rl[0] == cl
            c3 = three_side(cl)
            if c3:
                S["three_n"] += 1
                S["three_reads"] += len(rl)
                S["three_read_ok"] += sum(three_side(x) == c3 for x in rl)
                S["three_first"] += three_side(rl[0]) == c3
                S["three_any"] += any(three_side(x) == c3 for x in rl)
            # per-man DT techniques, only when the count on the line matches
            for x in rl:
                if len(x) == len(cl):
                    for a, b in zip(interior(cl), interior(x)):
                        S["dt_n"] += 1
                        if a == b:
                            S["dt_ok"] += 1
                        elif a in IDX and b in IDX:
                            S["dt_wide" if IDX[b] > IDX[a] else "dt_tight"] += 1
                    for a, b in zip((cl[0], cl[-1]), (x[0], x[-1])):
                        S["end_n"] += 1
                        S["end_ok"] += a == b
                else:
                    S["line_count_miss"] += 1
        row = dict(clip=c, coach_line=d.get("line"), coach_shell=cs, coach_cov=cc,
                   coach_rush=d.get("rush"), coach_blitz="/".join(d.get("blitz") or []))
        for n in names:
            row[n + "_line"] = "-".join(reader_line(rr[n]))
            row[n + "_shell"] = shell_of(rr[n])
            row[n + "_cov"] = rr[n].get("coverage")
            row[n + "_press"] = rr[n].get("pressure")
        rows.append(row)

    def pr(label, ok, n):
        if S[n]:
            print(f"{label:<46} {S[ok]:>3}/{S[n]:<3} {S[ok]/S[n]:.3f}")
        else:
            print(f"{label:<46} n/a")

    print(f"snaps in chart {S['snaps']}, without any read {S['no_read']}")
    pr("shell: per read", "shell_read_ok", "shell_reads")
    pr("shell: first reader", "shell_first", "shell_n")
    pr("shell: either reader", "shell_any", "shell_n")
    pr("shell: right when both agree", "shell_agree_ok", "shell_agree_n")
    pr("blitz y/n: per read", "blitz_read_ok", "blitz_reads")
    pr("blitz y/n: first reader", "blitz_first", "blitz_n")
    pr("blitz y/n: either reader", "blitz_any", "blitz_n")
    pr("blitz y/n: right when both agree", "blitz_agree_ok", "blitz_agree_n")
    pr("coach's blitzes caught by either", "blitz_true_caught_any", "blitz_true_n")
    pr("coach's blitzes caught by both", "blitz_true_caught_all", "blitz_true_n")
    pr("coverage: per read (all Coach-covered snaps)", "cov_read_ok", "cov_reads")
    pr("coverage: per read that made a clear call", "cov_read_ok", "cov_read_called")
    pr("coverage: right when both agree on a call", "cov_agree_ok", "cov_agree_n")
    pr("line exact: per read", "line_read_exact", "line_reads")
    pr("line exact: first reader", "line_first_exact", "line_n")
    pr("line exact: either reader", "line_any_exact", "line_n")
    pr("line exact: right when both agree", "line_agree_ok", "line_agree_n")
    pr("3-tech side: per read", "three_read_ok", "three_reads")
    pr("3-tech side: first reader", "three_first", "three_n")
    pr("3-tech side: either reader", "three_any", "three_n")
    pr("DT technique per man (count matched)", "dt_ok", "dt_n")
    print(f"   DT misses wide {S['dt_wide']}  tight {S['dt_tight']};  reads with wrong count on line {S['line_count_miss']}")
    pr("end technique per man (count matched)", "end_ok", "end_n")
    print("lines written right-to-left and turned around (clips):", sorted(set(FLIPPED)))
    if "--csv" in sys.argv:
        out = sys.argv[sys.argv.index("--csv") + 1]
        keys = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)


main()
