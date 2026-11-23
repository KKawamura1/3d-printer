"""GW01-V4: 120-degree release, using the common V3 rotor/guide geometry.

Only the desired angle changes. The 60-degree version remains reproducible.
"""
from __future__ import annotations
import argparse
from . import axial_v3 as shared

VERSION = "GW01-V4"
RELEASE_ANGLE = 120


def build_parts():
    return shared.build_parts(RELEASE_ANGLE)


def validate(parts):
    return shared.validate(parts, RELEASE_ANGLE)


def export(out):
    return shared.export(out, release_angle=RELEASE_ANGLE, model_id=VERSION)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="build/gravity-wheel-g01-v4")
    export(parser.parse_args().out)
