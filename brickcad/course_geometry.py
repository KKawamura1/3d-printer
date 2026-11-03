"""Numerically stable shared sweep interpolation primitives.

Keep the historical arithmetic order of the two rise variants: CAD loft and
boolean operations can be sensitive to even tiny floating-point differences,
and PR56 verifies BRep parity with the original parts.
"""


def smoothstep_fall(t):
    """Full height at t=0, zero at t=1; caller clamps the input."""
    return 1 - 3*t*t + 2*t*t*t


def smoothstep_rise_expanded(t):
    """Historical expanded evaluation used in straight/loft roof transitions."""
    return 3*t*t - 2*t*t*t


def smoothstep_rise_factored(t):
    """Historical factored evaluation used in the R48 roof transitions."""
    return t*t*(3 - 2*t)
