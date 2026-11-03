"""Revision-pinned T01 replay; imports only the straight-tunnel CAD source.

The CAD version planner statically fingerprints T01 alone, not D01.
"""
from parts.tunnel import design_e31 as reference
from brickcad.course_generator import main_for_source


if __name__ == "__main__":
    main_for_source(reference)
