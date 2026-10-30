"""Recessed, versioned part IDs on a specified exterior planar face."""
import cadquery as cq


def engrave(shape, label, *, x, y, z, size=3., depth=.4):
    # XZ normal is -Y: text starts inside the wall and cuts towards the outside.
    tool=(cq.Workplane('XZ',origin=(x,y+depth,z))
          .text(label,size,depth+.05,font='DejaVu Sans',kind='bold',combine=False).val())
    result=shape.cut(tool).clean()
    if not result.isValid() or len(result.Solids())!=1 or shape.Volume()-result.Volume()<.2:
        raise ValueError(f'Failed recessed ID: {label}')
    return result


def engrave_west(shape,label,*,x,y,z,size=3.,depth=.4):
    # West exterior faces -X; local text right is -Y when viewed outside.
    plane=cq.Plane(origin=(x+depth,y,z),xDir=(0,-1,0),normal=(-1,0,0))
    tool=(cq.Workplane(plane)
          .text(label,size,depth+.05,font='DejaVu Sans',kind='bold',combine=False).val())
    result=shape.cut(tool).clean()
    if not result.isValid() or len(result.Solids())!=1 or shape.Volume()-result.Volume()<.2:
        raise ValueError(f'Failed recessed ID: {label}')
    return result
