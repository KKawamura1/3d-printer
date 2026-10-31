"""Stable validation contract for versioned CAD outputs.

A model owns geometric checks and report["passed"]; the pipeline owns mesh
verification when the model did not emit report["mesh"]. No physical fit,
slicing or visual review is inferred from either result.
"""
import json


def verified_report(stl, *, mesh_validator=None):
    """Validate report.json next to an STL, filling only a missing mesh result.

    Existing negative mesh results are never overridden. The optional checker
    permits fast isolated tests without importing the CAD kernel.
    """
    report_path = stl.parent / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("passed") is not True:
        raise ValueError(f"CAD geometry verification failed: {report_path} (passed must be true)")

    mesh = report.get("mesh")
    if mesh is None:
        if mesh_validator is None:
            # Keep the incremental planner and its tests independent of CadQuery.
            from brickcad.verify import mesh_check
            mesh_validator = mesh_check
        mesh = mesh_validator(stl)
        if not isinstance(mesh, dict) or mesh.get("passed") is not True:
            raise ValueError(f"CAD mesh verification failed: {stl}")
        report["mesh"] = mesh
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"CAD REPORT: computed missing mesh verification for {stl}", flush=True)
    elif not isinstance(mesh, dict) or mesh.get("passed") is not True:
        raise ValueError(f"CAD mesh verification failed: {report_path}")
    return report
