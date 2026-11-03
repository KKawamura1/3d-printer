"""Shape-neutral CAD delivery shared by PR56's course geometry families.

CAD construction, shape tolerances and mesh sampling parameters remain in each
family. This module only exports the already-built BRep and normalizes
float32-degenerate STL facets; it cannot silently change the course geometry.
"""
from pathlib import Path
import struct

import cadquery as cq

from brickcad.verify import mesh_check


def normalize_binary_stl(path):
    """Discard triangles whose vertices collapse after float32 STL encoding.

    Preserve the original header and retained triangle bytes. This is the
    identical filtering rule formerly copied into every course exporter.
    """
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) < 84:
        raise ValueError("Malformed binary STL (missing header)")
    count = struct.unpack_from("<I", raw, 80)[0]
    if count < 1 or len(raw) != 84 + count * 50:
        raise ValueError("Malformed binary STL (triangle count)")
    retained = []
    for index in range(count):
        triangle = raw[84 + 50 * index:134 + 50 * index]
        coordinates = struct.unpack("<12fH", triangle)[3:12]
        if len({tuple(coordinates[j:j+3]) for j in (0, 3, 6)}) == 3:
            retained.append(triangle)
    if not retained:
        raise ValueError("STL has no non-degenerate triangles")
    if len(retained) != count:
        path.write_bytes(raw[:80] + struct.pack("<I", len(retained))
                         + b"".join(retained))
    return len(retained)


def export_geometry(shape, out, *, tolerance=.01, angular_tolerance=.1):
    """Export STL + STEP, checking the mesh without changing the input BRep.

    The family passes its proven tessellation tolerances, e.g. the sloped R48
    tunnel intentionally uses .02/.15, unlike other families' .01/.10.
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    stl = out / "brick.stl"
    cq.exporters.export(shape, str(stl), tolerance=tolerance,
                        angularTolerance=angular_tolerance)
    normalize_binary_stl(stl)
    cq.exporters.export(shape, str(out / "brick.step"))
    return stl, mesh_check(stl)
