# Gold-set test for the frame readers

Coach's checked calls are the answer key. Before changing how readers work (a brief edit, a new crop, a new example),
run the readers on the same snaps, score them, and keep the change only if the score goes up. Built 10/21/2026.

## Files
- `gold_fronts.csv`: one row per Coach-checked snap (line in the offense's left-to-right order, front family, 3 tech side,
  nose, group, box, shell, set times). The real answer key (104 snaps from one opponent) is game data and isn't in this
  repo; `gold_fronts_example.csv` shows the schema with two anonymized rows.
- `front_test_brief.md`: the line-count brief under test. Edit it to try a change.
- `make_gold_test.py`: picks snaps (seeded, spread across Coach's front groups), pulls only those clips from the zips,
  makes strips, writes one prompt per reader. Snaps quoted as examples in any reader rule file are left out (blind test).
- `score_gold.py`: accuracy per read + how often two readers agree and how right they are when they agree.
  Appends to `score_log.csv` (the history: every change and its score).
- `gold_lib.py`: line parsing and comparison. `grab_gold.py`: frame grabber (copied into each run's `tools/`).

## Run a test
1. `python3 -P make_gold_test.py <scratchpad>/gold_runN --per 12 --readers 2 --snaps-from sample_seed1_v261109.json`
   (the frozen 24 snaps of run 5; every run that should be compared with run 5 or later uses this file.)
   For a fresh sample drop `--snaps-from` and give `--n 24 --seed <new>`, then save that run's snaps the same way.
   **The seed alone does not fix the sample.** Snaps quoted in the rule files are dropped before the seeded pick, so a
   new example clip in `front_brief.md` changes which 24 snaps seed 1 gives. Runs 1-4 (10/21-10/22) were picked that
   way and their run folders are gone, so their exact snaps cannot be rebuilt (their logged misses name OPL 46, OPL 123,
   OPK 12 and OPK 108, which are not in the frozen sample). Compare run 5 and later with each other, not with 1-4.
2. Launch one reader agent per `<run>/prompts/*.md` (effort xhigh), each told to read and follow its prompt file.
3. `python3 -P score_gold.py <scratchpad>/gold_runN --label "what changed" --model <reader model>`.
   Add `--no-log` to look at a part-finished run without writing to the history. `--snaps-from <old run>/manifest.json`
   on step 1 reuses an earlier run's exact snaps.

## Change one thing per run
A score moves for three reasons: the brief, the shared rule files the brief tells readers to open, and the model the
readers run on. The log keeps all three (`brief`, `rules`, `model`), so compare two rows only when two of them match.
`rules` is filled from the manifest (`rules_sha`: `front_brief.md` + `defensive_front_definitions.md`) unless `--rules`
says otherwise. To test a new model against an old row, give the readers the old brief and the old rule files (pull
them from git into the scratchpad and point the prompts there).

## Second graded set: shell, blitz, coverage (OPA, 49 snaps)
`gold_fronts.csv` grades fronts only. `score_opa.py` grades what readers say about the secondary, against the chart
Coach made blind on 11/01 (OPQ's defense vs OPA, 49 snaps: line, shell, coverage, blitz and who):
`60_scout_gameplans/2026_wk12_opq/scout/data/filmroom2_chart_v261101c.json`.

    python3 -P score_opa.py <chart.json> <reads_dir> [--csv per_clip.csv]

Reader files are `opa_{a1,a2,b1,b2,c1,c2}.jsonl` in `reader_brief.md` format; a1 + a2 read the same snaps, and so on.
It prints shell, blitz yes / no, how many of Coach's blitzes were caught, coverage (per read, per clear call, and when
both readers agree), exact line, 3 technique side, DT and end technique per man with the wide / tight split.
Baselines, same scorer:

| Readers | Snaps | Shell | Blitz y/n | Coach's blitzes caught | Coverage per read | Coverage, both agree | Exact line | DT per man |
|---|---|---|---|---|---|---|---|---|
| October (11/01), 6 readers | 49 | 92/98 | 79/86 | 7/10 | 51/88 | 24/26 | 36/98 | 151/202 |
| October, the c pair | 17 | 31/34 | 30/34 | 4/6 | 17/34 | 7/9 | 18/34 | 60/72 |
| Fable 5.2 (11/09), the c pair | 17 | 30/34 | 29/34 | 4/6 | 23/34 | 11/12 | 14/34 | 52/68 |
| Fable 5.2 (11/09), the c pair, lean brief (definitions + method only) | 17 | 29/34 | 29/34 | 5/6 | 24/34 | 11/12 | 15/34 | 51/64 |

Rules for this set: the chart is Coach's and never goes to a reader; a rerun uses the rule files as they stood before
the grading (the 11/01 paragraphs in `front_brief.md` / `reader_brief.md` were written from these snaps); 17 snaps is a
small sample, so a 3-read swing is noise. The reader files and prompts are in that week folder: October in
`scout/reads/opa/` (point `<reads_dir>` there for the first row), the Fable 5.2 pair in `scout/reads/opa_f52_v261109/`.
A new reader must not open any `scout/reads/opa*` folder.

## The same readers on wide-angle film (11/10, 60 snaps, six more games)

I had charted 390 snaps of this opponent across 7 games in the film room, but only the 49 above had ever been used to
grade coverage and line. `score_opa.py <merged chart> <reads_dir> --game <code>` now grades any one game from the
merged chart. The fresh run: 10 charted snaps per game from the other six games (seeded, snaps quoted in the rule
files left out), two blind readers each, current rule files, Fable 5.2 xhigh. Readers were told to write technique
numbers even from the wide so the line could be graded.

Cameras: game 1 = end zone + wide, game 2 = tight + wide, games 3-6 = wide only.

| | G1 | G2 | G3 | G4 | G5 | G6 | All six | First game (11/09 pair) |
|---|---|---|---|---|---|---|---|---|
| Coverage, both agree on a call | 0/1 | 2/2 | 2/4 | 5/7 | 6/7 | 2/2 | 17/23 | 11/12 |
| Coverage, per clear call | 5/10 | 5/7 | 5/13 | 13/20 | 14/18 | 8/14 | 50/82 | |
| Coverage, per read | 5/20 | 5/20 | 5/20 | 13/20 | 14/20 | 8/20 | 50/120 | 23/34 |
| Shell, both agree | 5/6 | 7/7 | 7/7 | 4/8 | 7/7 | 5/9 | 35/44 | |
| Shell, per read | 14/20 | 17/20 | 17/20 | 10/20 | 17/20 | 11/20 | 86/120 | 30/34 |
| Blitz yes / no, per read | 20/20 | 20/20 | 16/20 | 14/14 | 14/20 | 18/20 | 102/114 | 29/34 |
| My blitzes caught | - | - | 0/2 | - | 0/3 | 0/1 | 0/6 | 4/6 |
| Exact line, per read | 0/2 | 0/20 | 0/20 | 0/20 | 0/20 | 0/18 | 0/100 | 14/34 |
| DT technique per man | 0/4 | 7/40 | 4/28 | 5/36 | 5/40 | 10/36 | 31/184 | 52/68 |

What it says:
- Without a high end-zone angle the readers cannot give technique numbers: 0 exact lines in 100 reads, and the two
  readers matched each other on 1 of 50 snaps. Reversing my line does not help, so it is not a left / right mix-up.
  The rule "never write a technique number from the wide" stays.
- Coverage when both readers agree drops from 11/12 to 17/23, and they agreed on a call on only 23 of 60 snaps. On
  wide film the pre-fill covers fewer snaps and is less safe, so it stays a suggestion.
- No reader caught any of my 6 blitzes from the wide.
- 10 snaps a game is a small sample: a 2-read swing in one game is noise. Game 1 is the only one with an end-zone
  angle and I had charted the line on only 2 of its sampled snaps, so this run does not test line reads from a good
  camera.
- My line cells with typed notes in them ("5-3-1-5 L-R", "Wide 5-1-3-5", "S7-1-1-S7") are cleaned by the scorer
  (`coach_line`), not in the chart. A cell that is not a full line ("Even", "6 man bear") grades nothing. 10 of 226
  cells needed it.

## Reading the score
- **exact line** = every technique right, offense left to right. **family** = EVEN / ODD / TITE / BEAR, scored two ways:
  the reader's own front word, and `family_from_line` = the family code names from his line (`gold_lib.line_family`, the
  same rule `build_import.py` uses). `misses.csv` in the run folder lists every read that missed, with both.
- **agree / right when agree** decides auto-accept: if two blind readers agree and that's right 95%+ of the time,
  agreed snaps skip Coach's check; only disagreements and spot checks go to him.
- **fair line** (`line_fair`, `fair_agree`, `fair_acc_when_agree`) = exact line, except that an end with no Y on his
  side may be 5 or 9. Coach 11/09: that spot is a judgment because the gaps are not uniform ("a wide 5 with no tight
  end is a 9"); with a Y the exact spot (5 / 7 / 6 / 9) still counts. The OPJ key is his 10/18-19 calls, where a
  wide hand-down end with no Y is a 5, so plain `exact_line` punishes a reader who writes 9 there (run 8: 12% exact,
  31% fair). **Judge a rule change on the fair line**, with `core` (inside men + count) beside it.
- OPJ scores run a little high: the shared rules (`front_brief.md`, `defensive_front_definitions.md`) were written
  from Coach's OPJ corrections. The honest test is the next opponent's film once Coach checks it.

## Runs on the frozen sample (seed 1, 24 snaps, 48 reads, Fable 5.2 xhigh unless noted)

| Run | Setup | Family | Exact | Fair line | Core | 3 side | Nose | Fair: agree / right when agree |
|---|---|---|---|---|---|---|---|---|
| 5 | run-3 brief + run-3 rule files | 42 | 20 | 22 | 26 | 35 | 37 | 10 snaps / 70% |
| 6 | run 5 on Opus 5.5 | 37 | 25 | 27 | 29 | 35 | 42 | 17 / 65% |
| 7 | lean brief (definitions + method only) | 30 | 12 | 16 | 18 | 32 | 28 | 9 / 44% |
| 8 | rule files as of 11/09 morning | 40 | 6 | 15 | 20 | 33 | 34 | 14 / 36% |
| 9 | run 5 at medium effort | 31 | 11 | 13 | 17 | 32 | 23 | 8 / 38% |
| 10 | live 11/09 rule files: end reworded, "write the tighter one" out, OPQ lines kept | 42 | 15 | 21 | 26 | 35 | 36 | 14 / 57% |
| 11 | run 10 minus the six OPQ-derived `front_brief.md` lines | 41 | 20 | 24 | 28 | 37 | 39 | 15 / 60% |

48 reads per run = about 7 points of noise on any one number (3 reads). Compare two runs snap by snap, not by totals.
No run is near the 95% auto-accept bar on the line. FAMILY is: when two readers agree on the family they are right
20 of 21 (runs 5 and 10), 20 of 22 (run 11).

## Rules cut 11/09 (Coach: test the OPQ rules, cut the ones that don't earn their place)

Six `front_brief.md` lines written from OPQ film were never tested on a key. Run 10 kept them, run 11 cut
them, everything else the same. Run 11 was equal or better on every line number (fair line 24 vs 21, exact 20 vs 15,
core 28 vs 26, 3 side 37 vs 35, nose 39 vs 36); run 10 led only on family, by one read. All of it is inside the noise,
so the finding is "the lines did not help", not "the lines hurt". A rule has to earn its place, so they came out.

Limits of this test:
- It was one block (all six in or all six out). 48 reads cannot resolve one line at a time.
- The OPJ key grades the line only. The four lines about the box, backers and pressure are not graded by it.
  The evidence for those is the lean-brief pair on the OPQ vs OPA chart (table above): no rule files at
  all, and shell, blitz and coverage scored the same as the full brief.
- The end-width rule is still live in `recognition_card.md` and `reader_brief.md`; only the copy here was cut.

To put one back, paste it into `front_brief.md` under "Calibration rules", rerun on the frozen sample, and keep it only
if the paired count goes up. The cut text, word for word:

- **Use the whole ladder (Coach 10/25, OPQ).** The old nose line named only 0 / 1 / 2i and warned off 1, and readers over-called 2i. Pick from 0, 1, 2i, 2, 3 by the guard's eyes and shoulders; when you can't split 2i / 2 / 3, mark the line conf L instead of defaulting to 2i.
- **Name an end by his width (Coach 10/22, 11/01, 11/09).** Aligned on the LOS with the DL and postured to rush = on the line, standing or not. With a Y on his side, name the exact spot: 5 (tackle's outside shoulder), 7 (Y's inside), 6 (head-up on the Y), 9 (outside the Y). With no Y on his side it is a judgment, because the gaps are not uniform: tight on the tackle = 5, a wide 5 = 9, and either is accepted. What matters there is that he is on the list (OPQ 110: a wide standing end was left off the line; Coach had 5-0-9).
- **Read the defense's personnel before naming overhangs (OPQ 14/155).** In a 4-2-5, the box-side apex player opposite the RB is a WILL/ILB, and the slot defender to the field is a nickel. Neither is an "overhang". Name them by role.
- **The hash decides box or not (OPQ 98/107).** On the boundary side the field is condensed, so a player apexed between the tackle and #2 can play the box and still cover the slot = count him as a box player. Box is never fewer than the DL plus the MIKE (107: 4 DL + MLB = 5, reader wrote 4).
- **"Walked up" means shallower than his usual depth (OPQ 110).** A backer at his normal 4-5 yds is not walked up, so don't flag him. When two backers show, say which one came (OPQ 145: #36 blitzed, #40 dropped).
- **The set frame comes after the motion settles (Coach 10/24, OPQ vs OPR 10).** Backers move with a motion man; a frame grabbed mid-motion made a 4.5-5 yd MIKE look walked up at 3 and became a false pressure flag. Grab at the last still moment before the snap. A MIKE who follows a rolling QB or drops is not pressure (OPR 6); a standing man at line depth who plays as a D-lineman is on the line, not a backer (OPR 9); backers flowing on an outside-zone RPO are a run fit (OPR 3).
