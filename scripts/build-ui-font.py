"""Regenerate embedded UI glyphs from an installed @fontsource/noto-sans-jp package. Requires fonttools."""
import argparse
from pathlib import Path
import base64,logging
from fontTools.ttLib import TTFont
from fontTools import subset
from io import BytesIO
logging.getLogger('fontTools').setLevel(logging.ERROR)
parser=argparse.ArgumentParser()
parser.add_argument('fontsource_package',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
source=args.fontsource_package
chars={ord(c) for c in (root/'brickcad/viewer.html').read_text() if ord(c)>127}
remaining=set(chars);rules=[]
for p in sorted((source/'files').glob('*-400-normal.woff')):
 f=TTFont(p);codes=remaining.intersection(f.getBestCmap())
 if not codes:continue
 opts=subset.Options();opts.layout_features=[]
 sub=subset.Subsetter(options=opts);sub.populate(unicodes=codes);sub.subset(f)
 b=BytesIO();f.flavor='woff';f.save(b)
 rules.append("@font-face{font-family:BrickJP;font-style:normal;font-weight:400;font-display:block;src:url(data:font/woff;base64,"+base64.b64encode(b.getvalue()).decode()+") format('woff');unicode-range:"+','.join(f'U+{c:X}' for c in sorted(codes))+';}')
 remaining-=codes
assert not remaining,remaining
assets=root/'brickcad/assets';assets.mkdir(exist_ok=True)
(assets/'viewer-font.css').write_text('/* Noto Sans JP UI subset, SIL OFL 1.1. See OFL.txt. */\n'+'\n'.join(rules))
(assets/'OFL.txt').write_text((source/'LICENSE').read_text())
print('Embedded Japanese UI font:',len(chars),'glyphs',len(rules),'subsets',(assets/'viewer-font.css').stat().st_size,'bytes')
