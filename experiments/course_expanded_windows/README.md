# More viewing windows on six other tunnel rails (2026-11-22)

This experimental branch extends PR #75's architectural windows while preserving every previously generated version, the channel geometry, existing rail connection mouths, studs and E31-05 receivers. This is independent of PR #85's SC02-right clearance experiments.

| PR75 reference | New comparison ID | Windows before → after | Change |
| --- | --- | --- | --- |
| E01-V8 | E01-V10 | 6 → 8 | two 32mm flat facades, 3 → 4 each |
| E01L-V6 | E01L-V8 | 6 → 8 | mirrored E01, same layout |
| SC02L-V11 | SC02L-V13 | 3 → 5 | long outer convex, width 10mm |
| SD03-V16 | SD03-V18 | 6 → 8 | outer straight+convex 3 → 5; inner flat remains 3 |
| SD04-V21 | SD04-V23 | 6 → 8 | mirrored long outside wall, same |
| T01-V7 | T01-V9 | **3 → 3** | 2x2 is compact enough; keep three 5.5mm windows, only enlarge ID |

E01's short 32mm side walls need four *narrower* 4.5mm windows to keep at least 2.5mm
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

## Shared enlarged ID marking (Issue #83)

This revision increases *engraved ID letter height* from 3.0mm to
**5.0mm (1.67x)**, while keeping engraving **depth 0.40mm**.
The new shared `brickcad/course_marking_v2.py` helper uses bold DejaVu Sans
and places each ID on an exterior south/west planar face below the windows.
It verifies the *actual BRep text cutter* is at least 70% supported by intact
material, and that windows have removed at most 0.01 mm³ from the lettering
area. It additionally checks the resulting shape remains one BRep and keeps
original overall dimensions. These are CAD guards, not proof of legibility
at 0.20mm layer height; measure the 5mm trial on A1 mini before generalizing.

The former 3mm-only production marking contract remains unchanged for
historical builds. This experiment uses an opt-in v2 marking policy and
bumps all six IDs; earlier 3mm-only window variants remain available in the
original PR #87 workflow artifacts (2026-11-22 initial run).

Related issue: #83. Do not change the historical 3mm CAD source/contract to
make past artifacts appear to have the new engraving.

CAD verification is explicit and only for these six new v2 IDs.

On the two sharp sloped curves (SD03/SD04), the 5mm glyph intersects a
more complicated sloped shell than on horizontal rails. The v3 generator
tries several recorded Z bands and accepts only a candidate that passes the
**same exact collision, glyph coverage and single-solid criteria**. It
fails closed if all locations are unsuitable. This is intentional rather
than silently reducing text height for those two variants.

The v3 run also retains the original six-model geometry/fit checks.

The first 5mm trial found scalar subtraction-vs-intersection volume
inconsistencies for both sharp-turn loft bodies, even though the letters
were supported and the resulting BRep remained a single valid solid.
The next revision uses an **exact negative geometry check** when the two
scalar volumes differ: material lost outside the intended glyph tool, or
material mysteriously added, is not accepted. An unproven scalar-only
workaround is not used to waive the window overlap guard.

This run rechecks the exact letter-cut BReps for all six specimens.

### User visual feedback (2026-11-22)

T01 (2x2) has too many narrow windows in the four-hole rendering: restore
three wider 5.5mm windows (as in PR75) for its 5mm engraving revision.
For E01 (4x4), the dense solid outside the R48 curve is undesirable. A
separate stacked *compact arc-body* experiment will compare trimmed curved
shells plus windows on the actually visible outside bend, rather than simply
adding ornamental holes to the old four-by-four solid. SC02's curved
footprint is the reference, but original 4x4 stud/tube connections may no
longer be available everywhere and require dedicated tests.
