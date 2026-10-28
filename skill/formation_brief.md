# Formation-naming pass (our names, every offensive snap)

Coach wants every snap's formation in OUR language: `TRIPS RT STRONG`, `DICE LT`, `TREY LT BULL STRONG`. Shape labels like "3x1" or "2x2" aren't acceptable output. If you can see the receivers and backs, name it.

## Inputs (filled by the launcher)
- Game: {game_label}. Teams: {teams}.
- Work dir: {work} (`sheets/cNNN.jpg`, `clips/`, `clips_tight/` when the zip has a Tight angle)
- Clips: {first}–{last}. Possession per clip: {odk_file} (O = {o_team} has the ball, D = {d_team} has the ball, K = kick, skip those).
- Output: `{out}`, one JSON line per scrimmage snap in your range (skip kicks and no-snap clips).

Assist note: Hudl Assist's `DOUBLES` only describes the receivers. A full house behind it is DIAMOND (OPF). See `00_standards/hudl_assist_formation_crosswalk.md`.

## Find the center from the QB, then read numbers (Coach, OPC clip 10, 10/13)
OPC clip 10, as Coach laid it out from the near side: WR #17 split out, space, RT #55, RG #71, C #53, LG, LT, TE (far end), the H 2 yds off the ball between the LT and LG, the QB 5 yds DIRECTLY behind the center, the RB directly behind the QB (pistol), and a WR wide on the far side. That makes it TANDEM LT PISTOL. The reader called it DOOR RT with conf H, because it trusted a ball sighting through a line seen at an angle and took the RT (#55) for a TE. Order of checks:
1. **The QB lines up directly behind the center** (under center or in the gun). Draw a line straight forward from the QB: the lineman it hits is the center. Use the QB only, because the RB is often offset. Count the linemen on each side from the center.
2. **Count out from the center and use numbers to confirm.** In high school a TE wears an eligible number (1–49 or 80–99), and a 50–79 is a lineman, never the TE. A split-out receiver beyond the last lineman isn't part of the line count. **Unbalanced, overload and tackle-over sets are legal** (Coach 10/13). Don't assume two linemen on each side of the guards: count every 50–79 on each side of the center. Three on one side and one on the other = tackle over (e.g. TACKLE OVER TREY RT STRONG). The eligible number on the end tells you where the TE is.
3. **The center's number should match across snaps** (OPC: C #53, RG #71, RT #55).
4. A ball sighting comes last. Never mark conf H from a ball sighting alone.

## Count the line before you name a TE side (Coach, OPC 10/12)
Readers flipped the TE side on OPC 13 and 31 and missed the TE altogether on 13. Coach: "there's only two linemen left of the center, not sure how the readers would be confused on this." At the set frame, find the snapper (ball in his hands), then count the players in stances on each side of him. 2 and 3 = the TE is on the 3 side. 2 and 2 = no TE on the line. Do this on every snap before you use DOOR, TANDEM or TRIO.
- **A crouched player 1–2.5 yds off the ball beside the TE = the TANDEM wing (Y2), not a fullback.** On LT, Coach named it TANDEM RT PISTOL (13, 31). An earlier "#42 = FB → DOOR 2 BACK" rule was based on a wrong description and is void.
- **TE on the line on one side + the off-ball Y on the other = `DOOR <TE side> DICE <Y side>`** (Coach, OPC 13: DOOR LT DICE RT PISTOL). Not plain DOOR.
- **Even after the line count, the TE side was wrong on 4 of 12 OPC snaps (Coach 10/13), one of them marked H.** From a sideline wide angle, mark the TE side conf L unless the snapper and both ends are plainly visible in the zoom crop.
- **RB straight behind a gun QB = PISTOL** (Coach on OPC 13, 31). Write it when you can see it.
- **On or off = his own depth against the tackle (Coach, OPA varsity vs OPB clip 18, 10/16).** The end-zone reader called DOOR RT 2 BACK; Coach: DICE RT 2 BACK UNDER. The man beside the RT was a Y OFF the ball: his toes, body and head were all behind the RT's. On the end-zone angle, compare his toes, hips and helmet with the tackle's; any of them clearly behind = OFF. Cross-check only: only 7 can be on the line (5 OL + 2 ends), so if the outermost WR on that side is on the line, the inside man is usually off. The WR check is a heuristic, not the test. Off = DICE (1 WR + Y) or TREY (2 WRs + Y), not DOOR / TRIO / TROOP / TANDEM.

## How to look
1. **Find the set moment from the timeline strip, not the detector.** Run `python3 "{skill}/scripts/snap_strip.py" {work} <clip>` and Read `strips/cNNN.jpg`: one stamped frame per second over the whole clip. Pick `set_t` = the LAST moment everyone is still (one legal motion man allowed) right before the ball moves. Then `grab.py` at `set_t` and `set_t + 1`: the +1 frame must show the play under way, or you picked too early. The detector hint it prints is often wrong: on OPA clip 55 (28 s long) it said 1.2 s while players were still walking up; the set was about 11 s. Never write "clip starts just before the snap" without checking the clip's length on the strip.
2. Zoom when it's crowded: `python3 "{skill}/scripts/grab.py" {work} <clip> <t> --crop x0,y0,x1,y1 --zoom 2` (add `--tight` for the Tight angle).
3. Count it out: who's on the line, who's off, where the TE(s) are, where the RB is relative to the QB, and how many receivers are on each side.

## Our formations (2026; all take LT/RT, the side named from the OFFENSE's view facing the defense)
| Call | Structure | Side (LT/RT) = |
|---|---|---|
| DOUBLE | 2x2 spread, no TE | AWAY from the RB. LT/RT follows the Y, and in DOUBLE the Y is opposite the RB (RB offset right = DOUBLE LT) |
| DICE | 2x2 with the Y OFF the line (H-back/sniffer, wing-depth or behind the tackle) | the Y's side |
| DOOR | 2x2 with the Y ON the line (attached TE) | the Y's side |
| TREY | 3x1 with the Y OFF the line on the trips side (Y is the #3 inside, off the ball near the tackle) | trips side |
| TRIPS | 3x1 spread, three receivers, no TE | trips side |
| TRIO | 3x1 with an attached TE as the trips side's #3 | trips side |
| TRIBE | 3x1 bunch (three in a tight cluster); WIDE TRIBE = bunch set out wide | bunch side |
| TROOP | 3x1 with a nub (alone) TE on the single side: exactly ONE TE, three receivers the other way. Coach rejected a TROOP RT PISTOL call on OPA clip 94 (wrong structure AND not pistol) | **the TE side** (Coach 10/18, OPJ OPK 78: TE left + trips right = TROOP LT; readers had named it by the trips side). STRONG = RB on the TE side |
| TANDEM | TE + wing to the same side (add TWINS if 2 WRs the other way). Coach's example, OPA clip 94: TE + Y wing left, twins right, RB opposite = TANDEM LT TWINS | TE side |
| DOUBLE DICE | 2 WRs + an off-ball wing beside EACH tackle (some coaches call it "dixie" or double wing) | AWAY from the RB, like DOUBLE (RB left of QB = DOUBLE DICE RT). Coach's name, 10/6 (OPA clips 6–7 and their 2nd-half base) |
| QUADS | four receivers to one side | quads side |
| EMPTY | no back | 3-receiver side |
| DIAMOND | full house: QB + three backs in a diamond | none |
| BEAST | our OWN short-yardage set. **Never write BEAST on another team** (OPA 10/10: readers wrote BEAST on all 11 OPB heavy snaps; Coach: DOUBLE TIGHT DOUBLE WING) | none |
| DOUBLE TIGHT DOUBLE WING | opponent heavy set: an attached TE at each end of the line plus an off-ball wing outside each TE, no split WRs. Add `UNBALANCED` when the line or the TE/wing pair is shifted to one side (OPB 42–43) | none |
| VICTORY | kneel-down formation (Coach, OPA clip 116) | none |

Tags:
- `STRONG` = the RB aligned to the strength side. Leave it off when the RB is on the other side.
- `BULL`/`BEAR` = Y in the B gap.
- `STACK` = stacked receivers.
- `OVER` / `TACKLE OVER` = unbalanced, tackle covered.
- Two backs in the backfield: name the formation from the receivers, then add `2 BACK` (e.g. `DOUBLE RT 2 BACK`).
- **PISTOL only when it's unmistakable:** RB directly behind the QB (not offset at all) with the QB at pistol depth (about 3–4 yds), clear on a zoomed frame. A back who is only slightly offset is NOT pistol: name the side he's on and use STRONG or no tag. When in doubt, leave PISTOL off. (Coach, 10/6: "you called trips rt pistol a lot" when it was plain TRIPS RT.)
- Under center: add `UNDER`.
- Motion: name the set where it STARTS, and put the motion in `motion` (e.g. `"Z JET RT"`).

Coach's own calls on similar film, as examples: DOUBLE DICE RT, TREY RT STRONG, TRIPS LT STRONG, DICE LT STRONG, TREY LT BULL STRONG, TACKLE OVER TREY RT STRONG, TRIO RT, TRIBE LT STRONG, DOUBLE LT, DOUBLE DOOR, TANDEM RT TWINS STRONG.

## Calibration rules from Coach's tags (OPA vs OPB, 10/10: family agreed 68 of 97)
- **Before any Y name, prove there IS a Y (blind test 10/10: the biggest miss).** Work in this order:
  1. **Count the backs.** No back = EMPTY (clip 26: called TREY RT, Coach: "no backs in the backfield and no Ys").
  2. **Find a TE.** A Y has a TE body and number and lines up within about a yard outside the tackle. A receiver 2+ yards outside the tackle, or one who lines up wide on other snaps, is a SLOT, even into the short side of the field where slots set up tight to the formation (Coach on clip 22: "the difference between a slot receiver on the short side of the field and a Y 1x1 off the tackle"). If the same big player doesn't show up at Y on several snaps, the team is in spread personnel, so use TRIPS / DOUBLE, not TREY / DICE.
  3. **Only then** apply the on/off depth rule below to decide DOOR vs DICE or TRIO vs TREY.
  In OPA's 1st half, readers called TREY 9 times (Coach: TRIPS on 7) and DICE 4 times (Coach: DOUBLE on all 4). The `alt` was right on 11 of the 19 misses. **When you're torn between a Y name and a no-Y name, the no-Y name is primary** unless you've identified a TE.
- **STRONG: check the RB against the trips side on every TRIPS/TREY.** Missed on 34 and 50 (RB to the trips side = TRIPS RT/LT STRONG).
- **In fog or at the goal line, keep the team's established base set** unless you clearly see it change. OPA 88–92: readers switched to TREY RT; Coach had DOUBLE DICE on all 5 (PISTOL on 88–89), and the alt had it on 3.
- **Punt formation on 4th down = PUNT, even when they fake it** (clip 80, a fake punt; reader called TWINS LT). Flag it: a fake punt changes down, distance and gain for the whole series.
- **On vs. off is depth, not posture (only AFTER you've found a TE; on 10/10 readers wrongly applied this to slots) (DOOR vs DICE, TRIO vs TREY).** A standing Y beside the tackle reads "attached" from the sideline. Compare his helmet to the tackle's: if it's behind the tackle's hip, he's OFF (DICE/TREY). Call DOOR/TRIO only when he's clearly on the line, with his hand down or helmet level with the tackle. Clip 60: near Y standing a step off the tackle; reader said DOOR RT, Coach DICE RT. Clip 59: DOOR RT → Coach TREY LT.
- **LT / RT is ALWAYS the Y / TE side, in every formation (Coach 10/18).** TRIPS RT = the Y (#3) is on the right; DOUBLE RT = Y right; TROOP RT = TE right (trips go left). **STRONG = the RB on the Y's side.** Name the Y first, then the side, then STRONG.
- **BULL / BEAR = the Y off the ball in the LT-LG gap (BULL) or the RG-RT gap (BEAR)** (glossary). Name the gap you see; don't write BULL for every off-ball Y (Coach 10/18: OPK 103 = TREY RT BEAR STRONG, readers wrote BULL).
- **A TE with a wing beside him = TANDEM, and the twins go the other way.** Find the wing first. If one side has a wing next to an end-of-line player, that side is the TANDEM side, even when the other side's slot looks like a #3. OPA 95–99: readers said TRIO LT / TROOP RT; Coach TANDEM RT STRONG TWINS (2 of those 5 had the side flipped as well).
- **DICE vs TREY: count the WRs on the Y's side.** One WR + the Y = DICE; two WRs + the Y = TREY. Clip 10: reader TREY RT, Coach DICE RT.
- **DOUBLE DICE side = AWAY from the RB.** OPA 112–114: reader wrote DICE RT STRONG with the RB right; Coach DOUBLE DICE LT.
- **PISTOL**: clips 16–17 were plain TRIPS RT (see the PISTOL tag rule above).
- **A player still walking when the clip starts isn't set yet, and may be the back.** Clip 55 starts 0.6 s before the snap with #6 walking in near the tackle. The reader called TREY LT (conf L, "could be DOUBLE if #6 is a back"); Coach: a very clear DOUBLE RT. Find the QB and RB first, then count receivers. A player at RB depth beside the QB is the back, wherever he walked from. When your note gives an alternative name, put it in `alt` so it lands on the check list.
- **Opponent heavy/goal-line sets get conf L and go on the check list.** Don't reach for one of our names that only approximates it.

## Output line
```
{"clip": 16, "off_form": "TRIPS RT STRONG", "motion": null, "rb_side": "R", "te": 0, "conf": "H|M|L", "alt": null, "frame_t": 3.1, "note": "who you counted where, briefly"}
```
- Use `conf L` only when the frame really can't show it (fog, camera pan, clip starts after the snap). Still give your best name.
- When you're done: validate the file, then reply with a count by formation for each team and the clips you marked L.
