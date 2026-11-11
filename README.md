# AI film breakdown: parallel Claude agents tag game film, scored against a coach's answer key

High school football staffs spend hours each week tagging game film in Hudl, filling in down, distance, field
position, formation, defensive front and result for every snap. This repo is the workflow I built during the
2026 season to do the first pass automatically. It cuts the film into frames, splits the game across parallel
Claude reader agents, reconciles their reads into a Hudl import file, and hands me a short check list of the snaps
it isn't sure about. I coach high school football, so I'm both the builder and the user.

It tagged **about 980 snaps across nine games** in October 2026, covering our own games and opponent scouting film.

The part I'd point a reviewer to isn't the vision. It's the loop around it: an answer key I built by hand,
blind readers, a scoring script, and a rule that **a change to the agents' instructions stays only if the score
goes up.**

![Defensive-front accuracy across four scored instruction changes](docs/gold_runs.png)

## How it works

```mermaid
flowchart TD
    Z[Hudl film zip<br/>~100-140 clips] --> S[make_sheets.py<br/>contact sheets,<br/>per-second strips]
    S --> R1[Reader agent<br/>clips 1-38]
    S --> R2[Reader agent<br/>clips 39-76]
    S --> R3[Reader agent<br/>clips 77-114]
    R1 & R2 & R3 --> F[Formation and<br/>front passes]
    F --> C[Reconcile<br/>possession timeline,<br/>quarters, overrides]
    C --> B[build_import.py<br/>precedence rules]
    B --> X[Hudl import .xlsx]
    B --> L[Check list<br/>for the coach]
    L --> K[I correct] --> X
```

1. **Frames.** `make_sheets.py` pulls six stamped frames per clip from the wide camera into a contact sheet, and
   `snap_strip.py` adds one frame per second so a reader can pick the moment the offense is set. About a minute
   per game.
2. **Parallel readers.** One agent per ~35-40 clips, each with the reader brief (`skill/reader_brief.md`), the
   team codes and jersey descriptions, and the three clips before its range for context. Each agent writes one
   JSON line per clip as it goes. A ~110-snap game finishes in roughly 15-20 minutes.
3. **Specialist passes.** A formation pass (`skill/formation_brief.md`) names every offensive snap in our own
   terminology, and a front pass (`skill/front_brief.md`) lists every defensive lineman's alignment.
4. **Reconcile and build.** Possession must make football sense: every series ends in a score, punt, turnover,
   downs or the half. `build_import.py` then merges sources in a fixed precedence (frame reads < agent
   overrides < Hudl Assist < my own tags < approved fixes) and writes a Hudl-ready import file with the
   same row count as the film.
5. **Check list, not a re-tag.** I get a short list of the snaps that change the scouting picture, review
   those, and my corrections win.

## Measuring it: the gold set

Early on, the agents' defensive-front calls were still well off my own reads. The fix was to measure, not to
add more adjectives to the prompt.

- **Answer key:** I checked every defensive front on one opponent's film by hand (104 snaps).
- **Blind test:** `eval/make_gold_test.py` picks a seeded sample spread across front types, pulls only those
  clips, and leaves out any snap quoted as an example in the instructions.
- **Two readers per snap:** both read every snap independently. `eval/score_gold.py` scores each read and records
  how often the two agree and how often they're right when they do.
- **Auto-accept target:** if two blind readers agree and are right 95%+ of the time, agreed snaps can skip my
  review and only disagreements come to me.

| Run | Change | Front family | Core line | Exact line |
|---|---|---|---|---|
| 1 | Baseline line-count brief | 75% | 58% | 46% |
| 2 | + 6 worked example frames | 83% | 60% | 48% |
| 3 | + my interior-first rule + 3 examples | **88%** | **62%** | **52%** |
| 4 | + 2 more rules from a recheck | 85% | 60% | 48% |

In run 3, the two readers agreed on the front family on 88% of snaps and were right on 20 of 21 of those (95%),
which meets the auto-accept target on this sample. Run 4 added two sensible-sounding rules and lost ground, so
**both rules came out** and run 3 stayed the base. The full history is in `eval/score_log.csv`.

What the numbers taught me: worked examples and prompt rules fix *category* errors (counting a walked-up
linebacker as a lineman, missing a hidden nose tackle). The fine splits that remain (a 3-technique vs a 4i)
need measurement from the image, not more prompt text.

### November: testing the rules I already had

By November the briefs had picked up rules from later opponents that had never been scored. I froze one sample
(24 snaps, two blind readers, 48 reads per run) and re-ran it with one thing changed at a time. 48 reads means
about 3 reads of noise, so the honest answer to most changes is "no gain", and then the rule comes out.

| Run | Change | Front family (of 48) | Fair line | Core line | Right when both agree (fair line) |
|---|---|---|---|---|---|
| 5 | Run-3 brief and rule files | 42 | 22 | 26 | 70% |
| 6 | Run 5 on a different model (Opus 5.5) | 37 | 27 | 29 | 65% |
| 7 | Lean brief: definitions and method only | 30 | 16 | 18 | 44% |
| 9 | Run 5 at medium reasoning effort | 31 | 13 | 17 | 38% |
| 10 | Current rule files with six later rules kept | 42 | 21 | 26 | 57% |
| 11 | Run 10 without those six rules | 41 | 24 | 28 | 60% |

"Fair line" counts the exact line, except that an end with no tight end on his side may be a 5 or a 9: the gaps are
not uniform, so that spot is a judgment call.

- **The six later rules came out.** Run 11 was equal or better on every line number. The difference is inside the
  noise, so the finding is "they did not help", not "they hurt". The cut text is kept in `eval/README.md` so any one
  of them can be re-tested.
- **An older rule came out too.** "Write the tighter technique when unsure" cost six reads.
- **Model and effort.** The two current models split the numbers (one better on family, the other on the line), so
  the model is not the bottleneck. Lowering the reasoning effort was a clear loss.
- **The lean brief was much worse on fronts** but read the shell, the blitz and the coverage as well as the
  full brief. The worked examples and rules earn their place on the line, not on those calls.
- Still no run is near the 95% auto-accept bar on the exact line. On the front *family*, agreed reads were right
  20 of 21 (runs 5 and 10) and 20 of 22 (run 11).

### Coverage: pre-filled, not auto-accepted

When both blind readers agreed on a coverage, they matched my call 24 of 26 times in October and 11 of 12 on the
newer model. `scripts/agreed_calls.py` now pre-fills an agreed call in the film room for me to confirm. A
Cover 4 from a two-high shell or a Cover 0 with nobody deep is a one-tap suggestion; any other agreed call is shown
as a question with no button. Nothing is saved or printed until I tap.

### The same readers on wide-angle film

The coverage and line numbers above came from one game with a high end-zone camera. On 11/10 I ran the same readers
on 60 more snaps I had already charted, from six other games of the same opponent. Four of those games are
wide-angle only.

| | Six games, mostly wide angle | The end-zone game |
|---|---|---|
| Coverage right when both readers agree | 17 of 23 | 11 of 12 |
| Snaps where both readers agreed on a coverage | 23 of 60 | 12 of 17 |
| Exact defensive line, per read | 0 of 100 | 14 of 34 |
| My blitzes caught | 0 of 6 | 4 of 6 |

The camera decides what the readers can do. From the wide they cannot read technique numbers at all, they miss
blitzes, and an agreed coverage is right about three times in four. The full table is in `eval/README.md`.

## Lessons from the calibration log

Every miss I caught became a dated rule tied to the clip that taught it (`skill/SKILL.md`, "Calibration
log"). A few that generalize beyond football:

- **"I don't know" beats a guess.** On far-side plays, readers called run vs pass right on 1 of 6. The brief now
  requires `null` and low confidence when the handoff or throw isn't visible, and those snaps come to me.
- **Rules can be measured.** After a round of formation rules, a blind re-read of 45 unchanged clips went from 17
  to 26 correct.
- **Long-running agents must save as they go.** Three readers lost a whole game's work to API timeouts before
  writing their output. Now each clip is appended as it's read.
- **Heuristics are hints, not answers.** A motion detector picked the "snap" at 1.2 seconds on a clip whose real
  set was at 11 seconds (players walking up), and the reader named the wrong formation from that frame. Readers
  now choose the set moment from a per-second strip.
- **Cross-check sources.** Where the film has a burned-in scoreboard, its down and distance disagreed with the
  spot-built chain on 6 of ~90 snaps; the board wins.

## Known limits

- Coverage is never written from frames without my confirmation. Single readers can't reliably tell the two
  safeties' depths apart; agreed calls are pre-filled for me to confirm (see above).
- The line and blitz reads need a high end-zone camera. From a wide-only angle, exact lines were 0 of 100 and
  blitzes caught 0 of 6 (11/10 test).
- Ball spots are about ±3 yards, worse on the far hash.
- Telling whether the tight end is on or off the line from a sideline angle is hard, so those calls are marked
  low-confidence for review.
- A human read beats every frame read. When I disagree, the frames get re-checked and the rule goes into the
  brief.

## How this was built

I designed the workflow and the rules, built the answer key, and made every keep-or-kill call on the scores. **Claude Code wrote most of the code and runs the reader agents.** My job was
knowing what a correct read looks like, deciding what to measure, and not trusting a change until it scored.

## Repo map

| Path | What's there |
|---|---|
| `skill/SKILL.md` | The full runbook, including the dated calibration log |
| `skill/*_brief.md` | Instructions given to the reader, formation and front agents |
| `skill/scout_questions.md` | My standing scouting questions; every report section has to answer one |
| `skill/recognition_card.md` | Recognition card the readers use: technique numbers and the count rule for naming fronts |
| `scripts/` | Frame extraction, snap strips, import builder, tag comparison, naming board, agreed-coverage pre-fill |
| `eval/` | The gold-set test: sample picker, scorer, score history, the brief under test; `score_opa.py` scores readers against my blind chart of one game |
| `templates/front_board.html` | Page I use to name groups of similar fronts |

These are the working scripts from my coaching workspace, lightly edited for publication, not a packaged library.
In the runbook and briefs, "Coach" means me; the agents address their output to me.

## Privacy

No game film, frames, or player names are included. Opponents are anonymized to codes (OPA, OPB, ...), and the
answer key isn't published; `eval/gold_fronts_example.csv` shows its format.
