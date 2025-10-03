# kg_file_endpoints.py
from __future__ import annotations
from typing import Any, Dict, Optional
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# --- Utils to normalize output ---
def _nx_to_node_link(G: nx.Graph) -> Dict[str, Any]:
    data = json_graph.node_link_data(G)
    for n in data["nodes"]:
        n.setdefault("label", n.get("id"))
        node_id = n["id"]
        n.setdefault("degree", int(G.degree[node_id]) if G.has_node(node_id) else 0)
    for i, e in enumerate(data["links"]):
        e.setdefault("id", f"e{i}")
        if "relation" in e:
            e.setdefault("label", e["relation"])
    return {"nodes": data["nodes"], "edges": data["links"]}

def _filtered_graph(G: nx.Graph, q: Optional[str], min_degree: int, max_nodes: int) -> nx.Graph:
    H = G.copy()
    if min_degree > 0:
        H.remove_nodes_from([n for n in list(H.nodes) if H.degree[n] < min_degree])
    if q:
        ql = q.lower()
        H.remove_nodes_from([
            n for n, d in list(H.nodes(data=True))
            if ql not in str(n).lower() and ql not in str(d.get("label", "")).lower()
        ])
    if H.number_of_nodes() > max_nodes and H.number_of_nodes() > 0:
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
        rows.append({
            "subject": u,
            "relation": d.get("relation") or d.get("label"),
            "object": v,
            **({k: v for k, v in d.items() if k not in {"relation", "label"}}),
        })
    return rows

# --- Response models (just for docs) ---
class NodeLinkGraph(BaseModel):
    nodes: list[Dict[str, Any]]
    edges: list[Dict[str, Any]]

class TripletsPage(BaseModel):
    count: int
    skip: int
    limit: int
    items: list[Dict[str, Any]]

class KGFileEntry(BaseModel):
    file: str
    stem: str
    persist_dir: Optional[str] = None
    nodes: Optional[int] = None
    edges: Optional[int] = None

# --- Router factory ---
def create_kg_file_router(
    *,
    get_index_by_file,  # Callable[[str], KnowledgeGraphIndex | None]
    list_files,         # Callable[[], list[tuple[str, str]]] -> [(file_name, persist_dir)]
    prefix: str = "/kg/file",
) -> APIRouter:
    """
    Expose per-file KG graph endpoints. The app must supply:
      - get_index_by_file(file_name) -> current KG index (or None)
      - list_files() -> list of (file_name, persist_dir) available
    """
    router = APIRouter(prefix=prefix, tags=["knowledge-graph (per-file)"])

    @router.get("/list", response_model=list[KGFileEntry])
    def get_files():
        out: list[KGFileEntry] = []
        for file_name, persist_dir in list_files():
            idx = get_index_by_file(file_name)
            nodes = edges = None
            if idx is not None:
                G = idx.get_networkx_graph()
                nodes, edges = G.number_of_nodes(), G.number_of_edges()
            out.append(KGFileEntry(
                file=file_name,
                stem=Path(file_name).stem,
                persist_dir=persist_dir,
                nodes=nodes,
                edges=edges,
            ))
        return out

    @router.get("/node-link", response_model=NodeLinkGraph)
    def node_link(
        file: str = Query(..., description="Markdown filename (e.g., paper_12.md)"),
        query: Optional[str] = Query(None, description="Filter nodes by substring"),
        min_degree: int = Query(0, ge=0),
        max_nodes: int = Query(2000, ge=1, le=20000),
    ):
        idx = get_index_by_file(file)
        if idx is None:
            raise HTTPException(404, f"No KG index loaded for file '{file}'")
        G = idx.get_networkx_graph()
        H = _filtered_graph(G, query, min_degree, max_nodes)
        return _nx_to_node_link(H)

    @router.get("/neighbors", response_model=NodeLinkGraph)
    def neighbors(
        file: str = Query(..., description="Markdown filename (e.g., paper_12.md)"),
        center: str = Query(..., description="Center node id"),
        depth: int = Query(1, ge=1, le=4, description="Hop radius"),
        max_nodes: int = Query(500, ge=1, le=5000),
    ):
        idx = get_index_by_file(file)
        if idx is None:
            raise HTTPException(404, f"No KG index loaded for file '{file}'")
        G = idx.get_networkx_graph()
        H = _ego_subgraph(G, center, depth, max_nodes)
        return _nx_to_node_link(H)

    @router.get("/triplets", response_model=TripletsPage)
    def triplets(
        file: str = Query(..., description="Markdown filename (e.g., paper_12.md)"),
        skip: int = Query(0, ge=0),
        limit: int = Query(200, ge=1, le=2000),
    ):
        idx = get_index_by_file(file)
        if idx is None:
            raise HTTPException(404, f"No KG index loaded for file '{file}'")
        G = idx.get_networkx_graph()
        trips = _derive_triplets_from_edges(G)
        total = len(trips)
        page = trips[skip : skip + limit]
        return TripletsPage(count=total, skip=skip, limit=limit, items=page)

    return router
