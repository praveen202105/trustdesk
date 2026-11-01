import argparse
import json
from pathlib import Path

from .config import settings
from .db import SessionLocal
from .ingest import ingest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["import-data", "index-knowledge", "evaluate"])
    parser.add_argument("--directory", default=settings.data_dir)
    parser.add_argument("--suite", choices=["provided"], default="provided")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.command == "evaluate":
        from .evaluation import evaluate_sync

        result = evaluate_sync(SessionLocal)
        serialized = json.dumps(result, indent=2)
        if args.output:
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(serialized + "\n")
        print(serialized)
        return
    with SessionLocal.begin() as session:
        if args.command == "import-data":
            result = ingest(session, Path(args.directory))
        else:
            from .knowledge import index_knowledge

            result = {"indexed_chunks": index_knowledge(session)}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
