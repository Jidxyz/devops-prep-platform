# Drill apps

Three self-contained HTML tools over the same matrix data. Each is a single file
with the questions and answers embedded — **no server, no build step, no
dependencies.** Download and open in a browser.

Currently loaded with **Git (152 items)** as a working scope. The other fourteen
domains are structured for but not yet wired in.

| File | Model | Use it when |
|---|---|---|
| [`focus.html`](./focus.html) | One card at a time, in finite sessions | You have ten minutes and no willpower |
| [`map.html`](./map.html) | All 152 items as an explorable branch graph | You want to see where you're weak and pick |
| [`checklist.html`](./checklist.html) | Scored list with expandable answers | Doing a deliberate scoring pass, or reading |

## Shared behaviour

- Scores are **0 / 1 / 2**, matching the matrix's own scale, so totals reconcile
  with the scoring summary tables.
- Progress saves to `localStorage`, **per browser**. Use **Export** to write a
  `scores.json` you can back up or move between the three apps — they share the
  same format.
- Keyboard throughout. In `focus`: `space` reveals, `1` `2` `3` score, `esc`
  ends the session. In `map`: `J` jumps you to the highest-value item, arrows
  step, `space` reveals.

## Regenerating the data

`extract.py` parses the matrix and an answer key into the JSON the apps embed:

```bash
python3 extract.py            # writes git-data.json
```

To add another domain, adjust the line range and item-prefix pattern at the top
of the script, then rebuild the HTML with the new JSON substituted for the
`/*__DATA__*/` placeholder.
