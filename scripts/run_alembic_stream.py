"""Run alembic upgrade with streamed output and logging for long-running migrations.

Usage: python scripts/run_alembic_stream.py upgrade head

This helper runs alembic as a subprocess and forwards stdout/stderr in real-time,
so logs can be tailed by CI or a developer while the migration runs.
"""
import subprocess
import sys

if __name__ == "__main__":
    args = sys.argv[1:] or ["upgrade", "head"]
    cmd = [sys.executable, "-m", "alembic"] + args
    print("Running:", " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
    )
    try:
        if proc.stdout is not None:
            for line in iter(proc.stdout.readline, ""):
                print(line, end="")
        ret = proc.wait()
        sys.exit(ret)
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        sys.exit(1)
        raise
