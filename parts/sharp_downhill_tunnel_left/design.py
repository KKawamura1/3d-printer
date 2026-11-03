"""SD04-V9 left-hand tunnel: mirror the shared SD03 geometry, then engrave.

Geometry, receiver, studs, port sampling and STL validation have one
authoritative implementation in parts.sharp_downhill_tunnel_right.design.
Keep this thin adapter to preserve a separately identifiable left STL.
"""
from parts.sharp_downhill_tunnel_right import design as shared

PART_ID = 'SD04-V9'
SOURCE_VERSION = 'SD03-V10'
if shared.PART_ID != SOURCE_VERSION:
    raise ValueError(
        f'{PART_ID} requires right-hand geometry {SOURCE_VERSION}, '
        f'but imported {shared.PART_ID}; bump both printed revisions together'
    )

MIRROR = True
KIND = shared.KIND
DROP = shared.DROP
TUNNEL = shared.TUNNEL
STEEP = shared.STEEP
LENGTH = shared.LENGTH
FLOOR = shared.FLOOR
BALL = shared.BALL
DEPTH = shared.DEPTH
LABEL_X = shared.LABEL_X
LABEL_Z = shared.LABEL_Z
xy = shared.xy
height = shared.height
slope = shared.slope
wire = shared.wire
stations = shared.stations
loft = shared.loft


def build_part(label=PART_ID):
    # shared.build_part mirrors the undecorated BRep first and then engraves
    # the provided left-specific label with brickcad.marking standard defaults.
    return shared.build_part(label=label, mirror=True)


def path():
    return shared.path(mirror=True)


def ports():
    return shared.ports(mirror=True)


def verify(shape, params):
    return shared.verify(shape, params, mirror=True)


def export(out):
    return shared.export(out, mirror=True, part_id=PART_ID)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    export(ap.parse_args().out)
