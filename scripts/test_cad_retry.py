"""No-network tests for recovery of failed/cancelled CAD generation."""
import unittest
from unittest import mock

import cad_retry


def run(number, conclusion, *, status="completed"):
    return {"id": number, "run_number": number, "head_sha": "%040x" % number,
            "conclusion": conclusion, "status": status}


class RetrySelectionTests(unittest.TestCase):
    def test_failed_then_test_only_noop_then_fixed_still_retries(self):
        runs = [run(13, None, status="in_progress"), run(12, "success"),
                run(11, "failure"), run(10, "success")]
        seen = []
        def artifact(item):
            seen.append(item["run_number"])
            return item["run_number"] == 10
        unresolved = cad_retry.unrecovered_runs(runs, 13, artifact)
        self.assertEqual([item["run_number"] for item in unresolved], [11])
        self.assertEqual(seen, [12, 10])

    def test_successful_artifact_clears_prior_failure(self):
        runs = [run(20, None, status="in_progress"), run(19, "success"),
                run(18, "failure")]
        self.assertEqual(cad_retry.unrecovered_runs(
            runs, 20, lambda item: item["run_number"] == 19), [])

    def test_cancelled_or_pending_previous_attempt_is_retried(self):
        runs = [run(30, None, status="in_progress"), run(29, None, status="in_progress"),
                run(28, "cancelled"), run(27, "success")]
        self.assertEqual([r["run_number"] for r in
                          cad_retry.unrecovered_runs(runs, 30, lambda item: True)],
                         [29, 28])

    def test_no_failures_does_not_request_regeneration(self):
        runs = [run(4, "success"), run(3, "success")]
        self.assertEqual(cad_retry.unrecovered_runs(runs, 5, lambda item: False), [])

    @mock.patch.object(cad_retry, "git", return_value="base123")
    @mock.patch.object(cad_retry, "get_pr_base", return_value="pr-sha")
    @mock.patch.object(cad_retry, "api_get")
    def test_stacked_pr_uses_its_own_base(self, api, pr, git):
        api.side_effect = [
            {"workflow_runs": [run(5, "failure")]},
            {"artifacts": []},
        ]
        base, count = cad_retry.retry_base("example/repo", "branch", 6, "token")
        self.assertEqual((base, count), ("base123", 1))
        git.assert_called_once_with("merge-base", "HEAD", "pr-sha")

    @mock.patch.object(cad_retry, "git", return_value="parent123")
    @mock.patch.object(cad_retry, "get_pr_base", return_value=None)
    @mock.patch.object(cad_retry, "api_get")
    def test_default_branch_uses_parent_of_first_failed_push(self, api, pr, git):
        api.return_value = {"workflow_runs": [run(7, "failure"), run(6, "failure")]}
        base, count = cad_retry.retry_base("example/repo", "main", 8, "token")
        self.assertEqual((base, count), ("parent123", 2))
        git.assert_called_once_with("rev-parse", run(6, "failure")["head_sha"] + "^")


if __name__ == "__main__":
    unittest.main()
