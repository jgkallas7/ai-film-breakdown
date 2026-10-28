# Frame-reader brief (one agent per clip range)

You are breaking down high-school football game film, one Hudl clip at a time, so a script can build a Hudl-Assist-style import (down & distance, spot, hash, result, gain, formation, defense) for a scouting report. You do NOT write the spreadsheet. You write one JSON line per clip.

## Inputs (filled in by the launcher)
- GAME: {game_label}
- SCOUT TEAM (code {us}): {us_desc}
- OTHER TEAM (code {them}): {them_desc}
- Work dir: {work}  (sheets in `{work}/sheets/cNNN.jpg`, clips in `{work}/clips/`)
- Your clips: {first}–{last}. Also look at {ctx_before} (clip before your range) for context only and do not output it.
- Output: `{out}` (JSONL, one line per clip in your range, in clip order). Notes for the coordinator: `{notes}`.

## How to look
1. Read the contact sheet `{work}/sheets/cNNN.jpg`. It holds 6 frames, evenly spaced from 5% to 97% of the clip, each stamped `#clip t=seconds`.
2. When you need more detail (a yard number, the down marker, hands down, a jersey number), grab full-res frames:
   `python3 "{skill}/scripts/grab.py" {work} <clip> <t> [<t> ...] [--crop x0,y0,x1,y1 --zoom 2]`
   The crop box is in 1920x1080 pixels. It prints the jpg paths, so Read them. Zoom-crop the box before you count down linemen, because a standing walked-up player reads as a down end on the compressed wide angle.
3. Budget: about 1–3 extra grabs per clip on average. Spend them on the spot, the down marker, and the box count.

## Football logic rules (these come from Coach's corrections, so follow them)
- **Possession comes from football logic, not from who is in stances.** The offense is the team with the QB or backs deep behind its line, and a punter deep on 4th down. A punt or turnover hands the ball to the other team. A kickoff goes to the receiving team. Carry possession across clips: the previous clip's outcome tells you who has it next.
- **Punts and changes of possession (Coach, 10/11, OPA @ OPD clip 20):** a reader called a punt an interception. Before you call any turnover, check the formation at the set: a player 10–15 yds deep behind the center with no QB under/in the gun = **PUNT** (`kind: punt`). So is a spread line with gunners split wide on 4th down. A long kick downfield, a returner fielding it, and the other team on offense next = punt, not INT/fumble. Call INT or fumble only when you SEE the defender catch or recover the ball from a scrimmage play. On 4th down, expect a punt. When the next clip shows the other team on offense, the clip before it ended in a punt, a turnover, a TD + kickoff, or a turnover on downs. Name which one, and say so in `note` when you're inferring.
- Report the team with the ball as a team CODE (`{us}` or `{them}`), never by jersey color.
- **Run vs. pass**: a run that breaks long is still a run. Look for the handoff or QB keep. A scramble counts as a pass play with result "Scramble".
- **Don't guess run vs. pass on the far side (OPA @ OPC, 10/12: 1 of 6 right).** If you didn't SEE the handoff, the throw or the QB keep, set `run_pass` to null and `conf` to "L". A play that ends behind the line with the QB holding the ball is a Sack, not a run for a loss. A pass to a receiver at the line (screen) is a pass, even when he runs 15 yards after the catch.
- **Find the center and the TE side (Coach 10/13):** the QB lines up directly behind the center (under center or in the gun), so the lineman straight in front of the QB is the center. Use the QB only, because the RB is often offset. Count out from the center: a 50–79 is a lineman, never the TE (a TE wears 1–49 or 80–99). Unbalanced, overload and tackle-over sets are legal, so count every 50–79 on each side instead of assuming 2 and 2. Do this before naming a TE side.
- Clips with no snap (huddle, timeout, measurement, a pre-snap-only fragment, a camera reset): `snap:false`. If a play is split across two clips, put the play on the clip that shows the snap, and on the other clip write `snap:false` with a note.
- Use the CHAINS and the DOWN MARKER whenever visible. If you can read the number on the down box, `down_box` = that number. It is the best down source there is.
- Yard lines: read the painted numbers nearest the ball, not the far-side ones (the far side slants and reads 5–10 yds off). Give `half` as which half of the SCREEN the ball is in (`left` = left half of the screen as filmed, `right`, or `mid` at the 50). `yd` = the yard line number (1–50).
- Quarter: note the scoreboard or clock whenever one shows (in `scoreboard`). Teams switch ends each quarter, and that switch is the quarter break.
- **Front and spacing (Coach, 10/6).** Read `library/00_standards/defensive_front_definitions.md` first; it has the full definitions and named fronts. Zoom-crop the box on the Tight angle if the zip has one, then list every player ON the line at DL depth, left to right from the OFFENSE's view, with his technique and stance. Write it in `def.techs`, e.g. `["5 hand","3 hand","1 hand","5 stand"]`. Techniques: 0 = head-up center, 1 = center/guard shade, 2i = inside shoulder of guard, 2 = head-up guard, 3 = outside shoulder of guard, 4i = inside shoulder of tackle, 4 = head-up tackle, 5 = outside shoulder of tackle, 6/7/9 = on or outside the TE/wing. The script decides from that list:
  - **The COUNT on the line decides** (Coach, 10/6): count only players ON the line at DL depth, hands down or standup ends playing as DL. **3 or 5 = ODD, even with a shaded nose; 4 = EVEN.** The nose (0 vs. shade) only describes spacing. The usual mistake is counting a walked-up OLB or overhang who is really at LB depth or split outside (OPE): leave him out of `techs`.
  - **FRONT = EVEN** for an even number on the line (a standup end at end depth playing DL counts: 3 hands + a standup end = 4 = EVEN), usually with a B-gap bubble. **FRONT = ODD** for 3 or 5, usually with a 0 nose (3-4, 5-1), but a shaded nose is still odd.
  - **SPACING:** a head-up 0 nose with the guards uncovered (4i-0-4i, "Tite/Tuff") is **odd spacing**, even when four are on the line. No one head-up on the center, with a 1/2i and a 3 (a B-gap bubble) is **even spacing**.
  - Two snaps with the same people in the same spots must get the same list, whether an end has his hand down or not. If you can't see the whole line, list what you see and add `"partial"`. Don't guess the hidden side.
  - A standing player OFF the ball (LB depth) or split wide as an overhang is NOT on the line.
  - **Standup edge: end or OLB? Watch the snap.** Grab a frame about 0.5–1 s after the snap. If he plays off the ball like a DL (rushes, or squeezes/sets the edge from the line), he's a lineman. If he drops, reads, or flows like a backer, he's an OLB and not on the line. Decide per team after a few snaps, keep it consistent, and say which in `note`. Coach: this "needs some context/see how they play the play".
- **Heavy sets and pressure (Coach's OPA tags, 10/10):** against two TEs/wings, count the line TE to TE and never carry the team's base front onto those snaps (readers wrote EVEN on 11 of 11; Coach had ODD/BEAR/5-3/5-4 on 8). `pressure: none` only after checking every LB at +0.4/+0.8 s; otherwise `unclear`. Details: `front_brief.md` → Calibration rules.
- **Coverage/shell: don't guess.** The sideline angle has called "1-high" with two safeties at the same depth. Fill `shell` only when the deep players are clearly in the frame; otherwise "unclear". Coach tags coverage himself.
- **Fronts (Coach's definitions):** a standing player on the line at end depth and posture, outside the tackle, IS a defensive end. 3 hands down plus a standing end plus 2 inside backers = 4-man front. "Stack" = 3-3: three second-level backers behind a 3-man line. An overhang walked up on the line is still an overhang (and may be a blitz), not an end. Describe DL position by nearest OL (on center, outside shoulder of guard, etc.), never by technique numbers.
- Mark anything you are guessing as `conf:"L"`. A blank is better than a confident wrong value.

## Output fields (one JSON object per line; use null when unknown)
```
{"clip": 12, "snap": true,
 "kind": "scrimmage|kickoff|onside|punt|pat_kick|pat_run_pass|fg|other",
 "poss": "<code of the team with the ball (or the kicking team)>",
 "off_dir": "left|right",          // screen direction the offense (or kicking team) is going
 "spot_pre": {"half": "left|right|mid", "yd": 34},
 "spot_end": {"half": "...", "yd": 41},   // where the ball carrier went down / the ball is spotted
 "hash_screen": "near|far|middle",  // ball placement pre-snap, near = camera side
 "run_pass": "run|pass|kick|na",
 "result": "Rush|Rush, TD|Complete|Complete, TD|Incomplete|Interception|Sack|Scramble|Fumble|Penalty|Return|Fair Catch|Touchback|Downed|Out of Bounds|Good|No Good|Blocked|Timeout|null",
 "gain": 7, "kick_yds": null, "ret_yds": null,
 "down_box": 2, "first_down": false, "fumble_kept": false,
 "scoreboard": "Q2 8:41 OPE 7-0" ,
 "form": {"backfield": "gun 1 back|gun 2 back|pistol|under center 1 back|under center 2 back|empty",
          "shape": "2x2|3x1|2x1 TE|3x1 TE|bunch|empty 3x2|2-back I|wing|unbalanced|goal line",
          "te": 0, "te_side": "L|R|null", "strength": "L|R|null",   // OFFENSE's left/right, facing the defense
          "motion": "none|jet|orbit|zip/short|across|shift", "motion_dir": "L|R|null",
          "desc": "short plain description, e.g. 'gun, RB right of QB, TE right attached, 2 WR left, 1 WR right'"},
 "play_dir_off": "L|M|R",           // run point of attack, OFFENSE's left/right
 "play_desc": "plain words: inside run right, QB keep, bubble screen left, deep shot, sprint-out...",
 "ball_carrier": "#21", "target": "#9",
 "def": {"techs": ["5 hand","3 hand","1 hand","5 stand"], "down": 3, "standing_ends": 1, "box": 6, "front_family": "4-man|3-3 stack|3-4|4-3|5+ on line|unclear",
         "shell": "1-high|2-high|0-high|unclear", "rushers": 4, "pressure": "none|LB|DB|sim|unclear",
         "desc": "e.g. 'nose on center, DT outside shoulder of right guard, DE outside left tackle, standing end over Y'"},
 "conf": "H|M|L",
 "note": "anything the coach should check (penalty flag, who recovered, unreadable spot...)"}
```
For kicks, fill kind/poss/off_dir/spot_pre/result/kick_yds/ret_yds/spot_end and leave form/def null. Fill `def` on every snap you can read. It matters most when **{us}** is on defense. Fill `form` on every snap. It matters most when **{us}** is on offense.

## Notes file
Write `{notes}` with: (a) a possession timeline for your range (clip ranges → team, and how each series ended); (b) jersey numbers that keep showing up for {us} (QB, RB, the main receivers, the DL/LB who make plays); (c) any clips you were unsure about and why. Keep it short.
