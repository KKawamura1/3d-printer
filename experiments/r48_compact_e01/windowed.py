"""Issue #89 optical comparison: compact horizontal R48 with five outer windows.

A new E01-V12 candidate, not a rewrite of the successful E01-V3 or the
unwindowed E01-V11. Uses the actual E01 channel and SC02 curved footprint.
The PR #75 pointed-window *shape language* is borrowed, but its experimental
branch is not imported; this standalone comparison can run on main.
"""
import argparse
import json
import math
from pathlib import Path

import cadquery as cq

from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import engrave_course_west
from brickcad.standards import BALL_TRACK
from brickcad.verify import exact_bounds
from experiments.r48_compact_e01.design import build_compact

MODEL_ID = "E01-V12"
WINDOW_COUNT = 5
WINDOW_WIDTH = 10.0
OUTER_RADIUS = 63.9  # physical curved_footprint() outside radius, mm
WINDOW_Z = (BALL_TRACK.floor + 7., BALL_TRACK.floor + 18.,
            BALL_TRACK.floor + 22.)
WINDOW_DEPTH = 12.0


def window_centres():
    arc = OUTER_RADIUS * math.pi / 2
    gap = (arc - WINDOW_COUNT * WINDOW_WIDTH) / (WINDOW_COUNT + 1)
    if gap < 2.5:
        raise ValueError("Unsafe space between facade openings")
    return tuple(gap + WINDOW_WIDTH / 2 + i * (WINDOW_WIDTH + gap)
                 for i in range(WINDOW_COUNT))


def window_cutters():
    """Five gable pentagons, each tangent to the convex curve and cut inward.

    Keep the concave wall unperforated. The cutter stops well before it.
    """
    arc = OUTER_RADIUS * math.pi / 2
    for s in window_centres():
        angle = -math.pi / 2 + s / arc * math.pi / 2
        rx, ry = math.cos(angle), math.sin(angle)
        outward = (rx, ry)
        inward = (-rx, -ry, 0)
        tangent = (ry, -rx, 0)
        # Origin 1.6 mm outside the outermost SC02 footprint.
        plane = cq.Plane(
            origin=(-32 + (OUTER_RADIUS + 1.6) * outward[0],
                    32 + (OUTER_RADIUS + 1.6) * outward[1], 0),
            xDir=tangent, normal=inward,
        )
        half = WINDOW_WIDTH / 2
        zlo, zshoulder, ztip = WINDOW_Z
        shape = (cq.Workplane(plane)
                 .polyline(((-half, zlo), (half, zlo),
                            (half, zshoulder), (0, ztip),
                            (-half, zshoulder)))
                 .close().extrude(WINDOW_DEPTH).val())
        yield shape


def build_windowed():
    shape, fit, tubes = build_compact(marked=False)
    original = shape
    volumes = []
    for cutter in window_cutters():
        next_shape = shape.cut(cutter).clean()
        removed = shape.Volume() - next_shape.Volume()
        if removed < 2.0:
            raise ValueError(f"One of the five windows missed the physical wall: {removed}")
        if not next_shape.isValid() or len(next_shape.Solids()) != 1:
            raise ValueError("Facade opening broke the connected shell")
        volumes.append(removed)
        shape = next_shape
    # Keep part marking on the solid inlet skirt, away from side windows.
    shape = engrave_course_west(
        shape, MODEL_ID, x=-fit.width / 2, y=-16., z=3.8
    )
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Windowed R48 shell not a single connected BRep")
    if original.Volume() <= shape.Volume():
        raise ValueError("Windows must remove real material")
    return shape, fit, tubes, volumes


def export(out):
    out.mkdir(parents=True, exist_ok=True)
    shape, fit, tubes, volumes = build_windowed()
    stl, mesh = export_geometry(shape, out, tolerance=.02, angular_tolerance=.15)
    bounds = exact_bounds(shape)
    checks = {
        "single_valid_solid": shape.isValid() and len(shape.Solids()) == 1,
        "watertight": bool(mesh["passed"]),
        "mesh_volume_matches_brep": abs(mesh["signed_volume_mm3"] -
                                        shape.Volume()) / shape.Volume() < .001,
        "five_real_outer_windows": len(volumes) == WINDOW_COUNT
                                   and min(volumes) > 2.,
        "three_complete_receiver_tubes": len(tubes) == 3,
        "four_by_four_duplo_envelope": (
            bounds[0] <= fit.width + .11 and bounds[1] <= fit.depth + .11),
    }
    report = {
        "model_id": MODEL_ID,
        "source_unwindowed": "E01-V11",
        "status": "experimental_unprinted_unrounded",
        "geometry": {"bounds_mm": bounds, "volume_mm3": shape.Volume()},
        "facade": {"side": "outer_convex", "windows": WINDOW_COUNT,
                   "width_mm": WINDOW_WIDTH, "window_spacing_centres_mm":
                   list(window_centres()), "removed_volume_each_mm3": volumes},
        "checks": checks,
        "passed": all(checks.values()),
        "slicing_validated": False,
        "visual_reviewed": False,
        "physical_rolling_validated": False,
        "note": ("Do not print before sharp cut edges, visible window placement, "
                 "roof/stud structural support, slicer and physical checks pass."),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2,
                                                 ensure_ascii=False) + "\n")
    if not report["passed"]:
        raise ValueError(f"Windowed E01 failed checks: {checks}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("build/issue89-e01-windows"))
    args = parser.parse_args()
    print(json.dumps(export(args.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
