"""Small subprocess checks for stage completion, failures and timeout recovery."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).with_name('run-stage.py')


class StageTests(unittest.TestCase):
    def run_stage(self, code, *options):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        result = subprocess.run([sys.executable, str(RUNNER), '--name', 'check',
                                 '--log-root', str(root), *options, '--',
                                 sys.executable, '-c', code], capture_output=True, text=True,
                                timeout=10)
        events = [json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
        return result, events

    def test_completion_preserves_output_and_fingerprint(self):
        result, events = self.run_stage("print('child output')", '--artifact', str(RUNNER))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(events[-1]['event'], 'completed')
        artifact = next(e for e in events if e['event'] == 'artifact')
        self.assertEqual(artifact['sha256'], hashlib.sha256(RUNNER.read_bytes()).hexdigest())
        self.assertEqual(Path(events[0]['output_log']).read_text().strip(), 'child output')

    def test_cwd_is_explicitly_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = subprocess.run(
                [sys.executable, str(RUNNER), '--name', 'cwd', '--cwd', str(root),
                 '--log-root', str(root / 'logs'), '--',
                 sys.executable, '-c', 'import os; print(os.getcwd())'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(root), next((root / 'logs').glob('*.log')).read_text())

    def test_child_failure_is_not_completion(self):
        result, events = self.run_stage('raise SystemExit(7)')
        self.assertEqual(result.returncode, 7)
        self.assertEqual(events[-1]['event'], 'failed')

    def test_timeout_records_heartbeat_and_stops_child(self):
        result, events = self.run_stage('import time; time.sleep(60)',
                                        '--timeout', '.3', '--heartbeat', '.05')
        self.assertEqual(result.returncode, 124)
        self.assertIn('heartbeat', [e['event'] for e in events])
        self.assertEqual(events[-1]['event'], 'timeout')

    def test_missing_artifact_is_failure(self):
        result, events = self.run_stage('pass', '--artifact', '/nonexistent/stage-artifact')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(events[-1]['error_type'], 'FileNotFoundError')


if __name__ == '__main__':
    unittest.main()
