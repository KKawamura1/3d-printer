"""Current production contract for every Issue #37 ball-course geometry.

Routing choices describe geometry, never a fit profile or engraving version.
The historical fit profiles remain available to archived experiments, but
production course builders can only use this module's fixed E31-05 settings.
"""
from dataclasses import dataclass, field, replace
from contextlib import contextmanager
from contextvars import ContextVar

FIT_PROFILE_ID = "duplo-e27-play-v1"  # Starting stud/receiver; E31 is applied below
RECEIVER_DEPTH_MM = 4.75
TUBE_RADIUS_MM = 6.60
SLOT_END_Z_MM = 3.50
MARK_SIZE_MM = 3.0
MARK_DEPTH_MM = 0.4
PRODUCTION_CONTRACT = "issue37-e31-05-shallow-engraved-v1"

# Ordered, intentional Issue #37 classification axis values.
CATEGORY_AXES = {
    1: ("horizontal", "straight", "open"),
    2: ("horizontal", "gentle_right", "open"),
    3: ("horizontal", "gentle_left", "open"),
    4: ("horizontal", "sharp_right", "open"),
    5: ("horizontal", "sharp_left", "open"),
    6: ("horizontal", "straight", "tunnel"),
    7: ("horizontal", "gentle_right", "tunnel"),
    8: ("horizontal", "gentle_left", "tunnel"),
    9: ("horizontal", "sharp_right", "tunnel"),
    10: ("horizontal", "sharp_left", "tunnel"),
    11: ("gentle", "straight", "open"),
    12: ("gentle", "gentle_right", "open"),
    13: ("gentle", "gentle_left", "open"),
    14: ("gentle", "sharp_right", "open"),
    15: ("gentle", "sharp_left", "open"),
    16: ("gentle", "straight", "tunnel"),
    17: ("gentle", "gentle_right", "tunnel"),
    18: ("gentle", "gentle_left", "tunnel"),
    19: ("gentle", "sharp_right", "tunnel"),
    20: ("gentle", "sharp_left", "tunnel"),
    21: ("steep", "straight", "tunnel"),
    24: ("steep", "sharp_right", "tunnel"),
    25: ("steep", "sharp_left", "tunnel"),
}
REVERSIBLE_PAIRS = {(2, 3), (4, 5), (9, 10)}


def course_axes(numbers, *, windows=0):
    """Canonical geometry axes for one physical mesh (may cover two directions)."""
    ids = tuple(numbers)
    if len(ids) not in (1, 2) or any(i not in CATEGORY_AXES for i in ids):
        raise ValueError("Unknown Issue #37 category combination")
    if len(ids) == 2 and ids not in REVERSIBLE_PAIRS:
        raise ValueError("Only the three documented reverse-running pairs may share a mesh")
    slope, curve, enclosure = CATEGORY_AXES[ids[0]]
    if len(ids) == 2:
        other = CATEGORY_AXES[ids[1]]
        if (slope, enclosure) != (other[0], other[2]):
            raise ValueError("Opposite travel categories disagree")
    if type(windows) is not int or windows not in (0, 3):
        raise ValueError("Only current zero/three window layouts are supported")
    if windows and ids != (16,):
        raise ValueError("Window openings supported only on gentle straight tunnel")
    return {"slope": slope, "curve": curve, "enclosure": enclosure,
            "windows": windows}


def kernel_for(course):
    """Geometry-specific algorithm selected exclusively by the four course axes."""
    if not isinstance(course, dict) or set(course) != {"slope", "curve", "enclosure", "windows"}:
        raise ValueError("Course requires slope, curve, enclosure and windows")
    slope, curve = course["slope"], course["curve"]
    enclosure, windows = course["enclosure"], course["windows"]
    if type(windows) is not int or windows not in (0, 3):
        raise ValueError("Invalid window count")
    if slope == "horizontal":
        if windows:
            raise ValueError("Windows not supported for horizontal course")
        if curve == "straight":
            return "straight_rail" if enclosure == "open" else "straight_tunnel" if enclosure == "tunnel" else _unsupported()
        if curve in ("gentle_right", "gentle_left"):
            return "loft" if enclosure == "open" else "horizontal_r48_tunnel" if enclosure == "tunnel" else _unsupported()
        if curve in ("sharp_right", "sharp_left"):
            return "sharp_r16" if enclosure in ("open", "tunnel") else _unsupported()
    if slope == "gentle":
        if curve == "straight":
            if enclosure == "open" and not windows:
                return "loft"
            if enclosure == "tunnel" and windows == 3:
                return "downhill_windowed"
        if windows:
            raise ValueError("Windows unsupported for sloped curves")
        if curve in ("gentle_right", "gentle_left"):
            return "loft" if enclosure == "open" else "sloped_r48_tunnel" if enclosure == "tunnel" else _unsupported()
        if curve in ("sharp_right", "sharp_left") and enclosure in ("open", "tunnel"):
            return "loft"
    if slope == "steep" and enclosure == "tunnel" and not windows and curve in (
        "straight", "sharp_right", "sharp_left"
    ):
        return "drop"
    raise ValueError("Unsupported course axes: " + repr(course))


def _unsupported():
    raise ValueError("Unsupported course enclosure")


def validate_course_axes(course, numbers):
    expected = course_axes(numbers, windows=3 if tuple(numbers) == (16,) else 0)
    if course != expected:
        raise ValueError("Course axes disagree with Issue #37 category: " + repr(numbers))
    return kernel_for(course)


def course_fit(*, nx, ny, height_units=1, **overrides):
    """One source for fit-profile selection and E31 tube sizing."""
    # Only the two geometry-only deviations currently used by verified courses
    # are permitted. Never allow changing studs, cavity wall or E31 tube sizing.
    prohibited = set(overrides) - {"height", "body_offset_xy"}
    if prohibited:
        raise ValueError("Production course fit cannot override E31 profile: "
                         + ", ".join(sorted(prohibited)))
    from brickcad.model import brick_from_fit
    profile = brick_from_fit(
        FIT_PROFILE_ID, nx=nx, ny=ny, height_units=height_units, **overrides
    )
    result = replace(profile, tube_radius=TUBE_RADIUS_MM)
    audit = _CURRENT_COURSE.get()
    if audit is not None:
        audit.fit_calls += 1
    return result


def add_course_receiver_features(shape, centres, tube_radius, *, receiver_depth):
    """No historical default receiver_depth: explicit shallow contract or fail."""
    if abs(float(receiver_depth) - RECEIVER_DEPTH_MM) > 1e-6:
        raise ValueError("Course receiver must use shallow 4.75 mm E31-05")
    if abs(float(tube_radius) - TUBE_RADIUS_MM) > 1e-6:
        raise ValueError("Course tube OD must be 13.20 mm")
    from parts.tunnel.e31_fit import (
        add_e31_05_receiver_features, slot_end_z_for_receiver_depth,
    )
    if slot_end_z_for_receiver_depth(receiver_depth) != SLOT_END_Z_MM:
        raise ValueError("Course receiver slot end is not Z3.50")
    result = add_e31_05_receiver_features(
        shape, centres, tube_radius, receiver_depth=receiver_depth
    )
    audit = _CURRENT_COURSE.get()
    if audit is not None:
        audit.receiver_calls += 1
    return result


def _validate_mark(label, size, depth):
    if not isinstance(label, str) or not label or (
        abs(float(size) - MARK_SIZE_MM) > 1e-8
        or abs(float(depth) - MARK_DEPTH_MM) > 1e-8
    ):
        raise ValueError("All course parts require their ID at 3.0 mm / 0.4 mm")


def engrave_course(shape, label, *, x, y, z, size=MARK_SIZE_MM, depth=MARK_DEPTH_MM):
    _validate_mark(label, size, depth)
    from brickcad.marking import engrave
    result = engrave(shape, label, x=x, y=y, z=z, size=MARK_SIZE_MM, depth=MARK_DEPTH_MM)
    audit = _CURRENT_COURSE.get()
    if audit is not None:
        audit.marked_labels.append(label)
    return result


def engrave_course_west(shape, label, *, x, y, z, size=MARK_SIZE_MM, depth=MARK_DEPTH_MM):
    _validate_mark(label, size, depth)
    from brickcad.marking import engrave_west
    result = engrave_west(shape, label, x=x, y=y, z=z, size=MARK_SIZE_MM, depth=MARK_DEPTH_MM)
    audit = _CURRENT_COURSE.get()
    if audit is not None:
        audit.marked_labels.append(label)
    return result


@dataclass
class CourseBuildAudit:
    """Record actual common operations performed during one production export.

    This is an enforcement boundary, not an optional builder-provided status
    flag. Independent parity and old experiments never enter this context.
    """
    model_id: str
    fit_calls: int = 0
    receiver_calls: int = 0
    marked_labels: list[str] = field(default_factory=list)

    def validate(self):
        if self.fit_calls < 1:
            raise ValueError(f"{self.model_id}: production fit bypassed")
        if self.receiver_calls < 1:
            raise ValueError(f"{self.model_id}: production E31 receiver bypassed")
        if self.marked_labels != [self.model_id]:
            raise ValueError(
                f"{self.model_id}: requires exactly one final standard engraving; "
                f"got {self.marked_labels!r}"
            )

    def manifest(self):
        self.validate()
        return {
            "model_id": self.model_id,
            "production_contract": PRODUCTION_CONTRACT,
            "fit_calls": self.fit_calls,
            "e31_receiver_calls": self.receiver_calls,
            "final_marking_labels": list(self.marked_labels),
        }


_CURRENT_COURSE: ContextVar[CourseBuildAudit | None] = ContextVar(
    "issue37_current_course", default=None
)


@contextmanager
def audited_production_course(model_id):
    """Reject missing, duplicate, temporary, or wrong-ID finishing in production."""
    if _CURRENT_COURSE.get() is not None:
        raise ValueError("Nested production course builds are not allowed")
    if not isinstance(model_id, str) or not model_id:
        raise ValueError("A production course must have a valid model ID")
    audit = CourseBuildAudit(model_id)
    token = _CURRENT_COURSE.set(audit)
    try:
        yield audit
        audit.validate()
    finally:
        _CURRENT_COURSE.reset(token)
