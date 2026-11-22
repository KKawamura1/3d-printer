"""Compact E01 R48 tunnel experiment: SC02 footprint, visible curved windows.

The existing E01-V10/E01L-V8 remain fully intact as a control. Trim the
overbuilt 4x4 square *after* reconstructing the original audited E31 source,
using the exact quarter-annulus CAD footprint used by SC02, then reveal
the bend itself with nine window ports along the convex external wall.

Physical E31 studs/receivers outside the arc are deliberately sacrificed.
This prototype is *not* a full 4x4 stud/receiver plate after trimming.
"""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path

import cadquery as cq

from brickcad.course_architectural_windows import (
    Facade, MIN_POST, _track_r48, _verify_visibility, _window_geometry,
    model, source_unmarked,
)
from brickcad.course_artifacts import export_geometry
from brickcad.course_contract import PRODUCTION_CONTRACT, audited_production_course
from brickcad.course_marking_v2 import MarkSite, engrave_large
from brickcad.course_r48_sloped_tunnel import curved_footprint
from brickcad.standards import BALL_TRACK
from brickcad.verify import exact_bounds

TRIALS = {"E01-V3": "E01-V12", "E01L-V1": "E01L-V9"}
WINDOWS = 9
WINDOW_WIDTH_MM = 6.5
OUTER_RADIUS = 48 + BALL_TRACK.width / 2
INNER_RADIUS = 48 - BALL_TRACK.width / 2
# SC02 curved_footprint outer uses 63.9 and inner width 31.8, rather
# than relying on any particular layout file.
ARC_LENGTH = OUTER_RADIUS * math.pi / 2
MAX_BOUND_DRIFT_MM = .12


def compact_footprint(left):
    f = curved_footprint()
    return f.mirror("XZ") if left else f


def outer_facade(left):
    """Walk the whole outer bend rather than punching through 4x4 infill."""
    sign = -1 if left else 1

    def sample(s):
        theta = -math.pi / 2 + (s / ARC_LENGTH) * math.pi / 2
        rx, ry = math.cos(theta), math.sin(theta) * sign
        wall = (-32 + OUTER_RADIUS * rx, 32 * sign + OUTER_RADIUS * ry)
        inward = (-rx, -ry)
        x, y, floor = _track_r48(s / ARC_LENGTH, left, False)
        return wall, inward, (x, y, floor + BALL_TRACK.radius), floor

    return Facade(
        "outside-curved-shell", "convex", ARC_LENGTH, WINDOW_WIDTH_MM,
        sample, "nine real bend sightlines; no false distant facade openings",
    )


def window_stations():
    return tuple(ARC_LENGTH * (i + 1) / (WINDOWS + 1)
                 for i in range(WINDOWS))


def min_post_mm(stations):
    positions = [stations[0] - WINDOW_WIDTH_MM / 2]
    positions.extend(
        b - a - WINDOW_WIDTH_MM for a, b in zip(stations, stations[1:]))
    positions.append(ARC_LENGTH - stations[-1] - WINDOW_WIDTH_MM / 2)
    return min(positions)


def channel_parity(old, clipped, left):
    """Sample unchanged mouth and passage throughout whole old R48 path.

    The ring cut must not alter existing material/air inside the rolling
    corridor, even at both connecting radial ends. Exact source geometry
    is used for both occupancy checks; no STL-derived approximation.
    """
    checks = 0
    sign = -1 if left else 1
    for i in range(25):
        theta = -math.pi/2 + (i/24)*math.pi/2
        for radius in (34., 38., 42., 48., 54., 58., 62.):
            for z in (6., 9., 15., 23., 31.):
                x = -32 + radius * math.cos(theta)
                y = sign * (32 + radius * math.sin(theta))
                pos = cq.Vector(x, y, z)
                if old.isInside(pos) != clipped.isInside(pos):
                    raise ValueError(
                        f"Original inlet/exit/track geometry changed at "
                        f"{x:.3f}, {y:.3f}, {z:.3f}")
                checks += 1
    return checks


def retained_connections(fit, left):
    """Conservative complete-site count; partial clipped features untrusted."""
    sign = -1 if left else 1

    def contains_disc(x, y, radius):
        # Full circle must remain in the annular radial band, and in
        # the quarter-arc sector, including margins at inlet/outlet.
        y *= sign
        dx, dy = x + 32, y - 32
        rho = math.hypot(dx, dy)
        return (INNER_RADIUS + radius + 1e-4 < rho <
                OUTER_RADIUS - radius - 1e-4
                and dx > radius and -dy > radius)

    studs = [(x, y) for x, y in fit.studs()
             if contains_disc(x, y, fit.stud_radius)]
    tubes = [(x, y) for x, y in fit.tubes()
             if contains_disc(x, y, fit.tube_radius)]
    if len(studs) < 3 or len(tubes) < 2:
        raise ValueError(
            f"Not enough fully retained connectors: {len(studs)} studs "
            f"/ {len(tubes)} tubes")
    return {"full_stud_site_count_minimum": len(studs),
            "full_tube_site_count_minimum": len(tubes),
            "conservatively_full_stud_sites_xy": studs,
            "conservatively_full_tube_sites_xy": tubes,
            "nominal_4x4_connection_area_retained": False}


def build(source_id, root):
    if source_id not in TRIALS:
        raise ValueError("Only the original horizontal R48 tunnel is supported")
    m = model(source_id)
    new_id = TRIALS[source_id]
    left = m["source"]["recipe"]["direction"] == "left"
    folder = Path(root) / new_id
    folder.mkdir(parents=True, exist_ok=True)

    facade = outer_facade(left)
    stations = window_stations()
    if min_post_mm(stations) < MIN_POST:
        raise ValueError("Too many convex windows for minimum external pillars")

    with audited_production_course(new_id) as audit:
        original, fit = source_unmarked(m)
        old_bounds = exact_bounds(original)
        compact = original.intersect(compact_footprint(left)).clean()
        # SC02's quarter-annulus slices the edges of two E01 receiver
        # beads, leaving two isolated 0.026mm³ crumbs at Z0.36–3.45.
        # They must not ship as floating printable debris. Reject any
        # disconnected *useful* material instead of blindly picking the
        # largest component. This is true for both mirrored parts.
        all_pieces = sorted(
            compact.Solids(), key=lambda part:part.Volume(), reverse=True)
        detached = all_pieces[1:]
        detached_volumes = [piece.Volume() for piece in detached]
        if detached and (any(v >= .1 for v in detached_volumes)
                         or sum(detached_volumes) >= .2):
            raise ValueError(
                f"{new_id}: unsafe detached solids after trim: "
                f"{detached_volumes!r}mm³")
        if detached:
            print("REMOVE ISOLATED RECEIVER CRUMBS", new_id,
                  [round(v,4) for v in detached_volumes], flush=True)
            compact = all_pieces[0].clean()
        if not compact.isValid() or len(compact.Solids()) != 1:
            raise ValueError(f"{new_id}: invalid single solid after tiny debris cleanup")
        source_volume, compact_volume = original.Volume(), compact.Volume()
        if compact_volume >= source_volume * .95:
            raise ValueError("Unproductive compact trim (less than 5% volume reduction)")
        parity_samples = channel_parity(original, compact, left)
        connection_evidence = retained_connections(fit, left)

        # Nine independent BRep cuts would rebuild/reheal the entire
        # hollow clipped ring nine times. One compound cut preserves the
        # same openings, then the checked CAD visibility ray for *each*
        # window proves the actual opening succeeds. This is significantly
        # faster without replacing geometry validation with layout guesses.
        cutters_and_geometry = [
            _window_geometry(facade, station) for station in stations]
        all_openings = cq.Compound.makeCompound(
            [cut for cut, _ in cutters_and_geometry])
        shape = compact.cut(all_openings).clean()
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError("Batch cut broke the compact R48 shell")
        removed = compact.Volume() - shape.Volume()
        if removed <= 8 * WINDOWS:
            raise ValueError(
                f"Nine windows removed too little real shell: {removed:.2f}mm³")
        window_evidence = []
        for station, (cutter, geometry) in zip(stations, cutters_and_geometry):
            wall_samples = _verify_visibility(compact, shape,
                                              geometry, guard=True)
            window_evidence.append({
                "arc_station_mm": round(station, 4),
                "window_width_mm": WINDOW_WIDTH_MM,
                "original_wall_samples": wall_samples,
                "postcut_blocked_samples": 0,
                "cut_with_nine_window_compound": True,
            })

        # South-side label on square E01 is now outside the trimmed shell;
        # reuse the fully supported west face orientation of compact SC02.
        mark = MarkSite("west", -fit.width/2, 16. if left else -16., 10.5)
        shape, marking = engrave_large(
            shape, compact, new_id, mark, audit=audit)

    contract = audit.manifest()
    bounds = exact_bounds(shape)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Final CAD is not one connected solid")
    if any(abs(a-b) > MAX_BOUND_DRIFT_MM
           for a, b in zip(old_bounds, bounds)):
        raise ValueError(f"Unexpected changed full envelope: {old_bounds} / {bounds}")

    _, mesh = export_geometry(shape, folder, tolerance=.015,
                              angular_tolerance=.1)
    mesh_ok = abs(mesh["signed_volume_mm3"]-shape.Volume())/shape.Volume() < .001
    checks = {
        "arc_geometry_valid": compact.isValid() and len(compact.Solids()) == 1,
        "no_unattached_print_fragments": (
            all(v < .1 for v in detached_volumes)
            and sum(detached_volumes) < .2),
        "original_channel_and_mouth_samples": parity_samples == 875,
        "trim_achieves_5pct_reduction": compact_volume < source_volume*.95,
        "nine_windows_in_bend": len(window_evidence) == WINDOWS,
        "arc_pillars_min_2_5mm": min_post_mm(stations) >= MIN_POST,
        "all_windows_see_ball": all(
            p["original_wall_samples"] > 0 for p in window_evidence),
        "full_connectors_maintained_along_arc": (
            connection_evidence["full_stud_site_count_minimum"] >= 3 and
            connection_evidence["full_tube_site_count_minimum"] >= 2),
        "new_5mm_id_not_in_windows": (
            marking["window_mark_overlap_mm3"] < .01 and
            marking["actual_material_coverage"] >= .7),
        "single_solid": shape.isValid() and len(shape.Solids()) == 1,
        "unchanged_envelope_for_adjacent_rail_interfaces": all(
            abs(a-b) <= MAX_BOUND_DRIFT_MM for a,b in zip(old_bounds,bounds)),
        "watertight_mesh": mesh["passed"],
        "mesh_volume_agrees": mesh_ok,
        "unique_marking_once": contract["final_marking_labels"] == [new_id],
    }
    report = {
        "part_id": new_id, "source_model_id": source_id,
        "passed": all(checks.values()), "checks": checks,
        "geometry": {
            "original_square_cad_volume_mm3": source_volume,
            "removed_isolated_crumbs_mm3": [round(v, 5) for v in detached_volumes],
            "compact_unwindowed_cad_volume_mm3": compact_volume,
            "final_cad_volume_mm3": shape.Volume(),
            "body_volume_reduction_before_windows_ratio":
                1-compact_volume/source_volume,
            "bounds_mm": bounds, "sampled_original_channel_points": parity_samples,
            "window_count": WINDOWS, "minimum_post_mm": min_post_mm(stations),
            "material_removed_by_windows_mm3": removed,
            "windows": window_evidence,
            "connections": connection_evidence,
        },
        "marking": marking,
        "production_contract": PRODUCTION_CONTRACT,
        "contract_evidence": contract,
        "mesh": mesh,
        "physical_fit_validated": False,
        "physical_rolling_validated": False,
        "durability_validated": False,
        "slicing_validated": False,
        "child_safe_edges_physically_verified": False,
    }
    (folder/"report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    if not report["passed"]:
        raise ValueError(f"{new_id}: CAD failed {checks}")
    print(f"{new_id}: compact E01, {WINDOWS} outside windows, "
          f"{1-compact_volume/source_volume:.1%} less original bulk; "
          f"CAD/STL PASS", flush=True)
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",choices=sorted(TRIALS))
    parser.add_argument("--out",type=Path,default=Path("build/course-compact-e01"))
    args=parser.parse_args()
    results=[build(sid,args.out) for sid in
             ([args.model] if args.model else list(TRIALS))]
    (args.out/"report.json").write_text(
        json.dumps({"passed":all(r["passed"] for r in results),
                    "cases":results},ensure_ascii=False,indent=2)+"\n")
