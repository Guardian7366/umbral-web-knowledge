"""Data and shared reader for the approved graph and local preview."""
import json
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from src.web.documents_archive import document_payload, render_original_reader


PREVIEW_SNAPSHOT = Path(__file__).with_name("graph_snapshot.json")
RELEASE_SNAPSHOT = Path(__file__).with_name("graph_release.json")
RELEASE_SHA256 = "7a5af51e84ef2abeda043cf1e40c8fb98a5f457455a34fdfb5b5aa9da44d0fe5"


@lru_cache(maxsize=2)
def load_graph(*, release=True):
    snapshot = RELEASE_SNAPSHOT if release else PREVIEW_SNAPSHOT
    contents = snapshot.read_bytes()
    if release and sha256(contents).hexdigest() != RELEASE_SHA256:
        raise ValueError("Unrecognized release graph snapshot")
    graph = json.loads(contents.decode("utf-8"))
    nodes, edges = graph["nodes"], graph["edges"]
    ids = {node["id"] for node in nodes}
    pairs = {(edge["source"], edge["target"]) for edge in edges}
    if (
        graph["schemaVersion"] != "0.1.0"
        or not graph["source"]["commit"].startswith("28eee54")
        or graph["counts"] != {"nodes": 27, "edges": 15}
        or len(nodes) != len(ids) or len(ids) != 27
        or len(edges) != len(pairs) or len(pairs) != 15
        or any(edge["source"] not in ids or edge["target"] not in ids or not edge["verb"]
               or edge["directed"] is not True for edge in edges)
    ):
        raise ValueError("Invalid historical graph inventory")
    return graph


def original_response(action, documents, badge, symbol, *, release=True):
    """Resolve an explorer request by canonical ID and render the approved reader."""
    if not isinstance(action, dict) or not isinstance(action.get("token"), str):
        return None
    identifier = action.get("id")
    if not isinstance(identifier, str):
        return None
    try:
        valid = any(identifier == node["documentId"] for node in load_graph(release=release)["nodes"])
    except (OSError, ValueError, KeyError, TypeError):
        valid = False
    original = next((doc for doc in documents if valid and doc.doc_id == identifier), None)
    if original is None:
        return {
            "token": action["token"],
            "html": '<p role="alert">The original document is currently unavailable.</p>'
                    '<button type="button" data-graph-reader="retry">Retry</button>'
                    '<button type="button" data-graph-reader="back">Back to graph</button>',
        }
    return {
        "token": action["token"],
        "html": render_original_reader(document_payload(original), badge, symbol,
                                       actions="data-graph-reader", back="back",
                                       retry="retry", back_label="Back to graph"),
    }
