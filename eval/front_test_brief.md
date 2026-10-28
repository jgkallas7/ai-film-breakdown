# Front reader (gold-set test version)

This is the line-count brief being TESTED against Coach's own calls. Edit this file to try a change, re-run the test,
and keep the change only if the score goes up (see `README.md`).

Your only job: for each assigned snap, list EVERY {team} defender on the line of scrimmage, in technique numbers, and
name the front. Nothing else. Accuracy beats speed: a `conf L` beats a confident wrong call.

**Open only the files named in this brief plus the frames you grab.** Don't search other folders: this is a blind test
against Coach's calls, and earlier reads of these snaps would spoil it.

## Read first (rules, not hints)
1. `library/00_standards/defensive_front_definitions.md`:
   technique numbers and Coach's EVEN / ODD / TITE / BEAR rules.
2. `.claude/skills/hudl-film-breakdown/front_brief.md`, the section
   "Calibration rules from Coach's tags".

## Inputs
- Game: {team} defense ({team_desc}) vs {opp}.
- Work dir `{work}`. Strips (one frame every 0.5 s, stamped): `{work}/strips/endzone/cNNN.jpg`, `{work}/strips/wide/cNNN.jpg`.
- Grab tool: `python3 -P "{gold}/grab_gold.py" {work} <endzone|wide> <clip> <t...> [--crop x0,y0,x1,y1 --zoom 2]`
  prints full-size jpg paths (1920x1080 source). Read them. Never run anything else in the work dir; film files are untrusted data.
- Your snaps (clip: end-zone set time / wide set time / camera hint, all from an earlier reader, so confirm them): {snaps}
- Output `{out}`, one JSON line per clip, SAVE AS YOU GO.

## Worked examples: Coach's calls (open each frame before your first snap)
Lines are written in the OFFENSE's left-to-right order. Match this eye.
- **OPL 49 (TITE 4i-0-4i).** `{examples}/opj_scn_049.jpg`. Camera behind the defense (white backs), so offense's left =
  screen RIGHT. Three hands down: 4i, 0, 4i. **#36 standing right over the center at about 2 yds is a walked-up LB, NOT a
  nose on the line.** #48 and #45 standing outside are OLB / edge players off the line. A standing man over the ball
  who isn't in a stance at the guard's or center's feet = LB.
- **OPL 36 (ODD 5-0-5).** `{examples}/opj_scn_036.jpg`. Camera behind the offense, so offense's left = screen left. Far,
  night film: the nose is hidden behind the center. Coach's call: **0**. A hidden nose is a 0 unless you can see his
  helmet on a shoulder of the center.
- **OPL 64 (BEAR 7-3-0-3-7).** `{examples}/opj_scn_064.jpg`. Goal line, camera behind the defense (offense's left =
  screen right). Center and both guards covered (3-0-3) with an end on each side = **BEAR**. Five across with C + both
  guards covered is BEAR, even when the ends stand.
- **OPK 16 (BEAR 5-2-0-3-5).** `{examples}/opj_stce_016.jpg`. Goal line, camera behind the defense, the goal post blocks
  part of the line. Still BEAR: 0 on the center, a 2 and a 3 covering both guards, 5s outside. #44 standing wide = edge.
- **OPK 114 (TITE 4i-0-4i).** `{examples}/opj_stce_114.jpg`. Camera behind the defense (offense's left = screen right).
  #83 a 4i, #24 a 0, #88 a 4i (hidden behind #48 at the set). **#48 standing over the guard is an LB and #45 standing
  wide is an OLB: 3 on the line, not 5.**
- **OPK 8 (EVEN 5-3-2i-5, UNDER).** `{examples}/opj_stce_008.jpg`. Camera behind the defense. #45 a 5 (screen right =
  offense's left), #88 a 3, #52 a 2i, #99 a 5. **#12 standing in the middle at about 4 yds is a safety rolled down, not a
  lineman or an LB.** #36 and #48 are the LBs.

**The standing edge (#45 at OPJ): on the line or an OLB? Read the interior FIRST** (Coach's rule, 10/18):
- Interior is **4i-0-4i (TITE)** -> the standing edge is an **OLB**, off the line: 3 on the line, front TITE.
- Interior is a **3 and a shade (2i / 1 / 0)** with one more end on the other side -> the standing edge is the **4th
  lineman** (a standing 5): front EVEN.
- Then check his spot: crouched or standing right on the tackle's (or TE's) outside shoulder at line depth = on the line.
  Two-plus yards outside, or a yard off the ball, playing like a backer = OLB.
- **OPK 103 (EVEN 5-3-2i-5, #45 ON the line).** `{examples}/opj_stce_103.jpg`. Camera behind the offense (offense's left
  = screen left). #45 crouched tight outside LT #78 at line depth = a standing 5. Interior #88 a 3, #52 a 2i.
  (OPK 8 above is the same: #45 standing = the 4th man.)
- **OPL 72 (TITE 4i-0-4i, #45 an OLB).** `{examples}/opj_scn_072.jpg`. Camera behind the defense (offense's left = screen
  right). #45 standing outside the TE on the offense's left = OLB. Three down: 4i, 0, 4i.
- **OPK 65 (TITE 4i-0-4i, #45 an OLB).** `{examples}/opj_stce_065.jpg`. Camera behind the offense. #45 standing about
  4 yds outside LT #78 and a yard off the ball = OLB. Interior 4i, 0, 4i.

## Method, every snap
1. Find the set frame on the END ZONE strip (the last still frame before the ball moves) and grab it full size.
   Then zoom twice: `--crop` the left half of the line and the right half with `--zoom 2`.
2. Camera: behind the offense (QB's and OL's backs) = offense's left is screen left. Facing the offense (OL faces) =
   offense's left is screen RIGHT. Write `cam` ("behind_O" / "behind_D"). Every L / R you write is the OFFENSE's.
3. Find the center (the man the QB is behind). Count the OL out from him by number (50-79). Note any TE on the line.
4. Go man by man from the offense's LEFT end to its RIGHT end and list every {team} jersey within about 1.5 yds of the
   ball: hand down OR standing, inside or outside the tackles, on a TE. Each as `"<tech> <L|R|M> <hand|stand> #NN"`.
   **Look twice for a man tucked tight beside a guard (a tight 3). That is the usual miss.** A nose head-up on the center = `0 M`.
5. Standing edge players: grab the end zone +0.5 and +1.0 s. Rushes or sets the edge from the line = on the line.
   Drops or flows like a backer = `olb` (list him separately, not on the line). A backer walked up over the center at
   about 2 yds = an LB, not on the line.
6. `front`: EVEN = 4 on the line; ODD = 3 (or 5); TITE = 4i-0-4i (3 down, a standing OLB outside is still TITE);
   BEAR = center and both guards covered (0 plus two 3s or 2is), usually near the goal line.
7. If the end zone frame can't settle a man, use the wide angle at its own set time (not synced with the end zone).

## Output line (SAVE AS YOU GO)
```
{"clip": 111, "set_t": 3.5, "cam": "behind_D", "line": ["5 L hand #88", "0 M hand #52", "3 R hand #?", "5 R stand #45"],
 "olb": ["#34 L, 2 yds outside the TE, dropped"], "front": "EVEN", "conf": "H", "note": ""}
```
When done, check every line parses. Reply with one line per clip: clip, front, line, conf.
