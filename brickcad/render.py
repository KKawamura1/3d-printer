"""Render the actual BRep mesh, including a boolean-cut section."""
import json
from pathlib import Path
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def mesh(shape):
    verts, faces = shape.tessellate(0.03, 0.20)
    return [v.toTuple() for v in verts], faces


def preview(shape, p, out):
    fig = plt.figure(figsize=(14, 8), facecolor='#f5f7fa')
    cutter = cq.Workplane('XY').box(p.width+2,p.depth+2,30,centered=(True,False,False)).val()
    section = shape.cut(cutter)
    for index, (title, obj, elev, azim) in enumerate([
        ('Top / studs',shape,28,-55),('Underside / tubes',shape,-35,-55),
        ('BRep cut: y < 0',section,15,65),('Stacked / exploded',None,22,-50)
    ],1):
        ax=fig.add_subplot(2,2,index,projection='3d')
        items = [(obj,'#dc493c')] if obj is not None else [(shape,'#dc493c'),(shape.translate((0,0,p.height+2.5)),'#2783b5')]
        for item,color in items:
            verts,faces=mesh(item)
            ax.add_collection3d(Poly3DCollection([[verts[k] for k in f] for f in faces],facecolors=color,linewidths=0,shade=True,alpha=1))
        ax.set_xlim(-p.width/2-2,p.width/2+2)
        ax.set_ylim(-p.depth/2-2,p.depth/2+2)
        h=p.height+p.stud_height+(p.height+2.5 if obj is None else 0)
        ax.set_zlim(0,h)
        ax.set_box_aspect((p.width+4,p.depth+4,h))
        ax.view_init(elev,azim)
        ax.set_title(title,fontsize=12)
        ax.set_xlabel('X / mm'); ax.set_ylabel('Y / mm'); ax.set_zlabel('Z / mm')
    fig.suptitle(f'{p.ny} x {p.nx} brick | radial clearance {p.clearance:+.2f} mm',fontsize=17)
    fig.tight_layout()
    fig.savefig(out/'preview.png',dpi=150)
    plt.close(fig)


def viewer(shape, p, report, out):
    verts,faces=mesh(shape)
    template=(Path(__file__).parent/'viewer.html').read_text()
    payload=json.dumps(dict(vertices=verts,faces=faces,height=p.height,width=p.width,
                            report=report),separators=(',',':'))
    (out/'viewer.html').write_text(template.replace('__DATA__',payload))
