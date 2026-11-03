"""E31-05 R48 horizontal tunnel, mirrored left/right before per-side marking.

The historical parts/elbow E01-V2 and play-set stay immutable. See issue #37.
"""
from dataclasses import asdict, replace
from pathlib import Path
import hashlib
import json
import math
import struct

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.marking import engrave
from brickcad.model import brick_from_fit, receiver
from brickcad.provenance import design_manifest
from brickcad.standards import ROUNDED_EDGES
from brickcad.verify import exact_bounds, mesh_check, precise_volume
from parts.elbow.design import TURN_CENTRE, TURN_RADIUS, verify as verify_legacy_course
from parts.tunnel.design import Tunnel
from parts.tunnel.e31_fit import (
    BEAD_MINOR_RADIUS, SLOT_END_RADIUS, SLOT_WIDTH,
    add_e31_05_receiver_features, slot_end_z_for_receiver_depth,
)

PART_ID = "E01-V3"
LEFT_PART_ID = "E01L-V1"
STATIONS = 72
CIRCULAR_LIP_MM = 1.0
ROOF_TRANSITION_MM = 4.0


def _blend(distance):
    u = min(1.0, max(0.0, (distance - CIRCULAR_LIP_MM) / ROOF_TRANSITION_MM))
    return u * u * (3.0 - 2.0 * u)


def _section(angle_degrees, blend, t):
    """A four-edge section on the local tangent plane of the R48 centreline.

    The floor's circle is unchanged; the roof starts circular at both mouths
    and transitions to the historical self-supporting teardrop inside.
    """
    theta = math.radians(angle_degrees)
    normal = (-math.sin(theta), math.cos(theta), 0)
    inward = (-math.cos(theta), -math.sin(theta), 0)
    plane = cq.Plane(
        origin=(TURN_CENTRE[0] + TURN_RADIUS * math.cos(theta),
                TURN_CENTRE[1] + TURN_RADIUS * math.sin(theta), 0),
        xDir=inward, normal=normal,
    )
    radius = t.radius
    cy = t.floor + radius
    a = radius / math.sqrt(2)
    b = t.bridge_width / 2

    def mix(circle, raised):
        return circle * (1 - blend) + raised * blend

    end = (mix(radius * math.cos(math.radians(75)), b),
           mix(cy + radius * math.sin(math.radians(75)), t.ceiling))
    mid = (mix(radius / 2, (a + b) / 2),
           mix(cy + radius * math.sqrt(3) / 2, (cy + a + t.ceiling) / 2))
    apex_z = mix(cy + radius, t.ceiling)
    wire = (cq.Workplane(plane)
            .moveTo(-a, cy + a)
            .threePointArc((0, t.floor), (a, cy + a)))
    if blend >= 1 - 1e-12:
        return wire.lineTo(b, t.ceiling).lineTo(-b, t.ceiling).lineTo(-a, cy + a).close().val()
    return (wire.threePointArc(mid, end)
            .threePointArc((0, apex_z), (-end[0], end[1]))
            .threePointArc((-mid[0], mid[1]), (-a, cy + a))
            .close().val())


def _channel(t):
    total_length = TURN_RADIUS * math.pi / 2
    wires = []
    for i in range(STATIONS + 1):
        travelled = total_length * i / STATIONS
        blend = _blend(min(travelled, total_length - travelled))
        wires.append(_section(-90 + 90 * i / STATIONS, blend, t))
    return cq.Solid.makeLoft(wires, ruled=True)


def build_unmarked(t=Tunnel()):
    """Return one valid, undistorted right-hand BRep without an ID stamp."""
    # E31-05 is an explicit adaptation of the E27 4x4 grid, not E27 clutch.
    p = replace(brick_from_fit("duplo-e27-play-v1", nx=4, ny=4, height_units=2),
                tube_radius=6.60)
    outer = cq.Workplane("XY").box(
        p.width, p.depth, p.height, centered=(True, True, False))
    outer = (outer.edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
            .edges(">Z").fillet(ROUNDED_EDGES.corner_radius))
    result = receiver(p, outer, t.cavity_height, ROUNDED_EDGES.receiver_entry)
    result = result.cut(_channel(t))
    studs = make_studs(p.studs(), p.height, p.stud_radius - p.clearance,
                       p.stud_inner_radius, p.stud_height,
                       ROUNDED_EDGES.stud_lip_radius)
    shape = result.union(studs).val().clean()
    # All nine tubes are intact in this rectangular 4x4 shell; no clipped
    # supports are invented. Use shortened E31 slots for a shallow receiver.
    shape = add_e31_05_receiver_features(
        shape, p.tubes(), p.tube_radius, receiver_depth=t.cavity_height)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("E31 gentle tunnel must be one valid solid")
    return shape, p


def mark_part(unmarked, p, direction):
    if direction not in ("right", "left"):
        raise ValueError("direction must be right or left")
    if direction == "right":
        return engrave(unmarked, PART_ID, x=0, y=-p.depth / 2, z=12)
    # Mirror the UNSTAMPED model first; south exit occupies x~16 on the
    # left part, so stamp the unobstructed southwest facade at x=-17.
    return engrave(unmarked.mirror("XZ"), LEFT_PART_ID,
                   x=-17, y=-p.depth / 2, z=12)


def build_part(direction="right", t=Tunnel()):
    raw, p = build_unmarked(t)
    return mark_part(raw, p, direction), p


def _mouth_round(shape, direction, t):
    cy = t.floor + t.radius
    mouths = [(-31.85, -16), (16, 31.85)] if direction == "right" else [
        (-31.85, 16), (16, -31.85)]
    # At each visible aperture the circle must end close to its top;
    # the raised internal teardrop roof must NOT appear at the mouth.
    return all(
        not shape.isInside(cq.Vector(x, y, cy + t.radius - .35))
        and shape.isInside(cq.Vector(x, y, cy + t.radius + .35))
        for x, y in mouths
    )


def _clean_collapsed_stl(path):
    raw = path.read_bytes()
    n = struct.unpack_from("<I", raw, 80)[0]
    triangles = []
    for i in range(n):
        tri = raw[84 + 50 * i:134 + 50 * i]
        vertices = struct.unpack("<12fH", tri)[3:12]
        if len({tuple(vertices[j:j + 3]) for j in (0, 3, 6)}) == 3:
            triangles.append(tri)
    path.write_bytes(raw[:80] + struct.pack("<I", len(triangles)) + b"".join(triangles))
    return n - len(triangles)


def export(out=Path("build/gentle-curve-tunnel"), *, direction="right"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    t = Tunnel()
    shape, p = build_part(direction, t)
    # Reflect the left shape back before the legacy west/north course
    # assembly checks; the track and ports must remain mirror-symmetric.
    canonical = shape if direction == "right" else shape.mirror("XZ")
    report = verify_legacy_course(canonical, t)

    stl_path = out / "brick.stl"
    cq.exporters.export(shape, str(stl_path), tolerance=.025, angularTolerance=.15)
    collapsed = _clean_collapsed_stl(stl_path)
    cq.exporters.export(shape, str(out / "brick.step"))
    restored = cq.importers.importStep(str(out / "brick.step")).val()
    stl_report = mesh_check(stl_path)
    bounds = exact_bounds(shape)
    original_volume = precise_volume(shape)
    checks = report["checks"]
    checks.update(
        dimensions=all(abs(a - b) < .02 for a, b in
                       zip(bounds, (63.8, 63.8, 42.9))),
        mesh=stl_report["passed"],
        mesh_volume=abs(stl_report["signed_volume_mm3"] - shape.Volume()) /
                    shape.Volume() < .001,
        step_roundtrip=(restored.isValid() and len(restored.Solids()) == 1
                        and abs(precise_volume(restored) - original_volume) /
                        original_volume < 1e-5
                        and all(abs(a - b) < .02 for a, b in
                                zip(exact_bounds(restored), bounds))),
        circular_mouths=_mouth_round(shape, direction, t),
        e31_shallow_slots=(p.tube_radius == 6.60 and
                          slot_end_z_for_receiver_depth(t.cavity_height) == 3.50 and
                          t.cavity_height - (3.50 + SLOT_END_RADIUS) >= .60 - 1e-6),
        correctly_marked=(shape.isValid() and len(shape.Solids()) == 1),
    )
    report.update(
        schema_version=1,
        kind="gentle-horizontal-tunnel",
        id=PART_ID if direction == "right" else LEFT_PART_ID,
        direction=direction,
        passed=all(checks.values()),
        geometry=dict(bounds_mm=bounds, volume_mm3=shape.Volume(),
                      parameters=asdict(p)),
        design=design_manifest(p, channel=t),
        mesh=stl_report,
        collapsed_stl_triangles_removed=collapsed,
        roof_style=dict(mouth="circular", interior="high_teardrop",
                        circular_lip_mm=CIRCULAR_LIP_MM,
                        roof_transition_mm=ROOF_TRANSITION_MM),
        e31_05_receiver=dict(tube_od_mm=13.20, bead_minor_radius_mm=BEAD_MINOR_RADIUS,
                             slot_width_mm=SLOT_WIDTH, slot_end_z_mm=3.50,
                             receiver_depth_mm=t.cavity_height,
                             roof_clearance_mm=.60),
        physical_fit_validated=False,
        physical_rolling_validated=False,
        slicing_validated=False,
        limitations=[
            "CAD sweeps are clearance tests, not rolling/friction simulations.",
            "Both directions require incoming momentum and physical ten-run trials.",
            "The shallow E31 slot has only small-coupon print evidence; inspect 4x4 floor.",
            "Inspect underside bridges, roof and readable stamps with supports OFF.",
        ],
        files={name: hashlib.sha256((out / name).read_bytes()).hexdigest()
               for name in ("brick.stl", "brick.step")},
    )
    (out / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("GENTLE TUNNEL", direction, "PASS" if report["passed"] else "FAIL",
          checks, flush=True)
    if not report["passed"]:
        raise RuntimeError("Gentle tunnel CAD validation failed")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("build/gentle-curve-tunnel"))
    args = parser.parse_args()
    export(args.out)
