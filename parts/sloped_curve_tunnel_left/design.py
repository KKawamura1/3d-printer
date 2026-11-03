"""SC02L-V4: same unmarked SC02-V10 CAD mirrored across XZ, then engraved.

The right shape owns the path, roof, lower receivers and E31 features.
This wrapper exists only to generate an independently versioned left STL.
"""
from pathlib import Path

from parts.sloped_curve_tunnel import design as right

PART_ID = right.LEFT_PART_ID
SOURCE_RIGHT_ID = right.PART_ID


def build_part():
    return right.build_part(side="left")


def export(out=Path("build/sloped-curve-tunnel-left")):
    return right.export(out, side="left")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("build/sloped-curve-tunnel-left"))
    export(parser.parse_args().out)
