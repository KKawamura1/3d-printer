# E01 compact R48, curve-side window experiment

Following the real STL preview, T01 is back to three windows in PR #87.
E01's old square 4x4 shell leaves a huge unused bulk around the R48 tunnel;
adding more deeply buried holes on its square facade does NOT address jams
inside the bend. SC02 already uses a compact quarter-annular footprint.

## Dedicated versioned comparison

| Legacy / PR87 | New candidate | Aperture arrangement |
| --- | --- | --- |
| E01-V10 (4x4 square) | E01-V11 | 9 x 6.5mm on the actual convex bend |
| E01L-V8 (mirror) | E01L-V9 | 9 x 6.5mm on the actual convex bend |
| T01-V9 (PR87 only) | not in this PR | retains three 5.5mm windows |

- Keep the original horizontal E01 ball passage and both mouths via SC02's
  quarter-ring footprint `curved_footprint()` and BRep intersection.
- Seven? No: **nine real windows**, distributed across ~100mm external curve
  with >3mm nominal pillars. Each opens an optical path to the ball.
- Use the new 5mm shared ID engraving, relocated to the SC02-like west face.
- Do not claim to retain **full 4x4 connection coverage**: removed corner
  areas necessarily remove portions of top studs and bottom E31 receivers.
  Count safely complete sites and keep the original surviving connector
  geometry unmodified; inspect cut edges/partial connectors before printing.
- Tests require unchanged sampled inlet/outlet and internal track occupancy,
  single valid solid, same 4x4 max envelope, preserved lower window guard,
  5mm marking without viewport collision and watertight STL.
- This is opt-in CAD-only, not physical strength, rolling or fitting proof.
  Original square E01 variants and their STLs remain unaffected.

Run fast tests:
`python -m unittest experiments.course_compact_r48.test -v`

For one side:
`python -m experiments.course_compact_r48.design --model E01-V3 --out build/compact-e01`

The separate workflow uses 2 parallel jobs only when explicitly requested,
to avoid adding expensive full BRep exports to every push.

Related: PR #75, #87, #85, issues #37, #77, #80, #83.

First CAD trial: both bend directions, no slow preview generation yet.
