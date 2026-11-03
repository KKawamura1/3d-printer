"""SC05-V1: unmarked SC03 R48 downhill CAD reflected for the left track.

One shape implementation in PR #46; each direction receives a separate
3mm/0.4mm non-mirrored engraved ID only after final BRep orientation.
"""
from parts.sloped_curve_open_right import design as shared

PART_ID = 'SC05-V1'
SOURCE_VERSION = 'SC03-V5'
if shared.PART_ID != SOURCE_VERSION:
    raise ValueError(
        f'{PART_ID} requires {SOURCE_VERSION}, found {shared.PART_ID}; '
        'bump both targets together')

MIRROR = False  # SC03 right already uses XZ reflection; opposite side is left
DROP = shared.DROP
LENGTH = shared.LENGTH
FLOOR = shared.FLOOR
BALL = shared.BALL
DEPTH = shared.DEPTH
LABEL_Z = shared.LABEL_Z
xy = shared.xy
height = shared.height
slope = shared.slope
loft = shared.loft


def build_part(label=PART_ID):
    return shared.build_part(label=label, mirror=MIRROR)


def path():
    return shared.path(mirror=MIRROR)


def ports():
    return shared.ports(mirror=MIRROR)


def verify(shape, params):
    return shared.verify(shape, params, mirror=MIRROR)


def export(out):
    return shared.export(out, mirror=MIRROR, part_id=PART_ID)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    export(ap.parse_args().out)
