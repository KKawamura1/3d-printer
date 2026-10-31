"""Run one bounded CAD/check/transfer stage with durable, compact progress logs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--cwd', type=Path, default=None)
    parser.add_argument('--log-root', type=Path, default=Path('build/stages'))
    parser.add_argument('--timeout', type=float, default=600)
    parser.add_argument('--heartbeat', type=float, default=15)
    parser.add_argument('--artifact', action='append', default=[])
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.timeout <= 0 or args.heartbeat <= 0:
        parser.error('command, positive timeout and heartbeat are required')
    args.log_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    stem = run_id + '-' + re.sub(r'[^A-Za-z0-9_.-]', '_', args.name)
    output_path = args.log_root / (stem + '.log')
    events_path = args.log_root / 'events.jsonl'
    started = time.monotonic()

    def emit(event, **fields):
        record = dict(timestamp=datetime.now(timezone.utc).isoformat(), run_id=run_id,
                      stage=args.name, event=event, elapsed_s=round(time.monotonic()-started, 3),
                      output_log=str(output_path), **fields)
        line = json.dumps(record, ensure_ascii=False)
        with events_path.open('a') as log:
            log.write(line + '\n')
            log.flush()
            os.fsync(log.fileno())
        print(line, flush=True)

    child = None

    def terminate():
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            # Also stop descendants still alive after the direct child exits.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'signal {signum}')

    signal.signal(signal.SIGTERM, interrupted)
    emit('start', command=command, cwd=str(Path.cwd()), timeout_s=args.timeout)
    try:
        with output_path.open('wb') as output:
            child = subprocess.Popen(command, cwd=args.cwd, stdout=output, stderr=subprocess.STDOUT,
                                     start_new_session=True,
                                     env={**os.environ, 'PYTHONUNBUFFERED': '1'})
            emit('spawned', pid=child.pid)
            next_heartbeat = started + args.heartbeat
            while child.poll() is None:
                now = time.monotonic()
                if now-started >= args.timeout:
                    terminate()
                    emit('timeout', pid=child.pid, returncode=child.returncode,
                         output_bytes=output_path.stat().st_size)
                    return 124
                if now >= next_heartbeat:
                    emit('heartbeat', pid=child.pid, output_bytes=output_path.stat().st_size)
                    next_heartbeat = now + args.heartbeat
                time.sleep(min(.2, args.heartbeat, max(.001, args.timeout-(now-started))))
        if child.returncode:
            emit('failed', returncode=child.returncode, output_bytes=output_path.stat().st_size)
            return child.returncode if child.returncode > 0 else 128-child.returncode
        for name in args.artifact:
            path = Path(name)
            digest = hashlib.sha256()
            with path.open('rb') as artifact:
                for chunk in iter(lambda: artifact.read(1024*1024), b''):
                    digest.update(chunk)
            emit('artifact', path=str(path), size_bytes=path.stat().st_size, sha256=digest.hexdigest())
        emit('completed', returncode=0, output_bytes=output_path.stat().st_size)
        return 0
    except KeyboardInterrupt as error:
        terminate()
        emit('interrupted', error=str(error))
        return 130
    except Exception as error:
        terminate()
        emit('failed', error_type=type(error).__name__, error=str(error))
        return 1


if __name__ == '__main__':
    sys.exit(main())
