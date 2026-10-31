"""Select and build only CAD jobs affected by changed source/config files.

One declarative cad/jobs/<id>.json defines a printable model. Dependencies are
built only when the dependent model is selected; every build is isolated on its
own Actions runner and exports a small preview alongside the STL artifact.
"""
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "cad" / "jobs"
OUTPUT = ROOT / "build" / "cad-artifacts"
WORK = ROOT / "build" / "remote"


def safe_path(path):
    p = Path(path)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise ValueError(f"Unsafe relative path: {path}")
    return p


def load_jobs(directory=JOBS):
    result = {}
    for filename in sorted(directory.glob("*.json")):
        spec = json.loads(filename.read_text(encoding="utf-8"))
        job_id = spec.get("id")
        if not isinstance(job_id, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", job_id):
            raise ValueError(f"Bad job ID in {filename}")
        if filename.stem != job_id or job_id in result:
            raise ValueError(f"Job ID/filename mismatch: {filename}")
        for required in ("watch", "depends_on", "command", "outputs"):
            if not isinstance(spec.get(required), list):
                raise ValueError(f"{job_id}: missing list {required}")
        if not spec["watch"] or not spec["outputs"]:
            raise ValueError(f"{job_id}: needs watch rules and STL outputs")
        if not spec["command"] or not all(isinstance(arg, str) for arg in spec["command"]):
            raise ValueError(f"{job_id}: command must be a nonempty argument list")
        for pattern in spec["watch"]:
            if not isinstance(pattern, str):
                raise ValueError(f"{job_id}: invalid watch")
            safe_path(pattern)
        for item in spec["outputs"]:
            if set(item) != {"path", "name", "report"}:
                raise ValueError(f"{job_id}: each output needs path, name and report")
            safe_path(item["path"])
            safe_path(item["report"])
            name = item["name"]
            if Path(name).name != name or not name.endswith(".stl"):
                raise ValueError(f"{job_id}: invalid printable name {name}")
        result[job_id] = spec
    for job_id, spec in result.items():
        for dep in spec["depends_on"]:
            if dep not in result or dep == job_id:
                raise ValueError(f"{job_id}: invalid dependency {dep}")
    def check_cycles(job_id, active, visited):
        if job_id in active:
            raise ValueError(f"Dependency cycle at {job_id}")
        if job_id in visited:
            return
        for dep in result[job_id]["depends_on"]:
            check_cycles(dep, active | {job_id}, visited)
        visited.add(job_id)
    visited = set()
    for job_id in result:
        check_cycles(job_id, set(), visited)
    return result


def changed_paths(before, after):
    if not before or set(before) == {"0"}:
        before = subprocess.check_output(
            ["git", "rev-parse", f"{after}^"], cwd=ROOT, text=True).strip()
    value = subprocess.check_output(
        ["git", "diff", "--name-only", "--no-renames", before, after],
        cwd=ROOT, text=True)
    return set(value.splitlines())


def select_jobs(jobs, changed):
    """Match configured inputs, then all downstream jobs that consume their output."""
    selected = {
        job_id for job_id, spec in jobs.items()
        if f"cad/jobs/{job_id}.json" in changed
        or any(fnmatch.fnmatchcase(path, pat) for path in changed for pat in spec["watch"])
    }
    while True:
        new = selected | {
            job_id for job_id, spec in jobs.items()
            if set(spec["depends_on"]) & selected
        }
        if new == selected:
            break
        selected = new
    return sorted(selected)


def ensure_stl(path):
    size = path.stat().st_size
    if size < 134 or (size - 84) % 50:
        raise ValueError(f"STL not binary or truncated: {path}")
    with path.open("rb") as source:
        source.seek(80)
        facets = struct.unpack("<I", source.read(4))[0]
    if not facets or size != 84 + 50 * facets:
        raise ValueError(f"STL facet count inconsistent: {path}")
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(block)
    return {"size_bytes": size, "triangles": facets, "sha256": sha.hexdigest()}


def run_build(jobs, job_id, complete):
    if job_id in complete:
        return
    spec = jobs[job_id]
    for dep in spec["depends_on"]:
        run_build(jobs, dep, complete)
    log_dir = WORK / "_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / (job_id + ".log")
    print(f"BUILD {job_id} start (log: {log.relative_to(ROOT)})", flush=True)
    command = spec["command"]
    try:
        with log.open("wb") as out:
            result = subprocess.run(command, cwd=ROOT, stdout=out,
                                    stderr=subprocess.STDOUT, timeout=1200,
                                    check=False)
        if result.returncode:
            raise RuntimeError(f"{job_id}: generator exited with {result.returncode}")
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as error:
        tail = log.read_bytes()[-2500:].decode("utf-8", errors="replace") if log.exists() else ""
        raise RuntimeError(f"{job_id}: {error}\nLast log output:\n{tail}") from error
    complete.add(job_id)
    print(f"BUILD {job_id} complete", flush=True)


def package(jobs, job_id):
    artifact = OUTPUT / job_id
    if artifact.exists():
        shutil.rmtree(artifact)
    artifact.mkdir(parents=True)
    files = {}
    for item in jobs[job_id]["outputs"]:
        source = ROOT / safe_path(item["path"])
        report_file = ROOT / safe_path(item["report"])
        if not source.is_file() or not report_file.is_file():
            raise FileNotFoundError(f"{job_id}: missing STL/report {source} / {report_file}")
        report = json.loads(report_file.read_text(encoding="utf-8"))
        if report.get("passed") is not True or report.get("mesh", {}).get("passed") is not True:
            raise ValueError(f"{job_id}: CAD/mesh validation not passed: {report_file}")
        meta = ensure_stl(source)
        target = artifact / item["name"]
        shutil.copyfile(source, target)
        report_target = artifact / f"{target.stem}.report.json"
        shutil.copyfile(report_file, report_target)
        preview = artifact / f"{target.stem}.preview.png"
        subprocess.run([sys.executable, "scripts/stl_snapshot.py", "--stl", str(target),
                        "--out", str(preview)], cwd=ROOT, check=True, timeout=180)
        files[item["name"]] = {**meta, "preview": preview.name,
                               "report": report_target.name}
        print(f"OUTPUT {job_id}: {target.name} ({meta['size_bytes']} bytes, {meta['triangles']} triangles)", flush=True)
    info = {
        "job": job_id, "source_commit": os.environ.get("GITHUB_SHA"),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": jobs[job_id]["watch"], "dependencies": jobs[job_id]["depends_on"],
        "physical_fit_validated": False, "slicing_validated": False, "files": files
    }
    (artifact / "manifest.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    (artifact / "SHA256SUMS.txt").write_text(
        "".join(f"{v['sha256']}  {name}\n" for name, v in files.items()), encoding="utf-8")
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("plan", "build", "list"))
    parser.add_argument("--before")
    parser.add_argument("--after")
    parser.add_argument("--targets", help="Comma-separated IDs for manual runs")
    parser.add_argument("--job", help="One ID selected by Actions matrix")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    jobs = load_jobs()
    if args.operation == "list":
        print("\n".join(jobs))
        return
    if args.operation == "plan":
        if args.targets:
            chosen = [s.strip() for s in args.targets.split(",") if s.strip()]
            if any(s not in jobs for s in chosen):
                parser.error(f"Unknown job(s): {chosen}")
            selected = sorted(set(chosen))
        else:
            if not args.after:
                parser.error("Provide --before/--after or --targets")
            changed = changed_paths(args.before, args.after)
            selected = select_jobs(jobs, changed)
            print(f"Changed inputs: {sorted(changed)}")
        payload = json.dumps({"include": [{"id": job} for job in selected]})
        print(f"Selected CAD jobs: {selected or '(none)'}")
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as out:
                out.write(f"matrix={payload}\nhas_jobs={str(bool(selected)).lower()}\n")
        return
    if args.job not in jobs:
        parser.error(f"Unknown CAD job: {args.job}")
    run_build(jobs, args.job, set())
    artifact = package(jobs, args.job)
    print(f"Artifact ready: {artifact.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
