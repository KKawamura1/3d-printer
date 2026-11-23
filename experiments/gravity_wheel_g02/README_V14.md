# GW02-V14 — reduce automatic support by changing the actual part shape

Issue #99 follow-up to V13. The user's support-enabled A1 mini G-code
(`GW02-V13_print_plate_A1mini_PLA_2h25m.gcode`, PLA Basic, 0.20mm,
tree(auto), support threshold 30°) places support not only under the two
DUPLO receivers, but at four rotor lip ends and below the stop fan.

**Goal:** Make those overhangs naturally self-supporting so Bambu Studio
requires little or no auto support. This is a **candidate design**; it cannot
claim zero support until support-ON G-code from the *new* STL confirms that.

## Changes

1. Two permanent 2.7 mm wide lip-to-side-panel webs **per rotor half**,
   located at the lip exits. Unlike V11's nine breakaway posts, these
   connections are part of the working rotor and will not be removed.
   The webs attach the tips at |Y|=10.8..16 to the existing print-bed
   outer panel. We must verify the 24.26 mm ball can still exit at impact.
2. Extend each central DUPLO tube cavity **above** the verified 4.75mm
   E31-05 insertion depth with a conical relief: at Z=4.74 the radius
   is 4.68mm, tapering to 0.15mm over 8mm. Sloped ceiling ~60.5°
   above the bed replaces a ~9.4mm horizontal hole roof.
   The receiver geometry **below Z=4.70** is unchanged; physical
   fit/strength still need testing.
3. The rear stand gets two thin permanent 1.8mm wide brackets at
   Y-local 0.5..2.3mm, which rise from the foot's existing roof cross
   at Z=6.35 to the underside of the stop fan at Z~19. The axle and
   removable stop pin remain identical.
4. Keep V13's four windows per foot, 10 independently printable parts
   in one A1 mini `print_plate.stl`, and zero sacrificial supports.

## Critical verification

- `python -m unittest experiments.gravity_wheel_g02.test_open_cup_v14 -v`
- `python -m experiments.gravity_wheel_g02.open_cup_v14 --out build/gw02-v14`
- Import `print_plate.stl` in Bambu Studio with the same **A1 mini /
  PLA Basic / 0.20mm Standard / tree(auto) / support threshold 30°**
  as V13. Recheck **actual** `Support` and `Support interface`
  G-code at rotor ends (Z4.2..5.2), at both foot roofs (Z4.2..5.2)
  and stop fan (Z14..20). Do not infer zero support from this README.
- Independently slice with **support OFF** and check that no new
  bridge/floating extrusion is introduced.
- Print only two stands and then two rotor halves *after* slicer audit.
  Inspect underside finish, coupling with real DUPLO, full ball
  retention/release trajectory, stop pin impact and fatigue. Until
  testing, this is an adult bench prototype, not child-safe.

The conical hole lengthens the central internal void and the lip webs
alter the exit profile: neither change is mechanically proven.
