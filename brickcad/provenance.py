"""Resolved design and source fingerprints; print observations live separately."""
from dataclasses import asdict
import hashlib
from pathlib import Path
from .standards import FAMILIES, fit_profile


def design_manifest(part, *, channel=None, channel_standard=None, finish=None):
    root = Path(__file__).resolve().parents[1]
    sources = sorted((root/'brickcad').glob('*.py'))
    sources += sorted((root/'parts').glob('*/design.py'))
    sources += [root/'brickcad/viewer.html', root/'brickcad/assets/viewer-font.css']
    return dict(
        family_standard_id=FAMILIES[part.family].id,
        fit_baseline=asdict(fit_profile(part.fit_profile_id)) if part.fit_profile_id else None,
        # Overrides, including legacy clearance, are explicit in the resolved inputs.
        resolved_parameters=asdict(part),
        body_xy_mm=[part.width, part.depth], receiver_opening_xy_mm=list(part.cavity_xy),
        channel_standard_id=channel_standard.id if channel_standard else None,
        channel=asdict(channel) if channel else None,
        edge_finish=asdict(finish) if finish else None,
        source_files={p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sources},
        print_setup=None, physical_fit_validated=False)
