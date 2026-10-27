"""Shared connection solids. Callers supply layout and resolved dimensions.

These primitives contain no family, fit-candidate or printer defaults.
"""
import cadquery as cq


def make_studs(points, base_z, outer_radius, inner_radius, height, lip_radius=0.):
    studs = cq.Workplane('XY', origin=(0, 0, base_z)).pushPoints(points).circle(outer_radius)
    if inner_radius:
        studs = studs.circle(inner_radius)
    studs = studs.extrude(height)
    return studs.edges('>Z').fillet(lip_radius) if lip_radius else studs


def make_receiver(outer, points, opening_xy, height, tube_radius, tube_inner_radius, entry=0.):
    cavity = cq.Workplane('XY').box(*opening_xy, height, centered=(True, True, False))
    result = outer.cut(cavity)
    for x, y in points:
        tube = (cq.Workplane('XY', origin=(x, y, 0)).circle(tube_radius)
                .circle(tube_inner_radius).extrude(height))
        result = result.union(tube)
    return result.edges('<Z').chamfer(entry) if entry else result
