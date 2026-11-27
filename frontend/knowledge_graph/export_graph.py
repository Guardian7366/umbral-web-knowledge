"""Regenerate the distributable graph from the pinned historical Git object."""
import argparse
import json
from pathlib import Path

from graph_adapter import load


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    graph, drawing_only = load(args.repo)
    if graph["counts"] != {"nodes": 27, "edges": 15} or len(drawing_only) != 9:
        raise SystemExit("Unexpected historical graph inventory")
    args.destination.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\r\n")
