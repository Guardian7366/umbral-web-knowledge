"""Read the pinned historical source through AST literals, with no author-code execution."""

import argparse
import ast
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess

REVISION = "28eee545412951218dd8c7de4392494fcacb0d09"
SOURCE = "src/graph.py"
FAMILY_GROUPS = {
    "Department": ("Interface Development", "Design and UX", "Creative Direction", "Project Management"),
    "Knowledge group": ("design_references", "creative_methods", "project_learnings"),
    "Concept": ("Prototype", "Reusable Components", "Visual Hierarchy", "Responsiveness",
                "Module Composition", "Ideation", "Visual Proposal Evaluation", "Concept Selection"),
    "Project example": ("Aula Clara Project", "Estudio Norte Project", "Mesa Abierta Project"),
}


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], encoding="utf-8")


def stable_id(prefix, *parts):
    serialized = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return f"{prefix}:{sha256(serialized.encode()).hexdigest()}"


def load(repo):
    blob = git(repo, "rev-parse", f"{REVISION}:{SOURCE}").strip()
    historical = git(repo, "show", f"{REVISION}:{SOURCE}")
    declarations = {}
    names = ("nodes", "edges", "internal_connections")
    for statement in ast.parse(historical).body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = statement.targets[0]
            if isinstance(target, ast.Name) and target.id in names:
                if target.id in declarations:
                    raise ValueError(f"Duplicate declaration: {target.id}")
                declarations[target.id] = statement.value
    node_dict = declarations["nodes"]
    if not isinstance(node_dict, ast.Dict):
        raise ValueError("Expected a literal node dictionary")
    keys = [ast.literal_eval(key) for key in node_dict.keys]
    if len(keys) != len(set(keys)) or not all(isinstance(key, str) and key for key in keys):
        raise ValueError("Invalid or duplicate original node key")
    catalog_rows = json.loads((repo / "data/catalog.json").read_text(encoding="utf-8"))
    catalog = {entry["id"]: entry for entry in catalog_rows}
    if len(catalog) != len(catalog_rows) or not set(catalog).issubset(keys):
        raise ValueError("Catalog IDs do not match historical graph")

    families = {key: family for family, members in FAMILY_GROUPS.items() for key in members}
    families.update({key: "Document" for key in catalog})
    if set(families) != set(keys):
        raise ValueError("Unclassified historical node keys")

    nodes = {}
    for key in keys:
        document = catalog.get(key)
        nodes[key] = {
            "id": stable_id("node", key), "originalKey": key, "family": families[key],
            "label": key.replace("_", " ").capitalize() if families[key] == "Knowledge group" else key,
            "documentId": key if document else None,
            "metadata": {"catalogTitle": document["title"], "catalogCategory": document["category"]}
            if document else {},
        }
    edges = []
    pairs = set()
    for source, target, verb, *_drawing in ast.literal_eval(declarations["edges"]):
        if source not in nodes or target not in nodes or (source, target) in pairs:
            raise ValueError(f"Invalid endpoint or repeated DiGraph pair: {source}, {target}")
        if not isinstance(verb, str) or not verb.strip():
            raise ValueError("Invalid edge label")
        pairs.add((source, target))
        edges.append({"id": stable_id("edge", source, verb, target), "source": nodes[source]["id"],
                      "target": nodes[target]["id"], "verb": verb, "directed": True})
    graph = {
        "schemaVersion": "0.1.0", "source": {"commit": REVISION, "path": SOURCE, "blob": blob},
        "counts": {"nodes": len(nodes), "edges": len(edges)}, "nodes": list(nodes.values()), "edges": edges,
    }
    return graph, ast.literal_eval(declarations["internal_connections"])


def sample(graph):
    keys = ("Design and UX", "Prototype", "Reusable Components")
    chosen = {node["originalKey"]: node for node in graph["nodes"] if node["originalKey"] in keys}
    nodes = [chosen[key] for key in keys]
    ids = [node["id"] for node in nodes]
    edges = [edge for edge in graph["edges"] if edge["source"] in ids and edge["target"] in ids]
    if {(edge["source"], edge["verb"], edge["target"]) for edge in edges} != {
        (ids[0], "creates", ids[1]), (ids[1], "generates", ids[2]),
    }:
        raise ValueError("The historical sample no longer matches its two expected relations")
    return {
        **graph, "nodes": nodes, "edges": edges,
        "counts": {"nodes": len(nodes), "edges": len(edges)}, "parentCounts": graph["counts"],
    }


def evidence(repo):
    graph, auxiliary = load(repo)
    originals = {node["id"]: node["originalKey"] for node in graph["nodes"]}
    linked = {edge[key] for edge in graph["edges"] for key in ("source", "target")}
    return {
        "graph": graph,
        "verifiableTriples": [[originals[edge["source"]], edge["verb"], originals[edge["target"]]]
                              for edge in graph["edges"]],
        "visualFamiliesProposed": dict(Counter(node["family"] for node in graph["nodes"])),
        "verbCounts": dict(Counter(edge["verb"] for edge in graph["edges"])),
        "isolated": [key for identifier, key in originals.items() if identifier not in linked],
        "drawingOnly": {
            "count": len(auxiliary), "segments": auxiliary,
            "historicalAttribute": "internal_connections",
        },
        "localOrigin": {
            "commit": git(repo, "rev-parse", "origin/main").strip(),
            "blob": git(repo, "rev-parse", f"origin/main:{SOURCE}").strip(),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(evidence(args.repo), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
