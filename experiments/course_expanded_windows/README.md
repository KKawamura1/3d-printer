# More viewing windows on six other tunnel rails (2026-11-22)

This experimental branch extends PR #75's architectural windows while preserving every previously generated version, the channel geometry, existing rail connection mouths, studs and E31-05 receivers. This is independent of PR #85's SC02-right clearance experiments.

| PR75 reference | New comparison ID | Windows before → after | Change |
| --- | --- | --- | --- |
| E01-V8 | E01-V9 | 6 → 8 | two 32mm flat facades, 3 → 4 each |
| E01L-V6 | E01L-V7 | 6 → 8 | mirrored E01, same layout |
| SC02L-V11 | SC02L-V12 | 3 → 5 | long outer convex, width 10mm |
| SD03-V16 | SD03-V17 | 6 → 8 | outer straight+convex 3 → 5; inner flat remains 3 |
| SD04-V21 | SD04-V22 | 6 → 8 | mirrored long outside wall, same |
| T01-V7 | T01-V8 | 3 → 4 | 2x2 short flat, width 4.5mm |

Short 32mm walls need four *narrower* 4.5mm windows to keep at least 2.5mm
nominal material between windows (3mm nominal at both ends).
Long outside curves have five windows, with 8mm width (sharp curve) or
10mm width (SC02L). Each CAD cut must pass connected BRep, original bounds,
material removal, actual sightline to the ball, lower guard, watertight STL,
and model ID engraving checks. The *nominal gap* calculation alone does not
establish strength of printed layers.

**Intentionally unchanged:** SC02-right (PR #85); compact C02 and three
steep vertical shafts (S01/S02/S03) which already use one opening; the
printed D01-V3; and all concave walls. Do not weaken a short thin-walled
part merely to increase window count.

## Focused development workflow

Run fast non-export tests:

    python -m unittest experiments.course_expanded_windows.test -v

Generate just one BRep/STL for iterative review:

    python -m experiments.course_expanded_windows.design --model SD03-V11 --out build/course-expanded-one

For all six, manually start **CAD preview and print artifacts** with
targets=experiments/course_expanded_windows. Its cad-build.json is auto:false
to avoid another slow CI generation on every PR push. Each version is a
separate STL and report; no multi-model print plate is imposed.

A successful CAD export is NOT slicing, durability, child safety, connector
fit or rolling validation. Inspect actual renderings and Bambu Studio
support-off slicing, print only selected specimens initially, and record
wall stiffness, bond strength and rolling behaviour.

Related: PR #75, #85; issue #37. Parent CAD/fit: PR56 and E31-05.

Automated CAD validation for all six can also be launched in parallel via
Actions > Expanded course windows CAD comparison. On the isolated experiment
branch, adding [generate-expanded-windows] to a change commit opts in. Unlike
the normal build, this intentionally skips slow snapshot rendering.
