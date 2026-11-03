"""Horizontal x straight x open: production R01-V1 E31-05 ball rail.

The same course axes + universal fit/mark contract as other Issue #37 parts.
Its measured straight-channel geometric kernel is independently implemented
without importing any historical part generator.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import cadquery as cq

from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import (
    course_fit, add_course_receiver_features, engrave_course,
    RECEIVER_DEPTH_MM, SLOT_END_Z_MM, TUBE_RADIUS_MM, PRODUCTION_CONTRACT,
)
from brickcad.model import receiver
from brickcad.standards import BALL_TRACK
from brickcad.verify import exact_bounds


@dataclass(frozen=True)
class StraightChannel:
    length: float = 63.8
    width: float = BALL_TRACK.width
    height: float = BALL_TRACK.height
    opening: float = BALL_TRACK.opening
    floor: float = BALL_TRACK.floor
    outer_radius: float = 0.8
    lip_radius: float = 0.5
    end_chamfer: float = 0.15
    entry: float = 0.3
    roof: float = 1.6

    @property
    def radius(self):
        depth = self.height - self.floor
        return ((self.opening / 2) ** 2 + depth * depth) / (2 * depth)


def build_course(model_id, recipe, *, marked=True):
    if recipe != {"channel": "standard", "length_mm": 63.8}:
        raise ValueError("Unsupported horizontal straight open recipe")
    if model_id != "R01-V1":
        raise ValueError("Only the validated R01-V1 design is supported")
    r = StraightChannel()
    cavity = r.floor - r.roof
    if abs(cavity - RECEIVER_DEPTH_MM) > 1e-6:
        raise ValueError("Unexpected straight-rail receiver depth")
    p = course_fit(
        nx=4, ny=2, height_units=1,
        body_offset_xy=(0., r.width - 31.8), height=r.height,
    )
    outer = (cq.Workplane("XY")
             .box(r.length, r.width, r.height, centered=(True, True, False))
             .edges("|Z").fillet(r.outer_radius)
             .edges(">Z").fillet(r.outer_radius))
    body = receiver(p, outer, cavity, r.entry, (r.length, r.width))
    groove = cq.Solid.makeCylinder(
        r.radius, r.length + 2,
        cq.Vector(-r.length / 2 - 1, 0, r.floor + r.radius),
        cq.Vector(1, 0, 0),
    )
    body = body.cut(groove)
    lips = [
        edge for edge in body.val().Edges()
        if edge.geomType() == "LINE"
        and edge.Length() > r.length - 2 * r.outer_radius - 1
        and abs(abs(edge.Center().y) - r.opening / 2) < .01
    ]
    if len(lips) != 2:
        raise ValueError("Expected two measured channel lips")
    body = body.newObject(lips).fillet(r.lip_radius)
    for x, start, end in [
        (-r.length / 2, r.radius + r.end_chamfer, r.radius),
        (r.length / 2 - r.end_chamfer, r.radius, r.radius + r.end_chamfer),
    ]:
        lead = cq.Solid.makeCone(
            start, end, r.end_chamfer,
            cq.Vector(x, 0, r.floor + r.radius), cq.Vector(1, 0, 0),
        )
        body = body.cut(lead)
    shape = add_course_receiver_features(
        body.val().clean(), p.tubes(), p.tube_radius, receiver_depth=cavity
    )
    if marked:
        shape = engrave_course(shape, model_id, x=0, y=-r.width / 2, z=10.)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Invalid production R01-V1 CAD")
    return shape, p


def export_course(model_id, recipe, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    shape, p = build_course(model_id, recipe)
    stl, mesh = export_geometry(shape, out, tolerance=.01, angular_tolerance=.1)
    r = StraightChannel()
    dims = exact_bounds(shape)
    checks = {
        "valid_single_solid": shape.isValid() and len(shape.Solids()) == 1,
        "dimensions": all(abs(a-b)<.01 for a,b in zip(dims,(r.length,r.width,r.height))),
        "e31_tube_radius": abs(p.tube_radius - TUBE_RADIUS_MM) < 1e-8,
        "short_receiver_slot": SLOT_END_Z_MM == 3.50,
        "three_receiver_tubes": len(p.tubes()) == 3,
        "floor_present": shape.isInside(cq.Vector(0, 0, r.floor-.1)),
        "channel_open": not shape.isInside(cq.Vector(0, 0, r.floor+.1)),
        "watertight_mesh": mesh["passed"],
        "mesh_volume": abs(mesh["signed_volume_mm3"]-shape.Volume()) / shape.Volume() < .001,
    }
    report = {
        "part_id": model_id, "passed": all(checks.values()),
        "checks": checks, "mesh": mesh,
        "geometry": {"bounds_mm": dims, "volume_mm3": shape.Volume()},
        "source_engine": "brickcad.course_straight_rail",
        "production_contract": PRODUCTION_CONTRACT,
        "physical_fit_validated": False,
        "physical_rolling_validated": False, "slicing_validated": False,
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    (out / "course-manifest.json").write_text(json.dumps({
        "schema_version": 1, "model_id": model_id,
        "mode": "independent_configured_geometry",
        "source_engine": "brickcad.course_straight_rail",
        "production_contract": PRODUCTION_CONTRACT,
        "recipe": recipe,
        "geometry_verified": report["passed"],
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
        "physical_fit_validated": False, "slicing_validated": False,
    }, ensure_ascii=False, indent=2)+"\n")
    if not report["passed"]:
        raise ValueError("R01-V1 production CAD validation failed: " + str(checks))
    return report
