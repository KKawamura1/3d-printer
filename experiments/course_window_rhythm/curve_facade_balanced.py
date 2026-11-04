"""SD04-V20: symmetry trial based on SD04-V19.

Same three pentagonal windows, same total outer facade and exactly the same
12-way arclength partition. Shift each window 0.5 section towards the inlet:
  V19: 2–3, 6–7, 10–11
  V20: 1.5–2.5, 5.5–6.5, 9.5–10.5

Gaps counted in *12th-section units*, excluding 1-section-wide apertures:
  inlet margin : gap1 : gap2 : exit margin = 1.5:3:3:1.5 = 1:2:2:1.

V19 and V18 stay untouched. This file is only a parameterization of the
audited V19 build, not a second divergent geometry implementation.
"""
from pathlib import Path
from experiments.course_window_rhythm import curve_facade

PART_ID = "SD04-V20"
SEGMENTS = ((1.5, 2.5), (5.5, 6.5), (9.5, 10.5))
ORIGINAL_SEGMENTS = curve_facade.SEGMENTS
FRACTIONAL_SHIFT = .5
PITCH_MM = curve_facade.TOTAL_WALL_MM / curve_facade.DIVISIONS
SHIFT_MM = FRACTIONAL_SHIFT * PITCH_MM


def design(cfg=None):
    return curve_facade.design(cfg, segments=SEGMENTS)


def build(out):
    return curve_facade.build(Path(out), segments=SEGMENTS, part_id=PART_ID)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path,
                   default=Path("build/course-window-balanced"))
    opt = p.parse_args()
    build(opt.out)
