"""Check deployment isolation without contacting Railway or spending money."""
import json
import stat
import subprocess
import tempfile
import uuid
from pathlib import Path

from render_config import render

inventory = {name: str(uuid.uuid4()) for name in ["Postgres", "api", "worker", "mock-actions", "web"]}
staging = render(inventory, "https://staging.example.com", "a" * 40, "staging")["services"]
production = render(inventory, "https://production.example.com", "a" * 40, "production")["services"]
for name in ["api", "worker", "mock-actions", "web"]:
    assert staging[inventory[name]]["source"]["checkSuites"] is True
    assert "source" not in production[inventory[name]]
for key in ["DEMO_LOGIN_TOKEN", "SESSION_SECRET", "MOCK_ACTION_SECRET"]:
    values = [staging[inventory[name]]["variables"][key]["value"] for name in ["api", "worker", "mock-actions"]]
    assert len(set(values)) == 1
    assert values[0] != production[inventory["api"]]["variables"][key]["value"]
for origin in ["http://example.com", "https://example.com/path", "https://example.com?secret=1"]:
    try:
        render(inventory, origin, "a" * 40, "staging")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid origin accepted")
with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    (folder / "inventory.json").write_text(json.dumps(inventory))
    args = ["python3", str(Path(__file__).with_name("render_config.py")), "--inventory", str(folder / "inventory.json"), "--origin", "https://example.com", "--revision", "a" * 40, "--environment", "staging", "--output", str(folder / "private.json")]
    assert subprocess.run(args, capture_output=True).returncode == 0
    assert stat.S_IMODE((folder / "private.json").stat().st_mode) == 0o600
    assert subprocess.run(args, capture_output=True).returncode != 0
print("Deployment config checks passed; no cloud mutation performed")
