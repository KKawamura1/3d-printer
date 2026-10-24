"""Assemble real browser screenshots for agent/human visual review."""
import sys
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
root=Path(sys.argv[1] if len(sys.argv)>1 else 'build/browser-qa')
files=sorted(root.glob('[0-9][0-9]-*.png'))
if not files:raise SystemExit('No browser screenshots found')
width,height=720,530
sheet=Image.new('RGB',(width*2,height*((len(files)+1)//2)), '#edf1f6')
draw=ImageDraw.Draw(sheet)
for i,p in enumerate(files):
    thumb=ImageOps.contain(Image.open(p).convert('RGB'),(width-16,height-32))
    x,y=(i%2)*width,(i//2)*height
    draw.text((x+8,y+6),p.stem,fill='#102030')
    sheet.paste(thumb,(x+8,y+26))
sheet.save(root/'review-sheet.jpg',quality=90)
