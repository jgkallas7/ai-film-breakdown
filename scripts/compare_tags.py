"""Compare our built import against Coach's Hudl export: where do the frame reads miss?

    python3 compare_tags.py <our_import.xlsx> <coach_export.xlsx> [--clips 1-116] [--out misses.csv]

Only rows where Coach filled a cell count. OFF FORM is scored three ways: family (first word,
DOUBLE DICE kept together), side (LT/RT), and tags (STRONG/PISTOL/BULL/...). Every miss is listed so
it can become a rule in formation_brief.md / reader_brief.md.
"""
import argparse, re
import pandas as pd

TAGS = ("STRONG", "PISTOL", "BULL", "BEAR", "OVER", "STACK", "2 BACK", "UNDER", "WIDE")


def fam(f):
    f = str(f).upper().replace("TACKLE OVER ", "")
    for two in ("DOUBLE DICE", "DOUBLE DOOR", "WIDE TRIBE"):
        if f.startswith(two):
            return two
    return f.split()[0] if f.split() else ""


def side(f):
    m = re.search(r"\b(LT|RT)\b", str(f).upper())
    return m.group(1) if m else ""


def tags(f):
    return {t for t in TAGS if t in str(f).upper()}


ap = argparse.ArgumentParser()
ap.add_argument("ours"); ap.add_argument("coach")
ap.add_argument("--clips"); ap.add_argument("--out")
a = ap.parse_args()
o = pd.read_excel(a.ours).set_index("PLAY #")
c = pd.read_excel(a.coach).set_index("PLAY #")
if a.clips:
    lo, hi = map(int, a.clips.split("-"))
    o, c = o.loc[lo:hi], c.loc[lo:hi]
misses = []
print(f"{'column':<14}{'coach rows':>11}{'agree':>8}")
for col in ("ODK", "PLAY TYPE", "RESULT", "OFF FORM", "DEF FRONT", "COVERAGE", "BLITZ"):
    if col not in c.columns:
        continue
    if col not in o.columns:
        o[col] = None                       # we didn't write it (e.g. COVERAGE is never frame-read)
    rows = c[col].dropna().index.intersection(o.index)
    if not len(rows):
        continue
    if col == "OFF FORM":
        for name, fn in (("form family", fam), ("form side", side), ("form tags", tags)):
            ok = [fn(o.at[r, col]) == fn(c.at[r, col]) if pd.notna(o.at[r, col]) else False for r in rows]
            print(f"{name:<14}{len(rows):>11}{sum(ok):>8}  ({100 * sum(ok) / len(rows):.0f}%)")
        for r in rows:
            if str(o.at[r, col]).upper() != str(c.at[r, col]).upper():
                misses.append((r, col, o.at[r, col], c.at[r, col]))
        continue
    ok = [str(o.at[r, col]).upper() == str(c.at[r, col]).upper() for r in rows]
    print(f"{col:<14}{len(rows):>11}{sum(ok):>8}  ({100 * sum(ok) / len(rows):.0f}%)")
    misses += [(r, col, o.at[r, col], c.at[r, col]) for r, k in zip(rows, ok) if not k]
m = pd.DataFrame(misses, columns=["CLIP", "COLUMN", "OURS", "COACH"])
print(f"\n{len(m)} misses")
if len(m):
    print(m.groupby("COLUMN").size().to_string())
    print("\nmost common OFF FORM swaps:")
    f = m[m.COLUMN == "OFF FORM"]
    if len(f):
        print(f.assign(o=f.OURS.map(fam), k=f.COACH.map(fam)).groupby(["o", "k"]).size().sort_values(ascending=False).head(10).to_string())
if a.out:
    m.to_csv(a.out, index=False)
