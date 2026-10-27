"""Build the maintained DUPLO 2x4 using its adjacent profile."""
import argparse
from pathlib import Path
import json
from brickcad.model import from_profile
from brickcad.__main__ import export

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('build/basic-brick'))
    args = ap.parse_args()
    export(from_profile(json.loads(Path(__file__).with_name('profile.json').read_text())), args.out)
