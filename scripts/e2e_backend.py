"""Test-only process supervisor with a disposable, isolated PostgreSQL schema."""
import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
from sqlalchemy import text
from trustdesk.db import engine

schema = "e2e_" + uuid.uuid4().hex
processes = []
with engine.begin() as connection:
    connection.execute(text(f'CREATE SCHEMA "{schema}"'))
env = {**os.environ, "DATABASE_SCHEMA": schema, "APP_ORIGIN": "http://localhost:3000"}

def stop(*args):
    raise KeyboardInterrupt

signal.signal(signal.SIGTERM, stop)
try:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True)
    subprocess.run([sys.executable, "-m", "trustdesk.cli", "import-data"], cwd=BACKEND, env=env, check=True)
    subprocess.run([sys.executable, "-m", "trustdesk.cli", "index-knowledge"], cwd=BACKEND, env=env, check=True)
    processes.append(subprocess.Popen([sys.executable, "-m", "trustdesk.worker"], cwd=BACKEND, env=env))
    processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "trustdesk.main:app", "--port", "8000"], cwd=BACKEND, env=env))
    processes[-1].wait()
except KeyboardInterrupt:
    pass
finally:
    for process in processes:
        process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    with engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
