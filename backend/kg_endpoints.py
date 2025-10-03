# kg_endpoints.py
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol, Tuple
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import networkx as nx
from networkx.readwrite import json_graph


# -------- Provider protocol (how we get the graph) --------
class KGProvider(Protocol):
    def get_graph(self) -> nx.Graph: ...


class KGFrozenGraph:
    """Wrap a prebuilt NetworkX graph."""
    def __init__(self, graph: nx.Graph):
        self._G = graph

    def get_graph(self) -> nx.Graph:
        # Return a copy so callers can safely mutate
        return self._G.copy()


class KGFromLlamaIndex:
    """
    Wrap a LlamaIndex KnowledgeGraphIndex via a callable
    that returns the current index (e.g., app.state.KG_INDEX).
    """
    def __init__(self, get_index: Callable[[], Any]):
        self._get_index = get_index

    def get_graph(self) -> nx.Graph:
        idx = self._get_index()
        if idx is None:
            raise HTTPException(503, "KG index not loaded")
        # Uses: kg_index.get_networkx_graph()
        return idx.get_networkx_graph()


# -------- Pydantic response models (lightweight) --------
class NodeModel(BaseModel):
    id: str
    label: Optional[str] = None
    degree: Optional[int] = None
    # you can add more fields (types, etc.) dynamically in dict payload


class EdgeModel(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None
    # you can add more edge metadata dynamically in dict payload


class NodeLinkGraph(BaseModel):
    nodes: list[Dict[str, Any]]
    edges: list[Dict[str, Any]]


class TripletsPage(BaseModel):
    count: int
    skip: int
    limit: int
    items: list[Dict[str, Any]]


class KGStats(BaseModel):
    nodes: int
    edges: int
    connected_components: int


# -------- Utilities --------
def _nx_to_node_link(G: nx.Graph) -> Dict[str, Any]:
    """
    Convert a NetworkX graph to a Cytoscape/Sigma/D3-friendly node-link JSON.
    Renames 'links' -> 'edges' and normalizes fields.
    """
    data = json_graph.node_link_data(G)

    # Normalize nodes: ensure id/label/degree
    for n in data["nodes"]:
        n.setdefault("label", n.get("id"))
        node_id = n["id"]
        n.setdefault("degree", int(G.degree[node_id]) if G.has_node(node_id) else 0)

    # Normalize edges: ensure id + label (from 'relation' if present)
    for i, e in enumerate(data["links"]):
        e.setdefault("id", f"e{i}")
        if "relation" in e:
            e.setdefault("label", e["relation"])

    return {"nodes": data["nodes"], "edges": data["links"]}


def _filtered_graph(
    G: nx.Graph,
    q: Optional[str],
    min_degree: int,
    max_nodes: int,
) -> nx.Graph:
    """
    Basic server-side filtering:
      - remove nodes with degree < min_degree
      - substring match on node id or label
      - downsample to largest CCs until <= max_nodes
    """
    H = G.copy()

    if min_degree > 0:
        H.remove_nodes_from([n for n in list(H.nodes) if H.degree[n] < min_degree])

    if q:
        ql = q.lower()
        H.remove_nodes_from(
            [
                n
                for n, d in list(H.nodes(data=True))
                if ql not in str(n).lower()
                and ql not in str(d.get("label", "")).lower()
            ]
        )

    if H.number_of_nodes() > max_nodes and H.number_of_nodes() > 0:
        # Keep largest connected components first
        comps = sorted(nx.connected_components(H), key=len, reverse=True)
        keep = set()
        for c in comps:
            if len(keep) + len(c) > max_nodes:
                break
            keep.update(c)
        H = H.subgraph(keep).copy()

    return H


def _ego_subgraph(G: nx.Graph, center: str, depth: int, max_nodes: int) -> nx.Graph:
    if center not in G:
        raise HTTPException(404, f"Center node '{center}' not found")
    nodes = {center}
    frontier = {center}
    for _ in range(depth):
        nxt = set()
        for u in frontier:
            nxt.update(G.neighbors(u))
        nodes |= nxt
        frontier = nxt
        if len(nodes) >= max_nodes:
            break
    return G.subgraph(list(nodes)[:max_nodes]).copy()


def _derive_triplets_from_edges(G: nx.Graph) -> list[Dict[str, Any]]:
    rows = []
    for u, v, d in G.edges(data=True):
        rows.append(
            {
                "subject": u,
                "relation": d.get("relation") or d.get("label"),
                "object": v,
                **({k: v for k, v in d.items() if k not in {"relation", "label"}}),
            }
        )
    return rows


# -------- Router factory --------
def create_kg_router(provider: KGProvider, prefix: str = "/kg") -> APIRouter:
    """
    Create a router exposing knowledge-graph endpoints under `prefix`.
    """
    router = APIRouter(prefix=prefix, tags=["knowledge-graph"])

    @router.get("/node-link", response_model=NodeLinkGraph)
    def get_node_link(
        query: Optional[str] = Query(None, description="Filter nodes by substring"),
        min_degree: int = Query(0, ge=0),
        max_nodes: int = Query(2000, ge=1, le=20000),
    ):
        G = provider.get_graph()
        H = _filtered_graph(G, query, min_degree, max_nodes)
        return _nx_to_node_link(H)

    @router.get("/neighbors", response_model=NodeLinkGraph)
    def get_neighbors(
        center: str = Query(..., description="Center entity/node id"),
        depth: int = Query(1, ge=1, le=4, description="Hop radius"),
        max_nodes: int = Query(500, ge=1, le=5000),
    ):
        G = provider.get_graph()
        H = _ego_subgraph(G, center, depth, max_nodes)
        return _nx_to_node_link(H)

    @router.get("/triplets", response_model=TripletsPage)
    def get_triplets(
        skip: int = Query(0, ge=0),
        limit: int = Query(200, ge=1, le=2000),
    ):
        """
        Return raw triplets (subject, relation, object). If the provider is LlamaIndex,
        you can optionally expose a direct call to its triplet store; otherwise we derive
        from the NetworkX edges.
        """
        G = provider.get_graph()
        # Best-effort: try to call the underlying index if present
        trips = None
        # If the provider wraps llamaindex, you can add a method to fetch its triplets directly.
        # Here we just derive from edges:
        trips = _derive_triplets_from_edges(G)
        total = len(trips)
        page = trips[skip : skip + limit]
        return TripletsPage(count=total, skip=skip, limit=limit, items=page)

    @router.get("/stats", response_model=KGStats)
    def stats():
        G = provider.get_graph()
        return KGStats(
            nodes=G.number_of_nodes(),
            edges=G.number_of_edges(),
            connected_components=nx.number_connected_components(G),
        )

    return router
