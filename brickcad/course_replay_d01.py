"""Revision-pinned D01 replay; imports only the downhill-tunnel CAD source.

Do not import T01's exporter here: model source version tracking must stay
isolated from the straight tunnel.
"""
from parts.downhill_tunnel import design as reference
from brickcad.course_generator import main_for_source


if __name__ == "__main__":
    main_for_source(reference)
