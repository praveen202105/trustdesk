import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from free_host import runtime_env


class FreeHostTests(unittest.TestCase):
    def test_private_config_and_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.json"
            path.write_text(json.dumps({"SESSION_SECRET": "test-value", "APP_ORIGIN": "https://example.com"}))
            with patch.dict(os.environ, {"TRUSTDESK_SECRET_FILE": str(path), "RENDER_GIT_COMMIT": "a" * 40}):
                env = runtime_env()
            self.assertEqual(env["SESSION_SECRET"], "test-value")
            self.assertEqual(env["REVISION"], "a" * 40)
            self.assertEqual(env["API_INTERNAL_URL"], "http://127.0.0.1:8000")
            path.write_text(json.dumps({"SESSION_SECRET": ["invalid"]}))
            with patch.dict(os.environ, {"TRUSTDESK_SECRET_FILE": str(path)}):
                with self.assertRaises(ValueError):
                    runtime_env()

    def run_supervisor(self, command):
        script = "import os;from free_host import supervise;raise SystemExit(supervise(" + repr(command) + ",dict(os.environ)))"
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent))
        return subprocess.Popen([sys.executable, "-c", script], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_child_failure_stops_unit(self):
        process = self.run_supervisor([
            ([sys.executable, "-c", "import time;time.sleep(0.2);raise SystemExit(2)"], None),
            ([sys.executable, "-c", "import time;time.sleep(60)"], None),
        ])
        output, _ = process.communicate(timeout=8)
        self.assertEqual(process.returncode, 1)
        self.assertIn(b"restarting the service as a unit", output)

    def test_sigterm_reaps_children(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = Path(tmp) / "pid"
            child = "import os,time;from pathlib import Path;Path(" + repr(str(pid_file)) + ").write_text(str(os.getpid()));time.sleep(60)"
            process = self.run_supervisor([([sys.executable, "-c", child], None)])
            try:
                deadline = time.monotonic() + 5
                while not pid_file.exists() and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(pid_file.exists())
                pid = int(pid_file.read_text())
                process.send_signal(signal.SIGTERM)
                process.communicate(timeout=8)
                self.assertEqual(process.returncode, 0)
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()


if __name__ == "__main__":
    unittest.main()
