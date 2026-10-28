---
name: hudl-film-breakdown
description: Break down untagged Hudl game-film zips (opponent scouting or our own games) from video frames into a Hudl-Assist-style import file (ODK, D&D, spot, hash, result, gain, backfield, formation/front structure) plus a check list for Coach. Use when Coach downloads game zips with an empty breakdown.xlsx, asks for "the Hudl Assist workflow", or wants opponent film broken down from frames.
---

# Hudl film breakdown from frames

Built 10/4–10/6/2026 (OPM game, OPE scout, OPA scout). Scripts live in `scripts/`. The reader instructions live in `reader_brief.md`.

## 00. Direction (before any film work)
Copy `scout_questions.md` (Coach's standing questions) to the week's `scout/` folder and ask Coach for any week-specific ones.
Collect only what answers a question. Every report section must answer one; cut the rest. (OPJ took 30+ versions partly
because coverage, blitz, keys and personnel were collected and printed without a question behind them, then cut.)
Before reporting a tendency, test it on the snaps where the possible keys disagree (see the rules in `scout_questions.md`).
For the [C] / [R→C] questions, build Coach a short clip list per question with `clip_list.py` (facts + reader hints pick
the snaps; Coach makes the call). Before changing a reader brief, score it on the gold set first (`gold/README.md`).

## 0. Intake (ask only what you can't see)
- Zips usually land in `the Downloads folder`. **Move** them to `Hudl Data/Game Film 2026/`.
- Check each zip with python `zipfile`: count the clips, check for `Wide`/`Tight` prefixes, and look at `breakdown.xlsx`. If only `PLAY #` is filled, the zip is untagged. If Assist columns are filled, don't frame-tag. Use Assist plus `00_standards/hudl_assist_formation_crosswalk.md` instead.
- **Assist files often show up separately** (e.g. `Palantine_Connant HA Week 4.xlsx`, 18 columns: D&D, spot, result, gain, OFF FORM/STR, PLAY DIR, QTR, SERIES, from the scout team's perspective). Copy them to `<folder>/hudl_assist/` (Coach may have one open in Excel, so a copy works when a move won't), check that the row count equals the clip count, and set `assist` in the game config. If readers are already running, send them `<code>_assist.csv` and tell them to stop reading spots/down markers and spend their grabs on `def` (scout team on D) and `form` (scout team on O), flagging "ASSIST DISAGREES" in `note`. Assist has **no DEF FRONT / COVERAGE / BLITZ**, so frame reads are still worth it for the defense even when Assist exists.
- **Coach may have pre-tagged ODK** (e.g. OPB vs OPA had only ODK filled). Confirm whose side O/D is on from one O clip and one D clip, then save his tags as `hudl_export_<code>.xlsx` (PLAY # + ODK) so they win, and give readers a `coach_odk.csv` to treat as the truth for possession.
- **Check whether the zip holds more than one game.** Hudl playlists sometimes run on into the next game (the OPB vs OPA soph zip had the start of the varsity game in clips 117–140). Warning signs: a kneel followed by a kickoff with no score before it, a jump from daylight/dusk to full night, a new camera position, or a quarter that's far too long. Look at the sheets on either side of the break, write `games: [{"name": ..., "clips": [a, b]}]` into the config, and keep reports to the right game.
- **Why Assist labels look odd:** Our team's Assist names come from a team-level diagram→name map (Classic → Team → Formation Names). The base diagrams show receivers/TEs only, and the backfield is a separate diagram, often unnamed. So `DOUBLES` can be a full-house DIAMOND. Read OFF FORM together with BACKFIELD, and when BACKFIELD is blank, look at a frame. Don't edit that page (Coach's instruction).
- Coach tells you the scout team's colors. Confirm home/away from clip 1–2 sheets: the near (camera) sideline bench, the midfield logo, and end-zone paint. Write the team codes and jersey descriptions down before you launch readers.
- Output folder: `library/60_scout_gameplans/<yyyy>_wk<NN>_<opponent>/` (opponent) or `90_metrics/<yyyy>_wk<NN>_<opp>_breakdown/` (our own game).

## 1. Contact sheets (scratchpad only, never a synced folder)
```
python3 .claude/skills/hudl-film-breakdown/scripts/make_sheets.py "<zip>" <scratchpad>/<code>
```
This takes about 1 minute per game with 8 threads (a 3 GB Wide+Tight zip takes a few minutes). It writes `clips/`, `sheets/cNNN.jpg` (6 stamped frames from the Wide angle) and `clips.json`. **If the zip has a Tight angle** (`Tight - Clip NNN.mp4`), it also extracts those to `clips_tight/`.
- `scripts/grab.py <work> <clip> <t...> [--crop x0,y0,x1,y1 --zoom 2] [--tight]` pulls full-res frames and zoom crops on demand. `--tight` uses the Tight angle. Tell readers to use it for every defensive front read whenever it exists: hands down, DL position by nearest OL, standing edges, LB depth.
- `scripts/snap_strip.py <work> <clip...>` builds `strips/cNNN.jpg`: one stamped frame per second over the whole clip. **Readers pick the set moment from the strip** (the last still moment before the ball moves, confirmed by a grab at set_t+1 showing the play under way). Added 10/10 after OPA clip 55: the motion detector said 1.2 s (players walking up) on a 28 s clip whose set was about 11 s, and the reader named the wrong formation from that frame.
- **Scoreboard overlay (OPE 10/9):** when the film has a burned-in board (bottom-left, `--crop 0,955,330,1070 --zoom 3`), it gives down, to-go, ball-on, quarter, clock and score. Readers took gains from the board change between clips: 6 of ~90 snaps disagreed with the spot-built chain, so board D&D goes in as quiet `fixes`. Ball-on digits misread sometimes (107-110 ran backward); trust down/to-go over ball-on.
- `scripts/snap_frame.py <work> <clip...>` (motion-energy snap guess) is a hint only. On the 46 OPA offense clips it disagreed with a stricter version on about half, and both missed clip 55. Players walking up and the camera panning fool it.

## 2. Reader agents (parallel, background)
- One general-purpose agent per **~35–40 clips** (8 agents for 3 games of ~100). Each agent gets `reader_brief.md` plus the placeholder values: game label, `us`/`them` codes plus jersey/bench descriptions, work dir, clip range, the 3 clips before its range as context, and output paths `reads/<code>_<a|b|c>.jsonl` + `_notes.md`.
- The brief already covers Coach's rules. Possession comes from football logic, not from who is in stances. Use the down marker and near-side numbers for the spot. Use his front definitions. A run that breaks long is still a run. Report no-snap clips as `snap:false`.

- **Readers append each clip's line as they finish it.** Put "SAVE AS YOU GO" in the prompt. On 10/10, three OPE readers lost everything when API timeouts killed them before they wrote their files at the end.
- **Game-flow-only reads (our own game, Coach tags formations/plays):** set `form`/`def` null, add a `penalty` object (`on`, `type`, `yds`, `accepted`, `pre_or_post_snap`), and give readers Coach's tagged clips as the our-offense possession list. About 28 clips per reader finished in ~15 min.
- **Check PLAY TYPE against the call name** before the self-scout. Readers typed plain run calls (BADGERS, LAZER PANTHERS ISO) as completions and the HONEY screen as a run. Pure run calls → Run, screens → Pass via `fixes`. Calls that went one way every game before (DICKEM, DINO) go on the check list.
- **Coach trims trailing clips in Hudl** (the next game): set `n_clips` so the import row count matches his playlist, not the zip.
- Use `"quiet": true` on fixes that are label corrections (OPP TEAM) so they don't show up as "FIXED from film".

## 2b. Formation-naming pass (always, unless Coach or Assist already named every snap)
Coach wants **our formation names** on every snap (`TRIPS RT STRONG`, `DICE LT`), never shape labels like "3x1". The general readers' `form` field is too thin for that: one reader copied "gun 2 back" onto 11 straight OPA snaps. So run a separate pass with `formation_brief.md` (about 3 agents per 110 snaps, both offenses). Output goes to `reads/form_*.jsonl`. Set `"forms": "reads/form_*.jsonl"` in the config. Those names go into OFF FORM, OFF STR and MOTION.

## 3. Reconcile, then build
1. Merge the possession timelines from the notes files across chunk boundaries. Every series has to end in a score, a punt, a turnover, downs, or the half. Fix the boundary disagreements in `coach_overrides_<code>.jsonl` (`{"clip": n, "src": "FABLE (reconcile)", ...}`).
2. Find the quarter breaks from scoreboard hints and end-switches. Put them in the config as `qtr_starts`.
3. Write `game_<code>.json` (see the docstring in `scripts/build_import.py`), then run:
   ```
   python3 .claude/skills/hudl-film-breakdown/scripts/build_import.py <folder>/game_<code>.json
   ```
   Precedence: frame reads < overrides (on reads) < Assist < Coach's Hudl export < `fixes`. (An export repeats every cell, Assist originals included, so OK'd fixes must go last.) Fix Assist errors the film proves (wrong kick label, wrong possession) ONLY after Coach OKs them, through the config's `fixes` list. Each fix lands on the check list as "FIXED from film". Assist owns the chain columns whenever it's present.
   It writes `<..>_hudl_import_vYYMMDD.xlsx` (full file, clip order, row count = the zip) and `<..>_check_list_vYYMMDD.csv`.
4. Spot-check 5–10 rows yourself against their sheets: a kick, a TD, a turnover, a penalty, and a long run. Then hand Coach the check list.

## 4. Import into Hudl (Coach does this, or Claude in Chrome with his OK)
- Import Data works only in **Hudl Classic**. It ALWAYS creates a separate data-only playlist ("Imported Data – <game>") with no video. That's normal, not a failure. To put the tags on the video:
  1. In the Classic library, **check the boxes for both playlists**: the game video and "Imported Data – …".
  2. Click **Match**. It opens in the Video Editor.
  3. **Verify the alignment** on 3–4 known clips (give Coach specific ones: the opening kick, a TD, a turnover, the last clip) before saving.
  4. **Save.** The data playlist is used up by the match (about 1 item left), and he can delete it once he's checked the result.
  If the alignment is off, stop before saving and find the offset (missing or extra clip).
- Hudl drops RESULT values it doesn't know. Use only Hudl's names (`Rush`, `Complete`, `Incomplete`, `Interception`, `Sack`, `Scramble`, `Fumble`, `Penalty`, `Return`, `Good`, `No Good`, `Rush, TD`, `Complete, TD`, …).
- Always upload the full file. Whether Hudl merges or replaces columns is unconfirmed. If Coach has tagged in Hudl since the download, get **Export Data** saved as `hudl_export_<code>.xlsx` and set `export` in the config first. His cells win.
- Merge split clips in Hudl only AFTER the import.

## 5. Then the scouting report
After Coach's corrections, aggregate by side of the ball (scout team O: formation/backfield → run/pass, direction, gain; scout team D: front family, shell, pressure by down & distance and by our formation family). Report style: see memory `report-style-preference`. PDF tables, no blurbs, neutral staff tone.

## 5b. Front naming board (Coach names fronts; built 10/6 for OPA)
1. Front pass: `front_brief.md` readers, about 10 snaps each, using the Tight angle and `scripts/cv_front.py` (run with `~/.venvs/cv/bin/python`: YOLO detection, numbered overlay, a 4-frame snap strip; `clip:set_t[:snap_t]`). The readers correct the snap time when the motion pick is early (it was on about half the OPA clips), and the stills are re-run with those times.
2. `scripts/build_naming_board.py` groups snaps by **count on the line + 0 nose + shade/3-tech orientation** (strength-relative). Exact tech strings over-split (24 groups for 40 snaps), because stance and 9s flip in fog. That gave 7 groups.
3. Publish `board/index.html` (template: `templates/front_board.html`; edit the title/intro; db collection `fronts`, one doc per group: name, rule). Read Coach's answers with ArtifactData `list`, write them as `def_front` in coach_overrides, and log his rules into `00_standards/defensive_front_definitions.md`.

## 6. Calibrate against Coach's tags (do this every opponent)
The readers' formation and front calls were "still pretty off" on OPA (10/6): PISTOL overused, EVEN/ODD inconsistent. The fix is data, not more adjectives:
1. Before the full read, ask Coach to tag about 12 snaps (6 offense, 6 defense) in Hudl, then Export Data. Or, after he finishes tagging a game, use his export.
2. `build_import.py <game.json> --frames-only` (our reads without his export), then `scripts/compare_tags.py <..._frames_only.xlsx> <coach_export.xlsx>` prints agreement by column (OFF FORM family, side, tags, DEF FRONT) and every miss.
3. Turn each repeated miss into a rule in `formation_brief.md` / `reader_brief.md` with the date and the clip that taught it. Re-run only the fields that missed.

### Calibration log
| Date | Game | Form family | Form side | DEF FRONT | BLITZ | Rules added |
|---|---|---|---|---|---|---|
| 10/22 | **Gold run 4**: + 'off-ball Y in BEAR/BULL → standing man outside = overhang' + 'crowded interior → write the tighter tech (0 / 4i)' (from Coach's OPK 102 recheck: TITE 4i-0-4i, #45 overhang) | | | family 85% (run 3: 88%), core 60% (62%), family agreed-right 95% (19/20). No gain; the BEAR rule misfired on OPK 115 (Coach EVEN, #45 on the line) | | **Both rules removed** (no score gain; Coach: rules get too rigid). Run-3 brief stays the base. Gold OPK 102 now 4i-0-4i (3 on the line); runs 1-3 rescored, unchanged |
| 10/21 | **Gold run 3**: + Coach's #45 rule (read the interior first: TITE → standing edge = OLB; 3 + shade → 4th lineman) + frames OPK 103, OPL 72, OPK 65 | | | **family 88%, line count 92%** (79→85→92 over runs 1-3), core 62%, exact 52%. **Family: two readers agree on 88% of snaps, right 95% (20/21) when they agree** → meets the auto-accept target on this sample. Left: fine splits both readers share (3 vs 4i, 5 vs 7, 0 vs 1: OPK 12/64/82/108/136/96), far goal-line BEAR (OPL 123, OPK 83), OPK 102 (all readers 5-1-3-5 vs Coach TITE, 3 runs) | | Use `gold/front_test_brief.md` (9 examples) as the base line-count brief for the next scout. Fine splits → measurement step |
| 10/21 | **Gold run 2**: same 24 snaps + 6 worked-example frames (`gold/examples/`, OPL 49/36/64, OPK 16/114/8) | | | family 75→83%, nose 75→79%, core 58→60%, exact 46→48%. Readers agree more (core 42→62%) but are right less when they agree (85→73%): shared misses are fine splits (3 vs 4i, 5 vs 7, 1 vs 2i; OPK 64/82/115/102, OPL 95 missed by both readers both runs). **Family-only: agree 75%, right 94% when they agree** | | Kept the examples. Prompts fix category errors (walked-up LB, BEAR, hidden 0); fine technique splits need measurement (detection vs OL helmets), not more prompt text |
| 10/21 | **Gold-set baseline** (`gold/`), 24 OPJ snaps spread over Coach's front groups, 2 blind xhigh readers each, line-count brief | | | family 75%, core line (inside techs + count) 58%, exact 46%, 3-tech side 73%; weighted to the real game mix: family 76%, core 62%. Two readers agree on core 54%, right 85% when they agree. Misses: walked-up LB counted on the line (OPL 46, both readers), hidden nose 0 vs 1, BEAR on the far end-zone camera (OPL 123, OPK 83), 5 vs 7 edges | | Auto-accept not safe yet (needs ~95% when agreed). Next: picture examples in the brief, re-score same seed |
| 10/18 | OPJ fronts board, 57 of 105 snaps Coach-checked | | | **40/57 right.** Misses: nose on the C written as 1 (it was 0: OPL 3/35/36, OPK 77/102); TITE 4i-0-4i read as 4-down (OPK 80/102, OPL 49); goal-line 5-across = BEAR not 'goal line'; 2i/3 inside-vs-outside (OPK 108/115/135/95); TE side (OPL 48). OVER/UNDER now named (3 to / away from the strength) | | Brief: `scout/opj_refine_brief_v261018.md`; answer key `reads_line/coach_examples_v261018.md`. Boards list the line in PICTURE order with the OL each man is over (Coach reads the frame left to right) |
| 10/18 | OPJ varsity D (OPK game 1 + OPL game 2, Wide + End Zone), Coach's validation board, 39 snaps | DOUBLE RT SPLIT = gun split backs + twins, no TE (we don't run it) | | 4/8 plain agrees; nose called 1 when Coach saw 0 (OPL 34, OPK 55/96/163) or 2i (OPK 8/10); #45 depends on the interior (TITE + standing 9 = ODD; 3 + 2i + wide 5 = EVEN) | **0/6** (all were LBs fitting run on PA / RPO / zone fake; a mug that drops = BLUFF) | Coverage 8/14 (missed Cover 2 vs trips OPL 47/109; called 3 where it was a tight-aligned quarters safety; PALMS OPK 75). End-zone depth made #12 (a safety) a 3rd LB and inflated box counts → place all 11 from the WIDE angle; box = within 5 yds, between the end men. New coverage method: Match Quarters box vs triangle, corners never lie. Brief: `scout/opj_pass2_brief_v261018.md` |
| 10/13 | OPA @ OPC, Coach tagged D rows 6–22 (12 OPC snaps) | 7/12 after the line-count pass (7, 10, 21 called DOOR RT = TANDEM LT; 14 TREY LT = DOOR RT; 10 was marked conf H and still wrong) | | EVEN/ODD 9/11; EVEN JET 0/2 (12, 21) | 0/5 (all "unclear"; he had SAM, MIKE+WILL, PINCH STUNT, MIKE+SAM x2) | Cause (Coach 10/13): the reader trusted a ball sighting through an oblique line and ignored the end man's number: #55 on the end can't be the TE. formation_brief now reads the end men's numbers first (50–79 = tackle) and bans conf H from a ball sighting alone. New name: DOOR LT DICE RT PISTOL (TE on the line one side, off-ball Y the other). Coverage: Cover 2 on 4 of 11 (11, 12, 13, 20), so not all Cover 4 |
| 10/12 | OPA @ OPC, OPA O run/pass vs the D coach's tags + Coach (6 clashes: 3, 48, 49, 64, 68, 70) | | | | | **Run/pass 1 of 6 right.** 48 handoff read as a deep dropback; 64 X screen, 68 hitches incomplete and 70 sack all read as runs. reader_brief: write run_pass null when the handoff/throw isn't seen; QB down behind the line = Sack. Check list = curated scheme questions only (`notes_only`) |
| 10/12 | OPA @ OPC (Wide only, xhigh readers), 3 D snaps Coach described (73–75, OPC TE sets) | 3/3 (STRONG missed on 75) | | 0/3: all read 3 on the line (ODD); Coach EVEN on all 3 because the readers dropped the standing 7/9 on the TE | 0/1: the MIKE blitz on 73 was called a walked-up "mug LB" | front_brief: check the TE for a standing 7/9 before calling ODD or "TE uncovered"; a backer walked up who comes at the snap = blitz, name him |
| 10/12 | OPA @ OPD (Wide only, far/hazy), 12 D snaps Coach tagged | ~6/11 (shapes) | | 4/8 real reads (4 more were blind '?' x4 placeholders) — missed the 4th man on 40/41/43/48 | 0/3 (all 'unclear') | Wide-only far film: readers can't place DL; don't run the align pass on it, Coach tags fronts |
| 10/10 blind re-read | OPA O, 45 clips Coach hadn't changed | new read 26/45 vs original 17/45 (alt right on 11 of the 19 misses) | | | | Y-proof order (backs → TE → on/off), no-Y name primary when torn, STRONG check, keep base set in fog, PUNT on fakes, snap_strip |
| 10/10 | OPA vs OPB (soph, 1–116) | 68/97 | 86/97 | 37/70 | 29/43 | formation_brief + front_brief "Calibration rules": on/off by depth, TANDEM before TRIO, no BEAST on opponents, TE-to-TE line count vs heavy, OVER/UNDER dropped, pressure checks |

- **Naming-board lesson (10/10):** the board put Coach's group names (OVER/UNDER) on every snap the readers had grouped. When the readers' techs were wrong, his name went onto the wrong snaps, and he later retagged them EVEN. Use board names as a sub-label only, and keep DEF FRONT to the family (EVEN/ODD/BEAR…) until he confirms per snap.

## Known limits (don't oversell)
- Formation names: always write OUR names (formation pass). Y on/off is the hard part from the sideline (DICE vs DOUBLE, TREY vs TRIPS), so mark those L when it's unclear. Don't fall back to shape labels. Coach corrects names; he doesn't want to rename shapes.
- Spots are ±3 yds. Far-hash balls read too far from the goal because of the yard-line slant. The far-side chains read 5–10 yds off.
- **Coverage is never written from frames** (the readers called 1-high with two safeties at the same depth). Coach tags coverage.
- **DEF FRONT comes from the reader's `techs` list** (only players ON the line at DL depth). **The count decides:** 3 or 5 = ODD (even with a shaded nose), 4 = EVEN, and 4 with a head-up 0 = `EVEN (ODD SPACING)`. The classic miss is counting a walked-up OLB who's at LB depth (OPE: Coach ODD on all 48 OPF snaps, while the old rule said EVEN on 27). See `00_standards/defensive_front_definitions.md`.
- (old rule) **DEF FRONT = EVEN / ODD / ODD (STACK) / 5+ ON LINE**, computed as hands down + standing ends on the line (a standup end is the 4th lineman). Never write raw "3 DOWN"/"4 DOWN": the same defense read as both on OPA clips 11 and 12. Team-specific names (OPE's ODD WALK / ODD MUG, 3-4) come from Coach's tags.
- Coach's eyes beat every frame read. When he disagrees, re-check the frames and log his rule into `reader_brief.md`.
