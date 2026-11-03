"""SD02-V4 open left curve: reflect SD01's unmarked BRep, then engrave.

All geometry, receiver, sweep and STL logic lives in the right-hand
implementation. Mirror the undecorated solid before adding a readable,
left-specific standard 3mm/0.4mm recessed marking.
"""
from parts.sharp_downhill_open_right import design as shared

PART_ID = 'SD02-V4'
SOURCE_VERSION = 'SD01-V4'
if shared.PART_ID != SOURCE_VERSION:
    raise ValueError(
        f'{PART_ID} requires shared geometry {SOURCE_VERSION}, '
        f'but imported {shared.PART_ID}; bump both versions together'
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
