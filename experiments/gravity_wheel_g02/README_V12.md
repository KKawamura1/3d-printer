# GW02-V12: flat-backed, tool-free print prototype (Issue #99)

V11's print orientation put the rotor split faces on the build plate. Each half-cup
then grew an arched roof whose unsupported Bambu Studio bridge paths required
nine breakaway posts. **V12 fundamentally changes the rotor cross-section and
print orientation**; it is not another post added to V11.

## New geometry

- Two rotor halves meet at Y=0 as before; four separate dowels and the
  existing DUPlO-bearing stands/axle remain.
- Each half has an **outer flat side panel** at Y=±16 mm, covering the
  intended ball channel. The two radial rails, hub and spoke connect to it.
- The **outer flat panel faces the print bed**. The ball running cavity and
  relieved rail areas expand as layers rise toward the rotor split.
- All **nine V11 sacrificial posts are eliminated**.
- The stop lug no longer projects beyond the bed-facing side panel. To
  retain the stop interaction, the stationary stop pin is extended inward.
- V4's 24.26 mm ball, inward slot, lifting lip, 160/170/180 stop hole
  locations, bearing/DUPlO stand interfaces, and 4-dowel scheme are reused
  as far as possible. **The cup wall shape, overall rotor thickness and
  stop-pin length HAVE changed**: do not interpret as drop-in parity.
- Output still has **10 separated printable objects** in a SINGLE
  `print_plate.stl` (two rotor halves, two stands, axle, stop pin,
  four dowels), arranged for the A1 mini 180x180 mm bed.
- `assembly.step` is free of printer-only supports.

## Critical verification

1. `python -m unittest experiments.gravity_wheel_g02.test_open_cup_v12 -v`
2. `python -m experiments.gravity_wheel_g02.open_cup_v12 --out build/gw02-v12`
3. Check `report.json` and STL watertightness; this is **CAD-only**.
4. Import **print_plate.stl as a single file** into Bambu Studio, preserving
   the provided orientation and placement. Profile: Bambu Lab A1 mini,
   PLA Basic, 0.20 mm Standard, support **OFF**.
5. Inspect the full *rotor* toolpaths in Preview, not only the mesh.
   Look for long unsupported `FEATURE: Bridge` paths, sudden starts of
   overhanging walls and floating islands. Save the actual G-code and
   verify the path and support footprint. **No actual slicer PASS yet.**
6. Only after slicing PASS: print the two rotor halves first, then test
   4-dowel assembly and a 24.26 mm ball. If that succeeds, print the full
   10-part plate and test stop, spin, release and impact loads.
7. **Keep away from children until attachment retention, shaft securing,
   impact resistance, and small-part hazards are addressed.**

## Open engineering questions

- Flat side panels increase the running-cavity's planarity and change
  ball retention and rotational inertia relative to V4/V11.
- The new inward-extended stop pin may intersect the rotor before target
  engagement; dynamic release is not validated.
- CAD shape success does not prove that Bambu Studio's actual print paths
  are supported: `slicer_validated: false` until G-code review.
- Physical ball release and wheel rotation are separate experiments.

Related: [Issue #99](https://github.com/KKawamura1/3d-printer/issues/99) /
[PR #97](https://github.com/KKawamura1/3d-printer/pull/97).
