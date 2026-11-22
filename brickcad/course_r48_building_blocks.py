"""Shape-preserving shared building blocks for R48 enclosure adapters.

Open curves and roofed tunnels intentionally keep different final boolean
ordering to retain the print-tested BRep. These helpers centralize the actual
outer-wire, loft, and E31 receiver construction, not merely metadata.
"""
import cadquery as cq

from brickcad.connections import make_receiver


def outer_section_wire(workplane, *, inner, outer, bottom, top,
                       top_corner_radius=0.):
    """Rectangular annular cross section in local sketch coordinates.

    For R48 open-course sections the local X coordinate is the radial offset,
    while for roofed XZ sections it is the absolute radius. Both use the same
    outer-wire construction. The optional corner fillet matches the PR91 roof.
    """
    section = workplane.polyline((
        (inner, bottom), (outer, bottom),
        (outer, top), (inner, top),
    )).close().val()
    if top_corner_radius:
        # The roofed variant is drawn in XZ: its top edges have world Z=top.
        # Open courses have no top fillet, so their sloping local planes do not
        # enter this branch.
        vertices = [v for v in section.Vertices()
                    if v.Center().z > top - .01]
        if len(vertices) != 2:
            raise ValueError("Expected exactly two top roof corners")
        section = section.fillet2D(top_corner_radius, vertices)
    return section


def loft_sections(wires, *, ruled):
    """One CadQuery sweep operation for all four R48 recipes.

    Keep original callers' station positions, ruled flag, clipping order and
    clean() calls. Their values affect the final BRep and print parity.
    """
    return cq.Solid.makeLoft(wires, ruled=ruled)


def receiver_underbody(outer, fit, depth, *, tubes=None, tube_radius=None,
                       entry=0.):
    """Create the shared E31 underside without adding a new solid floor.

    Open courses retain the full grid (later clipped to the envelope); roofed
    SC02 uses three complete tubes followed by its four established partial
    receivers. Nothing here fills the open stud sockets or changes the roof.
    """
    points = fit.tubes() if tubes is None else tubes
    radius = (fit.tube_radius - fit.clearance
              if tube_radius is None else tube_radius)
    return make_receiver(outer, points, fit.cavity_xy, depth,
                         radius, fit.tube_inner_radius, entry)


def sweep_enclosure(outer_wire_at, passage_wire_at, stations, *, ruled=True):
    """Build the outer shell and the passage with the same station set.

    These are separate solids so each established builder can preserve its
    own clipping and boolean order. This removes duplicate sweep pipelines
    without silently changing any geometry or print-support boundary.
    """
    stations = tuple(stations)
    if len(stations) < 2:
        raise ValueError("Swept R48 enclosure requires at least two stations")
    shell = loft_sections([outer_wire_at(t) for t in stations], ruled=ruled)
    passage = loft_sections([passage_wire_at(t) for t in stations], ruled=ruled)
    return shell, passage
