from pathlib import Path
import re
root = Path(__file__).resolve().parents[1]
for p in root.glob("*.md"):
    for link in re.findall(r"\]\(([^)]+)\)", p.read_text()):
        if not link.startswith(("http:", "https:", "#", "/")):
            assert (p.parent / link.split("#")[0]).exists(), (p.name, link)
print("Root documentation links valid")
