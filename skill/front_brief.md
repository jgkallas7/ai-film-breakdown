# Front-reading pass (every defensive snap, dense frames)

Goal: an exact alignment for every snap of {def_team}'s defense, so the snaps can be grouped and Coach can name each group. Read `library/00_standards/defensive_front_definitions.md` first. It's the rulebook.

## Inputs (filled by the launcher)
- Game: {game_label}. Defense: {def_team} ({def_desc}). Offense: {off_team} ({off_desc}).
- Work dir: {work}. For each clip:
  - `cv/cNNN_set.jpg`: Tight-angle SET frame (0.4 s before the computer-detected snap). Every defender is boxed and numbered **D1, D2…** from screen-left to screen-right.
  - `cv/cNNN_strip.jpg`: SET, +0.4 s, +0.8 s and +1.3 s after the snap.
  - `cv/cNNN.json`: `snap_t` and `set_t` in seconds.
  - Pull more: `python3 "{skill}/scripts/grab.py" {work} <clip> <t...> --tight [--crop x0,y0,x1,y1 --zoom 2]`. Use it for the box, the nose, and every standup edge.
- Clips: {clips}
- Output: `{out}`, one JSON line per clip.

## Steps for every snap
1. **Confirm the SET frame is set.** If the computer's snap is wrong, find the real snap with grabs at 0.2 s steps and say so in `note`.
2. **Find the center, then the player over him.** Is someone head-up (0), shaded (1), or is nobody there?
3. **List every defender ON the line at DL depth, left to right from the OFFENSE's view.** That's the `techs` field (format below). Mark each `hand` or `stand`. Use the technique numbers on the definitions page; the side is the offense's L or R.
4. **For each standing edge or walked-up player, decide end vs. OLB from the strip.** Zoom on +0.4 and +0.8. If he plays off the ball like a DL (rushes, or squeezes/sets the edge from the line), he's on the line. If he drops, reads or flows like a backer, he's an OLB: leave him out of `techs` and put him in `lbs`. Write what you saw in `edge_play`.
5. **Second level:** every linebacker's alignment (e.g. "#23 stack over L guard 4 yds", "walked up over the slot 2 yds"), plus `box` = defenders inside the tackle box within 5 yds.
6. **Pressure:** did anyone off the line rush at the snap (LB / DB)? Use `pressure: none | LB | DB | sim`.
7. **Front label, by the rule:** count the players in `techs`. 3 or 5 = ODD, 4 = EVEN. Add the spacing note when it applies (4 on the line with a 0 = "EVEN (ODD SPACING)"). If it's clearly a **stack** (backers directly behind 3 DL) or a **split** (both DTs shading the center, balanced), say so in `front_note`.
8. Consistency: two snaps with the same people in the same spots get the same `techs`. Compare with your previous snaps before you write.

## Calibration rules from Coach's tags (OPA vs OPB, 10/10: DEF FRONT agreed 37 of 70, BLITZ 29 of 43)
- **Against two TEs / two wings, the line runs TE to TE.** Count every defender on the line at DL depth from the outside of one TE to the outside of the other, including players head-up or outside the TEs and wings. Readers counted only the players inside the tackles and wrote EVEN on all 11 OPB DOUBLE TIGHT DOUBLE WING snaps; Coach had ODD 3, BEAR 3, 5-3/5-4 2, EVEN 3 (clip 66 = 5-4: defenders walked up over the TEs/wings). **Never carry a team's base front onto its heavy-set snaps.** Read each one fresh, mark it conf L, and put it on the check list.
- **Coach's heavy-set names:** BEAR, BEAR MUG, 5-3, 5-4, ODD MUG, ODD SHIFT / ODD UNBALANCED (the front slid to an unbalanced line). Give the techs; Coach names them.
- **Don't name OVER/UNDER.** Coach tags these snaps plain EVEN (he relabeled every OVER/UNDER snap from the board as EVEN). Give the techs only, and build no findings on which side the 3-tech went.
- **Pressure: never write `none` until every LB has been checked at +0.4 and +0.8 s.** Readers wrote none on 9 snaps where Coach tagged LB pressure. Name the rushers the way Coach does: MIKE, SAM (strong inside LB), WILL, EDGE / DOUBLE EDGE (both edges), "3 LBs" (all three), PINCH STUNT, BLUFF (shows blitz and bails), EDGE OPP RB. If you can't see every backer, write `unclear`, not `none`.
- **Check the TE for a standing 7/9 before you call ODD or write "TE uncovered"** (OPA @ OPC, Coach 10/12, clips 73–75). On all three of OPC's TE snaps, readers listed 3 on the line and called it ODD. Coach had EVEN on every one: OPA stands a 7 or 9 on the TE (73: double 1s, standing 9 to the TE, standing 5 away; 74: 5 and 1 open side, 4i and a standing 7 to the TE; 75: standing 5, 3, 1, 9). On the wide angle that standing player blends into the TE. Zoom-crop the TE at the set, and treat any defender within about 1.5 yds head-up or outside him at end depth as on the line.
- **A backer walked up over a guard who comes at the snap is a blitz, not a "mug LB" to leave out** (OPC 73: the MIKE blitzed; the reader wrote "walked-up/mug LB, not counted"). Keep him off `techs`, but put him in `pressure` as LB with his role (MIKE/WILL) when he crosses the line by +0.5/+1.0 s.
- **Run fits are not blitzes (Coach 10/18, OPJ: readers 0 of 6).** Backers stepping downhill on play action, an RPO or a zone fake are fitting the run. Call pressure only when a backer/DB rushes the QB from the snap on a straight dropback, or is past the line before the fake/mesh ends. A walked-up mug who drops at the snap = BLUFF.
- **Count the line twice; a tight 3 next to the guard hides (Coach 10/18, OPJ OPK 7 and 111).** Readers called 5-0-5 on snaps that were 5-0-3-5: the 3 tech sat right on the guard's outside shoulder and blended in. Zoom each half of the line and list every jersey within 1.5 yds of the ball. Each miss also drops the box by one (4 down + 2 LBs = 6).
- **A nose on the center is a 0 (Coach 10/18 fronts board, 5 misses).** Even leaning or with his helmet hidden behind the C. OPJ's 3-down front was 5-0-5, not 5-1-5. TITE = 4i-0-4i even with a standing 5 beside an off-ball BEAR/BULL Y. Five across with C + both guards covered = BEAR.
- **Nose: zoom before you write 1 (Coach 10/18).** 0 = on the center's helmet; 1 = on his shoulder in the A gap; 2i = on the guard's inside eye. Readers wrote 1 on six snaps that were 0 or 2i.
- **Place backers and safeties from the WIDE angle, never the end zone (10/18).** The end zone flattens depth: a safety at 8-12 read as a third backer and inflated the box. Box = within 5 yds, between the end men on the line.
- **Coverage stays Coach's.** He tags 0 / 1 / 2 / 4 (+ 4 CHECK, 4 MATCH). OPA: Cover 4 vs spread 19 of 29, Cover 0 vs heavy 10 of 11. The frame reads' "1-high base" was wrong.

## Output line
```
{"clip": 11, "set_ok": true, "techs": ["5 L stand", "3 L hand", "1 R hand", "5 R hand"],
 "edge_play": "D3 (#23-ish, standing L edge) rushed upfield at +0.4: DL",
 "lbs": ["#23 2 yds over L guard? (if not counted)", "#2x 4 yds over R guard"], "box": 6,
 "pressure": "none", "front": "EVEN", "front_note": "", "off_form_seen": "DICE LT",
 "conf": "H|M|L", "note": "what was hard"}
```
- `conf L` only when the frame can't show it (fog, the center hidden, the camera cut). Give your best read anyway and say why.
- When done: validate the file, then reply with counts by `front`, the most common `techs` patterns, and the clips that were L.
