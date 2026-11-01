"""Render a private Railway config patch; never contacts Railway or prints secrets.

Inventory JSON: {"Postgres":"service-id", "api":"...", "worker":"...",
"mock-actions":"...", "web":"..."}. Output stays outside tracked source.
"""
import argparse
import json
import os
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse


def render(inventory, origin, revision, environment):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Use the full tested Git commit SHA")
    url = urlparse(origin)
    if url.scheme != "https" or not url.hostname or url.path or url.query or url.fragment:
        raise ValueError("Use the web service's HTTPS origin without a trailing slash")
    services = json.loads(Path(__file__).with_name("railway-services.json").read_text())
    if set(inventory) != set(services) or len(set(inventory.values())) != 5:
        raise ValueError("Inventory must contain five unique exact service IDs")
    for value in inventory.values():
        if not re.fullmatch(r"[0-9a-f-]{36}", value):
            raise ValueError("Inventory values must be service UUIDs")
    common = {
        "DATABASE_URL": "${{Postgres.DATABASE_URL}}",
        "APP_ORIGIN": origin,
        "DEMO_LOGIN_TOKEN": secrets.token_urlsafe(24),
        "SESSION_SECRET": secrets.token_urlsafe(48),
        "MOCK_ACTION_SECRET": secrets.token_urlsafe(32),
        "MOCK_ACTION_BASE_URL": "http://${{mock-actions.RAILWAY_PRIVATE_DOMAIN}}:8001",
        "SECURE_COOKIES": "true",
        "AI_PROVIDER": "mock",
        "AI_MODEL": "mock-policy-v1",
        "EMBEDDING_PROVIDER": "mock",
        "EMBEDDING_MODEL": "mock-hash-v1",
        "EMBEDDING_DIMENSION": "64",
        "REVISION": revision,
    }
    services["Postgres"]["variables"]["POSTGRES_PASSWORD"] = secrets.token_urlsafe(40)
    for name, service in services.items():
        if name in {"api", "worker", "mock-actions"}:
            service["variables"].update(common)
        if name != "Postgres" and environment == "staging":
            service["source"] = {
                "repo": "praveen202105/trustdesk", "branch": "main",
                "checkSuites": True, "commitSha": revision,
            }
        service["variables"] = {key: {"value": value} for key, value in service["variables"].items()}
    return {"services": {inventory[name]: service for name, service in services.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--environment", choices=["staging", "production"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    patch = render(json.loads(args.inventory.read_text()), args.origin, args.revision, args.environment)
    # Exclusive creation prevents accidental secret rotation on a repeat command.
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as file:
        json.dump(patch, file, indent=2)
        file.write("\n")
    print("Private config written; no infrastructure has been changed.")


if __name__ == "__main__":
    main()
