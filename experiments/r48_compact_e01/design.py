"""Issue #89: opt-in compact horizontal R48 tunnel, using the SC02 footprint.

This is an independent E01-V11 *comparison specimen*. Existing production
E01/SC02, window experiments, track mouths, and E31-05 dimensions stay pinned.
No production dispatcher is modified. Do not call this physically validated.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cadquery as cq

from brickcad.connections import make_studs
from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import (
    RECEIVER_DEPTH_MM, add_course_receiver_features, course_fit,
    engrave_course_west,
)
from brickcad.course_r48_sloped_tunnel import curved_footprint
from brickcad.course_r48_tunnel import RoofSettings, channel
from brickcad.model import receiver
from brickcad.standards import BALL_TRACK, ROUNDED_EDGES
from brickcad.verify import exact_bounds

PART_ID = "E01-V11"
SOURCE_ID = "E01-V3"
RECIPE = {
    "direction": "right", "radius_mm": 48,
    "ceiling_mm": 34.8, "lip_mm": 1, "transition_mm": 4,
}
# E31 bead outer radius is 6.60 + 0.20 = 6.80 mm.
# 6.85 mm includes a small nominal sampling margin.
FULL_TUBE_PROBE_RADIUS = 6.85


def full_tube_centres(fit, footprint):
    """Only intact tubes may receive E31 split slots; clipped rings remain supports."""
    full = []
    for x, y in fit.tubes():
        if all(
            footprint.isInside(cq.Vector(
                x + FULL_TUBE_PROBE_RADIUS * math.cos(math.tau * k / 32),
                y + FULL_TUBE_PROBE_RADIUS * math.sin(math.tau * k / 32),
                2.0,
            ))
            for k in range(32)
        ):
            full.append((x, y))
    return full


def validate_mouth_clearance(footprint):
    """Both *unchanged* E01 circular mouth rims fit inside the SC02 silhouette.

    This asserts a positive nominal outer wall beside the mouth, not physical
    rolling or a mated-pair test. Endpoint locations remain those of E01-V3.
    """
    radius = BALL_TRACK.opening / 2 + 2.0  # nominal 2mm surrounding material
    if 48 - radius <= 48 - BALL_TRACK.width / 2:
        raise ValueError("Mouth wall insufficient for the proposed footprint")
    for angle in (-math.pi / 2, 0):
        cx, cy = -32 + 48 * math.cos(angle), 32 + 48 * math.sin(angle)
        for offset in (-radius, radius):
            for z in (BALL_TRACK.floor + 1., BALL_TRACK.floor + BALL_TRACK.radius):
                distance = 48 + offset
                sample = cq.Vector(-32 + distance * math.cos(angle),
                                   32 + distance * math.sin(angle), z)
                # At the exact exterior end plane, the mask can be tangent.
                # Probe just 0.1mm into the physical part for robust solid queries.
                normal_in = cq.Vector(1, 0, 0) if angle < 0 else cq.Vector(0, -1, 0)
                sample = sample.add(normal_in.multiply(.1))
                if not footprint.isInside(sample):
                    raise ValueError("R48 footprint clips the standard mouth rim")


def build_compact(*, marked=True):
    """Build original E01 internals; exchange only its exterior silhouette."""
    settings = RoofSettings.parse(RECIPE)
    fit = course_fit(nx=4, ny=4, height_units=2)
    footprint = curved_footprint()  # single geometry source shared with SC02
    validate_mouth_clearance(footprint)

    exterior = (cq.Workplane("XY")
                .box(fit.width, fit.depth, fit.height,
                     centered=(True, True, False))
                .edges("|Z").fillet(ROUNDED_EDGES.corner_radius)
                .edges(">Z").fillet(ROUNDED_EDGES.corner_radius))
    shell = receiver(fit, exterior, settings.cavity_height,
                     ROUNDED_EDGES.receiver_entry)
    # Same actual channel() loft and circular entrance/exit geometry as E01.
    shell = shell.cut(channel(settings))
    studs = make_studs(
        fit.studs(), fit.height, fit.stud_radius - fit.clearance,
        fit.stud_inner_radius, fit.stud_height,
        ROUNDED_EDGES.stud_lip_radius,
    )
    untrimmed = shell.union(studs).val().clean()
    shape = untrimmed.intersect(footprint).clean()

    full = full_tube_centres(fit, footprint)
    if set(full) != {(-16., -16.), (0., 0.), (16., 16.)}:
        raise ValueError(f"Unexpected complete underside tube layout: {full}")
    shape = add_course_receiver_features(
        shape, full, fit.tube_radius, receiver_depth=RECEIVER_DEPTH_MM
    )
    if marked:
        # The south face disappears when cropped. The west tunnel mouth
        # is hollow at Z12, so mark its *solid lower skirt* below floor Z6.35.
        # This is an experimental location, not yet sightline/print reviewed.
        shape = engrave_course_west(
            shape, PART_ID, x=-fit.width / 2, y=-16., z=3.8
        )
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Compact E01 must be a valid connected BRep")
    return shape, fit, full


def export(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    shape, fit, full = build_compact()
    bounds = exact_bounds(shape)
    expected_width = fit.width
    if bounds[0] > expected_width + .11 or bounds[1] > fit.depth + .11:
        raise ValueError(f"Compact footprint escaped existing 4x4 envelope: {bounds}")
    stl, mesh = export_geometry(
        shape, out, tolerance=.02, angular_tolerance=.15
    )
    checks = {
        "single_valid_solid": bool(shape.isValid() and len(shape.Solids()) == 1),
        "closed_mesh": bool(mesh["passed"]),
        "mesh_volume_matches_brep": (
            abs(mesh["signed_volume_mm3"] - shape.Volume()) /
            shape.Volume() < .001
        ),
        "uses_unchanged_source_channel": True,  # calls E01-V3's channel()
        "port_radius_unchanged_mm": BALL_TRACK.radius,
        "mouth_opening_unchanged_mm": BALL_TRACK.opening,
        "complete_e31_tubes_only": len(full) == 3,
    }
    report = {
        "model_id": PART_ID,
        "source_model_id": SOURCE_ID,
        "status": "experimental_unprinted",
        "geometry": {"bounds_mm": bounds, "volume_mm3": shape.Volume()},
        "complete_e31_tubes_xy_mm": full,
        "source_channel": "brickcad.course_r48_tunnel.channel",
        "shared_footprint": "brickcad.course_r48_sloped_tunnel.curved_footprint",
        "checks": checks,
        "passed": all(v for k, v in checks.items() if isinstance(v, bool)),
        "physical_rolling_validated": False,
        "slicing_validated": False,
        "edge_finish_reviewed": False,
        "note": ("Newly trimmed outline edges may be sharp. This specimen is "
                 "NOT print-approved until rounding, snap/photo, slicer, "
                 "and physical port/retention checks."),
    }
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    if not report["passed"]:
        raise ValueError(f"Issue89 CAD audit failed: {checks}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("build/issue89-e01"))
    args = parser.parse_args()
    print(json.dumps(export(args.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
