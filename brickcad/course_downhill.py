"""D01-derived, independently composed DUPLO downhill tunnel BRep.

Only the external wall windows and engraving are configurable. The proven
smoothstep floor, teardrop passage, E31-05 receiver and roof remain pinned.
Historical D01-V2 is intentionally not modified.
"""
from dataclasses import asdict, replace
import hashlib
import json
import struct
from pathlib import Path

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.marking import engrave
from brickcad.model import brick_from_fit, receiver
from brickcad.standards import BALL_TRACK, ROUNDED_EDGES
from brickcad.verify import exact_bounds, intersection, mesh_check, VOLUME_TOL
from parts.downhill_tunnel.design import (
    Downhill, _cut_passage, _window_cutter, floor_z, ball_positions,
    sampled_ball_intersections, ports,
)
from parts.tunnel.e31_fit import add_e31_05_receiver_features


def build_course(spec):
    """A new BRep assembly, not a call to legacy build_downhill/export."""
    d = Downhill()
    p = replace(brick_from_fit("duplo-e27-play-v1", nx=4, ny=2, height_units=3),
                tube_radius=6.60)
    outer = cq.Workplane("XY").box(p.width, p.depth, p.height,
                                    centered=(True, True, False))
    outer = outer.edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
    outer = outer.edges(">Z").chamfer(.5)
    body = receiver(p, outer, d.receiver_depth, ROUNDED_EDGES.receiver_entry)
    body = body.cut(_cut_passage(d))
    for win in spec["enclosure"]["windows"]:
        body = body.cut(_window_cutter(win["x_mm"],
                                     replace(d, window_width=win["width_mm"])))
    # D01's full rectangular upper/lower body has no unsupported clipped studs.
    studs = make_studs(p.studs(), p.height, p.stud_radius-p.clearance,
                       p.stud_inner_radius, p.stud_height,
                       ROUNDED_EDGES.stud_lip_radius)
    shape = body.union(studs).val().clean()
    shape = add_e31_05_receiver_features(shape, p.tubes(), p.tube_radius)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Configured downhill must have one valid connected solid")
    label = spec["id"] + "-" + spec["version"]
    shape = engrave(shape, label, x=0, y=-p.depth/2, z=9.)
    return shape, p, d


def geometry_checks(shape, p, d, windows):
    collisions = sampled_ball_intersections(shape, d, 33)
    bounds = exact_bounds(shape)
    # Probes are deliberately outside the running channel, on the window wall.
    # Lower guard must remain intact even when the opening passes the ball.
    checks = {
        "single_valid_solid": shape.isValid() and len(shape.Solids()) == 1,
        "size_2x4x3": all(abs(a-b) < .01 for a,b in zip(bounds, (63.8,31.8,62.1))),
        "ball_samples_clear": max(collisions) < VOLUME_TOL,
        "lower_floor_present": shape.isInside(cq.Vector(0,0,6.2)),
        "roof_present": shape.isInside(cq.Vector(0,0,57.0)),
        "windows_open": all(not shape.isInside(
            cq.Vector(w["x_mm"], -15.2, floor_z(w["x_mm"],d)+12)) for w in windows),
        "windows_guarded": all(shape.isInside(
            cq.Vector(w["x_mm"], -15.2, floor_z(w["x_mm"],d)+4)) for w in windows),
        "full_e31_tubes": len(p.tubes()) == 3 and abs(p.tube_radius - 6.6) < 1e-6,
        "eight_studs": len(p.studs()) == 8,
    }
    return checks, collisions, bounds


def _remove_float32_collapsed_triangles(stl):
    raw = stl.read_bytes()
    if len(raw) < 84 or len(raw) != 84 + struct.unpack_from("<I",raw,80)[0]*50:
        raise ValueError("Malformed binary STL")
    triangles = []
    for i in range(struct.unpack_from("<I",raw,80)[0]):
        tri = raw[84+50*i:134+50*i]
        coords = struct.unpack("<12fH",tri)[3:12]
        if len({tuple(coords[j:j+3]) for j in (0,3,6)}) == 3:
            triangles.append(tri)
    stl.write_bytes(raw[:80] + struct.pack("<I", len(triangles)) + b"".join(triangles))


def export_course(spec, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    shape, p, d = build_course(spec)
    windows = spec["enclosure"]["windows"]
    checks, collisions, bounds = geometry_checks(shape,p,d,windows)
    stl = out/"brick.stl"
    cq.exporters.export(shape, str(stl), tolerance=.03, angularTolerance=.2)
    _remove_float32_collapsed_triangles(stl)
    cq.exporters.export(shape, str(out/"brick.step"))
    mesh = mesh_check(stl)
    restored = cq.importers.importStep(str(out/"brick.step")).val()
    checks["mesh_closed"] = mesh["passed"]
    checks["step_roundtrip"] = (
        restored.isValid() and len(restored.Solids()) == 1
        and abs(restored.Volume() - shape.Volume()) / shape.Volume() < 1e-6
    )
    report = {
        "schema_version": 2,
        "part_id": spec["id"] + "-" + spec["version"],
        "passed": all(checks.values()),
        "geometry": {"kind": "straight_downhill_tunnel",
                     "bounds_mm": bounds, "volume_mm3": shape.Volume()},
        "fit_profile_id": p.fit_profile_id,
        "e31_05": {"tube_od_mm": 13.20, "bead_radius_mm": .20,
                   "split_slots": 4, "physical_fit_validated": False},
        "windows": windows, "parameters": asdict(d),
        "ports": [asdict(port) for port in ports(d)],
        "checks": checks, "mesh": mesh,
        "sampled_ball_collisions_mm3": collisions,
        "physical_fit_validated": False, "physical_rolling_validated": False,
        "slicer_support_free_validated": False,
        "limitations": [
            "Only finite 33-sample rigid-ball clearance is checked.",
            "No guarantee of natural roll, slicer result, or child safety.",
            "E31-05 transferred from another part and not physically checked.",
        ],
        "sha256_stl": hashlib.sha256(stl.read_bytes()).hexdigest(),
    }
    (out/"report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not report["passed"]:
        raise RuntimeError("Configured downhill geometry failed: " +
                           ", ".join(k for k,v in checks.items() if not v))
    return report
