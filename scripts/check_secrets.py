"""Focused scan of tracked text; never prints matching credential values."""
import re
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(["git","ls-files","-z"],cwd=root).decode().split("\0")
patterns=[r"gh[pousr]_[A-Za-z0-9]{30,}",r"sk-(?:proj-)?[A-Za-z0-9_-]{30,}",r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"]
issues=[]
for name in paths:
    if not name:
        continue
    if Path(name).name==".env" or (Path(name).name.startswith(".env.") and Path(name).name!=".env.example"):
        issues.append(name+": environment file must not be tracked")
    try:
        text=(root/name).read_text()
    except (UnicodeError,FileNotFoundError):
        continue
    if any(re.search(pattern,text) for pattern in patterns):
        issues.append(name+": possible credential")
if issues:
    raise SystemExit("\n".join(issues))
print("Tracked-file credential scan passed (heuristic; not a full secret-audit guarantee)")
