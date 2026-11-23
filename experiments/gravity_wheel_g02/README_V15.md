# GW02-V15 — stop bug patch + experimental DUPLO rail adapters

## Photo finding

The V14 printed roller does spin freely with the pin removed. The little
cylindrical stop lug is on the **INSIDE** of the rear side panel; this is a CAD
bug. V12-V14 places it at local Y=12..16 while the panel is Y=13.65..16,
leaving 1.65mm in the cup. The overly long pin begins at Y=8 and intersects
the cup rather than hitting only the lug.

## Repair WITHOUT reprinting either rotor

Reuse your complete, printed V14: **both rotor halves, both stands, axle, four
small dowels**. Discard the old long stop pin. V15 introduces two small repair
parts:

1. `stop_boss.stl`: a **9×9mm flat adhesive foot** with 6mm diameter external
   striker on it. The flat side is meant to be **bonded onto the OUTSIDE of
   the stopping-side rotor half at the point (X=0,Z=+42) relative to the
   centre axle**. Its root is at **Y=16mm**, where the original outer panel
   ends. It projects to Y=21.8mm.
2. `stop_pin.stl`: shorter removable stationary pin occupying
   **Y=17.8..44mm**. Insert into the existing 170° bracket hole. This pin
   stays entirely outside the original Y<=16mm cup wall.

**IMPORTANT**: Glue can fail in a hard stop; this is an **adult-controlled
low-force bench experiment**, not a child-safe or impact-rated finished
stopper. Apply no force or balls until adhesive has cured and verify the boss
holds by hand. If you want a durable stop, a redesigned snap-mechanism or
clamped connection is required. The original inward protrusion still exists:
if it catches the ball, do NOT force it; a flush cut/replacement rotor
remains a separate design decision.

## New DUPLO-compatible guide heads

Both use the measured existing straight-rail section:
**outer width31.65mm / open width25.74mm / 24.26mm ball / floor6.35mm**;
their underside uses the same shared **E31-05 2×2 DUPLO receiver** as V14.

- `entry_guide.stl`: mount its 2×2 receiver **4 full DUPLO bricks high**
  (4×19.2 = 76.8mm relative to the GW02 foot underside) on the right.
  Its near tip is X=+67mm, its standard butt-to-rail port X=+96mm at
  running-floor Z=83.15mm.
- `exit_guide.stl`: mount receiver **at the same height as GW02 feet**
  on the left. It spans X=-80mm (standard butt-to-rail port, Z=6.35mm
  running floor) to X=-47mm (uphill end near wheel, Z=15.0mm floor).
  A central integral web supports the rising track and remains in place.

The user can build higher/lower DUPLO towers as appropriate. The outer
ports have the same nominal width and floor datum as existing straight rails.
**They are not male/female click connectors**, but plain matching end faces.
Put regular straight rails next to the outer end and lock their bases to the
same DUPLO grid.

### IMPORTANT remaining function gap

The entry/exit lips are deliberately outside the rotating wheel's swept
envelope. The guide near mouths are at X=+67 / X=-47 while the original V4
theoretical cup mouths are about X=+29.73 (at rest) / X=-24.45 (170° stop).
Therefore handoff requires a **~37mm entry gap** and a **~23mm exit gap**
in X; the wheel cannot receive a slowly rolling ball across a large gap
by simply lining up the printed parts. **Do not assume this is a working
automatic transfer**; the guides are a starting datum to make real existing
DUPLO rails approach the machine. Closing the gap while avoiding the swept
wheel requires a subsequent movable/detachable funnel or redesigned cup
geometry. We explicitly test stationary guide clearance over 0..170°.

## CAD files
- `replacement_plate.stl`: **stop_boss + stop_pin + 2 guide heads**,
  four separate printable objects in one A1 mini plate.
- `guide_plate.stl`: guide heads only.
- Individual `stop_boss.stl`, `stop_pin.stl`, `entry_guide.stl`,
  `exit_guide.stl`; original V14 files stay available.
- `assembly.step` is only a mechanical arrangement/reference.

**Before printing**: verify slicer Preview, bridges, floating layers and
support removal on the new pieces; the CI CAD tests do not validate G-code.
**Before ball tests**: verify no early pin collision, hold the fixed base,
wear eye protection, and keep all PLA pins and balls away from children.
