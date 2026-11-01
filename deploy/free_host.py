"""Supervise the demo processes on a single free web instance.

Database stays external and durable. No implicit data import, no paid services,
no public API/action ports. A child failure stops the whole instance so the host
can restart it instead of leaving a partially healthy service running.
"""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def runtime_env():
    env = dict(os.environ)
    secret_path = Path(env.get("TRUSTDESK_SECRET_FILE", "/etc/secrets/trustdesk.json"))
    if secret_path.exists():
        values = json.loads(secret_path.read_text())
        if not isinstance(values, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
            raise ValueError("Secret configuration must be a string map")
        env.update(values)
    env.update({
        "API_INTERNAL_URL": "http://127.0.0.1:8000",
        "MOCK_ACTION_BASE_URL": "http://127.0.0.1:8001",
        "HOSTNAME": "0.0.0.0",
        "REVISION": env.get("RENDER_GIT_COMMIT", env.get("REVISION", "development")),
    })
    return env


def supervise(commands, env):
    children = []
    stopping = False

    def stop(_signal, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    result = 0
    try:
        for command, cwd in commands:
            children.append(subprocess.Popen(command, cwd=cwd, env=env))
        while not stopping:
            if any(child.poll() is not None for child in children):
                print("A TrustDesk process stopped; restarting the service as a unit", flush=True)
                result = 1
                break
            time.sleep(0.25)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        deadline = time.monotonic() + 20
        for child in children:
            try:
                child.wait(timeout=max(0.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    return result


def main():
    try:
        env = runtime_env()
        migration = subprocess.run([sys.executable, "-m", "trustdesk.manage"], env=env, timeout=180, capture_output=True)
        if migration.returncode:
            print("Database readiness/migration failed; deployment stopped. Check database access and migration compatibility.", flush=True)
            return 1
    except Exception:
        print("Private configuration or startup failed; no credential values are logged", flush=True)
        return 1
    commands = [
        ([sys.executable, "-m", "uvicorn", "trustdesk.main:app", "--host", "127.0.0.1", "--port", "8000"], "/app"),
        ([sys.executable, "-m", "uvicorn", "trustdesk.mock_actions:app", "--host", "127.0.0.1", "--port", "8001"], "/app"),
        ([sys.executable, "-m", "trustdesk.worker"], "/app"),
        (["node", "/web/server.js"], "/web"),
    ]
    return supervise(commands, env)


if __name__ == "__main__":
    raise SystemExit(main())
