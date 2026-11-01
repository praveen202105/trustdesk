import argparse
import json
from pathlib import Path

from .config import settings
from .db import SessionLocal
from .ingest import ingest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["import-data", "index-knowledge"])
    parser.add_argument("--directory", default=settings.data_dir)
    args = parser.parse_args()
    with SessionLocal.begin() as session:
        if args.command == "import-data":
            result = ingest(session, Path(args.directory))
        else:
            from .knowledge import index_knowledge

            result = {"indexed_chunks": index_knowledge(session)}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
