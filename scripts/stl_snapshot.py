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


def render(stl, output, max_faces=1800):
    with Path(stl).open("rb") as stream:
        stream.seek(80)
        count = int.from_bytes(stream.read(4), "little")
    faces = np.memmap(stl, dtype=TRI, mode="r", offset=84, shape=(count,))
    coords = faces["vertices"]
    minimum = coords.min(axis=(0, 1)).astype(float)
    maximum = coords.max(axis=(0, 1)).astype(float)
    if not np.isfinite(minimum).all() or not np.isfinite(maximum).all():
        raise ValueError("Non-finite STL vertex coordinate")
    mid = (minimum + maximum) / 2
    radius = max(float((maximum - minimum).max()) / 2, 1.0) * 1.08
    selected = np.linspace(0, count - 1, min(count, max_faces), dtype=np.int64)
    polygons = np.asarray(coords[selected], dtype=float)
    fig = plt.figure(figsize=(12, 9), facecolor="#f6f7fb")
    views = [
        ("Isometric", 26, -52),
        ("Underside", -50, -52),
        ("Top", 85, -85),
        ("Side", 8, -90),
    ]
    for i, (label, elev, azim) in enumerate(views, 1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        mesh = Poly3DCollection(polygons, facecolors="#5486b5",
                                edgecolors="none", linewidths=0, alpha=1)
        ax.add_collection3d(mesh)
        ax.set_xlim(mid[0] - radius, mid[0] + radius)
        ax.set_ylim(mid[1] - radius, mid[1] + radius)
        ax.set_zlim(mid[2] - radius, mid[2] + radius)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(label)
        ax.set_axis_off()
    dimensions = maximum - minimum
    fig.suptitle(
        f"{Path(stl).name} | {count:,} triangles | "
        f"bounds {dimensions[0]:.2f} x {dimensions[1]:.2f} x {dimensions[2]:.2f} mm\n"
        f"Sampled faces for preview only; full-resolution STL remains unchanged",
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
