"""No-network tests for recovery of failed/cancelled CAD generation."""
import subprocess
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

    @mock.patch.object(cad_retry, "git")
    @mock.patch.object(cad_retry, "api_get")
    def test_pr_retry_uses_failed_push_parent_not_pr_merge_base(self, api, git):
        # A large PR may contain many older, already-successful experiments.
        # Retrying one failed later push must not revalidate that entire diff.
        attempt = run(5, "failure")
        api.side_effect = [
            {"workflow_runs": [attempt]},
            {"artifacts": []},
        ]
        git.side_effect = ["", "parent-of-failed-push"]
        base, count = cad_retry.retry_base("example/repo", "feature/pr56", 6, "token")
        self.assertEqual((base, count), ("parent-of-failed-push", 1))
        self.assertEqual(git.call_args_list, [
            mock.call("merge-base", "--is-ancestor", attempt["head_sha"], "HEAD"),
            mock.call("rev-parse", attempt["head_sha"] + "^"),
        ])

    @mock.patch.object(cad_retry, "git")
    @mock.patch.object(cad_retry, "api_get")
    def test_default_branch_uses_parent_of_first_failed_push(self, api, git):
        api.return_value = {"workflow_runs": [run(7, "failure"), run(6, "failure")]}
        git.side_effect = ["", "parent-of-earliest"]
        base, count = cad_retry.retry_base("example/repo", "main", 8, "token")
        self.assertEqual((base, count), ("parent-of-earliest", 2))
        git.assert_any_call("merge-base", "--is-ancestor",
                            run(6, "failure")["head_sha"], "HEAD")
        git.assert_any_call("rev-parse", run(6, "failure")["head_sha"] + "^")

    @mock.patch.object(cad_retry, "git")
    def test_force_push_skips_discarded_history(self, git):
        old = run(20, "failure")
        current = run(21, "failure")
        git.side_effect = [
            subprocess.CalledProcessError(1, "git"),  # old SHA not ancestor
            "", "new-attempt-parent",
        ]
        self.assertEqual(cad_retry.failed_attempt_parent([current, old]),
                         "new-attempt-parent")
        self.assertEqual(git.call_args_list, [
            mock.call("merge-base", "--is-ancestor", old["head_sha"], "HEAD"),
            mock.call("merge-base", "--is-ancestor", current["head_sha"], "HEAD"),
            mock.call("rev-parse", current["head_sha"] + "^"),
        ])

    @mock.patch.object(cad_retry, "git",
                       side_effect=subprocess.CalledProcessError(1, "git"))
    def test_unreachable_failed_commit_never_expands_to_pr_base(self, git):
        self.assertEqual(cad_retry.failed_attempt_parent([run(20, "failure")]), "")
        git.assert_called_once_with("merge-base", "--is-ancestor",
                                    run(20, "failure")["head_sha"], "HEAD")

    def test_invalid_failed_sha_cannot_select_retry_base(self):
        self.assertEqual(cad_retry.failed_attempt_parent(
            [{"head_sha": "not-an-object"}]), "")



if __name__ == "__main__":
    unittest.main()
