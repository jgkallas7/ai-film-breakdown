"""Frame reads -> Hudl-Assist-style breakdown for Hudl Classic "Import Data".

    python3 build_import.py <game_config.json>

Config keys (paths relative to the config file's folder unless absolute):
  zip          Hudl game zip (its breakdown.xlsx fixes the row count / PLAY #)
  us, them     team codes the readers used ("OPE", "OPG")
  team, opp    TEAM / OPP TEAM text to write
  reads        glob of reader JSONL files ("reads/con_*.jsonl")
  overrides    OPTIONAL coach_overrides JSONL ({"clip": n, ...fields}); always wins over reads
  assist       OPTIONAL Hudl Assist xlsx for this game (same PLAY # rows). Its cells win over frame
               reads (D&D, spot, result, gain, OFF FORM...); frame reads still supply what Assist
               leaves blank (DEF FRONT / COVERAGE / BLITZ / MOTION / BACKFIELD). ODK / PLAY TYPE
               disagreements go on the check list -- that's how Assist mistakes get caught.
  fixes        OPTIONAL [{"clip": n, "<COLUMN>": value, "why": "...", "quiet": true?}] film corrections to Assist that
               Coach OK'd; applied after Assist, before his export, and listed on the check list as FIXED
  export       OPTIONAL Coach's Hudl "Export Data" xlsx; every cell he filled wins over everything
  coach_only   OPTIONAL [columns]: only the export's cells + fixes go in these columns (no frame reads at all)
  export_owns  OPTIONAL {"O": ["OFF FORM", ...]}: another coach owns those columns on rows with that ODK; they get
               exactly the export's cells (blanks stay blank). Re-export right before importing if he's still tagging.
  qtr_starts   OPTIONAL [first clip of Q2, Q3, Q4]; else QTR comes from reader scoreboards (gaps forward-filled)
  games        OPTIONAL [{"name": "Soph", "clips": [1, 116], "qtr_starts": [30, 58, 87]}, {"name": "Varsity", ...}]
               when one zip holds more than one game; quarters and the down/series chain restart at each game
  check_notes  OPTIONAL [{"clip": n, "note": "..."}] questions for Coach, listed first on the check list
  notes_only   true -> the check list is ONLY check_notes (curated, scheme questions). Default for Coach: he wants the
               few calls that change the scouting picture, not every low-confidence frame read (OPC 10/12, 72 items)
  out, check   output xlsx / check-list csv
  forms        OPTIONAL glob of formation-pass JSONL (formation_brief.md): {"clip", "off_form": "TRIPS RT STRONG",
               "motion"}; these team names go into OFF FORM / OFF STR / MOTION and beat the readers' shapes
  n_clips      OPTIONAL int: Coach deleted trailing clips in Hudl (e.g. the next game) -> keep only PLAY # 1..n_clips
               so the import row count matches his playlist, not the zip (OPE 10/11: zip 153, playlist 110)
  game_only    true -> keep only ODK + chain columns (PLAY #, ODK, DN, DIST, YARD LN, HASH, PLAY TYPE, RESULT, GN/LS,
               KICK YARDS, QTR, SERIES, TEAM, OPP TEAM, EFF). First import for Coach to filter O/D and tag himself.
  missing_plays true -> the film skips plays: when a play's end spot is 4+ yds off the next snap, use the reader's
               gain instead of next-snap minus this snap (OPA soph 10/16)
  fill_forms   true -> write frame-read structure into OFF FORM / DEF FRONT / COVERAGE / BLITZ (low trust, Coach renames)

Perspective = `us`: ODK O = us on offense, D = them on offense, K = kicks.
YARD LN from the offense's (or kicker's) side: -35 = own 35, +35 = opp 35.
Import rules (OPN 9/20, OPM 10/4): full file, clip order, row count must match the zip,
use only Hudl's own RESULT names (unknown values come through blank).
"""
import glob, io, json, re, sys, zipfile
from pathlib import Path
import pandas as pd


def load(cfg, base, n):
    reads = {}
    for f in sorted(glob.glob(str(base / cfg["reads"]))):
        for line in open(f):
            if line.strip():
                d = json.loads(line)
                reads[int(d["clip"])] = d
    missing = sorted(set(range(1, n + 1)) - set(reads))
    if missing:
        # with Assist, unread clips are fine: Assist supplies the game data, they just lack front reads
        assert cfg.get("assist") and (base / cfg["assist"]).exists(), f"missing clip reads: {missing}"
        print(f"no frame reads for {len(missing)} clips ({missing[0]}-{missing[-1]}): Assist only there")
        for c in missing:
            reads[c] = {"clip": c, "snap": None, "kind": None}
    for f in sorted(glob.glob(str(base / cfg["forms"]))) if cfg.get("forms") else []:
        for line in open(f):
            if line.strip():
                d = json.loads(line)
                c = int(d["clip"])
                if c in reads and d.get("off_form"):
                    reads[c]["hc_form"] = d["off_form"].upper()
                    reads[c]["hc_motion"] = d.get("motion")
                    if d.get("conf") == "L":
                        reads[c]["hc_form_check"] = f"formation '{d['off_form']}' is a guess: {(d.get('note') or '')[:90]}"
    ov = cfg.get("overrides") and base / cfg["overrides"]
    if ov and ov.exists():
        for line in ov.open():
            if line.strip():
                d = json.loads(line)
                reads[int(d["clip"])].update({k: v for k, v in d.items() if k != "clip"})
    return reads


def pos(spot, direction):
    """Yards to the opponent's goal line for an offense moving `direction` on screen."""
    if not spot or spot.get("yd") is None:
        return None
    if spot.get("half") == "mid" or spot["yd"] == 50:
        return 50
    toward = (spot["half"] == "right") == (direction == "right")
    return spot["yd"] if toward else 100 - spot["yd"]


def yard_ln(p):
    if p is None:
        return None
    return 50 if p == 50 else (p if p < 50 else -(100 - p))


def hash_lr(h, direction):
    if h == "middle":
        return "M"
    if h not in ("near", "far"):
        return None
    # moving screen-left: offense's right = far side; moving right: right = near side
    return ("R" if h == "far" else "L") if direction == "left" else ("R" if h == "near" else "L")


def backfield(f):
    t = ((f.get("backfield") if isinstance(f, dict) else f) or "").lower()
    if "empty" in t: return "Empty"
    if "pistol" in t: return "PISTOL"
    if "under" in t: return "Under Center"
    if "2 back" in t: return "gun 2 back"
    if "1 back" in t: return "gun 1 back"
    return None


KICK_KINDS = {"kickoff": ("KO", "KO Rec"), "onside": ("Onside Kick", "Onside Kick Rec"),
              "punt": ("Punt", "Punt Rec"), "pat_kick": ("Extra Pt.", "Extra Pt. Block"),
              "fg": ("FG", "FG Block")}
SHELL = {"1-high": "1 High", "2-high": "2 High", "0-high": "0 High"}


def front_label(df):
    """Coach's rule (10/6, OPA): a standup end ON the line at end depth is the 4th lineman -> EVEN.
    Count hands down + standing ends on the line; don't report raw hands-down counts (3 vs 4 down
    on the same defense looked like two different fronts)."""
    techs = [t for t in (df.get("techs") or []) if t and t != "partial"]
    if techs and "partial" not in (df.get("techs") or []):
        # COUNT decides (Coach 10/6): players ON the line at DL depth, hands down or standup ends playing DL.
        # 3 or 5 on the LOS = ODD even with a shaded nose; 4 = EVEN. The nose only describes spacing:
        # 4 on the line with a head-up 0 = EVEN (ODD SPACING). An OLB at LB depth / walked-out overhang is
        # NOT on the line (OPE's walked-up OLB was what made readers call their 3-down odd front even).
        n = len(techs)
        nose0 = "0" in [t.split()[0] for t in techs]
        if n % 2 == 0:
            return "EVEN (ODD SPACING)" if nose0 else "EVEN"
        return "ODD" if n <= 3 else f"ODD ({n} ON LINE)"
    fam = (df.get("front_family") or "").lower()
    down, se = df.get("down"), df.get("standing_ends") or 0
    if "stack" in fam:
        return "ODD (STACK)"
    if down is None:
        return None
    on_line = down + se
    if on_line >= 5:
        return "5+ ON LINE"
    return "EVEN" if on_line >= 4 or "4-man" in fam or "4-3" in fam else "ODD"


def quarters(cfg, R, n):
    if cfg.get("games"):
        out = {}
        for g in cfg["games"]:
            a, b = g["clips"]
            for c in range(a, b + 1):
                out[c] = 1 + sum(c >= x for x in g.get("qtr_starts", []))
        return {c: out.get(c) for c in range(1, n + 1)}
    if cfg.get("qtr_starts"):
        s = cfg["qtr_starts"]
        return {c: 1 + sum(c >= x for x in s) for c in range(1, n + 1)}
    q, out = None, {}
    for c in range(1, n + 1):
        m = re.search(r"Q\s*([1-4])", R[c].get("scoreboard") or "")
        if m and (q is None or int(m.group(1)) >= q):
            q = int(m.group(1))
        out[c] = q
    return out


def build(cfg, R, n):
    us = cfg["us"]
    Q = quarters(cfg, R, n)
    rows, checks = {}, []
    for c in range(1, n + 1):
        r = R[c]
        row = {"PLAY #": c, "QTR": Q[c]}
        kind, team, d = r.get("kind"), r.get("poss"), r.get("off_dir")
        if kind in KICK_KINDS and team and r.get("snap"):
            row.update({"ODK": "K", "PLAY TYPE": KICK_KINDS[kind][0 if team == us else 1],
                        "RESULT": r.get("result"), "HASH": hash_lr(r.get("hash_screen"), d),
                        "YARD LN": 3 if kind == "pat_kick" else yard_ln(pos(r.get("spot_pre"), d)),
                        "KICK YARDS": r.get("kick_yds"), "RET YARDS": r.get("ret_yds")})
        elif kind in ("scrimmage", "pat_run_pass") and team:
            row["ODK"] = "O" if team == us else "D"
            if r.get("snap") or r.get("result") in ("Penalty", "Timeout"):
                rp = r.get("run_pass")
                f = r.get("form") or {}
                df = r.get("def") or {}
                row["PLAY TYPE"] = {"run": "Run", "pass": "Pass"}.get(rp) if r.get("snap") else None
                if kind == "pat_run_pass" and r.get("snap"):
                    row["PLAY TYPE"] = "2 Pt."
                row["RESULT"] = r.get("result")
                row["HASH"] = hash_lr(r.get("hash_screen"), d)
                row["BACKFIELD"] = backfield(f)
                if rp == "run":
                    row["PLAY DIR"] = r.get("play_dir_off")
                if isinstance(f, dict) and f.get("motion") and f["motion"] != "none":
                    row["MOTION"] = f["motion"].upper()
                    row["MOTION DIR"] = f.get("motion_dir")
                if cfg.get("fill_forms") and isinstance(f, dict):
                    if f.get("shape"):
                        te = f" {f['te']}TE" if f.get("te") else ""
                        row["OFF FORM"] = f"{f['shape'].upper()}{te}"
                    row["OFF STR"] = f.get("strength")
                    fr = front_label(df)
                    if fr:
                        row["DEF FRONT"] = fr
                    # COVERAGE is never filled from frames: the sideline angle can't tell 1-high from
                    # 2 safeties at the same depth (Coach, 10/6: "said 1 high when it had two safeties")
                    if df.get("pressure") and df["pressure"] not in ("unclear",):
                        row["BLITZ"] = "NONE" if df["pressure"] == "none" else df["pressure"].upper()
                if r.get("hc_form"):                               # formation pass: our names, never shapes
                    row["OFF FORM"] = r["hc_form"]
                    side = re.search(r"\b(LT|RT)\b", r["hc_form"])
                    row["OFF STR"] = side.group(1)[0] if side else None
                    if r.get("hc_motion"):
                        row["MOTION"] = str(r["hc_motion"]).upper()
                for k in ("off_form", "off_str", "off_play", "def_front"):     # Coach overrides, our names
                    if r.get(k):
                        row[k.upper().replace("_", " ")] = r[k]
                if r.get("off_form") and not r.get("off_str"):   # strength follows Coach's name (LT/RT)
                    m = re.search(r"\b(LT|RT)\b", r["off_form"].upper())
                    row["OFF STR"] = m.group(1)[0] if m else None
                if r.get("off_form") == "":                      # Coach said the read name is wrong, no name yet
                    row["OFF FORM"] = None
                row["_pos"] = pos(r.get("spot_pre"), d)
                row["_team"] = team
        elif team:
            row["ODK"] = "K" if kind in KICK_KINDS else ("O" if team == us else "D")
        rows[c] = row

    # ---- chain pass: series, down, distance, gain ----
    series, last_team, down, ltg, prev_ltg = 0, None, None, None, None
    clips = list(range(1, n + 1))
    starts = {g["clips"][0] for g in cfg.get("games", [])}
    for i, c in enumerate(clips):
        row, r = rows[c], R[c]
        if c in starts:
            last_team = None                           # new game in the same zip
        if "_pos" not in row:
            if row.get("ODK") == "K" and r.get("kind") in ("kickoff", "punt", "onside", "fg") and r.get("snap"):
                last_team = None
            continue
        team, p = row["_team"], row["_pos"]
        if team != last_team:
            series += 1; down = 1; ltg = None; prev_ltg = None; last_team = team
        row["SERIES"] = series
        if p is None:
            row["GN/LS"] = r.get("gain")
            continue
        if R[c].get("kind") == "pat_run_pass":
            row["YARD LN"] = yard_ln(p)
            continue
        if ltg is None:
            ltg = max(p - 10, 0)
        box = r.get("down_box")
        if box and box != down:
            checks.append((c, row["QTR"], f"chain {down}", f"down marker reads {box} -- used the marker"))
            if box == 1:
                ltg = max(p - 10, 0)
            elif down == 1 and prev_ltg is not None and p > prev_ltg:
                ltg = prev_ltg
            down = box
        row["YARD LN"] = yard_ln(p)
        row["DN"], row["DIST"] = down, (p - ltg if ltg > 0 else p)
        end = next((g["clips"][1] for g in cfg.get("games", []) if g["clips"][0] <= c <= g["clips"][1]), n)
        nxt = next((rows[k] for k in clips[i + 1:end] if "_pos" in rows[k] or
                    (rows[k].get("ODK") == "K" and R[k].get("snap"))), None)
        same = nxt is not None and nxt.get("_team") == team and nxt.get("_pos") is not None \
            and R[nxt["PLAY #"]].get("kind") == "scrimmage"
        res = row.get("RESULT") or ""
        if "TD" in res:
            gain = p
        elif "Fumble" in res and not r.get("fumble_kept"):
            gain = r.get("gain")
        elif same:
            gain = p - nxt["_pos"]
            end = pos(r.get("spot_end"), r.get("off_dir"))
            if end is not None and abs(end - nxt["_pos"]) >= 4 and cfg.get("missing_plays") \
                    and r.get("gain") is not None:
                gain = r.get("gain")     # film has gaps (OPA soph 10/16): next snap isn't this play's end
            elif end is not None and abs(end - nxt["_pos"]) >= 4 and res != "Penalty":
                checks.append((c, row["QTR"], f"{down}&{row['DIST']}",
                               f"play ends ~{yard_ln(end)} but next snap is {yard_ln(nxt['_pos'])} (penalty/missing clip?)"))
        else:
            gain = r.get("gain")
        if res == "Timeout":
            gain = None
        if res == "Penalty" and not str(r.get("src", "")).startswith("COACH"):
            checks.append((c, row["QTR"], f"{down}&{row['DIST']}", "penalty -- on whom, how many yards?"))
            if gain is None or abs(gain) < 3:
                gain = None
        if row.get("PLAY TYPE") == "Pass" and res in ("Incomplete", "Interception"):
            gain = 0
        row["GN/LS"] = gain
        if row.get("PLAY TYPE") in ("Run", "Pass") and gain is not None and res != "Penalty":
            need = {1: 4, 2: row["DIST"] / 2}.get(down, row["DIST"])
            row["EFF"] = "Y" if ("TD" in res or gain >= need) else "N"
        turnover = (any(t in res for t in ("Interception", "Fumble")) and not r.get("fumble_kept")) or (
            down == 4 and same and nxt["_pos"] > ltg and res not in ("Penalty", "Timeout") and not r.get("first_down"))
        if turnover and same:
            checks.append((c, row["QTR"], f"{down}&{row['DIST']}",
                           f"'{res or 'no result'}' but the same team has it next clip -- recovery? possession?"))
            last_team = None
            continue
        prev_ltg = ltg
        if same:
            np_ = nxt["_pos"]
            if r.get("first_down") and np_ > ltg:
                ltg = np_
            if np_ <= ltg:
                down, ltg = 1, max(np_ - 10, 0)
            elif res not in ("Penalty", "Timeout"):
                down += 1
            if down > 4:
                checks.append((c, row["QTR"], "-", "chain went past 4th down -- spots/possession wrong"))
                down = 4
        else:
            last_team = team if nxt is not None and nxt.get("_team") == team else None

    # QA: scrimmage snaps with no formation, and readers repeating the same form block (lazy copy)
    snaps = [c for c in clips if R[c].get("snap") and R[c].get("kind") == "scrimmage"]
    blank = [c for c in snaps if not rows[c].get("OFF FORM")]
    if blank:
        print(f"WARNING: {len(blank)} snaps with no OFF FORM: {blank[:20]}{' ...' if len(blank) > 20 else ''}")
    run = 1
    for a, b in zip(snaps, snaps[1:]):
        same = (json.dumps(R[a].get("form"), sort_keys=True) == json.dumps(R[b].get("form"), sort_keys=True)
                and R[a].get("form") and not (R[a].get("hc_form") and R[b].get("hc_form")))   # formation pass replaced it
        run = run + 1 if same else 1
        if run == 5:
            print(f"WARNING: identical reader 'form' on 5+ snaps in a row ending at clip {b}: re-read them")
            checks.append((b, Q[b], "-", "reader repeated the same formation block on 5+ snaps: re-read"))
    for c in clips:
        if R[c].get("hc_form_check"):
            checks.append((c, Q[c], f"{rows[c].get('DN')}&{rows[c].get('DIST')}", R[c]["hc_form_check"]))
    for c in clips:
        r = R[c]
        if str(r.get("src", "")).startswith(("COACH", "CHAIN")):
            continue
        if r.get("snap") and r.get("kind") == "scrimmage" and r.get("result") in (None, "Fumble", "Interception"):
            checks.append((c, Q[c], f"{rows[c].get('DN')}&{rows[c].get('DIST')}",
                           f"result '{r.get('result')}' -- {(r.get('note') or '')[:90]}"))
        if r.get("snap") and r.get("kind") in ("pat_kick", "fg") and r.get("result") not in ("Good", "No Good", "Blocked"):
            checks.append((c, Q[c], "-", "kick result not visible"))
        if r.get("conf") == "L" and r.get("snap"):
            checks.append((c, Q[c], f"{rows[c].get('DN')}&{rows[c].get('DIST')}",
                           f"low-confidence read: {(r.get('note') or 'front/formation read is a guess')[:90]}"))
    return rows, checks


# Hudl's standard columns, used when the zip has no breakdown.xlsx
DEFAULT_COLS = ["PLAY #", "ODK", "DN", "DIST", "YARD LN", "HASH", "PLAY TYPE", "RESULT", "GN/LS", "OFF FORM",
                "OFF STR", "OFF PLAY", "PLAY DIR", "GAP", "DEF FRONT", "BLITZ", "COVERAGE", "KICK YARDS",
                "RET YARDS", "PENALTY", "PEN YARDS", "QTR", "SERIES", "TEAM", "OPP TEAM", "MOTION",
                "MOTION DIR", "BACKFIELD", "EFF"]


def main(cfg_path, frames_only=False):
    cfg_path = Path(cfg_path).resolve(); base = cfg_path.parent
    cfg = json.loads(cfg_path.read_text())
    if frames_only:                      # for compare_tags.py: our reads (+Assist) without Coach's export
        cfg.pop("export", None)
        cfg["out"] = cfg["out"].replace(".xlsx", "_frames_only.xlsx")
        cfg["check"] = cfg["check"].replace(".csv", "_frames_only.csv")
    P = lambda k: Path(cfg[k]) if Path(cfg[k]).is_absolute() else base / cfg[k]
    zf = zipfile.ZipFile(P("zip"))
    if "breakdown.xlsx" in zf.namelist():
        raw = pd.read_excel(io.BytesIO(zf.read("breakdown.xlsx")))
    else:                                # OPA soph 10/16: zip had clips only, no breakdown.xlsx
        n_mp4 = sum(1 for f in zf.namelist() if f.lower().endswith(".mp4") and not f.startswith("Tight"))
        raw = pd.DataFrame({c: [None] * n_mp4 for c in DEFAULT_COLS})
        raw["PLAY #"] = range(1, n_mp4 + 1)
    if cfg.get("n_clips"):
        raw = raw.head(int(cfg["n_clips"]))
    n = len(raw)
    assert list(raw["PLAY #"]) == list(range(1, n + 1)), "breakdown PLAY # is not 1..n"
    R = load(cfg, base, n)
    rows, checks = build(cfg, R, n)
    out = raw.copy().astype(object)
    for c, row in rows.items():
        for k, v in row.items():
            if not k.startswith("_") and v is not None and k in out.columns:
                out.loc[c - 1, k] = v
    out["TEAM"], out["OPP TEAM"] = cfg["team"], cfg["opp"]
    if cfg.get("assist") and P("assist").exists():
        ha = pd.read_excel(P("assist"))
        assert len(ha) == n and list(ha["PLAY #"]) == list(range(1, n + 1)), "assist rows != clips"
        for col, why in (("ODK", "possession/kick"), ("PLAY TYPE", "run/pass")):
            for i in range(n):
                a, f = ha.at[i, col], out.at[i, col] if col in out else None
                if pd.notna(a) and pd.notna(f) and str(a) != str(f) and "Pt" not in str(ha.at[i, "PLAY TYPE"]):
                    checks.append((i + 1, ha.at[i, "QTR"], f"{ha.at[i, 'DN']}&{ha.at[i, 'DIST']}",
                                   f"Assist {col} '{a}' vs frames '{f}' ({why}) -- Assist kept"))
        for col in ha.columns:
            if col in out.columns:
                m = ha[col].notna()
                out.loc[m, col] = ha.loc[m, col]
                if col in ("DN", "DIST", "GN/LS", "YARD LN", "SERIES", "EFF"):
                    # Assist owns the chain: don't leave frame-built chain values on rows Assist left blank
                    out.loc[~m & ha["ODK"].notna(), col] = None
    n_coach = 0
    if cfg.get("export") and P("export").exists():
        hx = pd.read_excel(P("export"))
        assert len(hx) == n and list(hx["PLAY #"]) == list(range(1, n + 1)), "export rows != clips"
        for col in hx.columns:
            if col in out.columns:
                m = hx[col].notna()
                n_coach += int(m.sum())
                out.loc[m, col] = hx.loc[m, col]
                if col in ("DEF FRONT", "COVERAGE", "BLITZ") and m.any():
                    out.loc[~m, col] = None       # Coach tagged this column: don't mix frame labels into his
        # another coach is tagging one side of the ball (OPC 10/12: a D coach owns OPA's O rows): on those rows the
        # listed columns are exactly what the export has, blanks included, so the import never adds to his work
        for odk, cols in (cfg.get("export_owns") or {}).items():
            rows = hx["ODK"] == odk
            for col in cols:
                if col in out.columns:
                    out.loc[rows, col] = hx[col][rows] if col in hx.columns else None
    # coach_only (OPC 10/13): these columns carry ONLY coaches' cells (export + fixes); our frame values are dropped,
    # so an import never puts a guessed formation / play type / front on a snap he hasn't tagged yet
    for col in cfg.get("coach_only", []):
        if col in out.columns:
            out[col] = hx[col] if (cfg.get("export") and P("export").exists() and col in hx.columns) else None
    # Coach-approved fixes go LAST: his export repeats every cell (Assist's originals too)
    for fx in cfg.get("fixes", []):
        i = int(fx["clip"]) - 1
        for col, v in fx.items():
            if col not in ("clip", "why", "quiet"):
                out.loc[i, col] = v
        if not fx.get("quiet"):                  # quiet = Coach-requested label fix (e.g. OPP TEAM), not a film call
                checks.append((fx["clip"], out.at[i, "QTR"], "-", f"FIXED from film: {fx.get('why', '')}"))
    if cfg.get("game_only"):   # Coach 10/11: first import = ODK + chain only, so he can filter O/D and tag the rest
        keep = ["PLAY #", "ODK", "DN", "DIST", "YARD LN", "HASH", "PLAY TYPE", "RESULT", "GN/LS", "KICK YARDS",
                "QTR", "SERIES", "TEAM", "OPP TEAM", "EFF"]
        out = out[[c for c in out.columns if c in keep]]
    out = out[[c for c in out.columns if out[c].notna().any()]]
    for c in out.columns:
        s = pd.to_numeric(out[c], errors="coerce")
        if out[c].notna().any() and s.notna().sum() == out[c].notna().sum() and (s.dropna() % 1 == 0).all():
            out[c] = s.astype("Int64")
    out.to_excel(P("out"), index=False)
    if cfg.get("assist") and P("assist").exists():      # chain checks were about frame-built D&D
        checks = [c for c in checks if not str(c[3]).startswith(("down marker", "play ends", "chain went"))]
    fixed = {int(f["clip"]) for f in cfg.get("fixes", [])}
    checks = [c for c in checks if not (c[0] in fixed and str(c[3]).startswith("Assist "))]
    ck = pd.DataFrame(checks, columns=["CLIP", "QTR", "D&D (built)", "CHECK"]).drop_duplicates()
    ck = ck.groupby("CLIP", as_index=False).agg({"QTR": "first", "D&D (built)": "last", "CHECK": " | ".join})
    if cfg.get("check_notes"):
        top = pd.DataFrame([{"CLIP": x["clip"], "QTR": Q.get(x["clip"]) if (Q := quarters(cfg, R, n)) else None,
                             "D&D (built)": "-", "CHECK": x["note"]} for x in cfg["check_notes"]])
        ck = pd.concat([top, ck], ignore_index=True)
    if cfg.get("notes_only"):        # Coach 10/12: a 72-item list buried the 3 questions that matter -> curated only
        ck = top if cfg.get("check_notes") else ck.iloc[0:0]
    ck.to_csv(P("check"), index=False)
    odk = out["ODK"].value_counts().to_dict() if "ODK" in out else {}
    print(f"{n} rows x {len(out.columns)} cols -> {P('out').name}  ODK {odk}  (coach cells kept: {n_coach})")
    print(f"{len(ck)} check items -> {P('check').name}")


if __name__ == "__main__":
    main(sys.argv[1], frames_only="--frames-only" in sys.argv)
