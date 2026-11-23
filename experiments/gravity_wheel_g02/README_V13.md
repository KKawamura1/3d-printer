# GW02-V13 — stand receiver roof bridge relief (Issue #99)

V12's actual Bambu Studio G-code showed two different classes of `Bridge`
extrusion: the rotor's longest paths were supported about every 2–3 mm by
infill; the **two fixed DUPLO stands** included continuous unsupported spans
of about **23.4 mm at Z≈5.0 mm**. Do not diagnose based solely on the nominal
length of a `FEATURE: Bridge` G-code line.

## Change vs V12
- **No change** to the two rotor halves, the axle, stop pin or four joiners.
- Both V4-derived fixed stands retain **all geometry below Z=4.70 mm**:
  shared E31-05 underside, 4.75 mm receiver depth, tube radius 6.60 mm and
  surrounding snap interfaces. The entire central pillar/bearing above
  Z=6.52 mm is also unchanged.
- Subtract **four rounded, annular-corner roof windows per stand**, from
  Z=4.74 to 6.52 mm. Quadrant opening bounds are approximately
  |X|, |Y-local| ∈ [2.5, 13.0] mm, intersected with
  *outside* a 7.35 mm central tube exclusion and *outside* the 12.8 ×
  10.8 mm protected footprint of the upright stem. Corner radius 0.6 mm.
- The windows do **not** require breakaway posts or additional assemblies.
  Ten independent STL objects remain on one A1 mini plate.

### Expected benefit, not a slicer measurement
Using V12 STL XY cross-sections (Z=4.6 as supporting layer vs Z=4.8
as roof), with 0.35 mm XY tolerance and 15° directional scans,
a comparable four-quadrant curved-window candidate shortened the
*geometric* estimated unsupported chord from ~25.6 mm to ~10 mm.
The generated V13 Bambu Studio G-code **must be checked**: this estimate is
not slicer-derived; local corner fillets and support patterns may alter it.

### Validation gate

1. V13 unittest and CAD/mesh CI success, one 10-part `print_plate.stl`
   within the 180×180 mm bed. `report.json` identifies changed roofs.
2. Import the STL into Bambu Studio **0.20 mm Standard / A1 mini /
   PLA Basic / support OFF**. Inspect stand bridges at Z=4.8–5.2 mm,
   rotor at Z=1.6 mm, and the thin upright axle. Verify real G-code
   extrusion support; the *length of Bridge path alone is insufficient*.
3. If no dangerous unsupported spans remain, print **two stands only**
   first. Verify E31/LEGO DUPLO fit, standing stability and stop impact
   strength before assembling and spinning the rotor.
4. Test rotor ball retention and ~160–180° impact release separately.
   V13 has **not been physically validated** and is not suitable for
   children until all fastening and small-part hazards are addressed.

This experiment builds on [Draft PR #100](https://github.com/KKawamura1/3d-printer/pull/100)
and follows [Issue #99](https://github.com/KKawamura1/3d-printer/issues/99).
