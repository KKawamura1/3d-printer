# STL transfer diagnostic (2026-10-31)

Isolated diagnostic branch, not a printable product. `small-tetrahedron.stl` is a 284-byte binary STL with four triangle faces.

Purpose: distinguish GitHub blob upload / commit / branch-update failures from CAD generation and preview failures. No CAD modeling or browser preview was run for the small sample.

The GitHub API transfer path was used instead of a local `git push`, so this verifies an API-equivalent upload and branch update, **not** the local Git transport used by Work.
