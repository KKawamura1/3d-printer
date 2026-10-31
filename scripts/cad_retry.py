"""Find CAD builds that failed on earlier pushes and still need a successful artifact.

GitHub Actions push events only contain the latest commit delta.  If that delta
only fixes a test, the version bump from the failed run is not present there.
This helper finds the failed streak since the last *delivered* CAD artifact and
provides a wider comparison base, without rebuilding on every normal push.
"""
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


API = "https://api.github.com"


def api_get(path, token):
    req = Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urlopen(req, timeout=25) as response:
        return json.load(response)


def unrecovered_runs(runs, current_number, has_artifact):
    """Previous failed/cancelled/unfinished runs since last successful STL upload.

    A successful no-op planner does NOT clear an earlier failed build.
    """
    failed = []
    previous = sorted(
        (run for run in runs if int(run["run_number"]) < current_number),
        key=lambda run: int(run["run_number"]),
        reverse=True,
    )
    for run in previous:
        if run.get("status") == "completed" and run.get("conclusion") == "success":
            if has_artifact(run):
                break
        else:
            failed.append(run)
    return failed


def get_pr_base(repo, branch, token):
    owner = repo.split("/", 1)[0]
    query = urlencode({"state": "open", "head": owner + ":" + branch, "per_page": 30})
    prs = api_get("/repos/" + repo + "/pulls?" + query, token)
    matching = [pr for pr in prs if pr.get("head", {}).get("ref") == branch]
    if len(matching) > 1:
        raise RuntimeError("Ambiguous open PRs for branch " + branch)
    return matching[0]["base"]["sha"] if matching else None


def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL).decode().strip()


def retry_base(repo, branch, current_number, token, default_branch="main"):
    query = urlencode({"branch": branch, "event": "push", "per_page": 100})
    runs = api_get(
        "/repos/" + repo + "/actions/workflows/cad-preview.yml/runs?" + query, token
    )["workflow_runs"]

    def has_artifact(run):
        data = api_get(
            "/repos/" + repo + "/actions/runs/" + str(run["id"]) +
            "/artifacts?per_page=100", token
        )
        return any(a.get("name") == "cad-verified-stl" and not a.get("expired", False)
                   for a in data.get("artifacts", []))

    failures = unrecovered_runs(runs, current_number, has_artifact)
    if not failures:
        return "", 0
    # The earliest unresolved attempt may contain the only version bump.
    earliest = failures[-1]
    pr_base = get_pr_base(repo, branch, token)
    if pr_base:
        base = git("merge-base", "HEAD", pr_base)
    elif branch == default_branch:
        base = git("rev-parse", earliest["head_sha"] + "^")
    else:
        base = git("merge-base", "HEAD", "origin/" + default_branch)
    return base, len(failures)


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ["GITHUB_REF_NAME"]
    number = int(os.environ["GITHUB_RUN_NUMBER"])
    token = os.environ["GITHUB_TOKEN"]
    base, failed_count = retry_base(repo, branch, number, token)
    print("CAD retry: unresolved runs =", failed_count,
          "comparison base =", base or "(none)", flush=True)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write("retry_base=" + base + "\n")


if __name__ == "__main__":
    main()
