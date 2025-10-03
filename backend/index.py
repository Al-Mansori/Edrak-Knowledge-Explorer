# index.py
import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.vector_stores import SimpleVectorStore
import shutil

import re

from tqdm import tqdm
try:
    import yaml  # optional: for YAML frontmatter if you have it
except Exception:
    yaml = None

# --- NEW/UPDATED IMPORTS (add these near your other imports) ---
from llama_index.core.indices.knowledge_graph import KnowledgeGraphIndex
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.core.query_engine import RetrieverQueryEngine, RouterQueryEngine, SubQuestionQueryEngine, TransformQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.core.selectors import MultiSelection
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.prompts import PromptTemplate
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

from dotenv import load_dotenv


load_dotenv()

# LlamaIndex (latest API)
from llama_index.core import (
    Document,
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter

# Google Gemini adapters (you can override Settings in your main file if you want)
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# For table HTML → text
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


# ----------------------------
# Settings / Defaults
# ----------------------------

DEFAULT_CHUNK_SIZE = 5012
DEFAULT_CHUNK_OVERLAP = 120

def _ensure_settings():
    """Set sensible defaults for Settings if not already configured."""
    Settings.llm = GoogleGenAI(model="gemini-2.5-flash-lite")
    Settings.embed_model = GoogleGenAIEmbedding(
        model_name="models/embedding-001",
        embed_batch_size=100
    )


# ----------------------------
# Parsing helpers
# ----------------------------

def _resolve_asset_path(content_list_dir: Path, rel_path: str) -> str:
    """
    Resolve image/table asset path like 'images/abc.jpg' relative to dataset root.
    content_list_dir is usually .../dataset/content_list
    assets live at .../dataset/images
    """
    if rel_path.startswith(("http://", "https://", "/")):
        return rel_path
    dataset_root = content_list_dir.parent
    return str((dataset_root / rel_path).as_posix())

def _html_to_text(html: str) -> str:
    if not html:
        return ""
    if BeautifulSoup is None:
        # Fallback if bs4 not installed
        return (
            html.replace("<br>", "\n")
                .replace("<br/>", "\n")
                .replace("</td>", "\t")
                .replace("</th>", "\t")
                .replace("</tr>", "\n")
                .replace("<td>", " ")
                .replace("<th>", " ")
                .replace("&nbsp;", " ")
        )
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def _text_from_item(item: Dict[str, Any], content_list_dir: Path) -> Optional[Document]:
    itype = item.get("type")
    page = item.get("page_idx")
    base_meta = {"source_type": itype, "page_idx": page,}

    if itype == "text":
        txt = (item.get("text") or "").strip()
        if not txt:
            return None
        text_level = item.get("text_level")
        meta = {**base_meta, "text_level": text_level}
        return Document(text=txt, metadata=meta)

    if itype == "image":
        cap_list = item.get("image_caption") or []
        caption = " ".join(cap_list).strip()
        img_path = item.get("img_path") or ""
        resolved = _resolve_asset_path(content_list_dir, img_path) if img_path else ""
        meta = {
            **base_meta,
            "image_path": resolved,
            "image_caption": caption,
            "image_footnote": " ".join(item.get("image_footnote", [])).strip(),
        }
        # Store caption as text for retrieval; keep path in metadata
        text = caption or f"Figure (no caption). Path: {resolved}"
        return Document(text=text, metadata=meta)

    if itype == "table":
        cap = " ".join(item.get("table_caption", [])).strip()
        body_html = item.get("table_body") or ""
        body_text = _html_to_text(body_html)
        foot = " ".join(item.get("table_footnote", [])).strip()
        img_path = item.get("img_path") or ""
        resolved = _resolve_asset_path(content_list_dir, img_path) if img_path else ""
        meta = {
            **base_meta,
            "table_caption": cap,
            "table_footnote": foot,
            "table_image_path": resolved,
        }
        # Make a compact textual representation for retrieval
        text_bits = []
        if cap:  text_bits.append(f"Table: {cap}")
        if body_text: text_bits.append(body_text)
        if foot: text_bits.append(f"Footnote: {foot}")
        if resolved: text_bits.append(f"(table image: {resolved})")
        text = "  ".join(text_bits).strip() or "Table (no content)"
        return Document(text=text, metadata=meta)

    # Ignore formulas or unknowns
    return None


# ----------------------------
# Public API
# ----------------------------

def load_documents_from_content_lists(content_list_dir: str) -> List[Document]:
    """
    Reads every JSON file under content_list/ and converts items into Documents.
    content_list_dir: path to the 'content_list' folder.
    """
    cdir = Path(content_list_dir)
    assert cdir.exists(), f"content_list dir not found: {content_list_dir}"

    docs: List[Document] = []
    json_files = sorted(cdir.glob("*.json"))
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            # some exports are a dict with 'items', others are a raw list
            items = data.get("items", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                continue

            for it in items:
                if not isinstance(it, dict):
                    continue
                if it.get("type") in ["formula", "image"]:
                    continue  # explicitly ignore
                doc = _text_from_item(it, cdir)
                if doc:
                    # stamp the source file for provenance
                    doc.metadata = {**doc.metadata, "filename": jf.name.split(".")[0]+".pdf"}
                    docs.append(doc)
        except Exception as e:
            print(f"[WARN] Failed parsing {jf.name}: {e}")

    return docs


def build_nodes(docs: List[Document],
                chunk_size: int = DEFAULT_CHUNK_SIZE,
                chunk_overlap: int = DEFAULT_CHUNK_OVERLAP):
    """Further chunk the already-chunked items to improve retrieval quality."""
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.get_nodes_from_documents(docs, show_progress=True)






def _persist_files_exist(persist_dir: str) -> bool:
    p = Path(persist_dir)
    return p.exists()


def build_or_load_index(content_list_dir: str,
                        persist_dir: str = "./.llamaindex_store",
                        rebuild: bool = False) -> VectorStoreIndex:
    """
    Build a fresh index (and persist) when:
      - rebuild=True, or
      - persist_dir missing/empty/incomplete
    Otherwise, load from storage.
    """
    _ensure_settings()

    need_build = rebuild or not _persist_files_exist(persist_dir)
    print(f"need_build: {need_build}")
    if not need_build:
        # Safe path: load
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        return load_index_from_storage(storage_context)

    # Build fresh
    Path(persist_dir).mkdir(parents=True, exist_ok=True)

    # 1) Parse → nodes
    docs = load_documents_from_content_lists(content_list_dir)
    print(f"Loaded {len(docs)} documents from content lists.")
    nodes = build_nodes(docs)

    # 2) Create EMPTY stores explicitly (prevents load attempts)
    storage_context = StorageContext.from_defaults(
        docstore=SimpleDocumentStore(),
        index_store=SimpleIndexStore(),
        vector_store=SimpleVectorStore(),
        persist_dir=persist_dir,
    )

    # 3) Build & persist
    index = VectorStoreIndex(nodes, storage_context=storage_context)
    index.storage_context.persist(persist_dir)
    print(f"Index built and persisted to {persist_dir}")
    return index


def load_index(persist_dir: str = "./.llamaindex_store") -> VectorStoreIndex:
    """Load an already persisted index; auto-rebuild if files are missing."""
    _ensure_settings()
    if not _persist_files_exist(persist_dir):
        raise FileNotFoundError(
            f"Index not found or incomplete in '{persist_dir}'. "
            "Call build_or_load_index(..., rebuild=True) first."
        )
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    return load_index_from_storage(storage_context)


def get_query_engine(index: VectorStoreIndex,
                     top_k: int = 5,
                     response_mode: str = "compact",
                     include_sources: bool = True,
                     only_file: Optional[str] = None):
    """
    Create a ready-to-use query engine.
    - Set 'only_file' to a content_list filename (e.g., 'paper_12.json') to restrict retrieval.
    """
    filters = None
    if only_file:
        filters = MetadataFilters(filters=[ExactMatchFilter(key="content_list_file", value=only_file)])

    return index.as_query_engine(
        similarity_top_k=top_k,
        response_mode=response_mode,
        include_sources=include_sources,
        filters=filters,
    )

# ----------------------------
# Markdown summary loader
# ----------------------------

_MD_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

def _parse_md_frontmatter(text: str):
    """
    Returns (meta_dict, body) if YAML frontmatter is present; otherwise ({}, original_text).
    Frontmatter is optional. If pyyaml isn't installed, we just strip it without parsing.
    """
    m = _MD_FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    body = text[m.end():]
    if yaml is None:
        return {}, body
    try:
        data = yaml.safe_load(raw) or {}
        return (data if isinstance(data, dict) else {}), body
    except Exception:
        return {}, body

def _extract_md_title(body: str) -> str:
    """
    Use the first ATX heading '# Title' as title if present, else empty string.
    """
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""

def load_documents_from_markdown_summaries(summary_dir: str) -> List[Document]:
    """
    Reads every .md/.markdown file under `summary_dir` and returns LlamaIndex Documents.
    Metadata set:
      - source_type: 'summary_md'
      - summary_file: filename
      - title: (from frontmatter 'title' or first '# ' heading)
      - any other frontmatter keys (author, year, doi, etc.) if present
    """
    sdir = Path(summary_dir)
    assert sdir.exists(), f"summary dir not found: {summary_dir}"

    docs: List[Document] = []
    for ext in ("*.md", "*.markdown"):
        for f in sorted(sdir.glob(ext)):
            try:
                raw = f.read_text(encoding="utf-8")
                fm, body = _parse_md_frontmatter(raw)
                title = fm.get("title") or _extract_md_title(body)

                meta = {
                    "source_type": "summary_md",
                    "summary_file": f.name.split(".")[0],
                    "title": title,
                }
                # merge the rest of frontmatter keys (non-destructive)
                for k, v in (fm or {}).items():
                    if k not in meta:
                        meta[k] = v

                text = body.strip()
                if not text:
                    continue
                docs.append(Document(text=text, metadata=meta))
            except Exception as e:
                print(f"[WARN] Failed parsing {f.name}: {e}")
    return docs

# ----------------------------
# KG helpers / API (NEW)
# ----------------------------


def build_or_load_kg_index(content_list_dir: str,
                           persist_dir: str = "./.llamaindex_store",
                           rebuild: bool = False,
                           max_triplets_per_chunk: int = 5) -> KnowledgeGraphIndex:
    """
    Build a Knowledge Graph index from your content_list JSON docs.
    Triplets are extracted via the configured LLM (Settings.llm).
    Persists a SimpleGraphStore under persist_dir/kg_store/.
    """
    _ensure_settings()

    os.makedirs(persist_dir, exist_ok=True)

    # If not rebuilding and KG store exists, load from storage
    has_kg = os.path.exists(os.path.join(persist_dir, "graph_store.json"))
    if not rebuild and has_kg:
        storage_context = StorageContext.from_defaults(
            persist_dir=persist_dir,
            graph_store=SimpleGraphStore(),
        )
        return KnowledgeGraphIndex.from_storage(storage_context=storage_context)

    # Build fresh KG
    docs = load_documents_from_content_lists(content_list_dir)
    nodes = build_nodes(docs)  # reuse your existing chunking

    storage_context = StorageContext.from_defaults(
        graph_store=SimpleGraphStore(),
    )

    kg_index = KnowledgeGraphIndex.from_documents(
        documents=[],  # we’ll insert nodes manually so chunking is respected
        storage_context=storage_context,
        max_triplets_per_chunk=max_triplets_per_chunk,
    )
    # Insert nodes (extracts triplets under the hood)
    kg_index.insert_nodes(nodes)
    kg_index.storage_context.persist(persist_dir)
    return kg_index


def load_document_from_markdown_file(md_path: str) -> Optional[Document]:
    """
    Load ONE markdown file into a LlamaIndex Document.
    Uses optional YAML frontmatter (title, etc.) if present.
    """
    p = Path(md_path)
    assert p.exists() and p.is_file(), f"markdown file not found: {md_path}"
    raw = p.read_text(encoding="utf-8")

    # Reuse your helpers if already defined
    fm, body = _parse_md_frontmatter(raw) if "_parse_md_frontmatter" in globals() else ({}, raw)
    title = (fm.get("title") if fm else None) or (_extract_md_title(body) if "_extract_md_title" in globals() else "")

    meta = {
        "source_type": "summary_md",
        "summary_file": p.name,
        "title": title,
    }
    if isinstance(fm, dict):
        for k, v in fm.items():
            if k not in meta:
                meta[k] = v

    body = body.strip()
    if not body:
        return None
    return Document(text=body, metadata=meta)


def build_or_load_kg_index_from_markdown_file(
    md_path: str,
    persist_dir: Optional[str] = None,
    rebuild: bool = False,
    max_triplets_per_chunk: int = 5,
) -> KnowledgeGraphIndex:
    """
    Build/load a Knowledge Graph from a SINGLE Markdown file.
    Persists to: {persist_dir}/graph_store.json
    If persist_dir is None, defaults to ./.kg_single/<file_stem>
    """
    _ensure_settings()

    # Default persist dir derived from filename
    if persist_dir is None:
        stem = Path(md_path).stem
        persist_dir = os.path.join(".",".kg_single", stem)

    os.makedirs(persist_dir, exist_ok=True)

    graph_path = os.path.join(persist_dir, "graph_store.json")
    has_kg = os.path.exists(graph_path)

    # Fast path: load if present and not rebuilding
    if has_kg and not rebuild:
        storage_context = StorageContext.from_defaults(
            persist_dir=persist_dir
        )
        return load_index_from_storage(storage_context=storage_context)

    # Build fresh from the one markdown file
    doc = load_document_from_markdown_file(md_path)
    if doc is None:
        raise ValueError(f"No text content found in markdown: {md_path}")

    # Chunk and prepare nodes
    nodes: List = build_nodes([doc])  # uses your DEFAULT_CHUNK_SIZE/OVERLAP

    storage_context = StorageContext.from_defaults(
        graph_store=SimpleGraphStore(persist_path=persist_dir)
    )

    print("Building graph index from single markdown…")
    kg_index = KnowledgeGraphIndex.from_documents(
        documents=[],  # insert nodes manually to honor your chunking
        storage_context=storage_context,
        max_triplets_per_chunk=max_triplets_per_chunk,
        show_progress=True,
    )

    # Insert nodes (simple batched insert; tweak batch_size if you like)
    for node in tqdm(nodes, desc="Inserting nodes"):
        kg_index.insert_nodes([node])

    kg_index.storage_context.persist(persist_dir)
    print(f"KG (single markdown) built and persisted to {persist_dir}")
    return kg_index
# ----------------------------
# KG from Markdown summaries
# ----------------------------

def build_or_load_kg_index_from_markdown(summary_dir: str,
                                         persist_dir: str = "./.kg_from_summary",
                                         rebuild: bool = False,
                                         max_triplets_per_chunk: int = 10,
                                         kg_namespace: str = "kg_from_summary") -> KnowledgeGraphIndex:
    """
    Build/load a Knowledge Graph from Markdown summaries.
    Persists to: {persist_dir}/{kg_namespace}/graph_store.json
    """
    _ensure_settings()
    os.makedirs(persist_dir, exist_ok=True)


    has_kg = os.path.exists(os.path.join(persist_dir, "graph_store.json"))
    if not rebuild and has_kg:
        storage_context = StorageContext.from_defaults(
            persist_dir=persist_dir,
        )
        return load_index_from_storage(storage_context=storage_context)

    # Build fresh from markdown docs
    md_docs = load_documents_from_markdown_summaries(summary_dir)
    nodes = build_nodes(md_docs)

    storage_context = StorageContext.from_defaults(
        graph_store=SimpleGraphStore(persist_path=persist_dir),
    )

    print("Building graph index..")
    kg_index = KnowledgeGraphIndex.from_documents(
        documents=[],  # we insert nodes to honor your chunking
        storage_context=storage_context,
        max_triplets_per_chunk=max_triplets_per_chunk,
        show_progress=True,
    )
    print(f'Inserting {(len(nodes))} nodes into kg')
    for node in tqdm(nodes, desc="Inserting nodes"):
        kg_index.insert_nodes([node])
    print("Inserted")
    kg_index.storage_context.persist(persist_dir)
    print(f"KG (markdown) built and persisted to {persist_dir}")
    return kg_index


# ----------------------------
# CLI (optional)
# ----------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build or load a persistent LlamaIndex from content_list JSON files.")
    parser.add_argument("--content_list_dir", type=str, required=True, help="Path to dataset/content_list directory")
    parser.add_argument("--persist_dir", type=str, default="./.llamaindex_store", help="Directory to persist index")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild instead of loading existing index")
    parser.add_argument("--query", type=str, default="", help="Optional one-off query to test retrieval")
    parser.add_argument("--top_k", type=int, default=5, help="Top-K nodes to retrieve")
    args = parser.parse_args()

    idx = build_or_load_index(args.content_list_dir, args.persist_dir, rebuild=args.rebuild)

    if args.query:
        engine = get_query_engine(idx, top_k=args.top_k)
        resp = engine.query(args.query)
        print("\n=== Answer ===")
        print(resp.response)
        print("\n=== Sources ===")
        for s in resp.source_nodes:
            preview = s.node.get_content()[:160].replace("\n", " ")
            print(f"- {s.metadata.get('content_list_file','?')} | {s.metadata.get('source_type')} | p{ s.metadata.get('page_idx') } | score={s.score:.2f}")
            print(f"  {preview}…")