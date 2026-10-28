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
1. `python3 -P make_gold_test.py <scratchpad>/gold_runN --n 24 --per 12 --readers 2 --seed 1`
   (same seed = same snaps; change the seed for a fresh sample.)
2. Launch one reader agent per `<run>/prompts/*.md` (effort xhigh), each told to read and follow its prompt file.
3. `python3 -P score_gold.py <scratchpad>/gold_runN --label "what changed"`.

## Reading the score
- **exact line** = every technique right, offense left to right. **family** = EVEN / ODD / TITE / BEAR.
- **agree / right when agree** decides auto-accept: if two blind readers agree and that's right 95%+ of the time,
  agreed snaps skip Coach's check; only disagreements and spot checks go to him.
- OPJ scores run a little high: the shared rules (`front_brief.md`, `defensive_front_definitions.md`) were written
  from Coach's OPJ corrections. The honest test is the next opponent's film once Coach checks it.
