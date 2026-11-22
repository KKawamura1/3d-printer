"""Opt-in large side ID engraving for new DUPLO rail revisions.

Legacy Issue37 production CAD intentionally keeps its immutable 3mm lettering.
This versioned marking policy is shared by enlarged-window experiments; it
never changes ball channels, connection mouths or old released artifacts.

All checks use exact BRep boolean intersections, NOT just 2D rectangles.
"""
from dataclasses import dataclass

import cadquery as cq

SIZE_MM = 5.0
DEPTH_MM = 0.4
TOOL_EXTENSION_MM = 0.05
POLICY_ID = "course-id-5mm-bold-recessed-v2"
MIN_FULL_TEXT_COVERAGE = 0.70
MAX_WINDOW_MARK_OVERLAP_MM3 = 0.01


@dataclass(frozen=True)
class MarkSite:
    face: str  # south (-Y) or west (-X)
    x_mm: float
    y_mm: float
    z_mm: float

    def __post_init__(self):
        if self.face not in ("south", "west"):
            raise ValueError("Only exterior planar south/west text is supported")


def mark_tool(label, site, *, size=SIZE_MM, depth=DEPTH_MM):
    if not label or size != SIZE_MM or depth != DEPTH_MM:
        raise ValueError("Use the versioned 5mm x 0.4mm large-ID policy")
    if site.face == "south":
        plane = cq.Plane(
            origin=(site.x_mm, site.y_mm + depth, site.z_mm),
            xDir=(1, 0, 0), normal=(0, -1, 0))
    else:
        plane = cq.Plane(
            origin=(site.x_mm + depth, site.y_mm, site.z_mm),
            xDir=(0, -1, 0), normal=(-1, 0, 0))
    return (cq.Workplane(plane)
            .text(label, size, depth + TOOL_EXTENSION_MM,
                  font="DejaVu Sans", kind="bold", combine=False)
            .val())


def engrave_large(shape, original, label, site, *, audit):
    """Engrave exactly once; verify near-complete lettering and no lost windows.

    The current legacy course audit enforces one marking by ID. We record it
    explicitly here for the new opt-in policy rather than changing the old
    3mm-only engraving implementation or its historical geometry.
    """
    if audit.model_id != label or audit.marked_labels:
        raise ValueError("Only one correct revision marking is permitted")
    tool = mark_tool(label, site)
    volume = tool.Volume()
    if volume <= 0:
        raise ValueError("Empty marking tool")
    # Both solids are unengraved. The before/after material difference inside
    # the *actual text tool* is precisely how much of the proposed engraving
    # would be eaten by windows / passages. It is not a bounding-box guess.
    original_material = original.intersect(tool).Volume()
    available_material = shape.intersect(tool).Volume()
    window_overlap = max(0., original_material - available_material)
    coverage = available_material / volume
    if window_overlap > MAX_WINDOW_MARK_OVERLAP_MM3:
        raise ValueError(
            f"{label}: lettering overlaps a window by "
            f"{window_overlap:.3f}mm^3 at {site}")
    if coverage < MIN_FULL_TEXT_COVERAGE:
        raise ValueError(
            f"{label}: only {coverage:.1%} of text is on solid exterior at {site}")
    engraved = shape.cut(tool).clean()
    removed = shape.Volume() - engraved.Volume()
    if (not engraved.isValid() or len(engraved.Solids()) != 1
            or removed < .3 or abs(removed-available_material) > .06):
        raise ValueError(f"{label}: invalid, truncated or disconnected lettering")
    # The shared CAD production fit audit remains required and final marking
    # labels are enforced. Explicitly identify the new marking-policy version
    # in the experiment report, rather than relabeling legacy 3mm CAD.
    audit.marked_labels.append(label)
    return engraved, {
        "policy": POLICY_ID,
        "size_mm": SIZE_MM,
        "depth_mm": DEPTH_MM,
        "font": "DejaVu Sans bold",
        "face": site.face,
        "site_xyz_mm": [site.x_mm, site.y_mm, site.z_mm],
        "lettering_tool_volume_mm3": round(volume, 4),
        "actual_material_coverage": round(coverage, 4),
        "window_mark_overlap_mm3": round(window_overlap, 5),
        "removed_mm3": round(removed, 4),
    }
