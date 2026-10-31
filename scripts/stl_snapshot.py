"""Lightweight 4-view preview of a binary STL for remote artifact review.

The actual output STL is sampled for display only. This is a geometric
preview, not a screenshot of Bambu Studio, a BRep section, or slicing proof.
"""
import argparse
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

TRI = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])


def render(stl, output):
    with Path(stl).open("rb") as stream:
        stream.seek(80)
        count = int.from_bytes(stream.read(4), "little")
    faces = np.memmap(stl, dtype=TRI, mode="r", offset=84, shape=(count,))
    coords = faces["vertices"]
    minimum = coords.min(axis=(0, 1)).astype(float)
    maximum = coords.max(axis=(0, 1)).astype(float)
    if not np.isfinite(minimum).all() or not np.isfinite(maximum).all():
        raise ValueError("Non-finite STL vertex coordinate")
    # Render the full mesh, not a sparse sample of triangles. Randomly
    # omitting facets makes perfectly closed geometry look full of holes.
    # The original STL normals give simple directional lighting.
    polygons = np.asarray(coords, dtype=float)
    normals = np.asarray(faces["normal"], dtype=float)
    light = np.array([0.65, -0.4, 0.8])
    light /= np.linalg.norm(light)
    levels = 0.34 + 0.66 * np.maximum(normals @ light, 0)
    base_color = np.array([0.29, 0.54, 0.78])
    colors = np.minimum(base_color[None, :] * levels[:, None] + 0.09, 1.0)
    mid = (minimum + maximum) / 2
    span = np.maximum(maximum - minimum, 1.0)
    margin = span * 0.06
    fig = plt.figure(figsize=(12, 9), facecolor="#f6f7fb")
    views = [
        ("Isometric", 26, -52),
        ("Underside", -50, -52),
        ("Top", 85, -85),
        ("Opening / X", 10, 0),
    ]
    for i, (label, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        mesh = Poly3DCollection(polygons, facecolors=colors,
                                edgecolors="none", linewidths=0, alpha=1,
                                antialiased=False)
        ax.add_collection3d(mesh)
        ax.set_xlim(minimum[0] - margin[0], maximum[0] + margin[0])
        ax.set_ylim(minimum[1] - margin[1], maximum[1] + margin[1])
        ax.set_zlim(minimum[2] - margin[2], maximum[2] + margin[2])
        ax.set_box_aspect(tuple(span))
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(label)
        ax.set_axis_off()
    dimensions = maximum - minimum
    fig.suptitle(
        f"{Path(stl).name} | {count:,} triangles | "
        f"bounds {dimensions[0]:.2f} x {dimensions[1]:.2f} x {dimensions[2]:.2f} mm\n"
        f"Rendered from the full STL mesh; not a slicer or BRep inspection",
        fontsize=12
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=120)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stl", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    render(args.stl, args.out)


if __name__ == "__main__":
    main()
